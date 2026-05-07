---
id: TRACK-report-v2-changelog-engine
type: track
title: "Track Report v2.D.1 + v2.8 — Snapshot changelog engine + comparisons/changelog ON"
sprint: A11
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a11
  - status/consumed
---

# Track Report v2.D.1 + v2.8 — Snapshot changelog engine + comparisons/changelog ON

> **Lane ID:** `report-v2-changelog-engine` (cobre v2.D.1 + v2.8 — domínio
> + ativação fazem mais sentido juntos)
> **Branch prefix:** `agent/report-v2-changelog-engine/<yyyyMMdd-HHmm>`
> **Depende de:** v2.1 ✅ (placeholders `enabled:false` no YAML); v1 ✅
> **Paralelo com:** Onda v2.A já fechada; Onda v2.B (v2.4/v2.5/v2.6) e
> Onda v2.C (v2.7/v2.9/v2.10) **não** conflitam — mexem em arquivos
> disjuntos
> **Conflita com:** qualquer agente em
> `pipeline/domain/services/`, `backend/app/services/`, ou tocando
> `comparisons_*` / `changelog_*` no YAML
> **Onda v2:** D (enabler) + ativação v2.8
> **Sprint:** Report Premium UI · v2
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:**
> - [plan/REPORT_PREMIUM/_README.md §0.2 #4 + §17](../plan/REPORT_PREMIUM/_README.md)
>   (delta original "comparisons/changelog diferidos para v2 — depende
>   de SnapshotChangelogBuilder")
> - [BACKLOG.md — Report Premium UI v2 lanes](../BACKLOG.md#report-premium-ui--paridade-com-exemplo_de_relatoriohtml)
> - Auditoria 2026-04-25 §3.1 + §2.3 (origem do escopo)
> - Meta-prompt: [track_report_v2.md](track_report_v2.md)

> **Objetivo (1 frase):** construir o `SnapshotChangelogBuilder` que
> calcula deltas entre o snapshot atual (t) e o snapshot anterior (t-1)
> de cada relatório **e** ativar os blocos `comparisons` / `changelog`
> no YAML para renderizar `<ComparisonBlock>` e `<ChangelogList>` com
> dados reais.

---

## 1. Por que esta lane (e por que a fundi com v2.8)

A v1 deferiu duas features visuais a v2 (Delta #4 do plano):

- **Comparison block** — ex.: "Patrimônio: antes R$ 800k → depois R$ 850k"
  por seção, quando há snapshot anterior.
- **Changelog** — ex.: "S2 Fluxo de Caixa: receita +12%, despesas -3%"
  por seção, narrativa de "o que mudou desde o último relatório".

Ambos requerem **comparar dois snapshots E5** (current vs t-1) e
calcular deltas. Esse cálculo não existe — o pipeline hoje produz só o
snapshot atual; não há helper que carregue o anterior e faça diff.

`SnapshotChangelogBuilder` é o domain service que falta. Sem ele,
v2.8 (ativar no YAML) não tem dados para renderizar — flipar
`enabled:true` produziria seções vazias.

**Por que fundir v2.D.1 e v2.8:** Builder isolado sem consumo é YAGNI.
Ativação sem builder produz UI quebrada. Acoplar reduz risco e fecha
o débito de uma vez.

---

## 2. ⚠️ Decisões pendentes (gates antes de codar)

### Decisão D1 — onde mora o snapshot t-1?

| Opção | Trade-off |
|-------|-----------|
| **(a) `pipeline_artifacts` table** — query "último `analyze_finances` antes do current" | Limpo; já existe; respeita ADR-129 (sem disco). |
| **(b) Re-roda E5 com `as_of=t-1`** — caro mas determinístico | Lento; rejeitado. |
| **(c) Snapshot dump em S3/disco** | Viola ADR-129 (sem disco). Rejeitado. |

**Default sugerido:** (a). Verifica se `ArtifactStore.list_versions()`
ou similar já expõe; senão estende. Provavelmente já há helper em
`backend/app/services/artifact_reader.py` (ver ADR-120
`read_latest_artifact`).

### Decisão D2 — granularidade do delta

| Opção | Descrição |
|-------|-----------|
| **(a) Por seção** | 1 ComparisonBlock por seção S1/S2/S3/T2/T5; ChangelogList global |
| **(b) Por KPI** | Delta para cada KPI (~30 deltas no total); rico mas barulhento |
| **(c) Híbrido** | Por seção (a) + drill-down opcional (b) num modal |

**Default sugerido:** (a). Comece simples — drill-down (c) entra v3
se houver demanda.

### Decisão D3 — primeiro relatório do workspace

Quando NÃO há snapshot t-1 (primeiro relatório):
- ComparisonBlock: hidden gracefully (CSS `display:none` via
  `enabled` do data, não do layout).
- ChangelogList: mostra item único "Primeiro relatório — sem
  comparativo" OU hidden.

**Default sugerido:** hidden total no primeiro relatório; backend
retorna `null` em `comparisons` e `changelog` em vez de array vazio.
Frontend renderiza condicionalmente.

### Decisão D4 — ADR ou nota inline?

Nova ADR (ADR-13X) **obrigatória** porque:
- Adiciona contrato no `ReportAnalysisData`.
- Define semântica de "snapshot anterior" (mais recente t < t_current?
  ou versionado pelo usuário?).
- Define retenção: queries comparativas indefinidamente ou só últimos N?

Sem ADR, a próxima rotação de equipe não saberá decidir.

---

## 3. Regras inegociáveis

- **`pipeline/**` não importa `fastapi`/`celery`/`sqlalchemy`** — query
  do snapshot t-1 fica em `backend/app/services/` ou em adapter; service
  em `pipeline/domain/services/` recebe duas dataclasses (current + prev).
- **Money sempre `Decimal`/`Money`** (ADR-090). Deltas % calculados com
  Decimal, formatados via `<MonetaryValue/>` ou helper.
- **Stateless rigoroso** (ADR-111) — sem cache em memória; usar Redis
  se ficar caro.
- **Endpoint JSON novo** → `response_model` + `make update-openapi-snapshot`.
- **Goldens de paridade** — adicionar fixture `tests/fixtures/snapshot_pair/`
  com t e t-1, golden test calcula diff e bate JSON esperado byte-a-byte.
- **Sem LLM nesta lane.** Builder é puro cálculo. Narrativas LLM são
  v2.9 (independente).
- **Pre-flight de hotspot** se editar `BACKLOG.md`,
  `plan/REPORT_PREMIUM/_README.md`, `CHANGELOG.md`, `DECISIONS.md`.

---

## 4. Entregas

### 4.1 ADR-13X — Snapshot comparison semantics

**Arquivo:** [docs/DECISIONS.md](../DECISIONS.md) — adicionar nova ADR
ao final.

Conteúdo (esqueleto):

```markdown
### ADR-13X — `SnapshotChangelogBuilder` e contrato `comparisons`/`changelog`

**Status:** Decidida (2026-XX-XX). · **Sprint:** Report Premium UI v2.

**Contexto:** v1 deferiu `comparisons` + `changelog` para v2 (Delta #4
do plano). Lacuna técnica: pipeline produz só snapshot atual.

**Decisão:**
- "Snapshot t-1" = último `analyze_finances` em `pipeline_artifacts`
  com `created_at < t_current`, mesmo workspace, status `completed`.
- Builder é determinístico (sem LLM); deltas % = Decimal.
- Granularidade D2 = (a) por seção; KPIs drill-down adiado v3.
- Primeiro relatório → backend retorna `null`; frontend renderiza nada.
- Retenção: query indefinida; otimizar via index `(workspace_id, created_at DESC, stage)`.

**Consequências:**
- Frontend ganha `data.comparisons: ComparisonBlock[] | null` e
  `data.changelog: ChangelogEntry[] | null`.
- Backend endpoint `/v1/.../reports/:id` faz join opcional.
- `<ComparisonBlock>` e `<ChangelogList>` (já existem) ganham consumidores.
```

### 4.2 `SnapshotChangelogBuilder` em pipeline/domain

**Arquivo:** `pipeline/domain/services/snapshot_changelog_builder.py` (novo)

```python
from decimal import Decimal
from dataclasses import dataclass

@dataclass(frozen=True)
class ComparisonItem:
    section_id: str
    label: str
    before: Decimal
    after: Decimal
    delta_pct: Decimal

@dataclass(frozen=True)
class ChangelogEntry:
    section_id: str
    summary: str  # template determinístico, sem LLM
    delta_signal: str  # "up" | "down" | "stable"

@dataclass(frozen=True)
class SnapshotChangelogConfig:
    sections_to_compare: tuple[str, ...]  # ex.: ("S1", "S2", "S3", "T2")
    minimum_delta_pct: Decimal  # ex.: Decimal("0.5") — abaixo disso, "stable"

class SnapshotChangelogBuilder:
    def __init__(self, config: SnapshotChangelogConfig) -> None: ...

    def build(
        self,
        current: AnalyzeFinancesResult,
        previous: AnalyzeFinancesResult | None,
    ) -> tuple[list[ComparisonItem], list[ChangelogEntry]]: ...
```

ISP rigoroso (ADR-089/097) — recebe value object config, não
`StageConfig`.

### 4.3 Backend adapter — busca o t-1

**Arquivo:** `backend/app/services/snapshot_pair_loader.py` (novo)

Service backend (ele pode importar SQLAlchemy) que:
1. Recebe `workspace_id` + `report_id`.
2. Busca current via `read_latest_artifact("analyze_finances", workspace_id)`.
3. Busca anterior via query
   `SELECT * FROM pipeline_artifacts WHERE workspace_id = ? AND stage = 'analyze_finances' AND status = 'completed' AND created_at < ? ORDER BY created_at DESC LIMIT 1`.
4. Devolve par `(current_dto, previous_dto | None)`.
5. Chama `SnapshotChangelogBuilder.build()` com o par.

Index recomendado em Alembic:

```python
op.create_index(
    "ix_pipeline_artifacts_workspace_stage_created",
    "pipeline_artifacts",
    ["workspace_id", "stage", "created_at"],
    postgresql_using="btree",
)
```

### 4.4 DTOs e endpoint

**Arquivos:**
- `backend/app/schemas/dto/report/comparison.py` (novo)
- `backend/app/schemas/dto/report/changelog.py` (novo)
- `backend/app/api/reports.py` (existente — endpoint `GET /v1/.../reports/:id`)

Adicionar `comparisons: list[ComparisonItemRead] | None` e
`changelog: list[ChangelogEntryRead] | None` ao response. **Não
breaking** — campos opcionais, `null` para reports antigos.

`make update-openapi-snapshot` — comitar diff.

### 4.5 Frontend — types + render

**Arquivos:**
- [`frontend/src/types/report-analysis.ts`](../../frontend/src/types/report-analysis.ts)
  — adicionar `comparisons?: readonly ComparisonItem[] | null;
  changelog?: readonly ChangelogEntry[] | null`.
- [`frontend/src/components/report/sections/S1PatrimonioSection.tsx`](../../frontend/src/components/report/sections/S1PatrimonioSection.tsx)
  e similares — render condicional de `<ComparisonBlock>`.
- Componente `<ChangelogList>` (já existe em `ui/`) consumido por
  S10 ou nova seção dedicada (decidir com base em D2).

### 4.6 YAML — flipar enabled

**Arquivo:** [config/report_layout.yaml](../../config/report_layout.yaml)

Mudar todos os `comparisons_*` e `changelog_*` (placeholders criados
em v2.1) para `enabled: true`. Codegen, comitar TS+py.

### 4.7 Goldens de paridade

**Arquivo:** `tests/test_snapshot_changelog_builder.py` (novo)

Fixture `tests/fixtures/snapshot_pair/{current,previous}.json`. Builder
roda → produz JSON; comparado byte-a-byte com
`expected_changelog.json`. Tolerância 0,01 BRL na whitelist monetária
(padrão Caminho B).

Golden test E2E:
`tests/test_snapshot_changelog_e2e.py` — pipeline real produz par,
backend service consome, retorno do endpoint bate.

### 4.8 Frontend tests

- Vitest unitário para `<ComparisonBlock>` e `<ChangelogList>` com
  fixtures sintéticas.
- Playwright `@critical` snapshot por seção — atualizar baselines onde
  o ComparisonBlock agora aparece.

### 4.9 Atualizar docs

- [BACKLOG.md](../BACKLOG.md) — marcar v2.D.1 ✅, marcar v2.8 ✅,
  remover "comparisons e changelog" da lista de débitos da seção
  Report Premium UI.
- [plan/REPORT_PREMIUM/_README.md §17](../plan/REPORT_PREMIUM/_README.md) — atualizar.
- [CHANGELOG.md](../CHANGELOG.md) — entrada `feat(report):
  SnapshotChangelogBuilder + comparisons/changelog ativados (v2.D.1 +
  v2.8 · ADR-13X)`.

---

## 5. Sequência de commits sugerida (10-12 commits coesos)

```
1. docs(adr): ADR-13X — SnapshotChangelogBuilder semantics
2. feat(domain): SnapshotChangelogBuilder + Pydantic config
3. test(domain): goldens snapshot pair
4. feat(backend): snapshot_pair_loader service
5. db(backend): index ix_pipeline_artifacts_workspace_stage_created
6. feat(api): comparisons + changelog em GET /reports/:id
7. chore(openapi): update snapshot
8. feat(types): comparisons + changelog em ReportAnalysisData
9. feat(report): S1/S2/S3 renderizam ComparisonBlock; S10 ChangelogList
10. feat(layout): flipar enabled:true em comparisons/changelog
11. test(report): vitest + playwright snapshots atualizados
12. docs(report): v2.D.1 + v2.8 ✅ — BACKLOG + PLAN + CHANGELOG
```

---

## 6. Gates de push

```bash
pre-commit run --all-files
pytest tests -q                                # pipeline goldens
pytest backend/tests -q                        # backend service + endpoint
cd frontend && npm test -- --run               # vitest
cd frontend && npm run test:e2e -- --grep "@critical"
cd frontend && npm run build
```

**Pre-push drift check** obrigatório.

**Smoke humano:** abrir 2 relatórios reais (com e sem snapshot t-1) e
confirmar render correto antes de fechar a lane.

---

## 7. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Query `pipeline_artifacts` lenta sem index | A | M | Index Alembic na entrega 4.3 |
| Goldens E5 quebram em massa | M | A | Campo `comparisons` é **aditivo opcional** — goldens existentes não mudam |
| `<ComparisonBlock>` renderiza vazio em primeiro report | A | B | Render condicional `data.comparisons && data.comparisons.length > 0` |
| Workspace com 100+ reports — query escala? | B | M | Index resolve até ~10k reports/workspace; reavaliar se vazar |
| Decimal precision drift entre Python e JS | B | M | Wire = string decimal; render via `Money` helper; teste explícito |

---

## 8. Coordenação com outras lanes

- **v2.1 (placeholders YAML):** já fechada antes desta lane começar
  (pré-requisito).
- **v2.5 (`score` top-level):** se ainda aberta, coordene tipos —
  `ReportAnalysisData` é compartilhado.
- **v2.9 (LLM section_summaries):** roda em paralelo. Se v2.9 fechar
  primeiro, `summary` do `ChangelogEntry` pode upgrade para LLM-driven
  numa lane v3 separada.
- **v2.10 (PDF visual diff):** baselines vão regerar — comunique no
  chat para agente de v2.10 re-baselinar.

---

## 9. Anti-escopo

- **LLM em narrativas.** `summary` do `ChangelogEntry` é template
  determinístico ("Patrimônio cresceu 6%"). LLM = v2.9 separada.
- **Drill-down por KPI.** D2=(a) — fica para v3.
- **Edição manual de comparisons** ("consultor escreve à mão"). v3.
- **Reabrir Fases 0-10.** Tocar shell apenas onde explicitamente listado
  (entrega 4.5).
- **Mexer em `e6_render.py`/SSR/HTML standalone.** Morto ADR-129.
- **Adicionar campos não-listados** ao `ReportAnalysisData`. Se
  precisar de mais, abrir ADR e nova lane.

---

## 10. Estimativa

3-5 dias úteis (1 agente serial). Distribuição:

- D1-D4 + ADR-13X: 0.5 dia
- Builder + goldens (4.2, 4.7): 1 dia
- Backend service + index + endpoint (4.3, 4.4): 1 dia
- Frontend types + render (4.5, 4.6): 1 dia
- Tests E2E + snapshots (4.8): 0.5 dia
- Docs (4.9): 0.5 dia

**Commits esperados:** 10-12 (ver §5).

---

## 11. Definição de feito

1. ADR-13X mergeada em `main`.
2. `SnapshotChangelogBuilder` com 100% goldens verdes.
3. Endpoint retorna `comparisons`/`changelog` para reports com t-1,
   `null` para primeiros reports.
4. UI renderiza `<ComparisonBlock>` em S1/S2/S3 e `<ChangelogList>` em
   S10 (ou conforme D2 final).
5. YAML flipado para `enabled: true`.
6. Smoke humano em 2 relatórios reais (com e sem t-1) ✅.
7. BACKLOG marca v2.D.1 ✅ + v2.8 ✅; débito #3 da seção Report
   Premium UI removido.
8. CHANGELOG com entrada consolidada.
