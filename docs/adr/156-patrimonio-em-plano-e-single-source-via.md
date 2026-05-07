---
id: ADR-156
type: adr
title: "Patrimônio em `/plano` é single-source via `patrimonio_snapshot` (Direção E · Onda 7)"
status: Decidido
phase: "Direção E · Onda 7"
date: "2026-04-29"
relates_to: ["[[ADR-155]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 156"]
tags:
  - type/adr
  - status/decidido
size_lines: 90
---

# ADR-156 — Patrimônio em `/plano` é single-source via `patrimonio_snapshot` (Direção E · Onda 7)

**Status:** Decidido (Direção E · Onda 7) • **Data:** 2026-04-29

**Contexto:** Pré-Onda 7, `/plano` exibia o valor de patrimônio líquido
em **dois lugares** lendo caminhos potencialmente divergentes:
`PlanoKpiRow` consumia `overview.patrimonio` (vindo direto de
`listReports().reports[0].patrimonio_liquido`); `IFHeroCard` exibia
`progress.patrimonio` (output de `computeIFGoal` no backend, recebendo
o patrimônio como input). Hoje convergem por sorte do hook —
`computeIFGoal` ecoa o patrimônio recebido — mas qualquer refactor que
rotacione a fonte (cache, snapshot, derived metric) introduz risco de
"dois números diferentes na mesma tela", o que é ruptura imediata de
confiança em fintech: uma vez que o casal vê dois patrimônios, o
relatório inteiro vira suspeito.

A revisão de produto pré-Onda 7 (2026-04-29 com `product-designer` +
`financial-planner`) marcou esse risco como P0 — não há erro hoje, mas
a topologia convida a um.

**Decisão:** Toda exibição de patrimônio em `/plano` consome
`PatrimonioSnapshot` único do hook `usePlanoOverview`:

```ts
export interface PatrimonioSnapshot {
  value: number;           // patrimônio líquido em BRL
  asOf: string;            // created_at do relatório de origem (ISO)
  sourceReportId: string;  // ID do relatório de origem
}
```

- `usePlanoOverview` retorna `patrimonio_snapshot: PatrimonioSnapshot | null`.
  Substitui o campo `patrimonio: number | null` anterior. Build do
  snapshot mora em `loadLatestPatrimonioSnapshot` (interno ao hook) que
  lê `listReports(wsId)` e pega o primeiro relatório com
  `patrimonio_liquido != null`.
- `IFProgress.patrimonio` é **removido** — campo redundante que
  duplicava a fonte. `IFProgress` agora carrega só `pct + faltante`
  (resultado de `computeIFGoal`), não o input.
- `PlanoKpiRow` recebe prop `patrimonioSnapshot` e formata
  `snapshot.value`. Sem snapshot → degrada para "—".
- `IFHeroCard` recebe prop `patrimonio: number | null` separada de
  `progress`. O Hero só renderiza o gauge de progresso quando
  `progress && patrimonio != null` ambos disponíveis.
- `plano/page.tsx` é o único call-site que conecta os dois: passa
  `overview.patrimonio_snapshot` para `PlanoKpiRow` e
  `overview.patrimonio_snapshot?.value ?? null` para `IFHeroCard`. A
  decisão "qual número vira display" mora num só lugar.
- Test de regressão em
  `frontend/tests/components/PatrimonioSingleSource.test.tsx`
  renderiza ambos com o mesmo snapshot e assertiva que o Hero
  (`data-testid="if-hero-patrimonio"`) e o KPI mostram exatamente o
  mesmo `formatCurrency(snapshot.value)`. Bloqueia regressão futura
  que tente reintroduzir caminhos divergentes.

**Consequências:**

- ✅ Eliminado o risco "dois patrimônios diferentes na mesma tela" —
  só existe um caminho topologicamente, e há teste guarda.
- ✅ `IFProgress` mais coeso: representa apenas o resultado do cálculo
  IF (pct + faltante), não duplica entrada.
- ✅ Snapshot carrega `asOf + sourceReportId` — futura onda pode
  exibir "patrimônio de DD/MM (Relatório X)" ao lado do número sem
  refactor de fonte.
- ⚠️ Mudança breaking dentro do hook (`patrimonio` → `patrimonio_snapshot`,
  remoção de `progress.patrimonio`). Consumidores fora de
  `plano/page.tsx`/`PlanoKpiRow`/`IFHeroCard` não existem hoje —
  verificado por grep — mas qualquer agente que estiver tocando o
  hook em paralelo precisa rebasear.
- ❌ Adapter mínimo `progress.patrimonio` para back-compat **não foi
  oferecido** — cleanup vence sobre compat de consumer interno. Re-grep
  em `usePlanoOverview` antes de mexer.

**Referências de código:**

- `frontend/src/app/(app)/plano/_components/usePlanoOverview.ts` —
  `PatrimonioSnapshot` interface + `loadLatestPatrimonioSnapshot`.
- `frontend/src/app/(app)/plano/_components/PlanoKpiRow.tsx` — prop
  `patrimonioSnapshot`.
- `frontend/src/app/(app)/plano/_components/IFHeroCard.tsx` — prop
  `patrimonio: number | null` separada do progress.
- `frontend/src/app/(app)/plano/page.tsx` — único call-site.
- `frontend/tests/components/PatrimonioSingleSource.test.tsx` — test
  de paridade (gate de regressão).

**Relaciona-se a:**
[ADR-155](#adr-155--dashboard-absorvido-por-plano-direção-e-consolidação)
(consolidação que tornou `/plano` a "home única" e elevou esse risco a P0).
