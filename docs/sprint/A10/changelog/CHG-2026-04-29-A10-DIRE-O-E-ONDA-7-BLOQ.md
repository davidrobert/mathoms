---
id: CHG-2026-04-29-A10-DIRE-O-E-ONDA-7-BLOQ
type: changelog-entry
date: "2026-04-29"
sprint: A10
adrs: ["[[ADR-156]]"]
summary: |
  Direção E · Onda 7 — bloqueadores P0 fechados (2026-04-29). - **Direção E · Onda 7 — bloqueadores P0 fechados (2026-04-29):** os 5 fixes da [track_onda_7_p0_blockers.md](agent_prompts/track_onda_7_p0_blockers.md) entregu
tags:
  - type/changelog-entry
  - sprint/a10
---


# Direção E · Onda 7 — bloqueadores P0 fechados (2026-04-29)

- **Direção E · Onda 7 — bloqueadores P0 fechados (2026-04-29):** os 5
  fixes da [track_onda_7_p0_blockers.md](agent_prompts/track_onda_7_p0_blockers.md)
  entregues em main, ritual mensal volta a funcionar ponta-a-ponta:

  1. **`/plano` reordenado** — Estratégia → Plano de Ação → Mês
     corrente. "Mês corrente" agora é `<details>` colapsado por default
     (alertas + KPIs operacionais + ChartsGrid abrem com 1 clique).
     Reduz ~12 blocos visíveis para ~6-8 na leitura típica casal.
  2. **`/acao` default = Inbox quando há sugestões pendentes** + lê
     `?tab=inbox|tarefas|timeline|notas` da URL (deep-link do
     relatório). Wrappado em `<Suspense>` (padrão das demais rotas
     `useSearchParams`). TODO esquecido em `acao/page.tsx:10-12`
     fechado.
  3. **Anchor scroll `#SUG-XXX` corrigido** — `SuggestionCard` agora
     emite `id="SUG-${suggestion.id}"` (mantendo
     `data-suggestion-id` para testes). Página `/acao` faz polling
     2s pelo elemento (Inbox carrega assíncrono) e dispara
     `scrollIntoView` quando aparece. Highlight via `:target` Tailwind.
     Link em `SuggestionCallout` (relatório) atualizado para
     `/acao?tab=inbox#SUG-${id}`.
  4. **Patrimônio single-source ([ADR-156](DECISIONS.md#adr-156--patrimônio-em-plano-é-single-source-via-patrimonio_snapshot-direção-e--onda-7))** —
     `usePlanoOverview` expõe `patrimonio_snapshot: { value, asOf,
     sourceReportId } | null`. `PlanoKpiRow` e `IFHeroCard` consomem o
     **mesmo** valor; `IFProgress.patrimonio` removido como campo
     duplicado. Test de paridade em
     `tests/components/PatrimonioSingleSource.test.tsx` bloqueia
     regressão de "dois números diferentes na mesma tela".
  5. **`<OnboardingHero/>` para workspace zero** — quando
     `!ifGoal && decisions == 0 && tasks == 0`, `/plano` substitui
     todo o conteúdo por hero ensinante de 3 next-steps (Configurar
     IF · Importar relatório · Criar primeira decisão; passos com
     badge progressivo + CTA terciário desabilitado até IF vigente).
     Mata a "parede de blocos vazios" da primeira impressão. Hook
     auxiliar `useWorkspaceZeroSignals` lê `listDecisions` +
     `listTasks` em paralelo.

  Toques em produção: `frontend/src/app/(app)/plano/page.tsx`,
  `frontend/src/app/(app)/acao/page.tsx`,
  `frontend/src/app/(app)/plano/_components/{usePlanoOverview,PlanoKpiRow,IFHeroCard,OnboardingHero,useWorkspaceZeroSignals}.{ts,tsx}`,
  `frontend/src/app/(app)/acao/_components/SuggestionCard.tsx`,
  `frontend/src/components/report/sections/SuggestionCallout.tsx`,
  `frontend/tests/components/PatrimonioSingleSource.test.tsx`. Vitest
  691 passing (+2 novos), code-style baseline mantido (T3 ofensores
  novos contidos via extração para `useTabSelection` /
  `runZeroLoadEffect` / `AcaoLoaded`). Onda 7 ✅; Ondas 8 e 9 abertas.
