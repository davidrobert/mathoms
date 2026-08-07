---
id: A40.l18
type: lane
title: "Criticidade de stage: add-on advisory não veta o entregável; partial_failure alcançável"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l18-criticidade-de-stage
adrs:
  - "[[ADR-357]]"
depends_on:
  - "[[A40.l21]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/backend
---

# A40.l18 — `criticidade-de-stage`

> ✅ **Desbloqueada 2026-08-06:** a [[A40.l21]] mergeou em `c8239386` (#1232). Pelo
> §Predicado do campo `status` do [`_README`](../_README.md) — *`open` ⇔ todo
> `depends_on` terminal* — o `blocked` de 2026-08-03 ficou obsoleto no merge e não
> foi flipado então; quem lesse o `SPRINT_CURRENT` não veria a lane. `depends_on`
> **fica**: registra a ordem reader-first que foi cumprida, não um bloqueio vivo.
>
> **Relógio herdado da l21.** Os leitores tolerantes já estão em `main` e são dead
> code até esta lane emitir o writer. O §Gate de saída do [`_README`](../_README.md)
> manda **reverter a l21** (e o PR1 da [[A40.l20]]) se esta lane não mergear até
> `date_target: 2026-08-17`.
>
> ## 🔓 Estado em 2026-08-06 — **PR1 entregue, PR2 (o writer) é o que falta**
>
> **`status: open`, não `in_progress`** — e a distinção não é burocrática. O PR1
> (vocabulário inerte) mergeou em `4620cc04` (#1242); **não há branch nem PR
> aberto** para o PR2. Deixar `in_progress` faria esta P0 parecer **tomada** e
> ninguém a pegaria — o modo de falha exato que o §Delta de 2026-08-06 do
> [`_README`](../_README.md) §Predicado documenta para o `blocked` stale, só que
> pelo outro campo. Enquanto o PR2 não tiver dono, `open` é o valor honesto.
>
> **Já em `main`, não refazer:** `PipelineStageStatus.degraded` + gate de
> paridade Python↔TS (`4620cc04`/#1242) · migration dos 5 valores + gate AST de
> paridade de enum ([[A40.l19]], `c9688111`/#1241).
>
> **O PR2 é o §Delta do co-design + §Decisões do dono desta lane**, e o escopo
> está fechado — o que falta é execução, não decisão. Comece por §Delta,
> item 2 (a disposição cega à forma da não-entrega) e pelo §Critério de aceite
> corrigido; o bullet de `validation` foi **invertido** em 2026-08-06 e a forma
> antiga levaria ao comportamento errado.
>
> Onda 3 da A40 (§Frente 4 de [[PLAN-report-trust]]). Fecha a **classe**, não o caso.
> `depends_on` [[A40.l21]] por **ordem reader-first**: os leitores toleram
> `partial_failure` antes de o writer o emitir. Shipar o writer primeiro entregaria
> um run com banner vermelho e botão de reprocessar — pior que hoje.

## Problema

`StageResult.success: bool` é o único canal e `False` significa
indistintamente "o pipeline não pode continuar" e "este add-on não entregou". A
classe tem **3 membros vivos** na cauda pós-`analyze_finances`:
`review_finances_holistic`, `generate_narratives`
(`scripts/generate_narratives.py:971,980`) e `validate_cross`
(`scripts/validate_cross.py:699,711,717`). Qualquer um destrói o entregável.

`PipelineRunStatus.partial_failure` existe desde a migration inicial e **nunca é
atribuído**. `_finalize_pipeline_outcome` faz `if not has_failure:
_run_post_processing(...)` — e o post-processing é quem cria `reports`,
materializa lineage edges e sincroniza status E2.

[[ADR-199]] já declara o parecer *"não-bloqueante"* em
[`pipeline/stage_spec.py:243`](../../../../pipeline/stage_spec.py). Esta lane faz
o código cumprir a política escrita.

## Decisão

Ver [[ADR-357]] (`Proposto` — abrir **antes** do PR de implementação). Resumo:
`criticality: required|degradable` no registry (default fail-closed);
`StageResult.outcome ∈ {completed, skipped, degraded, failed}` derivado de
`(retorno, criticality)` no orquestrador; `PipelineStageStatus.degraded` novo;
`partial_failure` escrito; `failed_at_stage` **não** populado em degradação;
`degraded` **entra em `_STAGE_DONE_STATUSES`** (senão o redelivery re-paga o
stage LLM); artifact degradado commitado, nunca publicado — **exceto**
`generate_narratives`, que escreve na chave do E5 e corromperia o deliverable;
`_finalize_run` 3-way e post-processing rodando em degradação.

### Delta do co-design de 2026-08-06

Painel de 4 especialistas sobre 3 lacunas que uma recon adversarial expôs
(4 de 4 afirmações do plano inicial refutadas contra o código). O que mudou:

1. **`StageFailureReason` nasce** — enum fechado
   (`enforcement | provider_error | network | timeout | budget_exhausted |
   llm_unavailable | internal_error | unknown`), produzido **dentro** do
   `except Exception` de `backend/app/services/parecer_orchestrator.py:422` a
   partir de `type(exc)`/`exc.error_type`, propagado por `_needs_review_return`
   e persistido em `PipelineStageLog.output_summary` (JSON, **sem** coluna nova
   — precedente `summary["redelivered"]`). Nunca re-derivado por match de string
   sobre a mensagem: isso seria classificação fabricada.
   É **descritivo, nunca dispositivo** — ver [[ADR-357]] §2.
2. **A disposição é cega à forma da não-entrega.** As duas rotas do loop —
   `result is None` (exceção após retries) e `result.success is False` — mapeiam
   ambas para `degraded` quando `criticality=degradable`. **`result.error` é
   proibido como discriminador**: `error=None` significa "nenhuma exceção cruzou
   a fronteira do runner", não "o stage declarou". A mesma falha de rede cai dos
   dois lados conforme a linha (dentro de `llm.call` → `error=None`; em
   `store.write` → `error=str(exc)`).
3. **Gate estático fica só com a metade provada** — *"todo stage até
   `analyze_finances` é `required`"*. A recíproca forçaria `validate_cross` para
   dentro da classe por CI e transformaria questão semântica em invariante de
   pipeline; a criticidade da cauda segue declaração explícita por stage.
4. **Cascata que a lane cria é dívida da lane:** o early-return
   `missing_narrativas` (`scripts/validate_cross.py:713-717`) é **removido**.
   Sem isso, degradar `generate_narratives` — que esta lane manda fazer —
   derruba `validate_cross` junto e produz dupla lacuna. Sem narrativas, o stage
   pula a classe de render (CV9/CV10/CV14) e roda conservação normalmente.
5. **Retry declarado e morto é religado:**
   `backend/app/services/pipeline/retry_config.py:60-64` declara
   `review_finances_holistic` com `retryable_errors=[… rate_limit …]`, mas
   `_normalize("rate_limit")` produz `"rate limit"` **com espaço** contra o
   rótulo `"ratelimiterror"` — nunca casa. Corrigir para
   `ratelimit`/`overloaded`/`apistatus`; o teste de tabela nasce vermelho e
   documenta o bug.
6. **Observabilidade é condição de merge, não follow-up** — log sem sink é
   silêncio com outra sintaxe. Ver §Decisões do dono, itens 1 e 2.

## Decisões do dono (2026-08-06)

Três perguntas que o painel classificou como não-delegáveis, respondidas pelo
dono na mesma sessão:

1. **`CleanBar` suprimido agora; ressalva positiva fica com a [[A40.l22]].** O
   PR2 proíbe o `CleanBar` de renderizar em relatório derivado de run degradado
   — hoje ele **afirma** *"sem pendências que afetem a leitura deste relatório"*,
   e essa afirmação sai no PDF e circula entre cônjuge e contador. Mecanismo:
   `Report.pipeline_run_id` já é FK viva, o desfecho entra em
   `computeDataQualitySignals` sem coluna nova. Alternativa recusada: segurar o
   PR2 até a l22 — ela depende do PR1 da [[A40.l20]] e estouraria a
   `date_target`, revertendo a [[A40.l21]] já em `main`.
2. **Card em `/admin/metrics` + cadência do dono.** `pipeline_runs_by_status` +
   `stages_degraded_last_period` por `reason_class` em
   `internal_ops/metrics.py::get_metrics`. Sentry fica para a próxima janela
   (OWNER-GATED). Recusado explicitamente: **só** log estruturado — é o mesmo
   modo de falha que produziu o incidente de origem ([[ADR-304]] §Emenda: 16
   itens apagados em 7 runs, 9 dias sem detecção).
3. **Tolerância de conservação vira follow-up com ADR própria** — ver §Follow-ups
   nomeados, item 1.

## Follow-ups nomeados (não entram nesta lane)

Registrados aqui porque §Deferimento sem dono vira dívida invisível. Nenhum ID
de ADR é reservado em prosa (precedente [[ADR-356]]).

1. **Tolerância de conservação e classe de check.** `patrimonio_composicao_diff_pct_max: 5`
   (`config/pipeline.json`) deixa passar R$ 150k–400k de divergência não
   explicada num patrimônio de R$ 3–8M; e CV16 (dupla-contagem de receita) e
   CV17 (renda passiva), os **dois únicos** checks de tolerância zero, estão
   **fora** do conjunto que pausa, enquanto CV1 e CV6 — que são derivação, não
   conservação — estão dentro. Dono: `financial-planner`, ADR própria.
   Condição de retomada: decisão do dono de 2026-08-06 (§Decisões do dono, 3).
2. **Ressalva positiva na tela e no PDF** — [[A40.l22]], já existente.
3. **4º membro de falha temporária** na classe fechada client-facing da
   [[A40.l20]] §4, com CTA de re-geração — separado dos 3 juízos de conteúdo,
   senão um `ReadTimeout` diz ao cliente que o conteúdo dele foi retido por
   política.
4. **Assimetria de retry** — `retry_config["review_finances_holistic"]` só
   alcança o caminho de exceção. Nomeado como **não-corrigido aqui** para que
   ninguém "harmonize" e re-pague o stage LLM (regressão que a A37.l12 fechou).
5. **Run só-de-cauda com `from_stage`** — `_find_latest_analysis_artifact`
   filtra por `pipeline_run_id`, então o re-run não cria row em `reports`.
   Verificado que **não destrói** a existente; a dívida é o teste de regressão
   travando *"re-run de cauda nunca reduz `count(reports)`"* + a copy do CTA.
   Dono: [[A40.l20]] PR2.
6. **`StageSpec.writes` é ficção** para `generate_narratives` (declara chave
   própria, escreve na do E5) e `validate_cross` (declara chave, é read-only).
   Débito já nomeado na [[ADR-357]] §Consequências, mantido.

## Critério de aceite

- Fake de stage `degradable` com `success: False` ⇒ run `partial_failure`,
  1 row em `reports` com FK para o artifact E5, `stage_log.status == degraded`,
  `run.failed_at_stage is None`.
- Mesmo fake em stage `required` ⇒ `failed`, zero row em `reports`
  (comportamento atual preservado).
- **Teste de injeção nos 3 membros vivos** assertando que o report existe (KR-2).
- Regressão de redelivery: run com stage degradado ⇒ zero chamada LLM nova.
- `generate_narratives` degradado **não** deixa o payload `analyze_finances`
  corrompido (comparação byte-a-byte com o pré-stage).
- Stage `degradable` que **entrega veredito** com `validation.valid=False` ⇒
  continua `needs_review`: 1 row em `StageReview`, `run.paused_at_stage`
  preenchido, `review_reasons` materializadas. Gate **espelhado** sobre o mesmo
  stage: `success: False` ⇒ `degraded` + zero row em `StageReview`.
  > **Invertido em 2026-08-06 por co-design** (`senior-cto` + `financial-planner`
  > + `data-engineer` convergentes; `sre-devops` exigindo decisão explícita em
  > vez de derivação silenciosa). A forma anterior mandava o oposto — *"⇒
  > `degraded`, **não** `needs_review`; zero row em `StageReview`;
  > `paused_at_stage is None`"* — e teria apagado o único gate de pausa por
  > violação de conservação do produto.
  >
  > **`criticality` governa apenas o canal de NÃO-ENTREGA** (`success: False` ou
  > exceção). O canal `validation` é **ortogonal**: mede a qualidade de um
  > veredito que o stage **entregou**, e nada na [[ADR-357]] justifica acoplá-lo
  > à criticidade. O que destrói o entregável hoje são os três
  > `return {"success": False}` de `scripts/validate_cross.py:699,711,717` — não
  > o gate de conservação, que **pausa**, e pausar preserva o E5 e deixa o run
  > retomável. A lane captura 100% do incidente de origem sem encostar no freio.
  >
  > Consequência de produto se a forma anterior tivesse sido implementada:
  > CV1/CV2/CV3/CV6 falhando publicariam à família um relatório cujos números
  > não fecham, com banner de ressalva — informação **errada** vendida como
  > incompleta. Ver §Follow-ups nomeados, item 1.
- Gate estático: todo stage após `analyze_finances` é `degradable`; todo stage
  até ele é `required`. Falha se alguém inserir stage no meio sem decidir.
- `make update-openapi-snapshot` ⇒ o enum **`PipelineRunStatus` inalterado** (é
  ele que a [[ADR-357]] §3 protege: `partial_failure` é reuso, não status novo).
  O enum `PipelineStageStatus` ganha **exatamente `degraded`**, e nada mais.
  Idem `make update-db-schema-reference`.
  > Corrigido 2026-08-06 **por medição**. A forma anterior — *"diff vazio; diff
  > ⇒ §3 violada"* — era falsa e teria reprovado o PR correto:
  > [`PipelineStageLogResponse.status`](../../../../backend/app/schemas/pipeline.py)
  > publica o enum de **stage** no snapshot, então `degraded` (que a §3 **manda**
  > criar) muda `openapi.json` e `DB_SCHEMA_REFERENCE.md` — 1 linha em cada. A
  > previsão original raciocinou só sobre o status de **run**. Mesma correção na
  > [[ADR-357]] §Consequências.
- `dev/check_pipeline_boundaries.py` verde (mapeamento `outcome →
  PipelineStageStatus` mora em `backend/`).
- Log estruturado `stage_degraded` com `stage`, `criticality`, `reason_class`
  (nunca a prosa), `cost_usd`, `run_id`.
