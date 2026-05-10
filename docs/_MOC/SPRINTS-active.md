---
type: moc
title: SPRINTS-active — Sprint corrente + curating de prioridade
aliases: ["SPRINTS-active", "sprints-active"]
---

# SPRINTS-active — Sprint corrente + curating de prioridade

> **Editorial.** Resumo narrativo da sprint atual. Status detalhado: `_generated/SPRINT_CURRENT.md`.

## Sprint atual

**A11 — Platform review execution** (origem 2026-05-06).

32 tasks em 6 ondas, 138 findings consolidados de revisão multi-agente (data-engineer + financial-planner + product-designer + sre-devops + build-vs-buy + senior-cto), 6 ADRs Proposto (ADR-170 a ADR-175).

- **W1** ✅ entregue.
- **W2-W6** abertas conforme [plan/PLATFORM_REVIEW/_README.md](../plan/PLATFORM_REVIEW/_README.md).
- **A11.docreorg** (esta lane): execução do plano [DOC_REORG](../plan/DOC_REORG/_README.md) ([ADR-182](../adr/182-vault-de-documentacao-operacional-obsidian.md)).
- **A11.competitive-pierre** (novo, 2026-05-08): resposta competitiva a [Pierre Finance](https://lp.pierre.finance/) (CloudWalk) — quatro fases (recon POC, Mathoms-as-MCP, chat sobre relatório, reposicionamento brand). Plano em [plan/COMPETITIVE_PIERRE/_README.md](../plan/COMPETITIVE_PIERRE/_README.md). Tracks ready: [competitor-pierre-poc](../sprint/A11/tracks/competitor-pierre-poc.md) (Fase 1) · [gtm-landing-copy-rewrite](../sprint/A11/tracks/gtm-landing-copy-rewrite.md) (Fase 4.B skeleton, ancorada em [ADR-183](../adr/183-landing-positioning-pillars-2026.md)).
- **A11.cat-overrides-ux** (novo, 2026-05-10): editar 24 categorias default (template v1, [ADR-137](../adr/137-categorization-templates-overrides.md)) via UI; corrigir tela vazia em workspace novo. 4 ondas (cache fix → schema delta → ADR-185 Proposto → UI refactor). Plano em [plan/CATEGORY_OVERRIDES_UX/_README.md](../plan/CATEGORY_OVERRIDES_UX/_README.md). Tracks ready: [category-overrides-cache-fix](../sprint/A11/tracks/category-overrides-cache-fix.md) (W1 · senior-cto) · [category-overrides-schema-delta](../sprint/A11/tracks/category-overrides-schema-delta.md) (W2 · data-engineer) · [category-overrides-policy-adr](../sprint/A11/tracks/category-overrides-policy-adr.md) (W3 · PM) · [category-overrides-ui-refactor](../sprint/A11/tracks/category-overrides-ui-refactor.md) (W4 · product-designer, blocked).
- **A11.report-publication** (novo, 2026-05-10): conceito de "mês fechado" imutável — barreira temporal pra mutações retroativas (re-categorização, IRPF, Decision, cenários). Lane standalone (3d eng) promovida de "P0 do learning loop" por review PM 2026-05-10 (reusabilidade + desacopla risco cruzado). ADR Proposto: [ADR-187](../adr/187-relatorio-publicado-imutavel-mes-fechado.md). Track ready: [report-publication-impl](../sprint/A11/tracks/report-publication-impl.md).

## Sprint candidate (próxima)

**A12 — Categorization learning loop + post-A11 follow-up** (origem 2026-05-10, abre quando A11 fechar).

- **A12.cat-learning-loop**: promoção de override de transação em regra de categorização persistida. Co-design `financial-planner` + `product-designer`; modelo híbrido C-light + D-forte com invariantes (override manual sticky, mês fechado imutável, conflito determinístico). MVP V1 cortado pra 4 fases (P1-P4) + gate dogfood ≈12,5d eng (3-4 sem wall-clock). P5 inbox + P6 detector offline + alertas SRE são V2 pós-tração. Plano: [plan/CAT_LEARNING_LOOP/_README.md](../plan/CAT_LEARNING_LOOP/_README.md). ADR Proposto: [ADR-186](../adr/186-promocao-override-transacao-para-regra-categorizacao.md). **Pré-requisito externo:** A11.report-publication mergeado em `main`. Detalhe: [docs/sprint/A12/_README.md](../sprint/A12/_README.md).

## Pickup — antes de pegar lane

1. Confirme `git fetch origin` está atualizado.
2. Veja worktrees ativos: `git worktree list`.
3. Veja branches `agent/*` recentes: `git for-each-ref --sort=-committerdate refs/remotes/origin/agent/`.
4. Lane com slug em uso (worktree OU branch <24h): **não duplique**.
5. Slug das lanes desta sprint: **descritivo curto, kebab-case** (`a11-w2-t01`, `a11-docreorg-f1`, etc.).

## Sprints anteriores (encerradas)

| Sprint | Status | Resumo |
|---|---|---|
| A6 | done | Migração infra+domínio (ADR-097, ADR-111). |
| A7 | done | Config DB cutover (CLI legacy removal). |
| A8 | done | Continuação multi-tenant. |
| A9 | done | Multi-front improvements. |
| A10 | done | `goals.json` cutover final ([ADR-090](../adr/090-decimal-money.md) supersedes parcial). |

> Tracks por sprint disponíveis em [`docs/sprint/A6/tracks/`](../sprint/A6/tracks/), [`A7/tracks/`](../sprint/A7/tracks/), [`A8/tracks/`](../sprint/A8/tracks/), [`A11/tracks/`](../sprint/A11/tracks/), [`F7/tracks/`](../sprint/F7/tracks/), [`F9/tracks/`](../sprint/F9/tracks/), [`W5/tracks/`](../sprint/W5/tracks/), [`W6/tracks/`](../sprint/W6/tracks/). Lanes ainda em [BACKLOG](../BACKLOG.md) (legado); migração em F4.
