---
id: ADR-359
type: adr
title: "Dispatch assíncrono falha alto; quem cria estado pendente compensa"
status: Proposto
phase: "A40"
date: "2026-08-03"
relates_to:
  - "[[ADR-029-TQ]]"
  - "[[ADR-111]]"
  - "[[ADR-172]]"
  - "[[ADR-297]]"
  - "[[ADR-110]]"
supersedes:
  - "[[ADR-014]]"
superseded_by: []
aliases: ["ADR 359", "dispatch falha alto", "run orfao pending"]
tags:
  - type/adr
  - status/proposto
  - area/backend
  - area/pipeline
  - phase/a40
---

# ADR-359 — Dispatch assíncrono falha alto; quem cria estado pendente compensa

**Status:** Proposto (A40) • **Data:** 2026-08-03 • **Relaciona**
[[ADR-029-TQ]] (Celery + Redis), [[ADR-111]] (stateless rigoroso),
[[ADR-172]] (`failure_reason` + detector de runs travados), [[ADR-297]]
(guarda de redelivery), [[ADR-110]] (logging estruturado).
**Supersede** a cláusula de fallback de [[ADR-014]] (ver §Contexto).

## Contexto

Rodando o gate de paridade Go (F2) com Redis fora do ar, `make pipeline-run`
**retornou exit 0** e deixou o run `d0fd5f2a` em `pending` para sempre. Três
defeitos encadeados:

1. `start_pipeline_run` envolve o dispatch em `try/except Exception` e degrada
   para `threading.Thread(daemon=True)`. Em processo de vida curta
   (`run_workspace_pipeline.py`, que `make pipeline-run` usa) o thread morre
   junto com o processo, imediatamente após o dispatch.
2. Não há compensação: `_create_run` commita a linha `pending` e
   `start_pipeline_run` é chamado depois, sem `try/except`.
3. O órfão bloqueia todo disparo seguinte (`_check_no_active_run` + índice
   parcial `ux_pipeline_runs_ws_active`) com a mensagem "Cancele ou aguarde" —
   "aguarde" nunca resolve, porque não há nada para consumir a task.

O mecanismo não é regressão nova. Ele existe desde `6219acd5` (2026-04-14) e
tem cobertura formal residual: [[ADR-014]] §Fallback diz "Celery mantém thread
fallback se Redis indisponível" — cláusula que contradiz o próprio corpo daquela
ADR ("threads não sobrevivem a restart do servidor"). É essa cláusula, não a
decisão original já superseded por [[ADR-029-TQ]], que esta ADR supersede.

Dois achados do co-design que mudam o desenho:

- **O fallback duplica execução hoje.** `_dispatch_celery_task` faz `.delay()` e
  **depois** persiste `celery_task_id` em transação separada; o `try` do
  call-site envolve as duas. Enqueue OK + commit falho ⇒ a thread roda **e** a
  task está na fila. `_mark_run_started` só recusa status terminal, e `running`
  não é terminal ⇒ dois executores concorrentes sobre o mesmo `run_id`.
- **Nenhum teste exercita o fallback.** Os três testes que tocam o caminho
  patcham `start_pipeline_run` no call-site do use case. É código armado e não
  coberto.

Colateral: [[ADR-111]] §Contexto afirma "0 ocorrências de ... `threading.Thread`
em app code" e `STATELESS_AUDIT.md` §5 repete "nenhum resultado em app code". As
duas afirmações eram **falsas na data em que foram escritas** — o thread
precedia o audit em 6 dias. Não houve drift; nasceu errado, e ficou errado por
3,5 meses porque nada verificava a afirmação.

## Decisão

### 1. Dispatch falha alto; o fallback in-process é deletado

`_start_fallback_thread` é removido. `start_pipeline_run` levanta
`PipelineDispatchError` (tipado) e passa a `-> str`.

O argumento decisivo não é violar [[ADR-111]] — isso é sintoma. É que o thread
**transfere o dono do lifetime para um processo que não se comprometeu com ele**:
o CLI sai em `sys.exit`, o uvicorn recicla worker, e o Celery é justamente quem
tem contrato de sobrevivência (`acks_late`). Um executor sem dono é pior que
nenhum, porque produz sucesso reportado.

### 2. Compensação é do caller que executou a ação forward, uma por caller

Regra de saga. `start_pipeline_run` **não** transiciona estado — é porta de
dispatch. Compensação genérica no service seria uma regressão, porque os dois
callers mutaram estado diferente:

| caller | mutação forward | compensação correta |
| --- | --- | --- |
| `trigger_pipeline` | cria linha `pending` | `failed` + `failure_reason` |
| `resume_pipeline_run` | `needs_review`→`resuming` **e zera `paused_at_stage`** | **reverter** para `needs_review` restaurando `paused_at_stage` |

Marcar o resume como `failed` converteria pausa recuperável em run morto com o
ponto de pausa já perdido. Bônus: compensar no use case usa a mesma sessão async
que criou a linha, em vez de abrir `SyncSessionLocal` para escrever linha cuja
sessão async ainda está aberta no mesmo request.

### 3. O invariante é o par: `UPDATE` condicional × guarda de redelivery

Compensação **incondicional** é o footgun real. Se `.delay()` publicou e só o
ack falhou, a task **está** enfileirada; marcar `failed` + liberar o workspace
⇒ usuário dispara segundo run ⇒ dois workers escrevendo artefatos do mesmo
workspace. Compensação é `UPDATE ... WHERE status='pending'` com checagem de
`rowcount`, no padrão de `_flip_stuck_run_atomic`.

Com isso as duas ordens ficam seguras: compensação primeiro ⇒ o guard de
[[ADR-297]] recusa a redelivery; worker primeiro ⇒ `rowcount == 0`, compensação
no-op. **Este par é o invariante a testar**, não detalhe de implementação.

### 4. A fronteira de "dispatch falhou" exige pré-gerar o `task_id`

`celery_task_id` passa a ser gerado e persistido **antes** do `apply_async`. A
escrita do dispatcher era redundante (o worker grava em `_mark_run_started`),
então inverter a ordem não custa nada e compra dois invariantes:
`celery_task_id IS NULL` passa a significar de fato "dispatch nunca tentado", e
fecha a janela em que um run cancelado entre `.delay()` e a escrita não podia ser
revogado.

Só falha do **enqueue** compensa. Falha de escrita posterior é `logger.error` sem
propagar — a task está na fila, compensar ali seria errado.

O `try` envolve a chamada **inteira**, incluindo `_prepare_run_context` (hoje
fora dele): materialização de config/storage falha pela mesma porta e produz o
mesmo órfão. Dois motivos distintos, dois `failure_reason`.

### 5. Auto-cura no ponto de bloqueio — não cron, não endpoint novo

`_check_no_active_run`: se o run bloqueante é não-terminal, tem
`celery_task_id IS NULL` e é mais velho que o threshold, flippa para `failed` /
`dispatch_unconfirmed` (mesmo `UPDATE` condicional atômico) e deixa o novo run
seguir.

Roda exatamente no instante em que o usuário está sendo prejudicado, **não
depende de Redis**, e a concorrência já está resolvida (perdedor da corrida cai
no `IntegrityError` → `ConflictError`). Superfície de agendamento nova seria modo
de falha novo sem monitor que o observe.

### 6. Vocabulário de `failure_reason`: três valores, não um

- `dispatch_failed` — compensação síncrona; sabemos que o broker recusou.
- `run_setup_failed` — falha de `_prepare_run_context` (config/storage).
- `dispatch_unconfirmed` — varredura; só sabemos que ninguém reivindicou
  (provável morte do processo entre o INSERT e o dispatch).

São investigações e ações de runbook diferentes; colapsar num nome destrói o
sinal de postmortem.

### 7. Erro tipado → 503, e o log do broker é redigido

Propagar cru faz o cliente não distinguir "broker caiu, tente em 10s" de bug:
`ServiceUnavailableError` → 503 + `Retry-After`. Severidade `ERROR`, nunca
`CRITICAL` — falha de dispatch é sintoma; o incidente é "broker degradado", que
não é cognoscível de um call-site, e N CRITICALs por minuto de outage é fadiga
programada.

O log atual interpola `str(exc)` de erro de conexão, e `REDIS_URL` carrega
credencial em produção; a formatter redige por denylist de PII, não de URL com
senha. Passa a logar `type(exc).__name__` + host redigido.

### 8. Afirmação de audit sem gate é dívida, não garantia

`dev/check_stateless_primitives.py` — hard-fail desde a v1, em `pre-commit`
(dentro do Lint job; zero job novo de CI) — sobre o conjunto **fechado** de
primitivas nomeadas como proibidas em [[ADR-111]] §3, em `backend/app/**` +
`pipeline/**`. Allowlist por `(path, símbolo)` com justificativa por entrada, no
padrão de `dev/check_no_leak_field_consumers.py`; nunca por linha (bit-rot) nem
`# noqa` inline (torna o total incognoscível — e o defeito que estamos
consertando é "ninguém releu").

Isso **não** reabre a alternativa 2 de [[ADR-111]], que rejeitou lint para
**globais mutáveis** por falso-positivo (singleton legítimo é indistinguível de
dict acumulador por AST). Primitiva nomeada é a metade tratável.

O gate também assere que `STATELESS_AUDIT.md` menciona o path de cada entrada da
allowlist, fechando o loop doc↔código. E §5/§6 do audit **deixam de afirmar
"zero resultados"** e passam a apontar para o gate: afirmação que um gate
sustenta vale; contagem escrita à mão é passivo.

## Alternativas rejeitadas

- **Manter o fallback gateado por flag** — a flag cria segundo caminho de
  execução que ninguém testa (é literalmente o estado atual), e "processo curto"
  não é detectável de dentro do service. O fallback in-process legítimo já existe
  pronto (`task_always_eager`: mesma função, síncrona, caller dono do lifetime) e
  seu lugar é o CLI foreground, não o service — ver §Deferimentos.
- **Compensação genérica no service** — cobriria `resume` **errado**. Ver §2.
- **Reaper com predicado `pending AND celery_task_id IS NULL` sem §4** — na ordem
  atual um run legitimamente enfileirado pode ter a coluna NULL; com fila funda o
  reaper marcaria `failed` run legítimo, o worker depois recusaria por terminal, e
  o run seria descartado em silêncio com `failure_reason` mentiroso.
- **Cron de SO / endpoint em `ops.mathoms.ai`** — ver §5.
- **Threshold reusado de [[ADR-172]] (15min)** — aquele número está calibrado
  para *stage genuinamente lento*, semântica que não existe aqui. Env var própria,
  curta.

## Consequências

- A circularidade "o reaper mora no broker que caiu" **não intersecta** o modo de
  falha endereçado: a primeira linha (compensação síncrona) é write no Postgres e
  funciona com Redis fora; a varredura existe para "processo morreu entre INSERT e
  dispatch", que não correlaciona com broker fora.
- `-> str` mesmo com nenhum dos dois callers consumindo o retorno hoje (valor de
  log/teste). Regenerar `dev/code_style_baseline.json` (tem entradas para
  `start_pipeline_run` e `_start_fallback_thread`).
- `make update-openapi-snapshot`: handler de exceção não muda schema; diff só se
  `failure_reason` for exposto (ver Deferimentos).
- Débito nomeado, não corrigido aqui: há **3 sites `mark-then-dispatch`**
  (`pipeline_service`, `api/me.py`, `api/categorization_rules.py`). Os outros dois
  falham alto (bom) mas também não compensam a linha pendente — mesma classe,
  severidade menor.

## Deferimentos datados (2026-08-03)

Registrados aqui em vez de reservar ID de ADR (precedente [[ADR-356]]):

1. **Varredura de beat para órfão `pending`/`resuming`** estendendo
   `fin.detect_stuck_runs`. Condição de retomada: **§4 mergeado** (sem ele o
   predicado é inseguro) e o drift de enum de `pipelinerunstatus` resolvido — o
   tipo no DB não tem `resuming`, o que é escopo de **A40.l19**, não deste PR. O
   órfão em `resuming` é hoje o estado inescapável do sistema (invisível ao
   detector, `cancel_pipeline_run` recusa, `is_run_active` retorna `True` para
   sempre); `cancel_pipeline_run` cobrir `resuming` entra com essa varredura.
2. **Read path de `failure_reason`.** A coluna é write-only desde [[ADR-172]]:
   não está em `PipelineRunResponse` e o frontend não a lê, então a promessa
   "UI mostra mensagem honesta" nunca foi entregue. Custo: um campo +
   `make update-openapi-snapshot`.
3. **`docs/reference/runbooks/stuck_pipeline_runs.md`** cobrindo os três valores
   novos + `heartbeat_timeout` (que também nunca ganhou runbook). A bifurcação
   obrigatória: *broker fora ⇒ suba o broker, órfãos se curam no próximo trigger*
   vs. *worker vivo com fila funda ⇒ não cancele, espere*. Sem ela o operador
   cancela run legítimo.
4. **`--inline` no CLI via `task_always_eager`**, se algum dia houver demanda de
   rodar sem Redis. Foreground, operador quer o bloqueio, zero caminho novo.
5. **Copy da mensagem de bloqueio** (`_ACTIVE_RUN_MESSAGE`) → `product-designer`.
   Exigência que fica: nenhuma mensagem manda o usuário esperar por algo que
   nunca vai acontecer.
