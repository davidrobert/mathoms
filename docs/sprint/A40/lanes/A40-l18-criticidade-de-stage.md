---
id: A40.l18
type: lane
title: "Criticidade de stage: add-on advisory não veta o entregável; partial_failure alcançável"
sprint: A40
plan: PLAN-report-trust
status: shipped
priority: P0
branch_slug: a40-l18-criticidade-de-stage
adrs:
  - "[[ADR-357]]"
depends_on:
  - "[[A40.l21]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
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
> ## ✅ Estado em 2026-08-07 — **lane `shipped`; PR2 mergeado em [#1258](https://github.com/davidrobert/mathoms/pull/1258) (`b8460274`)**
>
> A regra que esta seção declarava — *"`status: open` até o merge"* — foi
> cumprida com atraso de campo: o merge saiu às 14h e o `status` só flipou às
> 18h, na varredura que também achou o `blocked` stale da [[A40.l22]]. **Os dois
> sentidos do §Predicado falharam no mesmo dia e pelo mesmo motivo** — o flip é
> manual e ninguém o faz no merge. Registrado aqui como terceira instância, que é
> o que autoriza gastar as ~10 linhas do gate derivável de `depends_on` +
> `status` (candidato: [[A40.l23]]).
>
> Os 8 commits do PR2 cobrem o §Critério de aceite
> inteiro **e** as duas condições de merge do §Decisões do dono:
>
> | Commit | O que entrega |
> | --- | --- |
> | `0b95d22d` | `StageSpec.criticality` + `commit_artifacts_on_degrade` + resolvedor puro `pipeline/stage_outcome.py` |
> | `d71d0c3c` | gate AST `dev/check_stage_criticality.py` (4 regras provadas por mutação) + cobertura do resolvedor |
> | `7f41be2e` | cascata `missing_narrativas` morta (classe de render SKIPA) + vocabulário de retry corrigido por medição |
> | `e4fcf337` | **o writer**: `partial_failure` escrito, `degraded` gravado e em `_STAGE_DONE_STATUSES`, post-processing em degradação, `failed_at_stage`/`failure_reason` NULL, degradação sem `stop_on_error` |
> | `263d4d1f` | 10 testes de aceite, 5 mutações provadas |
> | `2c8d169c` | **supressão do `CleanBar`** (§Decisões do dono, 1) |
> | `d88730fe` | **`StageFailureReason` + card em `/admin/metrics` + log** (item 2) |
> | `c807722d` | card no console ops + gate de paridade do `types.ts` + cadência no RUNBOOK |
>
> Suítes: backend 3162, pipeline 5913, frontend 1571, `tsc --noEmit` limpo nos dois
> apps. Snapshots: enums de pipeline **sem diff** (o PR1 pagou); `ReportResponse`
> e `MetricsResponse` ganham campo, o que é esperado.
>
> **§Follow-ups nomeados ganharam 3 itens** (ver seção): aliasing do
> `DBArtifactStore` (P1, `data-engineer`, ADR própria — e ela **depende** da §6),
> índice parcial de `pipeline_stage_logs` com gatilho medível, e CI própria do
> `frontend-ops` (lane A42).
>
> ## 📋 Co-design de 2026-08-07 — decisões que o escopo "fechado" não previa
>
> Painel de 4 especialistas sobre 14 questões que uma recon de medição expôs
> (várias afirmações dos docs refutadas). O que ficou decidido — **todos
> implementados no PR2**, exceto o índice parcial, que foi decidido *como
> dívida com gatilho* e não como entrega (o texto abaixo era "ainda não
> implementado" e ficou stale entre a decisão e o merge do mesmo dia):
>
> - **`CleanBar`:** `return null`, com os guards **invertidos** —
>   `if (signals.count > 0) return <SignalsAlert/>; if (runDegraded) return null;`
>   — para não tocar `computeDataQualitySignals`. Pôr `runDegraded` no `count`
>   renderizaria *"1 pendência afeta a precisão"* com uma `<ul>` **vazia**. O
>   slot já renderiza `null` em produção por dois vizinhos, então não há salto de
>   layout novo. Predicado **positivo** (`renderiza ⟺ run entregou sem stage
>   degradado`): o negativo deixaria o run **cancelado** com E5 ainda afirmando
>   "sem pendências". Desfecho vem por `ReportResponse`/payload que a página já
>   espera — **não** por fetch novo, senão o PDF captura o `CleanBar` no primeiro
>   paint. Campo **obrigatório** no DTO, nunca `boolean | undefined`.
>   Aceite que importa: `pdftotext` do relatório degradado **não** contém "sem
>   pendências que afetem a leitura".
> - **Card:** `pipeline_runs_by_status` ancorado em `PipelineRun.started_at`
>   (invariante grátis: soma == `pipeline_runs_last_period`);
>   `stages_degraded_last_period` por `reason_class` **e por `stage`**, ancorado
>   em `PipelineStageLog.started_at`; **taxa** na tela (contagem sem denominador
>   não sustenta threshold). Zeros **estruturais** em DTOs aninhados, não
>   `dict[str, int]` — o dict gera `additionalProperties` no snapshot e
>   `noUncheckedIndexedAccess` do `frontend-ops` convida ao `?? 0` que
>   re-conflaciona ausência com zero. Agregação em **Python** com projeção de
>   coluna (query JSON-path seria a primeira do repo e a suíte de PR só roda
>   SQLite). `cost_usd` **nullable** + `cost_known` sempre — a semântica de 3
>   casos já existe em `LLMCallMetrics`; `0.0` no timeout caro é a mesma falha de
>   silêncio que o dono recusou.
> - **`frontend-ops` não está em NENHUM workflow de CI** — um `types.ts`
>   dessincronizado passa todos os gates. Fechar a falha específica com gate de
>   paridade em pytest (idioma do PR1) + 1 linha no `files_yaml`; CI do
>   `frontend-ops` é lane própria (A42).
> - **Índice de `pipeline_stage_logs`** fica dívida com gatilho medível: a forma
>   certa em Postgres é índice **parcial**, e escolher o composto agora é escolher
>   o índice errado com custo de migration.
> - **Cadência de leitura do card** vai para `RUNBOOK.md` §7.3 com número e
>   threshold. Card que ninguém abre tem o mesmo modo de falha do log sem sink —
>   esta casa já perdeu 45 dias de nightly desligado sem notar.
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
   > ⚠️ **REFUTADO 2026-08-07 por medição no PR2. Não aplique a prescrição
   > acima — ela É a regressão.** Duas premissas erradas: (a) `should_retry`
   > recebe `str(exc)[:2000]`, **não** o nome da classe, e o que chega ali é uma
   > `LLMError` que re-embrulha a mensagem do provider; (b) `_normalize` colapsa
   > `_` em espaço nos **dois** lados, então o corpo do erro
   > (`rate_limit_error` → `rate limit error`) **casa** `rate_limit` e **não**
   > casa `ratelimit`. Trocar para `ratelimit` desligaria um retry que funciona,
   > e `apistatus` não casa mensagem nenhuma.
   >
   > **O gap real, e era silencioso:** o overload da Anthropic (529 / 500
   > `overloaded_error`, o transiente mais comum em pico) é mapeado por litellm
   > para `InternalServerError`, cuja mensagem não contém nenhum dos 5 padrões
   > antigos. E a mensagem de timeout tem duas formas — `classify_error` conhece
   > ambas, a tabela conhecia uma. **Entregue:** acrescentados `overloaded`,
   > `529` e `timed out`; nada removido; tabela extraída para constante única
   > (era repetida 4×). Teste alimentado pelo produtor
   > (`backend/tests/test_stage_retry_vocabulary.py`), provado por mutação —
   > contra a tabela antiga, exatamente os 5 casos dos gaps ficam vermelhos.
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
   Débito já nomeado na [[ADR-357]] §Consequências, mantido. Medido no PR2: o
   campo tem **1 consumidor** no repo inteiro (`validate_full_order`) e ninguém lê
   o artifact stage `generate_narratives` — é nó órfão, não aresta validada.
7. **Aliasing do `DBArtifactStore` — P1, dono `data-engineer`, ADR própria.**
   `_maybe_decrypt` devolve `row.content_json` por **referência** e a coluna é
   `JSON` plain sem `MutableDict`: `read → mutar in-place → write` na mesma
   `(stage, key)` é **lost update silencioso** quando
   `ENCRYPT_PIPELINE_ARTIFACTS=False`. Provado empiricamente no PR2. O default
   `True` mascara em produção, e os harnesses que desligam não rodam E5.N — por
   isso ninguém tropeçou. A ADR nova **depende** da [[ADR-357]] §6: consertar o
   aliasing sem a exceção travada em pé abre o vetor de corrupção do deliverable
   que hoje é impedido pelo próprio defeito.
8. **Índice de `pipeline_stage_logs`** — o card filtra `status` + `started_at` em
   full scan. Dívida deliberada: a forma certa em Postgres é índice **parcial**
   (`WHERE status='degraded'`), que não existe em SQLite, então escolher o
   composto agora é escolher o índice errado com custo de migration. Gatilho de
   retomada: Postgres vivo **e** rows degradadas na casa dos milhares, **ou** p95
   do endpoint encostando no 1s do `SLO.md`.
9. **CI própria do `frontend-ops`** — lane A42. O app não está em nenhum workflow;
   o PR2 fechou só a falha específica (paridade do `types.ts` por pytest + 1 linha
   no `files_yaml`). Job mínimo defensável: `setup-node@v4` + `npm ci` +
   `typecheck` + `lint`, gateado por grupo `frontend_ops` novo, sem Playwright e
   sem `build`.

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
- Gate estático (`dev/check_stage_criticality.py`): todo stage até
  `analyze_finances` é `required`; todo stage **após** ele **declara**
  `criticality=` explicitamente — com qualquer valor. Falha se alguém inserir
  stage no meio sem decidir.
  > **Reconciliado 2026-08-07 no PR2.** A forma anterior pedia *"todo stage após
  > `analyze_finances` é `degradable`"*, o que **contradizia o §Delta item 3**
  > desta mesma lane — ele recusou a recíproca por forçar `validate_cross` para
  > dentro da classe por CI e transformar questão semântica em invariante de
  > pipeline. As duas seções foram escritas no mesmo dia e ninguém notou.
  >
  > Exigir **declaração** em vez de **valor** entrega o que este critério quer
  > (*"falha se alguém inserir stage no meio sem decidir"*) sem o que o §Delta
  > recusa: o CI cobra a decisão, não escolhe o valor. Por AST, porque o default
  > do dataclass é indistinguível do valor explícito em runtime — a declaração só
  > existe no texto do código. O gate também recusa
  > `commit_artifacts_on_degrade` em stage `required` (config morta) e valor fora
  > de `{required, degradable}`.
- `make update-openapi-snapshot` e `make update-db-schema-reference` ⇒ **diff
  vazio nos dois enums**. Diff no enum de **run** ⇒ alguém adicionou status novo
  e a [[ADR-357]] §3 foi violada.
  > **Corrigido 2026-08-07 por medição no PR2 — terceira revisão deste bullet.**
  > A forma anterior (*"o enum `PipelineStageStatus` ganha exatamente
  > `degraded`"*) acertou a superfície e errou **quem paga**: o PR1
  > (`4620cc04`/#1242) já declarou o membro Python, então `degraded` já está no
  > `openapi.json` e no `DB_SCHEMA_REFERENCE.md`. Lida ao pé da letra, ela
  > reprovaria o PR2 correto. Medido: os dois `make` não produzem diff.
  >
  > Se o PR2 acrescentar campo a `MetricsResponse` (§Decisões do dono, 2), o
  > snapshot ganha diff **não-enum** — esperado, e não é violação da §3.
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
