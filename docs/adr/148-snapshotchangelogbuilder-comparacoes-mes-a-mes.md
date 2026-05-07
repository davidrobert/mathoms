---
id: ADR-148
type: adr
title: "`SnapshotChangelogBuilder`: comparações mês-a-mês de relatório"
status: Decidido
phase: "Onda v2.D · v2.D.1"
date: "2026-04-27"
relates_to: ["[[ADR-082]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 148"]
tags:
  - area/multitenancy
  - area/pipeline
  - area/report
  - status/decidido
  - type/adr
size_lines: 248
---

# ADR-148 — `SnapshotChangelogBuilder`: comparações mês-a-mês de relatório

**Status:** Decidido (Onda v2.D · v2.D.1) • **Data:** 2026-04-27 •
**Relaciona** [ADR-082](#adr-082--pipelineartifact-artefatos-computacionais-no-banco)
(`pipeline_artifacts`),
[ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy)
(D1/D2/D3 — services com value-object config, sem `Path`/`dict`),
[ADR-106](#adr-106--opt-in-db-artifacts-por-workspace--dbartifactstore-no-celery-task-a6b)
(`DBArtifactStore`),
[ADR-117](#adr-117--report-premium-ui-baseline-paridade-com-exemplo_de_relatoriohtml)
(Report Premium UI baseline),
[ADR-120](#adr-120--readers-user-facing-consultam-artifactstore-db-first-com-fallback-disco)
(`read_latest_artifact`),
[ADR-122](#adr-122--chart_conclusions-e-section_summaries-em-modo-híbrido-template--llm)
(narrativas determinísticas vs. LLM),
[ADR-131](#adr-131--report-referencia-pipeline_artifact-por-fk-drop-analysis_json_path)
(`Report.analysis_artifact_id`),
[ADR-132](#adr-132--lifecycle-scoping-de-pipeline_artifacts-workspace-vs-run)
(workspace-scoped vs. run-scoped artefatos).

**Contexto:** [ADR-117](#adr-117--report-premium-ui-baseline-paridade-com-exemplo_de_relatoriohtml)
deferiu para v2 dois blocos visuais que o template
`EXEMPLO_DE_RELATORIO.html` exibe por seção: **comparison block**
("Patrimônio: antes R$ 800k → depois R$ 850k") e **changelog**
("S2 Fluxo de Caixa: receita +12%, despesas −3%"). A v2.1
(`agent/report-v2-yaml-placeholders/...`, mergeada 2026-04-26) plantou
os placeholders no [config/report_layout.yaml](../config/report_layout.yaml)
em S1/S2/S3/T2/T3/T5 com `enabled: false` e
`deferred_until: "v2.D.1 SnapshotChangelogBuilder"`. v2.D.1 entrega o
builder; v2.8 (lane separada) flipa `enabled: true`.

A lacuna técnica é que o pipeline produz **apenas o snapshot atual**
(`analyze_finances` em `pipeline_artifacts`). Não existe helper que
carregue o snapshot anterior do mesmo workspace e compute deltas. Sem
esse cálculo, ativar os placeholders renderiza seções vazias. Ativar com
narrativa LLM tem dois problemas independentes — custo (~31 textos por
relatório, [ADR-122](#adr-122--chart_conclusions-e-section_summaries-em-modo-híbrido-template--llm))
e a falta dos números brutos para a LLM trabalhar em cima. Builder
determinístico resolve ambos: produz números (que a UI renderiza
diretamente) e dá insumo para a v2.9 LLM-driven futura.

Decisões precisaram ser tomadas em quatro eixos antes de codar:

**D1 — onde mora o snapshot t-1.** Três alternativas:

1. **Tabela nova `snapshot_changelog`** com `(workspace_id,
   period_yyyymm, analysis_hash, content_json)`. Permite TTL/retenção
   explícita e desacopla de `pipeline_artifacts`, mas duplica payload
   (~40-100 KB × N reports), exige migration nova, e replica o que
   `pipeline_artifacts` já modela. Rejeitado.
2. **Re-rodar `analyze_finances` com `as_of=t-1`** sob demanda. Caro
   (LLM em E5.N) e introduz não-determinismo (a LLM de t-1 ≠ a LLM de
   hoje). Rejeitado.
3. **Reusar `pipeline_artifacts`** — query "último
   `analyze_finances` do workspace com `created_at < current`". Único
   ponto de verdade (consistente com [ADR-131](#adr-131--report-referencia-pipeline_artifact-por-fk-drop-analysis_json_path));
   zero migration; respeita
   [ADR-129](#adr-129--descontinuação-completa-do-renderer-html-server-side)
   (sem disco). **Escolhido.**

**D2 — granularidade do delta.**

1. **Por seção** (5 ComparisonItems: S1/S2/S3/T2/T5; ChangelogList
   global ≤10 entradas). Simples de testar, rendering óbvio.
2. **Por KPI** (~30 deltas — patrimônio bruto, líquido, receita
   recorrente, despesas recorrentes, score, etc.). Rico mas
   barulhento; UI vira "tabela de mudanças" em vez de "leitura
   editorial".
3. **Híbrido** — (a) por seção + drill-down (b) num modal/popover.

**Escolhido (a).** (c) é v3 se houver demanda por drill-down; YAGNI
agora.

**D3 — primeiro relatório do workspace** (sem t-1 disponível). Builder
retorna `ComparisonResult(items=[], entries=[], has_previous=False)`.
Endpoint serializa `comparisons: null, changelog: null` (não array
vazio). Frontend renderiza condicionalmente
(`data.comparisons && data.comparisons.length > 0`). Distinção entre
`null` (não há t-1) e `[]` (há t-1, mas todos os deltas abaixo do
threshold) está intencionalmente preservada — a UI pode exibir copy
diferente ("Primeiro relatório — sem comparativo" vs. "Sem mudanças
materiais desde o último relatório").

**D4 — narrativa determinística vs. LLM.** Builder é **puro cálculo +
template** ("Patrimônio cresceu 6% desde o relatório anterior"),
seguindo o lado determinístico do híbrido de
[ADR-122](#adr-122--chart_conclusions-e-section_summaries-em-modo-híbrido-template--llm).
LLM reescreve a narrativa numa lane v2.9 futura, usando `summary` do
`ChangelogEntry` como input. Dois benefícios concretos: (1) v2.D.1
fecha sem dependência Anthropic; (2) o `delta_signal` + números ficam
estáveis e cacheáveis, mesmo se a redação mudar.

**Decisão:**

1. **Storage = `pipeline_artifacts` reuso.** Snapshot t-1 é resolvido
   por query

   ```sql
   SELECT * FROM pipeline_artifacts
   WHERE workspace_id = :ws
     AND stage IN ('analyze_finances', 'E5')
     AND artifact_key = 'analise_financeira'
     AND created_at < :current_created_at
   ORDER BY created_at DESC
   LIMIT 1
   ```

   Nenhuma tabela nova. Nenhuma migration de dados. Adapter backend
   (`backend/app/services/snapshot_pair_loader.py`) executa a query
   via SQLAlchemy; service de domínio
   (`pipeline/domain/services/snapshot_changelog/builder.py`) recebe
   duas dataclasses `AnalyzeFinancesSnapshot` e devolve
   `ComparisonResult` — zero importação de
   `fastapi`/`sqlalchemy`/`celery` em `pipeline/**` (gate de
   `dev/check_pipeline_boundaries.py`).

   **Por que `stage IN (...)`:** janela de compat
   [ADR-093](#adr-093--rename-completo-de-identificadores-de-stage-opção-a)
   continua aberta — `pipeline_artifacts.stage` aceita tanto `"E5"`
   (legado, pré-F9.3) quanto `"analyze_finances"` (descritivo). O
   loader normaliza via `to_legacy_stage_name`/`resolve_stage_name`.

2. **Identidade de snapshot derivada, não persistida.** A "key" lógica
   do snapshot — pedida no spec original como `(workspace_id,
   period_yyyymm, analysis_hash)` — é **calculada on-read** a partir
   do próprio artefato:

   - `workspace_id` — coluna direta em `pipeline_artifacts`.
   - `period_yyyymm` — extraído de `content_json["periodo"]` ou
     análogo, formato `YYYYMM`.
   - `analysis_hash` — `sha256(canonical_json(content_json))[:16]`,
     truncado, calculado em memória pelo loader. Útil para invalidar
     caches client-side; **não** é coluna nova no DB.

   Valor: zero schema change, identidade estável, comparações
   idempotentes (mesmo par sempre produz mesmo `ComparisonResult`).

3. **Granularidade = por seção (D2.a).**
   `ComparisonResult.items: list[ComparisonItem]` com 1 item por
   seção em `sections_to_compare` (default `("S1", "S2", "S3", "T2",
   "T5")`). Cada item carrega `before/after/delta_pct` em `Decimal`
   ([ADR-090](#adr-090--decimal-para-valores-monetários)).
   `ComparisonResult.entries: list[ChangelogEntry]` com 1 entrada por
   seção que cruza `minimum_delta_pct` (default `Decimal("0.5")` =
   meio porcento — abaixo, "stable"). Drill-down por KPI é v3.

4. **Primeiro relatório (D3) = `null` no wire.** Endpoint devolve
   `comparisons: null, changelog: null`. Frontend renderiza nada.

5. **Narrativa = template determinístico (D4).** `ChangelogEntry.summary`
   é construído por `format_summary(item)` em
   `pipeline/domain/services/snapshot_changelog/narratives.py` —
   templates por seção, sem LLM. `delta_signal: Literal["up", "down",
   "stable"]` derivado de `delta_pct` e `minimum_delta_pct`.

6. **Retenção: indefinida.** Comparativos consultam toda a história
   do workspace. Em workspaces com 100+ reports, query escala via
   índice existente
   `ix_pipeline_artifacts_workspace_stage_key (workspace_id, stage,
   artifact_key)` — cobre o predicado, embora `ORDER BY created_at
   DESC LIMIT 1` ainda exija sort do subset. Se latência observada
   passar de 50ms em produção, criar índice
   `ix_pipeline_artifacts_workspace_stage_created_desc
   (workspace_id, stage, created_at DESC)` em ADR/migration
   subsequente — **não** nesta. Premissa: ≤100 reports/workspace
   no horizonte de 12 meses; o sort é trivial nesse range.

7. **Endpoint contract (entrega v2.D.1 fica em **builder + service**;
   wire-up no endpoint `GET /v1/.../reports/:id` é parte de v2.8).** O
   shape final do payload, quando v2.8 ativar, é
   `comparisons: ComparisonItemRead[] | null` e
   `changelog: ChangelogEntryRead[] | null` em
   `ReportAnalysisData`. v2.D.1 já entrega os DTOs Pydantic e o
   service; v2.8 conecta no endpoint + flipa o YAML +
   `make update-openapi-snapshot`.

**Hook de persistência (FASE 2 desta lane):** snapshot atual já é
escrito por E5
([pipeline/stages/analyze_finances.py](../pipeline/stages/analyze_finances.py)
via `ctx.get_artifact_store().write(...)`). **Nenhum hook novo no E5
é necessário** — o builder consome o que já existe. Isto é
intencional: lane v2.D.1 não muda o contrato de escrita de E5; muda
apenas a leitura comparativa, que vive em
`backend/app/services/snapshot_pair_loader.py` e é chamada
on-demand pelo endpoint.

**Consequências:**

- ✅ **Zero schema change.** Nenhuma migration Alembic, nenhuma
  tabela nova, nenhuma duplicação de payload. Coerente com
  [ADR-131](#adr-131--report-referencia-pipeline_artifact-por-fk-drop-analysis_json_path)
  (single source of truth) e
  [ADR-132](#adr-132--lifecycle-scoping-de-pipeline_artifacts-workspace-vs-run)
  (lifecycle workspace-wide para reads cross-run).
- ✅ **Builder determinístico, sem LLM, sem dependência externa.**
  100% testável com goldens em fixtures sintéticas
  ([ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy)
  D2/D3). Cobertura de paridade legado-↔-novo não se aplica (feature
  nova). Money em `Decimal`
  ([ADR-090](#adr-090--decimal-para-valores-monetários)) end-to-end.
- ✅ **Pipeline-domain rigoroso.** Builder em
  `pipeline/domain/services/snapshot_changelog/` não importa
  fastapi/celery/sqlalchemy
  (gate `dev/check_pipeline_boundaries.py`). I/O fica no adapter
  backend; service recebe duas dataclasses prontas.
- ✅ **Custo de leitura previsível.** 1 query a mais por
  `GET /reports/:id` (fora do hot path do dashboard).
  `read_latest_artifact`-pattern reaproveitado
  ([ADR-120](#adr-120--readers-user-facing-consultam-artifactstore-db-first-com-fallback-disco)).
  Sem cache em memória ([ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6));
  se hot path no futuro, Redis 60s TTL é trivial.
- ⚠️ **Identidade de snapshot é derivada, não autoritativa.** Se
  duas runs no mesmo dia produzirem `content_json` byte-idêntico,
  o `analysis_hash` colide — aceito, porque o `created_at` quebra
  empate na ordenação e o `pipeline_artifacts.id` é estável.
- ⚠️ **Threshold global de "stable" (0,5%).** Não há override por
  seção em v2.D.1. Se o produto pedir "patrimônio é mais sensível
  que despesas", value-object `SnapshotChangelogConfig.thresholds:
  Mapping[str, Decimal]` é extensão aditiva sem ADR nova.
- ⚠️ **Workspaces com 100+ reports.** Query escala até ~10k
  reports/workspace via índice atual; se vazar, índice composto
  com `created_at DESC` resolve em 1 migration. **Não criado nesta
  ADR** — premissa de horizonte ≤100 reports/workspace por 12 meses.
- ❌ **Drill-down por KPI adiado para v3.** Decisão D2.a aceita
  trade-off de UI "editorial" sobre "tabela de auditoria".
- ❌ **Retenção indefinida.** Não há TTL/GC nas comparações. Aceito
  porque a comparação consulta sempre o mais recente t-1; reports
  antigos não viram custo de query (o `LIMIT 1` os ignora). GC
  pode entrar em ADR futura se o crescimento de
  `pipeline_artifacts` virar problema operacional — escopo
  separado.

**Coordenação com lanes vivas:**

- **v2.5 (`score?: ScoreData` top-level)** — absorvida pela v2.E.7
  ([ADR-139](#adr-139--finalização-migração-rechartschartjs-em-reports)).
  `ReportAnalysisData` ganha `comparisons?` e `changelog?` em v2.D.1
  (FASE 2) sem colisão com `score?` — campos disjuntos.
- **v2.9 (LLM section_summaries)** — independente. Quando v2.9
  entrar, `ChangelogEntry.summary` pode upgrade para LLM-driven em
  lane v3 separada; o cálculo e o `delta_signal` permanecem
  determinísticos.
- **v2.10 (PDF visual diff)** — quando v2.8 ativar
  `comparisons`/`changelog` no YAML, baselines vão regerar.
  Comunicar no chat de coordenação para o agente de v2.10
  re-baselinar.
