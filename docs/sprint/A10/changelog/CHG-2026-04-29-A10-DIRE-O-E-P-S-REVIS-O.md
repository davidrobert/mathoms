---
id: CHG-2026-04-29-A10-DIRE-O-E-P-S-REVIS-O
type: changelog-entry
date: "2026-04-29"
sprint: A10
adrs: ["[[ADR-156]]", "[[ADR-157]]", "[[ADR-158]]", "[[ADR-159]]", "[[ADR-160]]"]
summary: |
  Direção E pós-revisão de produto — Ondas 7/8/9 abertas (2026-04-29). - **Direção E pós-revisão de produto — Ondas 7/8/9 abertas (2026-04-29):** Revisão completa das interfaces consolidadas (Plano + Ação + Relatório) executada com
tags:
  - type/changelog-entry
  - sprint/a10
---


# Direção E pós-revisão de produto — Ondas 7/8/9 abertas (2026-04-29)

- **Direção E pós-revisão de produto — Ondas 7/8/9 abertas (2026-04-29):**

  Revisão completa das interfaces consolidadas (Plano + Ação +
  Relatório) executada com `product-designer` + `financial-planner` +
  análise de PM. Identificou **5 bloqueadores P0** que impedem o
  ritual mensal funcionar ponta-a-ponta, **6 lacunas metodológicas**
  (Cerbasi não coberto), **5 inconsistências de design system**.

  **3 ondas dedicadas** com prompts self-contained em `docs/agent_prompts/`:

  - [track_onda_7_p0_blockers.md](../../A11/tracks/onda-7-p0-blockers.md)
    (~3d, **P0** — recomendado primeiro): reordenar `/plano`
    (Estratégia → Plano de Ação → Mês corrente collapsible); `/acao`
    default = Inbox quando há pendentes + ler `?tab=`; fix anchor
    `#SUG-XXX` do relatório → Inbox; single-source `patrimonio_snapshot`;
    `<OnboardingHero/>` para workspace zero.
  - [track_onda_8_methodology_coherence.md](../../A11/tracks/onda-8-methodology-coherence.md)
    (~5-7d, P1, depende parcial de Onda 7 #4): 6 novas regras Suggestion
    (Cerbasi: endividamento, taxa poupança caindo, seguros, concentração
    instituição, lifestyle creep, renda passiva Perini); Decisions
    atualizam Goals via event projection; `context_snapshot` ao aceitar
    Suggestion; Decision → Task automática com templates `derived_from`;
    SuggestionCard borda colorida + sort por severidade; SuggestionsBanner
    com `maxSeverity` real.
  - [track_onda_9_design_system_polish.md](../../A11/tracks/onda-9-design-system-polish.md)
    (~3d, P2, independente): `<SectionHeading/>` primitivo (4 H2 → 1);
    `<EmptyState/>` primitivo (5 → 1); `<SegmentedTabs/>` primitivo
    (3 → 1); dedup tarefas Upcoming/Linked + filter param em `/acao`;
    badge sugestões pendentes no AppShell; **kill Timeline tab**
    (placeholder ensinante sem fonte virou ruído); mobile collapsibles
    + tap targets + Playwright iPhone 13.

  **Decisões de produto travadas (incorporadas nos prompts):** (i)
  `/plano` usa **collapsibles** (não tabs); (ii) Inbox continua tab em
  `/acao` (não vira rota top-level), visibilidade via badge no AppShell;
  (iii) Tasks aceitam ad-hoc e derivadas, com `derived_from`; (iv)
  Timeline tab removida; (v) Seguros em v1 só como regra de Suggestion
  (módulo é pós-GA).

  ADRs futuras já reservadas: ADR-156 (Patrimônio single-source · Onda 7),
  ADR-157 (Suggestion regras v2 · Onda 8), ADR-158 (Decisions → Goals
  projection · Onda 8), ADR-159 (Decision context_snapshot · Onda 8),
  ADR-160 (design system primitivos v2 · Onda 9).

  Entrada do banner em `BACKLOG.md` atualizada com tabela das 3 ondas
  + critérios de pickup.
