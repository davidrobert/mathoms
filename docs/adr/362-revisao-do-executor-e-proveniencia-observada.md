---
id: ADR-362
type: adr
title: "Revisão do executor é proveniência de processo observada, não garantia de reprodutibilidade"
status: Proposto
phase: "A40"
date: "2026-08-05"
amended_at: ["2026-08-05", "2026-08-06"]
relates_to:
  - "[[ADR-343]]"
  - "[[ADR-311]]"
  - "[[ADR-291]]"
  - "[[ADR-241]]"
  - "[[ADR-111]]"
  - "[[ADR-360]]"
supersedes: []
superseded_by: []
aliases: ["ADR 362", "executor_revision", "proveniência de código do run"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/ci
  - phase/a40
---

# ADR-362 — Revisão do executor é proveniência de processo observada

> **Emenda 2026-08-05 (correção de premissa, não de decisão):** o §Contexto
> afirmava que *"em produção não há `.git` nem SHA assado, logo incidente não é
> atribuível a release"*. **Não existe produção** — o projeto roda só na máquina
> do dono, em dogfood e desenvolvimento. A decisão sobrevive inteira (foi
> derivada de realidades locais: worktrees, árvore suja, worker stale); o que
> cai é um argumento de escopo que eu usei para dizer que o problema era maior
> que o dogfood. Ver §Emenda 2026-08-05.

## Contexto

Um relatório é entregue e **não há como saber qual código o computou**. Três
relógios existem e nenhum é registrado no lugar que importa:

1. o commit que **computou** o relatório (o run) — nunca registrado;
2. o commit no início de uma rodada de review — registrado em
   `capture_report_render.py::_git_sha`, mas é provenance da **captura de
   screenshot**, coletada quando a review começa (que pode ser dias depois do
   run, porque a skill aceita `report_id` histórico);
3. o commit no fechamento da síntese — nunca registrado.

Consequências medidas, todas verificadas em código:

- **`pipeline_runs.config_snapshot`** existe desde a migration inicial, tem
  writer **só** em `backend/tests/factories/builders.py` e **0 de 109 rows**
  preenchidas. Coluna sem contrato e sem consumidor.
- **`pipeline_artifacts.schema_version`** tem writer
  (`db_artifact_store.py::_schema_version_token`) e **zero leitores** — é
  derivada de `stage`, logo redundante.
- Achado de review pode já ter sido corrigido em `main` entre o run e o
  fechamento da rodada, e **o dado bruto para checar isso não existe**.
- ~~Em produção não há `.git` nem SHA assado: **incidente não é atribuível a
  release**.~~ **Retirado pela emenda de 2026-08-05: não existe produção.**

O precedente correto não é nenhuma das colunas mortas: é
**`prompt_version`** ([[ADR-311]]), que nasceu para ser consultável e tem
leitor real (`dev/reextract_stale_e2_llm.py`, `WHERE prompt_version < target`).

## Decisão

### 1. O nome diz a garantia: `executor_revision`, não `code_version`

`*_version` nesta casa significa **contrato declarado com ritual de bump**
(`mc_version` da [[ADR-360]], `score_version`). Este campo é **observado**, da
família `seed_usado`/`n_simulacoes_usado`.

E `code_version` venderia garantia que o sistema não tem — mediu-se que **o
mesmo SHA produz output diferente** e que **SHA diferente produz output
idêntico** (cache de LLM).

### 2. Cláusula de honestidade (invariante desta ADR)

> `executor_revision` identifica o processo que executou o loop. **Não é
> condição suficiente de reprodutibilidade.** Cinco entradas medidas movem
> número monetário com **zero commits**: (a) `temperature=0.1` no parecer;
> (b) cache de LLM com TTL de 7 dias; (c) `market_rates` resolvido por
> `get_latest_on_or_before` com `as_of_date or date.today()`;
> (d) `category_template` / `workspace_category_overrides` /
> `fiscal_parameters` / `LLMConfig` em DB ([[ADR-135]], [[ADR-137]]);
> (e) artefatos herdados (`base_run_id`, fallback workspace-scoped).

Vender garantia mais larga que a real é o defeito que a [[ADR-320]] e a
[[ADR-210]] já custaram a esta casa. A cláusula é normativa: qualquer
superfície que exiba a revisão exibe também esta ressalva.

### 3. Grão de **stage**, não de run — `pipeline_stage_logs`

`pipeline_stage_logs` **já é** a tabela de execuções que se pensaria criar:
não há unique em `(pipeline_run_id, stage)`, há **16 pares com 2 rows** no DB
de dogfood, e dois call-sites de produção já fazem `ORDER BY started_at DESC`
+ `first()` (`pipeline_task.py::_find_stage_completion_marker`,
`::_mark_running_stage_log_failed`). Criar `run_executions` produziria uma
**segunda verdade** sobre "que stage rodou quando".

```python
# backend/app/models/pipeline_run.py, em PipelineStageLog
executor_revision: Mapped[Optional[str]] = mapped_column(String(48), nullable=True)
```

- **Escrita só no INSERT** — os dois sítios são `_record_stage_running` e
  `_record_stage_skip`. Imutável depois. **Nunca** em `output_summary`: aquele
  campo é sobrescrito por atribuição total em três pontos
  (`pipeline_task.py:870`, `:1094`, `:1185`), então chave posta no INSERT é
  apagada no terminal — e as rows sem terminal (run que crashou) ficariam
  nulas exatamente onde a atribuição vale mais.
- **`String(48)`, não `String(20)`** — `varchar(n)` no Postgres **rejeita** o
  INSERT acima do limite. Um operador injeta `$GITHUB_SHA` (40 chars) e o
  sufixo `-dirty` soma 46; com 20, um typo de env var derruba o INSERT no
  primeiro stage de **todo** run. Defesa em duas camadas: normalização
  fail-fast no boundary **e** largura folgada.
- **`execucao_mista` é derivado**, nunca armazenado:
  `COUNT(DISTINCT executor_revision) WHERE pipeline_run_id = :r`.
- Índice: **nenhum**. A query é `WHERE pipeline_run_id = :r`, já servida; a
  revisão é projeção, não filtro. Índice entra quando existir query de
  produção que **filtre** por revisão.

### 4. Formato e sentinela

`"<sha12>"` ou `"<sha12>-dirty"` (sufixo do `git describe --dirty`). Árvore
suja ⇒ o SHA não identifica o código ⇒ comparação por igualdade acerta
sozinha. **Sem** campo de branch: mesmo SHA em duas branches é o mesmo código.

`NULL ≡ revisão desconhecida`, **sem backfill** — inferir a revisão de um run
passado por `created_at` vs `git log` não sabe qual worktree rodou, se a árvore
estava suja, nem se o worker estava stale. Mesma política textual da
[[ADR-311]]. No canal humano, `desconhecido`; a string `"unknown"` não entra
em lugar nenhum.

### 5. Resolução — enquadramento na [[ADR-111]]

`settings.BUILD_SHA` ← env `MATHOMS_BUILD_SHA`, pinada no **launch** do
processo. **Zero** subprocess `git` em `backend/app/**`, **zero** global novo
(`settings` já é módulo-level), **zero** entrada em `STATELESS_AUDIT.md §2`.

Enquadramento: **categoria (a)** — constante imutável lida do ambiente do
processo. A exceção (b) ("singleton lazy idempotente") é **inaplicável**: ela
exige que cada worker descubra o **mesmo** resultado, e a propriedade que
torna este campo útil é justamente **diferir** entre a API e um worker stale.

O `git` vive em `dev/build_info.py`. ~~Ele também avisa no launch quando
`pipeline.__file__` e `backend.app.__file__` resolvem para raízes git
diferentes — o caso `PYTHONPATH`-de-worktree que já invalidou um run.~~
**Retirado pela emenda de 2026-08-06:** `--check-roots` é morto por
construção (o `sys.path.insert` do próprio script iguala as raízes) e não
tinha chamador. O mecanismo real é o preflight — ver [[ADR-363]] §Emenda
2026-08-06.

## Proibições

`executor_revision` **nunca** entra em `artifact_key`, em `UniqueConstraint`,
na cache key de LLM, em `_lineage` ou em `artifact_lineage_edge`. Entrar em
qualquer um deles trocaria dedupe/lineage de dado por identidade de build.
Critério de recuo: o mesmo da [[ADR-311]] §D5.

## Alternativas rejeitadas

| Alternativa | Por que caiu |
|---|---|
| Coluna em `pipeline_runs` | `_mark_run_started` roda **duas vezes** por run no fluxo de resume (`_TERMINAL_RUN_STATUSES` exclui `resuming`/`needs_review` de propósito) ⇒ um escalar no run **mentiria** sobre quem computou os stages anteriores |
| Chave em `output_summary` (JSON já existente) | Sobrescrito por atribuição total em 3 pontos; sem schema declarado; perde as rows de crash |
| Coluna em `pipeline_artifacts` | Desnormalização de 10,5× sem query que a exija; e `write()` faz upsert in-place, então a revisão da row antiga seria sobrescrita sem histórico |
| Tabela nova `run_executions` | `pipeline_stage_logs` já a é; a nova seria rollup lossy e criaria segunda verdade |
| `git rev-parse` em runtime como fallback | Container slim não tem `.git` nem binário `git`; e o memo pinaria o HEAD **do momento do run**, não o bytecode carregado — mediu-se worker de 07:28 servindo HEAD de 08:13 |
| Backfill de runs históricos | Fabrica dado (ver §4) |
| Digest `commits_between` / índice por arquivo no consumo pelo LLM | Domínio empírico **vazio**: zero commits nos 6 arquivos-âncora dos P0/P1 da última rodada de review ⇒ zero flags na rodada que motivou este trabalho. E falso "já corrigido" descarta achado real, que é pior que ausência |

## Consequências

- Todo stage passa a declarar quem o executou; run que atravessa deploy,
  redelivery ou resume deixa de ser representado por um escalar falso.
- A camada de artefatos **workspace-scoped** ([[ADR-241]], 12 stages) continua
  **não atribuível**: o consumo por fallback só existe numa linha de log e o
  pick é time-dependent (`ORDER BY created_at DESC`), logo irrecuperável a
  posteriori. Mediu-se **7 de 54 runs (13%)** com artefato de análise e nenhum
  artefato de extração próprio. O entregável **conta** e declara que não
  atribui — persistir o `source_run_id` no momento do consumo é trabalho
  vizinho, não desta ADR.
- Retenção é favorável: **não existe prune de `pipeline_stage_logs`** (o beat
  schedule não tem job; o único DELETE é a purga LGPD, que apaga junto com o
  run), enquanto `pipeline_artifacts` tem prune diário. A atribuição é mais
  durável que o dado atribuído.
- `pipeline_stage_logs` está em `EXPORT_EXCLUDED_TABLES` ⇒ nenhum SHA de
  repositório vaza em export de titular.
- Cobertura parcial em dev é aceita **porque `desconhecido` é linha presente e
  em destaque**. Se virar linha faltando, o dogfood em Docker gera review sem
  revisão e ninguém nota — que é o modo de falha a eliminar.
- O stamp descreve o **launch**, não cada módulo: `pipeline.*` é importado lazy
  no corpo da task e o worker roda com `--max-tasks-per-child`, então um `git
  pull` mid-run dessincroniza sem mudar o stamp. Mitigado por preflight e pelo
  aviso de raízes divergentes; **não** resolvido.

## Emenda 2026-08-05 — não existe produção; o escopo é o loop local

O §Contexto listava a inatribuibilidade de incidente em produção como quarta
consequência medida. **Era hipótese, não medição:** o projeto roda exclusivamente
na máquina do dono, em dogfood e desenvolvimento. O plano [[PLAN-launch-trust]]
já parte de *"assumindo que o projeto ainda não está em produção"* — esta ADR era
o outlier do vault, não o vault.

**O que NÃO muda (e por que a decisão sobrevive intacta):** cada escolha desta
ADR foi derivada de realidade local, não de deploy.

| Decisão | Premissa que a sustenta | Local-only afeta? |
|---|---|---|
| Env pinada no launch, zero subprocess `git` em `backend/app` | Worker que memoiza o HEAD do momento do run mente sobre o bytecode — **incidente local, medido** (worker de 07:28 servindo HEAD de 08:13) | não |
| Grão de stage, não de run | `_mark_run_started` roda 2× no resume | não |
| Sufixo `-dirty` na identidade | Dogfood roda de worktrees, com árvore suja | **reforça** |
| `String(48)` | CI injeta `${{ github.sha }}` = 40 chars, e **CI é real** | não |
| `NULL ≡ desconhecido`, sem backfill | Backfill não sabe qual worktree rodou | **reforça** |

**O que muda:** o problema é exatamente o que o dono descreveu — **do loop de
dogfood**. Não há segunda justificativa de escopo. A consequência prática está na
[[ADR-363]], que carregava o peso do enquadramento de deploy.

**Efeito na prioridade:** a perna de produção da justificativa desaparece. O que
sustenta P1 é o custo local medido — o worker stale invalidou uma rodada inteira
de review (74 achados). Um PM pode legitimamente argumentar P2; a lane declara a
base honesta em vez de herdar a prioridade.

## Emenda 2026-08-06 — falso-verde do preflight e testes que não mordiam

Auditoria adversarial sobre o código entregue. Duas correções de **decisão**,
não de prosa:

1. **Árvore suja não pode virar verde.** `preflight_warning` decidia por
   igualdade de string, e `X-dirty == X-dirty` devolvia silêncio — no laço
   dominante do dogfood ("corrijo → reinicio → rodo → ajusto → rodo sem
   reiniciar"). Passa a existir veredito **inconclusivo**: com árvore suja de
   qualquer lado, a igualdade não prova nada porque o sha não identifica o
   código. Pela mesma razão, `ancestry` ganha o 7º estado `identical-dirty`.
2. **`skipped` não é `computado`.** A frase de escopo somava os dois e um run
   0-LLM anunciava "18 stage(s) computado(s)" com 8 inertes. Passa a contar em
   duas linhas, o que é a mesma disciplina anti-Goodhart que a A42 aplica aos
   próprios KRs.
3. **Cobertura parcial não colapsa.** NULL + valor no mesmo run reportava a
   revisão conhecida como se cobrisse o run inteiro. Agora há
   `atribuicao_parcial` em destaque, e o escalar do snapshot fica `None`.

E quatro testes entregues **não mordiam** — provado por mutação: o gate
anti-fabricação (comparava com `_ROOT` rodando *de* `_ROOT`), o de árvore suja
(asseria contra o ambiente, verde em CI por construção), a injeção da revisão
no handler do root, e a precedência `herdado > incremental`. Todos reescritos
com a mutação que os mata anotada.
