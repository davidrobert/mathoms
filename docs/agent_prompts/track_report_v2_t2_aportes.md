# Track Report v2.4 — T2 Aportes seção real

> **Status:** ✅ **2026-04-27** — entregue via commits `0805a87` (feat) + `38aa0ee` (refactor honrando 20 linhas).
> Decisão final: **D1=(a) MVP determinístico** (dados já existem em `dashboard.aportes` + `dashboard.investimentos_delta`; nenhuma mudança de pipeline/backend). Detalhes em [CHANGELOG](../CHANGELOG.md) e [BACKLOG v2.4](../BACKLOG.md).
>
> **Lane ID:** `report-v2-t2-aportes`
> **Branch prefix:** `agent/report-v2-t2-aportes/<yyyyMMdd-HHmm>`
> **Depende de:** v1 ✅; **idealmente** v2.5 (`score` top-level DTO) antes
> — evita conflito em `frontend/src/types/report-analysis.ts`. Se v2.5
> ainda não fechou, coordene ou rode v2.5 nesta mesma lane (split em 2
> commits sequenciais).
> **Paralelo com:** v2.1, v2.2, v2.3, v2.6, v2.7, v2.10 (tocam arquivos
> disjuntos)
> **Conflita com:** v2.5 (mesmos types), qualquer agente em
> `frontend/src/components/report/sections/TaticoSections.tsx`
> **Onda v2:** B
> **Sprint:** Report Premium UI · v2
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:**
> - [REPORT_PREMIUM_PLAN.md §17 — v2 roadmap](../REPORT_PREMIUM_PLAN.md)
> - [BACKLOG.md — Report Premium UI v2 lanes](../BACKLOG.md#report-premium-ui--paridade-com-exemplo_de_relatoriohtml)
> - Auditoria 2026-04-25 §3.2 (origem do escopo)
> - Meta-prompt: [track_report_v2.md](track_report_v2.md)

> **Objetivo (1 frase):** transformar a seção T2 (Tático · Aportes) de
> stub "estará disponível…" em seção real com KPIs e gráfico de aportes
> mensais, alimentada pelo snapshot E5 — fechando o débito em que a
> Fase 8 da v1 foi marcada ✅ embora T2 nunca tenha sido implementada.

---

## 1. Por que esta lane

[TaticoSections.tsx:96-106](../../frontend/src/components/report/sections/TaticoSections.tsx)
hoje tem:

```tsx
export function T2AportesSection({ data: _data }: { data: ReportAnalysisData }) {
  return (
    <ReportSection id="T2" title="Aportes e Investimentos">
      <ReportCard variant="feature" title="Aportes e Variação Patrimonial">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Dados de aportes detalhados estarão disponíveis com a integração
          do dashboard operacional.
        </p>
      </ReportCard>
    </ReportSection>
  );
}
```

A v1 marcou Fase 8 ✅ ("T1/T3/T5/T6 wired") — mas T2 ficou stub
silenciosamente. Para um leitor do BACKLOG isso parece "entregue", para
o usuário parece "feature falha". Esta lane fecha a inconsistência.

---

## 2. ⚠️ Decisões de produto pendentes — alinhar com dono ANTES de codar

T2 é seção de **modo Tático** (dashboard operacional). O exemplo HTML não
deixa T2 explícito do mesmo jeito que T1/T3/T6. Três caminhos possíveis:

### Decisão D1 — escopo de T2

| Opção | Descrição | Esforço |
|-------|-----------|---------|
| **(a) MVP determinístico** | KPIs simples derivados do snapshot existente: total aportado YTD, aporte médio mensal, comparação aporte vs receita, sequência de aportes (gráfico bar mensal). Sem campo novo no E5. | S (½ dia) |
| **(b) Médio com derivação leve** | (a) + adapter `aportesAdapter.ts` em `utils/` que cruza aportes × variação patrimonial; gráfico combo (bar aportes + line patrimônio). Sem campo novo no E5. | R (1 dia) |
| **(c) Completo — extensão E5** | Novo campo `aportes_detalhe` em `ReportAnalysisData` com breakdown por classe de ativo + projeção; service novo `aportes_analyzer.py` em pipeline. Goldens E5 atualizam. | O (3-4 dias) |

**Default sugerido:** (b). Ainda determinístico (sem LLM, sem novo
campo de pipeline), mas suficientemente rico para T2 deixar de parecer
placeholder. Se dono quer (c), abrir lane separada `report-v2-aportes-e5`
e fechar esta lane com (a)+(b).

### Decisão D2 — fonte de dados

Conferir com dono **e código**:
- `data.aportes` existe em `ReportAnalysisData`? (grep
  `frontend/src/types/report-analysis.ts`)
- `data.fluxo_caixa.aportes_*` existe?
- `data.dashboard.aportes_check` existe? — visto em
  [report_layout.yaml:376-394](../../config/report_layout.yaml).
- Onde está o snapshot canônico de aportes mensais?

Resposta provável (confirmar): `data.dashboard.aportes_check` traz
KPI agregado mensal; detalhe por mês precisa derivar de
`data.transacoes` filtrando por categoria/tag de aporte.

### Decisão D3 — gráfico

| Opção | Componente |
|-------|------------|
| Bar simples mensal | [`ChartBar`](../../frontend/src/components/report/charts/primitives/) |
| Combo aporte vs patrimônio | [`ChartCombo`](../../frontend/src/components/report/charts/primitives/) |
| Stacked por classe | [`ChartStackedBar`](../../frontend/src/components/report/charts/primitives/) |

**Default sugerido:** ChartCombo (bar aporte mensal + line patrimônio
acumulado). Reaproveita primitivo já testado.

---

## 3. Regras inegociáveis

- **Sem `any`/`Dict[str, Any]`.** `ReportAnalysisData` é o contrato; se
  algum campo de aportes ainda não está tipado, **adicionar tipo**
  (não `as Record<string, number>`).
- **Dinheiro nunca é `float`.** Aportes vêm como `Money.brl`/Decimal
  string no wire. Renderizar com `<MonetaryValue/>` (ADR-090).
- **Determinístico por padrão.** Esta lane **não** introduz LLM.
  Se opção (c) for escolhida e exigir analyzer, deve ser puro Python
  numérico — deixar LLM para v2.9.
- **Sem mocks de produção** no commit final. Se durante dev você
  hardcoded valores para ver render, remover antes de push (ESLint
  catch sometimes; verifique manualmente).
- **Sem reabrir T1/T3/T5/T6.** Eles funcionam — só toque T2.
- **Pre-flight de hotspot** se editar `BACKLOG.md` ou
  `REPORT_PREMIUM_PLAN.md` (CLAUDE.md §Hotspots).

---

## 4. Entregas

### 4.1 (sempre) Substituir stub

**Arquivo:** [frontend/src/components/report/sections/TaticoSections.tsx](../../frontend/src/components/report/sections/TaticoSections.tsx)

Trocar `T2AportesSection` por implementação real conforme D1.

**KPIs mínimos (D1=a+b):**
- Total aportado no período
- Aporte médio mensal
- Aporte previsto (se `orcamento_prospectivo.aporte_mensal` existir)
- % de meta atingida (se `meta_if` existir)

### 4.2 (se D1=b ou c) Novo adapter

**Arquivo:** `frontend/src/components/report/utils/aportesAdapter.ts` (novo)

Função pura que recebe `ReportAnalysisData` e retorna shape do gráfico:

```ts
export interface AportesChartData {
  readonly labels: readonly string[];        // meses YYYY-MM
  readonly aportes: readonly number[];       // BRL
  readonly patrimonio: readonly number[];    // BRL acumulado
}

export function deriveAportesChart(data: ReportAnalysisData): AportesChartData;
```

Testes Vitest em `frontend/src/components/report/utils/__tests__/aportesAdapter.test.ts`.

### 4.3 (sempre) Layout YAML

**Arquivo:** [config/report_layout.yaml](../../config/report_layout.yaml)

Atualizar bloco `tatico:` seção T2 para refletir conteúdo real (KPIs,
chart_id, conclusion). Exemplo:

```yaml
- id: "T2"
  title: "Aportes e Investimentos"
  enabled: true
  collapsible: true
  data_source: "dashboard.aportes_check + fluxo_caixa.aportes_*"
  kpis:
    - id: "total_aportado_ytd"
      enabled: true
    - id: "aporte_medio_mensal"
      enabled: true
  charts:
    - id: "aportes_combo_mensal"
      enabled: true
      conclusion: true
```

Rodar `python3 dev/codegen_report_layout.py` e comitar TS+py
gerados **no mesmo commit** que o YAML.

### 4.4 (se D1=c) Pipeline service

**Arquivo:** `pipeline/domain/services/aportes_analyzer.py` (novo)

Pydantic value object config (ADR-097), retorna dataclass tipada com
breakdown por classe + projeção. Goldens em
`tests/test_aportes_analyzer.py`.

**Não esquece:**
- Schema `config/schemas/e5.schema.json` atualizado.
- `make update-openapi-snapshot` se tocar endpoint.
- `dev/check_pipeline_boundaries.py` continua passando.

### 4.5 (sempre) Test E2E

**Arquivo:** `frontend/tests/e2e/reports/sections.tactical.spec.ts`
(existe — adicionar caso T2)

```ts
test("T2 Aportes — render KPIs e chart", async ({ page }) => {
  await page.goto("/reports/fixture-medium?mode=tatico");
  await expect(page.locator('[data-section="T2"]')).toBeVisible();
  await expect(page.locator('[data-section="T2"] [data-chart="aportes_combo_mensal"]')).toBeVisible();
  // axe-core passa
  await expectNoA11yViolations(page, '[data-section="T2"]');
});
```

### 4.6 (sempre) Atualizar docs

- [BACKLOG.md](../BACKLOG.md) — marcar `report-v2-t2-aportes` ✅,
  remover "T2 Aportes seção real" da lista de débitos da seção
  Report Premium UI.
- [REPORT_PREMIUM_PLAN.md §17](../REPORT_PREMIUM_PLAN.md) — atualizar
  status v2.4.
- [CHANGELOG.md](../CHANGELOG.md) — entrada `feat(report): T2 Aportes
  com KPIs + chart combo (v2.4 · ADR-13X se aplicável)`.

---

## 5. Sequência de commits sugerida

```
1. feat(types): score top-level + aportes_detalhe em ReportAnalysisData  [se v2.5 não fechou ainda]
2. feat(report): aportesAdapter — deriva chart data do snapshot          [4.2]
3. feat(report): T2 Aportes section com KPIs + ChartCombo                [4.1]
4. feat(layout): T2 enabled em report_layout.yaml + codegen              [4.3]
5. test(report): T2 e2e + axe-core + adapter unit                        [4.5]
6. docs(report): v2.4 ✅ — BACKLOG + PLAN + CHANGELOG                    [4.6]
```

Cada commit ≤300 linhas; commits independentes (não squash).

---

## 6. Gates de push

```bash
pre-commit run --all-files                    # PII, paths, msg
pytest backend/tests -q                       # se mexeu pipeline (D1=c)
pytest tests -q                               # se mexeu pipeline
cd frontend && npm test -- --run              # Vitest
cd frontend && npm run test:e2e -- --grep "@critical|T2"
cd frontend && npm run build                  # bundle health
```

Se **qualquer** falhar → não push. Investigar.

**Pre-push drift check** obrigatório antes de cada `git push origin main`:

```bash
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest backend/tests -q
```

---

## 7. Coordenação com outras lanes

- **v2.5 (`score` top-level DTO):** se ainda aberta quando você pegar
  v2.4, faça v2.5 dentro desta lane (commit 1) ou coordene com agente
  de v2.5 para mergear primeiro. **Não duplicar** mudança em
  `report-analysis.ts`.
- **v2.10 (PDF visual diff):** roda em paralelo. Quando v2.10 fechar
  baselines vão regerar — comunique no chat para agente de v2.10
  re-baselinar T2.
- **v2.7 (DnD Kanban):** disjunto, paralelo OK.

---

## 8. Anti-escopo

- **Reabrir T1/T3/T5/T6.** Esta lane é T2 only.
- **Adicionar novos modos.** Estratégico/Tático/USA já existem; não
  inventar "Operacional" etc.
- **Refatorar `ReportModeProvider`** — fora de escopo.
- **Mexer em `ReportTopNav`** — visualmente T2 já tem entrada na nav
  (se não tiver, é bug menor — abrir follow-up, não consertar inline).
- **LLM em aportes.** Se opção (c) precisar de classificação inteligente
  ("é aporte ou aporte+remuneração?"), abre lane v2.9.5 separada.

---

## 9. Estimativa por opção

| Opção D1 | Esforço | Comentário |
|----------|---------|------------|
| (a) MVP | ½ dia | Apenas substitui stub por KPIs do snapshot existente |
| (b) Médio | 1-2 dias | + adapter + chart combo + testes |
| (c) Completo | 3-5 dias | + pipeline service + goldens + ADR |

Default 1.5 dia (opção b).

---

## 10. Definição de feito

1. `T2AportesSection` renderiza KPIs + chart real para fixture
   `medium` em modo `tatico`.
2. Print preview do Chrome mostra T2 sem stub.
3. axe-core gate `@critical` cobre T2 — zero violações
   `critical+serious`.
4. BACKLOG marca v2.4 ✅.
5. Lane fechada via commit final em `main` com CI verde.
