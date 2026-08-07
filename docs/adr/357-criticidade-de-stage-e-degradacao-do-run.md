---
id: ADR-357
type: adr
title: "Criticidade de stage e degradação do run — add-on advisory não veta o entregável"
status: Proposto
phase: "A40"
date: "2026-08-03"
relates_to:
  - "[[ADR-199]]"
  - "[[ADR-131]]"
  - "[[ADR-212]]"
  - "[[ADR-297]]"
  - "[[ADR-291]]"
supersedes: []
superseded_by: []
aliases: ["ADR 357", "stage criticality", "partial_failure alcancavel"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/backend
  - phase/a40
---

# ADR-357 — Criticidade de stage e degradação do run

**Status:** Proposto (A40) • **Data:** 2026-08-03 • **Relaciona** [[ADR-199]]
(parecer declarado "não-bloqueante"), [[ADR-131]] (`Report.analysis_artifact_id`),
[[ADR-212]] (`ArtifactStore` DB-only), [[ADR-297]] (guarda de redelivery),
[[ADR-291]] (`from_stage`).

## Contexto

Run `2ded7aab` (2026-07-31) foi marcado `failed` com o E5 completo em
`pipeline_artifacts` (123.498 bytes). O relatório era derivável e não foi
derivado: `_finalize_pipeline_outcome` faz `if not has_failure:
_run_post_processing(...)`, e o post-processing é quem cria a linha em `reports`,
materializa lineage edges ([[ADR-279]]) e sincroniza status E2. Um defeito de
forma na prosa de um add-on advisory apagou os três.

`StageResult.success: bool` é o **único** canal de sinalização, e `False`
significa indistintamente "o pipeline não pode continuar" e "este add-on não
entregou". A política de raio de explosão fica codificada em quem **produz** o
valor, não em quem **decide** o destino do run — inversão de DIP.

A classe tem **3 membros vivos**, todos na cauda pós-`analyze_finances`:
`review_finances_holistic`, `generate_narratives`
([`scripts/generate_narratives.py:971,980`](../../scripts/generate_narratives.py))
e `validate_cross`
([`scripts/validate_cross.py:699,711,717`](../../scripts/validate_cross.py)).
Qualquer um destrói o entregável hoje.

Duas evidências de que o estado desejado já era o pretendido:

- [[ADR-199]] declara no próprio `STAGE_REGISTRY`
  ([`pipeline/stage_spec.py:243`](../../pipeline/stage_spec.py)) que o parecer é
  *"não-bloqueante"*. O código não cumpre a política escrita.
- `tier=free` **já** é a implementação de referência: o stage devolve
  `{"skipped": True}` (dict **sem** a chave `"success"`), o orquestrador conta
  como sucesso, o run completa e o relatório renderiza sem parecer. "Relatório
  sem parecer" já é estado de produto vendido e testado.

`PipelineRunStatus.partial_failure` existe no enum **desde a migration inicial**
e nunca é atribuído por nenhum caminho de código — vocabulário pré-pago.

## Decisão

### 1. `criticality` declarativa no registry

`StageSpec.criticality: Literal["required", "degradable"] = "required"` (default
fail-closed). `degradable` para os 3 membros da cauda. Invariante declarado:
**`analyze_finances` é o último stage `required`; a cauda é enriquecimento.**

Criticidade é do **registry**, não do stage (DIP) nem do run — com um único
deliverable ([[ADR-131]]), a variação "crítico num contexto, não em outro" não
existe hoje, e inventá-la seria abstração sem instância.

**`criticality` alcança apenas o canal de NÃO-ENTREGA (2026-08-06).** O canal
`validation` (`detail["validation"]["valid"]`, consumido por
`_has_validation_errors`) é **ortogonal** e permanece intocado: stage
`degradable` que **entrega** um veredito com `valid: False` continua pausando em
`needs_review`, com row em `StageReview` e `run.paused_at_stage`.

Declarado aqui, e não derivado do critério de aceite de uma lane, porque a
derivação silenciosa é o que produz mudança de contrato sem decisão. Dois
argumentos: (a) pausar **preserva** o E5 e deixa o run retomável — ninguém perde
entregável, que é o dano que esta ADR existe para impedir; (b) `validate_cross`
é o único degradável que emite `validation`, e ali `valid: False` são checks de
**conservação** (a soma fecha?) — publicar à família um relatório cujos números
não fecham, com banner de ressalva, seria vender informação **errada** como
incompleta. O que destrói o entregável hoje são os três
`return {"success": False}` do mesmo arquivo, e esses a `criticality` alcança.

### 2. Um canal, uma verdade

**Nenhuma chave nova no retorno do stage.** O stage continua dizendo "não
entreguei" (`success: False`); o orquestrador combina `(retorno, criticality)` →
`outcome ∈ {completed, skipped, degraded, failed}`. Rejeitado o contrato
`{"degraded": True}`: daria ao produtor o poder de silenciar a própria falha, e
dois canais podem discordar (`degraded: True` num stage `required` → política
indefinida).

> **Corrigido 2026-08-07, ainda em `Proposto`, por medição na A40.l18 PR2.** A
> forma anterior escrevia **`StageResult.outcome`** — campo do contrato. O
> desfecho é **derivado pelo decisor** (`pipeline/stage_outcome.py::resolve_stage_outcome`,
> consumido em `_execute_stages_loop`) e **não** é campo de `StageResult`.
>
> Dois motivos, o segundo mais forte que o primeiro. (a) Custo: o campo é
> descartado por **5 construtores campo-a-campo** (`pipeline_client.py` ×3,
> `pipeline-service/…/stage_executor.py`, `run_coordinator.py`) e pela struct Go
> `contracts_gen.go` — executor InProcess veria o valor, executor HTTP veria
> `None`, com a suíte verde; e quebra o gate de shape de
> `tests/test_cli_run_stage.py`. (b) Contrato: `StageExecuteResponse` é o que o
> **executor** devolve. Publicar `outcome` ali devolve ao produtor exatamente a
> caneta que esta § tirou dele ao rejeitar `{"degraded": True}`.
>
> Regra que fica: **descritivo viaja em `detail`; dispositivo é derivado pelo
> decisor.** É a mesma medição que valida `reason_class` em `output_summary`
> (§Delta item 1) e que reprova o campo `outcome`.

`{"skipped": True}` é normalizado para `outcome=skipped` no mesmo ato, e esse
desfecho mapeia para **`PipelineStageStatus.completed`** — o default atual (dict
sem `"success"` ⇒ `completed`) é **preservado**.

> **Precisão de 2026-08-07 (A40.l18 PR2).** As duas frases acima estavam em
> tensão: `{"skipped": True}` **é** um dict sem `"success"`, logo hoje já grava
> `completed`. Mapear `outcome=skipped` para `PipelineStageStatus.skipped`
> flipparia status **e** evento WS dos 5 early-returns de
> `pipeline/stages/parecer_planejador.py` (flag off, sem E5, sem backend,
> tier=free, sem API key) e dos `extract_*` sem documento — comportamento que
> ship hoje. `PipelineStageStatus.skipped` já significa outra coisa: o
> orquestrador decidiu **não rodar** o stage, gravado por `_record_stage_skip`
> antes da execução. `outcome=skipped` fica descritivo.

**A disposição é cega à FORMA da não-entrega.** As duas rotas do loop —
`result is None` (exceção após retries) e `result.success is False` — mapeiam
ambas para `degraded` quando `criticality=degradable`. **`result.error` é
proibido como discriminador:** `error is None` significa "nenhuma exceção cruzou
a fronteira do runner", não "o stage declarou". A assimetria é medida — a mesma
falha de rede vira `error=None` dentro de `llm.call` e `error=str(exc)` em
`store.write`, que fica fora do `try`.

**`reason_class` é descritivo, nunca dispositivo (2026-08-06).**
`StageFailureReason` (enum fechado: `enforcement`, `provider_error`, `network`,
`timeout`, `budget_exhausted`, `llm_unavailable`, `internal_error`, `unknown`)
viaja no `detail` e é persistido em `PipelineStageLog.output_summary`. Isso
**não** reabre a porta que esta seção fechou, e a diferença é verificável e não
retórica: `{"degraded": True}` era **dispositivo** — o produtor nomeava o próprio
raio de explosão. `reason_class` só entra em copy, log e alerta; **nenhuma
ramificação de status o consulta**. Invariante provado por teste paramétrico
sobre **todos** os membros do enum: para o mesmo stage degradável, a tripla
`(run.status, stage_log.status, existe row em reports)` é idêntica em todos.
Mutação que o teste mata: `if reason_class == "budget_exhausted": failed`.

Ele é **obrigatório, não cosmético**. A classe fechada client-facing da
[[A40.l20]] §4 tem 3 membros que são todos juízos sobre o conteúdo do cliente;
sem `reason_class`, um `ReadTimeout` da Anthropic cai nessa classe e a UI diz ao
cliente premium que o conteúdo dele foi retido por política — mentira nova, da
mesma família da que a l20 existe para consertar. A informação já existe e é
jogada fora: `_exc_label` lê `exc.error_type` e o achata em string de display.

### 3. `PipelineStageStatus.degraded` novo; `partial_failure` reusado

- **Stage:** valor novo `degraded`. Não reusar `needs_review`, que está acoplado
  a `StageReview` + `run.paused_at_stage` + `publish_needs_review` e é
  deliberadamente **excluído** de `_TERMINAL_RUN_STATUSES` para o resume
  re-entrar. Degradado é terminal e **não** retomável.
- **Run:** `partial_failure` reusado, com semântica **terminal, entregue, com
  lacuna declarada**. Decisivo: já está em `_TERMINAL_RUN_STATUSES`, logo herda
  de graça a guarda de redelivery ([[ADR-297]]). Um status novo obrigaria a
  lembrar de adicioná-lo ao set — esquecer reabre a regressão.
- `run.failed_at_stage` **não** é populado em degradação (hoje o é para todo
  não-sucesso): `failed_at_stage` preenchido + status `partial_failure` mentiria
  para todo leitor futuro. Derive o stage degradado de `stage_logs`.
- `run.failure_reason` **também** fica NULL em degradação.

> **Acrescentado 2026-08-07 (A40.l18 PR2).** `failure_reason` é coluna viva
> (`String(50)`) e o motivo não é só o argumento acima: é **vocabulário**.
> `pipeline_failure_reasons.py` tem 4 membros — `heartbeat_timeout`,
> `dispatch_failed`, `run_setup_failed`, `dispatch_unconfirmed` — e todos são
> falhas de propriedade do **run** (ninguém dono, nunca rodou). Escrever
> `StageFailureReason` no mesmo campo funde duas taxonomias sem discriminador, e
> o `SELECT failure_reason, count(*)` do runbook passa a devolver histograma
> misturado.
>
> Dos **4** writers de `failed_at_stage`, só os 2 de disposição de stage são
> blindados (`_record_stage_result`, `_record_stage_exception`).
> `_apply_task_crash_to_run` e o watchdog de `periodic_tasks.py` ficam intactos
> de propósito: são falha real do run e já filtram por status não-terminal
> (`_CRASH_RUN_STATUSES` / `status == running`), então nunca tocam um run
> `partial_failure`. Blindar os 4 quebraria crash-recovery.

### 4. `degraded` entra em `_STAGE_DONE_STATUSES`

Sem isso, o redelivery Celery re-executa e **re-paga** o stage LLM já cobrado
(US$ 0,48 no incidente) — reintroduz a regressão que a A37.l12 fechou, só no
ramo degradado. É a linha mais importante do PR.

Duas consequências medidas em 2026-08-07 (A40.l18 PR2), ambas implementadas:

- **O marcador de redelivery publica o status REAL.**
  `_publish_redelivered_stage_event` mandava tudo que não é `completed` para
  `publish_stage_skipped(..., "LLM stage skipped (redelivery)")`. Com `degraded`
  no set, um stage degradado redelivered seria anunciado como `skipped` — e
  `status` é contrato lido por `pipelineRunOutcome.ts`, não prosa. Reusa o
  evento (esta ADR recusa evento novo) com `status` parametrizado.
  `stage_degraded` é nome de **log**, nunca de evento WS.
- **O 3-way deriva da UNIÃO `flags da invocação ∪ stage_logs do run`.** A flag
  local mede a **invocação**; a degradação é do **run**. `resume_pipeline_run`
  re-despacha a task com o mesmo `run_id` e só os stages restantes — caminho
  vivo, não exótico — e o redelivery pula stages concluídos pelo marcador; nos
  dois casos as flags voltam limpas e o run finalizaria `completed` com um
  `stage_log` `degraded` no banco. `has_failure` continua vindo da flag porque o
  ramo de falha de commit de artefato grava `completed` no stage_log: só a união
  cobre as duas direções.

### 4b. Degradação **não** honra `stop_on_error`

Os 3 degradáveis são os **3 últimos** de `FULL_ORDER`, nesta ordem —
`generate_narratives → validate_cross → review_finances_holistic` — e o default
do trigger e do resume é `stop_on_error=True`. Se o ramo degradado herdasse o
`break`, degradar `generate_narratives` apagaria também a conferência de
consistência **e o parecer que o cliente premium pagou**: uma lacuna virando
três, criada pela própria lane que existe para matá-las. E a copy da l21
(*"Relatório gerado, sem as análises e comentários"*) sub-declararia o resto.

> **Acrescentado 2026-08-07 (A40.l18 PR2).** Não estava em nenhum critério de
> aceite — veio do co-design. Fica na ADR, e não só no critério da lane, pelo
> mesmo argumento com que a §1 se recusa a derivar contrato de critério de lane.
> Não-entrega de stage `required` continua honrando `stop_on_error`.

### 5. Precondição do report é o artifact E5, não o status do run

Reafirmação de [[ADR-131]]. `_create_report_from_output` já checa apenas a
existência do artifact E5; o único gate é o `if not has_failure`. Nenhuma ADR
declarava "report só de run completo" — o invariante não existia escrito.
`_finalize_run` passa a ser 3-way e o post-processing roda em degradação.

> **Precisado 2026-08-07 (A40.l18 PR2), três coisas que o texto não cobria.**
>
> **(a) `partial_failure` exige entregável.** Se o stage degradado é o que
> deveria produzir a dependência (`validate_cross` devolvendo `e5_not_found`), o
> run não tem E5, `_create_report_from_output` não acha artifact, e
> `partial_failure` — *"terminal, entregue, com lacuna declarada"* — mentiria:
> nada foi entregue. `_terminal_status` degrada para `failed` nesse caso. Isso
> **não** fura a cegueira da §2: a cegueira é sobre a **forma da não-entrega do
> STAGE**; *"o run entregou?"* é pergunta de **run**, respondida por evidência.
> Rejeitado o caso especial `if reason == "e5_not_found": required` — é o
> `if stage_name == _PARECER_STAGE_NAME` que esta ADR chama de precedente feio.
>
> **(b) O predicado tolera o base run.** `_find_latest_analysis_artifact` filtra
> `pipeline_run_id == run_id`, mas em run só-de-cauda com `from_stage` o E5
> pertence ao **base run** e é lido por fallback do store ([[ADR-291]]). O
> predicado consulta `pipeline_run_id IN (run.id, run.base_run_id)`; filtrar só
> pelo próprio reprovaria um run de cauda íntegro. `_find_latest_analysis_artifact`
> **não** foi estendido — mudar criação de report para re-run de cauda é o
> §Follow-ups item 5 da lane.
>
> **(c) O gate do post-processing é POSITIVO.** `if not has_failure` era
> negativo, e negativo deixa passar todo status futuro sem decisão.
> `_POST_PROCESS_STATUSES` nomeia `completed`, `partial_failure` e `cancelled` —
> o último para **preservar** comportamento vivo: hoje o loop faz `break` com
> `has_failure=False`, `_finalize_run` early-returna no status, e cancelar depois
> de `analyze_finances` já gera relatório. Mudar isso é lane própria.

### 6. Artifact degradado é persistido, nunca publicado

Em degradação o artifact é **commitado** (hoje é rolled-back), para que a
superfície de diagnóstico tenha o que ler. Não viola [[ADR-212]]:
`SCHEMA_BY_STAGE` não mapeia `review_finances_holistic`. É **obrigatório**, não
opcional: o marcador terminal promete "artefatos persistidos", e marcar
`degraded` com artifact rolled-back faz o marcador mentir.

Os dois leitores já discriminam por `_meta.status == "Gerado"`.

**Exceção travada:** commit-on-degrade só é seguro quando o artifact degradado
tem **chave própria**, porque é ali que cabe o marcador `_meta.status` que os dois
leitores usam para discriminar. `generate_narratives` escreve em
`analyze_finances`/`analise_financeira` — a mesma chave do E5 — e ali não há onde
pôr esse marcador sem mentir sobre um E5 que está **completo**. A política é
declarada **por stage** (`StageSpec.commit_artifacts_on_degrade`), não derivada de
`StageSpec.writes` (que é ficção para 2 dos 3 degradáveis).

> **Justificativa substituída 2026-08-07 (A40.l18 PR2), decisão inalterada.** A
> forma anterior dizia *"commitar merge parcial ali corrompe o deliverable"*.
> **O merge parcial não é reproduzível hoje:** `generate_narratives` tem
> exatamente **1** `store.write`, e ele é a última instrução antes do sucesso —
> os dois `success: False` o precedem. Pior: a mutação in-place de `e5_data` que
> antecede o write não chega ao banco de jeito nenhum, porque a coluna é `JSON`
> **sem** `MutableDict`. Ou seja, a proteção que o texto anterior invocava é
> fornecida por um **defeito de aliasing**, não pela política — e o dia em que
> esse defeito for consertado, o vetor nasce de verdade.
>
> A decisão sobrevive; a razão não. Manter o texto original faria a próxima
> pessoa travar a exceção sem travar a propriedade que a sustenta (a posição do
> write), e o primeiro refactor que mova o write para cima reabriria o buraco em
> silêncio.
>
> **Débito derivado, fora desta lane:** `DBArtifactStore._maybe_decrypt` devolve
> `row.content_json` por **referência** e a coluna é `JSON` plain sem
> `MutableDict` — `read → mutar in-place → write` na mesma `(stage, key)` é
> **lost update silencioso** quando `ENCRYPT_PIPELINE_ARTIFACTS=False` (o default
> `True` mascara, reconstruindo o dict). Dono `data-engineer`, ADR própria, e ela
> **depende** desta §: consertar o aliasing sem a exceção travada em pé abre o
> vetor de corrupção do deliverable.

### 7. Migration do drift de enum

A migration inicial criou `pipelinestagestatus` com 5 valores e
`pipelinerunstatus` com 6. O Python tem `skipped_free_tier`/`needs_review` e
`needs_review`/`resuming` a mais, **sem nenhum `ALTER TYPE`**. Funciona porque
dev é SQLite; em Postgres o caminho de `needs_review` do stage log — **já vivo**
([[ADR-272]]/E3) — quebraria no `INSERT`. A migration inclui os 4 valores em
drift + `degraded`, no padrão guardado por dialeto já usado no repo.

> ✅ **Entregue pela [[A40.l19]] em `c9688111` (#1241), 2026-08-06**, junto com
> `dev/check_enum_migration_parity.py` — o gate que faltava. Ele lê os dois lados
> por **AST** e não o banco de teste: este nasce de `Base.metadata.create_all`,
> que materializa o próprio enum Python, e teria ficado verde durante todos os
> meses de drift. Direção `python ⊆ declarado`, nunca igualdade — Postgres não
> tem `DROP VALUE`, e exigir igualdade transformaria toda remoção legítima em
> falha eterna. É também o que tornou seguro mergear a migration antes do membro
> Python (`degraded` declarado no tipo, ausente no código, gate verde).

### 8. Degradável = não-retryável in-run, não-reexecutável, re-rodável por run novo

`_run_stage_with_retry` só retenta exceção — correto como está. "Retentar só o
parecer" é run novo com `from_stage` ([[ADR-291]]), não resume.

**O motivo é que o retry transitório já foi consumido a montante.**
`LLMService.call` ([`pipeline/llm/litellm_client.py`](../../pipeline/llm/litellm_client.py))
já retenta `RETRYABLE_ERRORS` com backoff 30/60/120s e escalada de timeout
([[ADR-270]]). Repetir no orquestrador é layering de retry que a própria ADR-270
§1 proíbe.

> **Justificativa substituída em 2026-08-06, ainda em `Proposto`.** A forma
> anterior era *"veredito de enforcement sobre gerador estocástico não é
> transitório, e o dinheiro já foi gasto"*. **As duas premissas são falsas no
> ramo de infra**, e a medição é o `except Exception` de
> [`parecer_orchestrator.py`](../../backend/app/services/parecer_orchestrator.py)
> (`# noqa: BLE001 — todas exceções viram needs_review`), que envolve
> `llm.call` inteiro: queda de provider, `ReadTimeout`, 5xx, hard-stop de budget
> ([[ADR-173]]) e bug de código chegam ao orquestrador como `success: False` com
> `error is None`, indistinguíveis de um veredito de enforcement. Nesse ramo a
> falha **é** transitória e o dinheiro **não** foi gasto.
>
> A conclusão sobrevive; a justificativa não. Manter o texto original faria a
> próxima pessoa deduzir que degradação implica dinheiro gasto — e desenhar
> billing ou alerta em cima de uma premissa falsa.

> **Vocabulário de retry corrigido 2026-08-07 (A40.l18 PR2), divergindo da
> prescrição do §Delta item 5 da lane.** Aquele item mandava trocar `rate_limit`
> por `ratelimit`, alegando que o primeiro *"nunca casa"* contra o rótulo
> `ratelimiterror`. **Duas premissas erradas, medidas:** (a) `should_retry`
> recebe `str(exc)[:2000]`, não o nome da classe — e o que chega ali é uma
> `LLMError` que re-embrulha a mensagem do provider; (b) `_normalize` colapsa `_`
> em espaço nos **dois** lados, então o corpo do erro (`rate_limit_error` →
> `rate limit error`) casa `rate_limit` e **não** casa `ratelimit`. Aplicar a
> prescrição seria a regressão.
>
> O gap real é outro e era silencioso: o **overload** da Anthropic (529 / 500
> `overloaded_error`, o transiente mais comum em pico de capacidade) é mapeado por
> litellm para `InternalServerError`, cuja mensagem não contém nenhum dos 5
> padrões antigos. E a mensagem de timeout aparece em **duas** formas —
> `classify_error` conhece ambas (`timeout` e `timed out`), a tabela de retry
> conhecia uma. Acrescentados `overloaded`, `529` e `timed out`; nada removido.
>
> A **assimetria** segue não corrigida de propósito (§Follow-ups item 4 da lane):
> nenhuma exceção do parecer chega a `_run_stage_with_retry`, porque
> `parecer_orchestrator` converte tudo em `success: False` antes de sair. Para
> aquele stage a tabela é inerte — religá-la re-pagaria o stage LLM já cobrado.

## Alternativas rejeitadas

- **Contrato de retorno do stage (`{"degraded": True}`)** — criticidade viraria
  decisão do produtor; dois canais podem discordar. Ver §2.
- **Especializar só o parecer (`if stage_name == _PARECER_STAGE_NAME`)** — barato,
  não fecha a classe, e há precedente feio disso em
  `_should_persist_planner_review`.
- **`completed_with_degradation` novo** — perde a herança de
  `_TERMINAL_RUN_STATUSES`. Ver §3.
- **Coluna `degraded_at_stage`** — derivável de `stage_logs`.

## Consequências

- Frontend: os **7** read sites que tratam `partial_failure` como falha devem ser
  corrigidos **antes** do writer emitir (reader-first — ver [[A40.l21]]).
  Shipar o writer primeiro entrega um run que produziu relatório com banner
  vermelho de falha, pior que hoje.
- `publish_run_completed`/`publish_run_failed` recebem o status real como
  parâmetro em vez de ganharem um terceiro evento.
- `make update-openapi-snapshot` → **`PipelineRunStatus` inalterado** (é o que
  esta §3 protege — `partial_failure` já está publicado, e reuso é justamente o
  ponto). `PipelineStageStatus` **ganha `degraded`**, 1 linha; idem
  `docs/reference/DB_SCHEMA_REFERENCE.md` via `make update-db-schema-reference`.
  Diff no enum de **run** ⇒ alguém adicionou status novo e a §3 foi violada.
  > Corrigido 2026-08-06, ainda em `Proposto`, por medição na A40.l18. A
  > previsão original era "diff vazio esperado" e teria reprovado o PR que
  > cumpre a §3: [`backend/app/schemas/pipeline.py`](../../backend/app/schemas/pipeline.py)
  > declara `status: PipelineStageStatus` em `PipelineStageLogResponse`, logo o
  > enum de stage é superfície pública de API. O raciocínio original cobriu só o
  > status de run.
  >
  > **Corrigido de novo 2026-08-07 — terceira revisão desta linha, por medição no
  > PR2.** A previsão acima acertou a superfície e errou **quem paga**: o PR1
  > (`4620cc04`/#1242) já declarou o membro Python, então `degraded` já está em
  > `docs/reference/api/v1/openapi.json` e em `DB_SCHEMA_REFERENCE.md`. Medido no
  > PR2: os dois `make` produzem **diff vazio**. Um revisor que leia "ganha
  > exatamente `degraded`" ao pé da letra reprova o PR correto.
  >
  > Lição de forma: previsão de diff de snapshot precisa nomear **qual PR** paga,
  > não só qual superfície muda. Esta linha errou 3× por omitir isso.
- Débito nomeado, **não** corrigido aqui: `StageSpec.writes` é ficção para
  `generate_narratives` (declara chave própria, escreve na do E5) e
  `validate_cross` (declara chave, é read-only). `validate_full_order` valida um
  grafo com 2 arestas fictícias.
- **Prevenção herdada de [[ADR-358]]:** decisão cujo enforcement depende de
  evidência futura nasce `Proposto`, ou nasce `Decidido` com o gate registrado em
  `OWNER-GATED-active.md`. `Decidido` + "validar depois" foi o defeito que
  produziu o incidente de origem.
