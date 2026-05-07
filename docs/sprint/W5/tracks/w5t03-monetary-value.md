---
id: TRACK-w5t03-monetary-value
type: track
title: "Track W5-T03 — `<MonetaryValue size=\"kpi\">` migration"
sprint: W5
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/w5
  - status/consumed
---

# Track W5-T03 — `<MonetaryValue size="kpi">` migration

> **Lane ID:** `w5t03-monetaryvalue`
> **Branch prefix:** `agent/w5t03-monetaryvalue/<yyyyMMdd-HHmm>`
> **Plano canônico:** [plan/PLATFORM_REVIEW/_README.md §W5-T03](../plan/PLATFORM_REVIEW/_README.md)
> **Onda:** Wave 5 (paraleliza com W5-T01 — não toca os mesmos arquivos)
> **Severity:** P1 · **Effort:** M (~1 dia, PR único)
> **Owner:** product-designer
> **Depende de:** W1-T01 ✅ (text-style-kpi-value já existe em tokens.css)
> **Findings cobertos:** PD-006, PD-010, PD-011, PD-012, PD-013

---

## Briefing

`MonetaryValue` (`frontend/src/components/report/MonetaryValue.tsx`) já
expõe `size="hero" | "kpi" | "body"` que aplica `text-style-*` do
design-tokens. KPIs hoje empilham `font-mono text-{xl,2xl,3xl}
font-semibold tabular-nums` *em volta* do `<MonetaryValue/>` — duplicam
tipografia, divergem em peso/tamanho e burlam o token. Objetivo:
substituir o wrapper `<p className="font-mono text-Xxl ...">` pela prop
`size` correta. Em paralelo, eliminar `toLocaleString("pt-BR")` direto
em strings monetárias.

---

## 1. Inventário — wrappers em valor monetário (9 call-sites em 6 arquivos)

| # | Arquivo | Linha | Wrapper atual | Valor envolto |
|---|---------|-------|---------------|---------------|
| 1 | `frontend/src/components/report/cards/EndividamentoCard.tsx` | 28 | `font-mono text-3xl font-semibold tabular-nums text-[var(--semantic-gain)]` | literal `R$ 0,00` |
| 2 | `frontend/src/components/report/cards/EndividamentoCard.tsx` | 42 | `mt-1 font-mono text-2xl font-semibold tabular-nums` | `<MonetaryValue value={total}/>` |
| 3 | `frontend/src/components/report/cards/IrpfIrPagoCard.tsx` | 32 | `mt-1 font-mono text-2xl font-semibold tabular-nums` | `<MonetaryValue value={ir}/>` |
| 4 | `frontend/src/components/report/cards/IrpfRendaAnualCard.tsx` | 23 | `mt-1 font-mono text-2xl font-semibold tabular-nums` | `<MonetaryValue value={bruta}/>` |
| 5 | `frontend/src/components/report/cards/IrpfRendaAnualCard.tsx` | 31 | `mt-1 font-mono text-xl font-semibold tabular-nums text-[var(--semantic-gain)]` | `<MonetaryValue value={liquida}/>` |
| 6 | `frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx` | 34 | `font-mono text-2xl font-semibold tabular-nums` | `<MonetaryValue value={0}/>` |
| 7 | `frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx` | 48 | `mt-1 font-mono text-2xl font-semibold tabular-nums` | `<MonetaryValue value={capacidade}/>` |
| 8 | `frontend/src/components/report/cards/IrpfSplitTrabalhoCapitalCard.tsx` | 26 | `font-mono text-lg font-semibold tabular-nums` | `<MonetaryValue value={value}/>` |
| 9 | `frontend/src/components/report/charts/RendaEvolucaoChart.tsx` | 41 | `font-mono text-3xl font-semibold tabular-nums` | `<MonetaryValue value={point.value}/>` |

### Wrappers em valor **não-monetário** (5 — fora de escopo, abrir PD-022)

`%`, `meses`, contagem em IFHeroCard.tsx:98, EndividamentoCard.tsx:50,
ReservaEmergenciaCard.tsx:41, S3InvestimentosSection.tsx:94,
ConsumoConscienteCard.tsx:49. Não pertencem ao `<MonetaryValue/>`.
Registrar **PD-022** (primitiva `<TabularValue/>` ou `<Pct/>`) — não
bloqueia W5-T03.

---

## 2. Inventário — `toLocaleString()` direto em strings monetárias (9 ocorrências)

| # | Arquivo | Linha | Padrão | Substituir por |
|---|---------|-------|--------|----------------|
| 1 | `frontend/src/components/report/cards/EstrategiaAporteCard.tsx` | 47 | `R$ ${total.toLocaleString("pt-BR")}` | `formatCurrency(total)` |
| 2 | `frontend/src/components/report/cards/StressScenarioCard.tsx` | 21–28 | `fmtBRL` artesanal | `formatCurrency` ou novo `formatCurrencyInt` |
| 3 | `frontend/src/components/report/sections/ApendicesSections.tsx` | 276 | `milhas.saldo_total.toLocaleString("pt-BR")` (saldo de pontos — NÃO BRL) | `formatNumber(saldo, 0)` |
| 4 | `frontend/src/components/report/sections/ApendicesSections.tsx` | 286–290 | `valor_estimado.toLocaleString("pt-BR", {style:"currency", ...})` | `<MonetaryValue value={valor_estimado} fractionDigits={0}/>` |
| 5 | `frontend/src/app/(app)/config/CategoriesTab.tsx` | 297 | `R$ ${cat.monthly_cap.toLocaleString("pt-BR")}` | `formatCurrency(cat.monthly_cap)` |
| 6 | `frontend/src/app/(app)/plano/_components/SupportGoalsRow.tsx` | 65 | `US$ ${goal.inputs.meta_usd.toLocaleString("pt-BR")}` | `formatCurrency(meta_usd, "USD")` |
| 7 | `frontend/src/app/(app)/plano/dolarizacao/wizard/page.tsx` | 177 | `US$ ${preset.toLocaleString("pt-BR")}` | `formatCurrency(preset, "USD")` |
| 8 | `frontend/src/app/(app)/plano/dolarizacao/wizard/page.tsx` | 228 | `US$ ${metaUsd.toLocaleString("pt-BR")}` | `formatCurrency(metaUsd, "USD")` |
| 9 | `frontend/src/lib/goalPremissas.ts` | 128 | `US$ ${inputs.meta_usd.toLocaleString("pt-BR")}` | `formatCurrency(inputs.meta_usd, "USD")` |

---

## 3. Diff por arquivo (representativos)

### 3.1 EndividamentoCard.tsx
```diff
-          <p className="font-mono text-3xl font-semibold tabular-nums text-[var(--semantic-gain)]">
-            R$ 0,00
-          </p>
+          <MonetaryValue value={0} size="kpi" className="text-[var(--semantic-gain)]" />
@@
-              <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
-                <MonetaryValue value={total} />
-              </p>
+              <MonetaryValue value={total} size="kpi" className="mt-1" />
```

### 3.2 IrpfRendaAnualCard.tsx
```diff
-          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
-            <MonetaryValue value={bruta} />
-          </p>
+          <MonetaryValue value={bruta} size="kpi" className="mt-1" />
@@
-          <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-[var(--semantic-gain)]">
-            <MonetaryValue value={liquida} />
-          </p>
+          <MonetaryValue value={liquida} size="kpi" className="mt-1 text-[var(--semantic-gain)]" />
```

### 3.3 EstrategiaAporteCard.tsx (toLocaleString)
```diff
+import { formatCurrency } from "@/lib/format";
@@
-        ? `Aporte mensal de R$ ${total.toLocaleString("pt-BR")} no dia ${estrategia.dia_aporte ?? "?"} de cada mês`
+        ? `Aporte mensal de ${formatCurrency(total)} no dia ${estrategia.dia_aporte ?? "?"} de cada mês`
```

### 3.4 ApendicesSections.tsx (milhas)
```diff
+import { formatNumber } from "@/lib/format";
@@
-                <dd className="font-mono tabular-nums">
-                  {milhas.saldo_total.toLocaleString("pt-BR")}
-                </dd>
+                <dd className="font-mono tabular-nums">
+                  {formatNumber(milhas.saldo_total, 0)} pts
+                </dd>
@@
-                <dd className="font-mono tabular-nums">
-                  {milhas.valor_estimado.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 })}
-                </dd>
+                <dd>
+                  <MonetaryValue value={milhas.valor_estimado} fractionDigits={0} />
+                </dd>
```

### 3.5 SupportGoalsRow.tsx + dolarizacao/wizard + goalPremissas.ts
```diff
-      ? `US$ ${goal.inputs.meta_usd.toLocaleString("pt-BR")}`
+      ? formatCurrency(goal.inputs.meta_usd, "USD")
```

---

## 4. Cobertura PD-006/010/011/012/013

| Finding | Coberto? | Gap |
|---------|----------|-----|
| PD-006 — KPI monetário sem token canônico | ✅ 6 cards (Endividamento, IrpfIrPago, IrpfRendaAnual, IrpfPgblCapacidade, IrpfSplit, RendaEvolucao) | — |
| PD-010 — single chore, 11 call-sites | ✅ 9 monetários + 9 toLocaleString = 18 (excede 11) | — |
| PD-011 — `toLocaleString` direto | ✅ 9 ocorrências mapeadas | Decisão sobre `formatCurrencyInt` em StressScenario |
| PD-012 — wrappers `font-mono text-Xxl tabular-nums` redundantes | ✅ 9 monetários removidos | 5 não-monetários ficam → **PD-022** |
| PD-013 — Cards Premium | ✅ todos cobertos | IFHeroCard:98 (`pct`) é não-monetário → PD-022 |

---

## 5. Risco de regressão

1. **Zero unit tests + zero snapshot tests no frontend** (`grep` em `frontend/src/**/*.test.{ts,tsx}` retornou vazio). Risco unit baixo.
2. **Playwright `@critical`** pode assertar `font-family`/`font-feature-settings`. Rodar `cd frontend && npm run test:e2e --grep '@critical'` antes do push.
3. **`tokens.css` deve expor `text-style-kpi-value`** — confirmar com `grep text-style-kpi-value frontend/src/styles/tokens.css` antes do commit.
4. **Visual diff Playwright (PDF)** — diff esperado em cards onde `text-xl`/`text-3xl` viraram `text-2xl` canônico. Atualizar baselines deliberadamente; documentar no PR.

---

## 6. Decisões abertas

1. **`formatCurrencyInt(v)`** sem centavos em StressScenarioCard — criar ou aceitar centavos universalmente? Recomendação: aceitar centavos (padroniza).
2. **`size="kpi-sub"`** para variação `text-xl` (IrpfRendaAnualCard:31, IrpfSplitTrabalhoCapital:26) — criar size novo ou aceitar override `text-lg`/`text-xl` por className? Recomendação: criar `size="kpi-sub"` para fechar consistência.

---

## 7. Sequência (PR único — Trade-off 4 do plano)

A decisão CTO já está registrada (Posição A — single PR). Quebrar em 3
sub-PRs (cards / toLocaleString / KPICard audit) só acrescenta overhead
de rebase sem ganho.

---

## Critério de aceite

- [ ] 9 wrappers `font-mono text-Xxl tabular-nums` em torno de `<MonetaryValue/>` removidos.
- [ ] 9 `toLocaleString("pt-BR")` em strings monetárias substituídos.
- [ ] Decisão registrada (PR comment ou ADR rápido) sobre `formatCurrencyInt` e `size="kpi-sub"`.
- [ ] **PD-022** aberto no PLATFORM_REVIEW_PLAN para itens não-monetários.
- [ ] `cd frontend && npm test -- --run` verde + `npm run test:e2e --grep '@critical'` verde.
- [ ] Visual review humano em `/reports/[id]` (S1 Endividamento + Reserva, S_IRPF_RENDA, S3 RendaEvolucao) — sem regressão de leitura.

---

## Anti-escopo

- 5 wrappers em valor não-monetário (% / meses / contagem) — abrir **PD-022** dedicado.
- Refactor de `KPICard` (`frontend/src/components/KPICard.tsx`) — auditar callers em PR separado se ≥3 inline format.
