---
id: ADR-441
type: adr
title: "Erro de banco cruza fronteira de persistência por shape, nunca por valor"
status: Decidido
date: "2026-10-08"
tags: [type/adr, status/decidido, area/backend, area/seguranca, area/observabilidade]
relates_to:
  - "[[ADR-068]]"
  - "[[ADR-110]]"
  - "[[ADR-111]]"
  - "[[ADR-231]]"
  - "[[ADR-273]]"
  - "[[ADR-357]]"
  - "[[ADR-371]]"
  - "[[ADR-404]]"
  - "[[ADR-435]]"
supersedes: []
superseded_by: []
amended_at: []
---

# ADR-441 — Erro de banco cruza fronteira de persistência por shape, nunca por valor

> `Decidido` em 2026-10-08 — co-desenho `sre-devops`, revisão `senior-cto`. **D1** entregue
> em #2081 (hot-fix), **D2** em #2094; a **D3** vem no PR seguinte.

## Contexto

Medido em 2026-10-08 em Postgres 16: `match_or_create` com `codigo_rfb='01-12'` levantou
`DataError`, e `str(exc)` trazia `[parameters: {...}]` com endereço e nome do imóvel. O
texto ia cru para `pipeline_stage_logs.errors` e para o canal do WS. Quatro medições
fizeram do defeito uma classe:

1. **O caminho não era o suspeito.** O `except` de `pipeline/orchestrator.py::_run_stage`
   engole a exceção do stage e devolve `StageResult.error = str(exc)`, sem teto — ela
   nunca chega a `_run_stage_with_retry`.
2. **O driver põe o valor no texto.** O psycopg 3 monta `str(orig)` com o
   `PQresultErrorMessage` inteiro. Medido ao vivo em PG 16, com `hide_parameters` ligado:
   o DETAIL do 23505 na chave natural traz nome e endereço, o 23502 traz a linha
   (`Failing row contains`), o 22P02 traz o valor na mensagem primária.
3. **O bind processor também.** Com `hide_parameters=True`, um `Numeric` que recebe texto
   sai `StatementError: (builtins.ValueError) could not convert string to float:
   'R$ 350.000,00'` — no SQLite do dogfood, hoje.
4. **"É `StatementError`?" deixa passar.** `PendingRollbackError` — sessão compartilhada
   pelos resolvers, envenenada por flush engolido — repete o texto original sem cadeia.

O dano maior é fora do DB — stdout do container, AOF do redis, fornecedor de OTel,
transcript de sessão de agente —, onde a eliminação do art. 18 da LGPD não alcança. O
CLAUDE.md pede "valor ofensor + shape" **e** proíbe logar dado sensível: quando o valor
pode ser PII, vale o segundo — a doutrina da [[ADR-404]] D4/D5.

## Decisão

**D1 — Engine nasce com `hide_parameters=True`.** Todo construtor fora de teste; gate AST
`dev/check_engine_hide_parameters.py` + teste comportamental sobre os objetos de
`database.py`. Corta o bound parameter em todo sink; **não** alcança o texto do driver
nem o do bind processor. Sem escape hatch: o dogfood roda sobre dado real.

**D2 — Texto de erro que cruza fronteira sai de um sanitizador único**,
`pipeline/observability/failure_text.py::describe_failure` (função pura sobre objeto vivo,
como o `redaction.py` da [[ADR-273]]):

- **Detecção** — raiz de módulo (`sqlalchemy`, `psycopg`, `asyncpg`, `sqlite3`) na MRO de
  **qualquer** elo: `__cause__`, `__context__` mesmo suprimido, membros de grupo. O
  conjunto é pinado por enumeração: toda classe exportada por `sqlalchemy.exc`,
  `sqlalchemy.orm.exc`, `psycopg.errors` e `sqlite3` é detectada. Só objeto vivo — texto já
  achatado (`str(e)` num dict, stderr repassado) fica fora; sanitiza quem tem o objeto.
- **Mensagem** — tipo do elo de topo (o tipo de domínio sobrevive), tipo do driver,
  sqlstate, identificadores de catálogo (`constraint`, `table`, `column`, `datatype`) e o
  marcador fixo `valores do banco omitidos`. Nenhum texto de driver nem de bind
  processor. Sem `schema_name`: é sempre `public` e casava `/schema/` no frontend.
- **Rótulo por sqlstate** (`57014` → statement timeout…) é compatibilidade de
  apresentação, subordinado à [[ADR-357]]: o backend nunca o lê; classe é `reason_class`.
- **Contrato** — traceback com frames e tipo, sem mensagem; nunca levanta; nunca
  `str()`/`repr()` em objeto do driver; sem cache ([[ADR-111]]). **Sem opt-out**:
  `raise X(msg) from None` não se distingue de lavagem (`raise X(f"{e}") from None`).
- **Fronteiras** — `except` do orchestrator (`StageResult.error`, evento OTel,
  `db_sqlstate`/`db_constraint` no `stage_error`); `pipeline/cli_run_stage.py::main` (corpo
  do 503 do shell Go); a borda do executor; o crash da task (`Task crashed:`); os
  `logger.exception` de commit de artefato (`exc_info=False` + shape, ADR-404 D5); e uma
  **Task base no app Celery inteiro** (`task_cls`, sobrescreve `__call__`), que cobre o
  log de falha, o result backend e o `on_failure` das 14 tasks. `Retry`, `Ignore`,
  `Reject` e `BaseException` fora de `Exception` passam intactos.
- **Frontend** — `pipelineErrorMessages.ts` ganha a PRIMEIRA regra, chaveada no marcador:
  statement timeout → mensagem de timeout; o resto → genérico da fase. O marcador é
  contrato Python ↔ TypeScript, com teste dos dois lados.

**D3 — Handler sanitiza o record, e o Celery não instala handler próprio.** Filtro por
objeto (`record.exc_info`, `record.args`, `record.msg`) nos nossos handlers e no
`StageLogTail`; receiver no sinal `celery.signals.setup_logging`. Medido: sem ele o root
do worker tem dois handlers, um fora do JSON e do filtro — e `worker_hijack_root_logger=False`
ainda deixa dois. Não espera o go-live: pelo item 3, o SQLite leva valor ao log hoje.

**D4 — OTLP só liga com scrub no exporter.** `SQLAlchemyInstrumentor` e
`CeleryInstrumentor` gravam o texto do driver por fora do nosso código.

**D5 — Matriz por PRODUTOR** — cobertura declarada é a medida ([[ADR-435]]):

| Superfície | Produtor | Coberto por |
|---|---|---|
| `stage_log.errors` e canal do WS | `except` do orchestrator; crash da task | D2 |
| | ramo `SystemExit` (`tail.first_error_message`, já texto) | D3 |
| | `_summarize_per_doc_errors` (`str(e)` por documento) | deferido |
| `output_summary` | `traceback` da borda do executor | D2 |
| | `log_tail` (`StageLogTail`) | D3 |
| | `detail.errors[]` (soft-fail de stage) | deferido |
| span OTel do stage | orchestrator | D2 |
| span de auto-instrumentação | `SQLAlchemyInstrumentor`, `CeleryInstrumentor` | D4 |
| log de falha e result backend do Celery | Task base | D2 |
| log de retry do Celery (`Retry.exc`) | quem chama `self.retry(exc=…)` | deferido |
| log do worker/API (`exc_info`, `%s`) | call-sites de log | D3 |
| corpo do 503 do shell Go | `cli_run_stage` (`_fail`) | D2 |
| stderr do filho repassado pelo shell Go | `logChildStderr` (já texto) | D3 |
| `documents.error_message` ×3, `data_export_requests.error_message` | services | deferido |

Prova da D2: `tests/unit/pipeline/test_failure_text.py`,
`backend/tests/test_falha_de_stage_nao_publica_valor_do_banco.py`,
`backend/tests/test_task_base_do_celery_redige_erro_de_banco.py`,
`tests/test_cli_run_stage_redige_erro_de_banco.py` e
`frontend/tests/lib/pipelineErrorMessages.test.ts` — cada fronteira revertida sozinha
derruba o seu teste.

## Deferimentos datados (2026-10-08)

- **As linhas "deferido" da D5 e a D4.** Dono: o dono do repo, que abre a lane. Retomada:
  antes do go-live em Postgres com dado real. A D3 não é deferida — vem logo após a D2.

## Alternativas rejeitadas

- **Só D1.** Deixa o DETAIL do driver e o texto do bind processor.
- **Só D2.** Enumeração: o log fica fora, e cada sink novo reabre a classe.
- **Allowlist de sqlstate com primária "sem valor".** Depende de `lc_messages` e versão.
- **`isinstance(exc, StatementError)`.** Medido: `PendingRollbackError` escapa.
- **Decorator no `run` da task.** Medido: derruba `self.retry(exc=…)` e `autoretry_for`,
  que passam a ver só o tipo redigido.
- **`worker_hijack_root_logger=False`.** Medido: o root do worker segue com dois handlers.
- **Regex sobre `[parameters:`.** Fecha a sintaxe de hoje, não a classe.
- **Emenda à [[ADR-404]].** A §Fronteira dela põe o `stage_log` no plano de controle.

## Consequências

- Depuração por tipo, sqlstate, constraint e frames, com reprodução sintética.
- UX: o headline de falha de stage deixa de casar padrão por acidente — hoje um
  `[SQL: … api_key_encrypted …]` vira "PDF protegido por senha" ([[ADR-068]]).
- Mesma classe por outra porta, fora daqui: `pydantic.ValidationError` ecoa `input_value=`.
- Rows antigas com `[parameters:`/`DETAIL:` seguem em repouso até decisão do dono, a
  partir de contagem read-only; limpeza é UPDATE do texto, nunca DELETE, e só depois do
  deploy.
