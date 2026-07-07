---
id: TRACK-irpf-full-schema-ui
type: track
title: "Track IRPF Full Schema UI — relatório premium consome KPIs do E1.6"
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

# Track IRPF Full Schema UI — relatório premium consome KPIs do E1.6

> **Lane ID:** irpf-full-schema-ui
> **Branch prefix:** `agent/irpf-full-schema-ui/*`
> **Depende de:** [track_irpf_full_schema.md](irpf-full-schema.md) ✅ mergeada (E1.6 backend + analyzer + E5 wire em `main` desde 2026-04-30, [ADR-157](../../../DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full)).
> **Conflita com:** `config/report_layout.yaml`, `frontend/src/generated/report-layout.ts`, `backend/app/generated/report_layout.py` (codegen [ADR-076](../../../DECISIONS.md#adr-076--design-tokens-unificados-site--relatório)), e qualquer track `report-v2-*` ativo que mexa nas mesmas seções/charts.
> **Onda:** independente — pode rodar paralela ao Sprint A8 desde que respeite YAML/codegen.
> **ADR:** **não obrigatória** — mudanças de produto/UX sob ADR-076 (design system) e ADR-157 (E1.6 schema) já vigentes; abrir ADR nova só se decidir substituir gauge/visualização canônica ou alterar tokens.
> **Supervisão:** **G4 (`product-designer`)** obrigatório antes do PR · **G2 (`data-engineer`)** se mudar shape de `irpf_kpis` no E5 · **G0 (`financial-planner`)** para validar copy/labels (alíquota efetiva vs carga tributária, capacidade PGBL, split trabalho×capital).

> **Objetivo (1 frase):** materializar no relatório premium os 6 KPIs já produzidos pelo `IRPFAnalyzer` (renda anual líquida, alíquota dual, capacidade PGBL, split trabalho×capital, evolução, sinalizações de otimização) — workspaces sem IRPF não regridem (try-read opcional já em produção).

---

## Por que esta lane

### Sintoma

`IRPFAnalyzer` está em produção (`pipeline/domain/services/irpf_analyzer.py`) e o E5 já emite a chave `irpf_kpis` no output (`scripts/e5_analyze.py::_e5_load_irpf_kpis`), mas **nenhum componente do relatório consome**. O usuário sobe declaração IRPF, processo extrai, KPIs são calculados, e o relatório premium não exibe nada disso.

### O que falta

1. **`config/report_layout.yaml`** ganha 2 seções novas:
   - "Renda anual e impostos" (KPIs: renda líquida, IR efetivo, alíquota dual)
   - "Otimização tributária" (capacidade PGBL não usada, dependentes ociosos, dedutíveis subutilizados)
2. **Codegen** roda em `dev/codegen_report_layout.py` para sincronizar `frontend/src/generated/report-layout.ts` + `backend/app/generated/report_layout.py`.
3. **Componentes React** novos em `frontend/src/components/report/` que consomem `output["irpf_kpis"]` do E5:
   - Cards: renda anual, IR efetivo, capacidade PGBL.
   - Charts: gauge dual de alíquota (RFB-style + Cerbasi-style), gráfico de evolução de renda multi-anos (line/bar), pie chart split trabalho×capital.
   - Card de **otimização tributária** (PGBL não usado, dedutíveis abaixo do ótimo) — **G0 + G4 sign-off**.
4. **Tipo TS** gerado a partir do schema E1.6 (ou definido manualmente em `frontend/src/types/irpf.ts`) que tipa o shape do `irpf_kpis` no `ReportOutput`.

---

## Regras inegociáveis

1. **Tokens, não hex literal** ([ADR-076](../../../DECISIONS.md#adr-076--design-tokens-unificados-site--relatório)): nunca cor literal — sempre `var(--brand-*)`, `var(--surface-*)`, `var(--semantic-*)`. Verde para "capacidade não usada disponível" pode parecer positivo mas é alerta — alinhar copy com G4/G0.
2. **Valores monetários:** sempre `<MonetaryValue/>` (font-mono + tabular-nums, [frontend/src/components/report/MonetaryValue.tsx](../../../../frontend/src/components/report/MonetaryValue.tsx)). Nunca `Intl.NumberFormat` inline em renderização de BRL.
3. **Sem `any`/`unknown` sem narrow** — TS strict. Tipos do `irpf_kpis` chegam por `unknown` do E5 output e devem ser narrow-validados antes de uso.
4. **Degrada gracioso:** quando `output.irpf_kpis === undefined`, **omitir as 2 seções inteiras** do relatório — não renderizar placeholder vazio. YAML `enabled: true` mas componente checa presença e devolve `null`.
5. **Codegen é fonte de verdade** ([ADR-076](../../../DECISIONS.md#adr-076--design-tokens-unificados-site--relatório)): após editar YAML, rodar `python3 dev/codegen_report_layout.py` e commitar o diff junto. CI falha se não.
6. **Pipeline não importa framework** — domain layer (`pipeline/domain/services/irpf_analyzer.py`) **não muda**. Se faltar query no analyzer, abrir followup (não estender da UI).
7. **Idiom `period_toggle`/`comparisons`/`changelog`** existentes no YAML: aplicar onde fizer sentido (evolução de renda merece toggle multi-anos).
8. **Acessibilidade WCAG 2.1 AA** ([engineering:accessibility-review](../../../../.claude/agents/product-designer.md)): contraste, keyboard nav, screen reader labels nos charts.

---

## Entregáveis

### A. YAML — seções novas em `config/report_layout.yaml`

Sob `estrategico.sections` (provavelmente após S2 ou S3, posição decidida com G4):

```yaml
- id: "S_IRPF_RENDA"
  title: "Renda anual e impostos"
  enabled: true
  summary: true
  divider_before: true
  charts:
    - id: "renda_evolucao_multi_anos"
      enabled: true
      conclusion: true
    - id: "aliquota_efetiva_dual_gauge"
      enabled: true
      conclusion: true
  cards:
    - id: "renda_anual_familiar"
      enabled: true
      variant: "feature"
      size: "half"
    - id: "ir_pago_total"
      enabled: true
      variant: "feature"
      size: "half"
    - id: "split_trabalho_capital"
      enabled: true
      variant: "feature"
      size: "full"

- id: "S_IRPF_OTIMIZACAO"
  title: "Otimização tributária"
  enabled: true
  summary: true
  cards:
    - id: "pgbl_capacidade"
      enabled: true
      variant: "warn"
      size: "half"
    - id: "dependentes_status"
      enabled: true
      variant: "feature"
      size: "half"
    - id: "dedutiveis_subutilizados"
      enabled: true
      variant: "warn"
      size: "full"
```

(IDs e copy são placeholders — G4 finaliza.)

Adicionar entradas em `chart_canvas_map` para os 2 charts novos.

### B. Codegen + tipos TS

```bash
python3 dev/codegen_report_layout.py
```

Commitar diff em `frontend/src/generated/report-layout.ts` e `backend/app/generated/report_layout.py`.

Tipo TS para `irpf_kpis`:

```ts
// frontend/src/types/irpf.ts
export interface IrpfKpis {
  ano_base: number;
  anos_disponiveis: number[];
  renda_anual_familiar_brl: string;       // Decimal-string
  renda_liquida_familiar_brl: string;
  ir_pago_total_brl: string;
  aliquota_sobre_tributavel_pct: string;  // Decimal-string ("17.50")
  aliquota_sobre_total_pct: string;
  pgbl_capacidade_dedutivel_brl: string;
  split_trabalho_brl: string;
  split_capital_brl: string;
  evolucao_renda_anos: Record<string, string>;  // { "2024": "150000.00" }
}
```

Narrow guard `isIrpfKpis(value: unknown): value is IrpfKpis`.

### C. Componentes React

```
frontend/src/components/report/cards/
  IrpfRendaAnualCard.tsx
  IrpfIrPagoCard.tsx
  IrpfPgblCapacidadeCard.tsx
  IrpfDependentesCard.tsx
  IrpfDedutiveisCard.tsx
frontend/src/components/report/charts/
  RendaEvolucaoChart.tsx       (Chart.js — line/bar multi-anos)
  AliquotaDualGauge.tsx        (Chart.js — 2 gauges side-by-side)
frontend/src/components/report/IrpfRendaSection.tsx
frontend/src/components/report/IrpfOtimizacaoSection.tsx
```

Padrão: cada componente recebe `kpis: IrpfKpis | null`. Quando `null` → retorna `null` (omitir seção).

### D. Hook + integração com `ReportSection`

```ts
// frontend/src/components/report/hooks/useIrpfKpis.ts
export function useIrpfKpis(reportOutput: unknown): IrpfKpis | null {
  // Narrow guard sobre output.irpf_kpis
}
```

Plugar nas 2 sections novas via `ReportSection` (padrão estabelecido em S1, S2…).

### E. Acessibilidade + testes

- ARIA labels em gauges, descriptions em line/bar charts.
- Vitest unit tests para narrow guard, formatters, e renderização condicional (kpis null → null).
- Playwright `@critical` test: declaração de fixture sintética → relatório carrega → seções IRPF visíveis com valores corretos.
- Visual baseline (`tests/visual-baselines/`) — 1 light + 1 dark.

### F. Documentação

- Atualizar [docs/plan/REPORT_PREMIUM/_README.md §17](../../../plan/REPORT_PREMIUM/_README.md) (se aplicável) com as 2 seções novas.
- `docs/CHANGELOG.md` entrada datada quando mergear.
- Marcar lane A8.2 ✅ no BACKLOG.

---

## Subagentes obrigatórios

| Gate | Quando | Subagente | O que aprovar |
|---|---|---|---|
| **G4** | Antes de codar componente | `product-designer` | Hierarquia das seções no relatório, copy ("Otimização tributária" vs "Eficiência tributária"), variant dos cards (warn vs feature), gauge dual vs gauge único, formato de label (% com 1 ou 2 casas), responsividade. |
| **G0** | Antes do PR | `financial-planner` | Cobertura semântica (renda líquida descontando PGBL é "ativo" ou "passivo"?), copy de "capacidade PGBL não usada" (não pode soar como recomendação automática sem nuance INSS), gating do card "dependentes ociosos" (precisa cônjuge sem renda ou filho universitário < 24, regras Cerbasi). |
| **G2** | Se for adicionar query nova ao analyzer | `data-engineer` | Shape de `irpf_kpis`, contrato com E5, retrocompatibilidade. |
| **G3** | Antes do PR | `senior-cto` (review) | TS strict, narrow guards, sem `any`. |

---

## Sequência de commits sugerida

```
1. feat(report): YAML + codegen para 2 seções IRPF (S_IRPF_RENDA + S_IRPF_OTIMIZACAO)
2. feat(frontend): tipos + narrow guard isIrpfKpis + hook useIrpfKpis
3. feat(frontend): cards IRPF (renda, IR pago, PGBL, dependentes, dedutíveis)
4. feat(frontend): charts (renda_evolucao + aliquota_dual_gauge) — Chart.js
5. feat(frontend): IrpfRendaSection + IrpfOtimizacaoSection plugadas no ReportShell
6. test(frontend): vitest unit + Playwright @critical + visual baselines (light+dark)
7. docs(changelog): A8.2 ✅ saída + entrada datada CHANGELOG
```

---

## Definition of Done

- [ ] G4 (`product-designer`) sign-off em PR comment com transcrição
- [ ] G0 (`financial-planner`) validou copy/labels (transcrição em PR)
- [ ] `pre-commit run --all-files` passa
- [ ] `pytest backend/tests -q` passa
- [ ] `cd frontend && npm test -- --run` passa
- [ ] `cd frontend && npm run test:e2e -- --grep @critical` passa
- [ ] Visual baselines refrescadas e committadas (light + dark)
- [ ] Codegen sync — `python3 dev/codegen_report_layout.py` no-op
- [ ] Workspace de demo com IRPF processado mostra as 2 seções com valores corretos; workspace **sem** IRPF **omite** as 2 seções (degrada gracioso)
- [ ] PR mergeada em `main` com CI verde — só então a lane vira `completed`
- [ ] BACKLOG A8.2 marca sub-lane `irpf-full-schema-ui` ✅

---

## Riscos / pontos de atenção

1. **Hex literal no YAML/SVG do gauge.** Tokenizar tudo via `var(--*)`. CI tem grep contra hex; falhar pre-commit.
2. **Carga tributária dual confunde usuário.** Se G4/G0 acharem ruim mostrar dois números, virar 1 + tooltip explicando o outro. Decisão de produto.
3. **Charts em workspaces com 1 declaração.** `evolucao_renda_anos` com 1 ano vira ponto solo — degrade gracioso (mostrar valor pontual + nota "comparação aparece quando houver ≥2 declarações").
4. **Capacidade PGBL = positivo ou negativo?** "Você tem R$ 14.000 de capacidade não usada" pode soar como dívida — copy é crítico (G0).
5. **Dependentes ociosos** é tema sensível (sugerir adicionar cônjuge como dependente toca status fiscal real). Card exige copy super-cauteloso e talvez disclaimer.
6. **Charts Chart.js vs Recharts**: hoje a Onda v2.E migrou para Chart.js ([ADR-139](../../../DECISIONS.md#adr-139--finalização-migração-rechartschartjs-em-reports)) — usar Chart.js, sem regredir.
7. **Snapshot changelog** ([ADR-148](../../../DECISIONS.md#adr-148--snapshotchangelogbuilder-comparações-mês-a-mês-de-relatório)): essas 2 seções entram em comparações mês-a-mês? Decisão com G4 — provavelmente **sim** (renda muda, capacidade PGBL muda).

---

## Referências

- Backend mergeado: commits `7b26dfc`..`27e1de1` em `origin/main` (lane irpf-full-schema)
- [ADR-157](../../../DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full) — schema + KPIs canônicos
- [ADR-076](../../../DECISIONS.md#adr-076--design-tokens-unificados-site--relatório) — design tokens + codegen YAML
- [ADR-139](../../../DECISIONS.md#adr-139--finalização-migração-rechartschartjs-em-reports) — Chart.js como engine canônica
- [ADR-148](../../../DECISIONS.md#adr-148--snapshotchangelogbuilder-comparações-mês-a-mês-de-relatório) — comparações mês-a-mês
- Padrão de componentes: [frontend/src/components/report/](../../../../frontend/src/components/report)
- KPIs em [pipeline/domain/services/irpf_analyzer.py](../../../../pipeline/domain/services/irpf_analyzer.py) + wire em [scripts/e5_analyze.py::_e5_load_irpf_kpis](../../../../scripts/analyze_finances.py)
