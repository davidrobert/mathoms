---
type: moc
title: SPRINTS-active — Sprint corrente + curating de prioridade
aliases: ["SPRINTS-active", "sprints-active"]
---

# SPRINTS-active — Sprint corrente + curating de prioridade

> **Editorial.** Resumo narrativo da sprint atual. Status detalhado: `_generated/SPRINT_CURRENT.md`.
>
> **Fonte de verdade da sprint corrente:** o campo `sprint_status` no frontmatter de cada `docs/sprint/<X>/_README.md`. Valores: `current` (única) · `candidate` (próxima) · `paused` (escopo aberto, ceu prioridade — múltiplas permitidas) · `done` (encerrada). Validado por `python3 dev/build_doc_index.py --check` — falha se houver 2+ MOCs com `current` ou status fora do vocabulário. Ao virar a sprint, edite os `_README.md` envolvidos **antes** de regenerar. Transições típicas: `current → done` (escopo entregue) · `candidate → current` (promoção); transições com débito conhecido: `current → paused` ou `candidate → paused` ([[ADR-234]]).

## Sprint atual

_Nenhuma sprint `current` no momento._ A15 (FU-3 imóvel financiado) encerrou 2026-05-20 com 8 PRs e ADR-227 `Decidido`. A11 e A12 permanecem `paused` (ver §Sprints pausadas) — a decisão sobre qual retomar fica aberta. Para promover, edite o `_README.md` da sprint escolhida (`paused → current`) e regenere `_generated/`.

## Sprint candidate (próxima)

_Nenhuma sprint em `candidate` no momento._ Decisão sobre próxima sprint fica em aberto pós-A15.

## Sprints pausadas

Sprints com escopo aberto cujo trabalho foi suspenso. Retomada não-bloqueada: lanes ready continuam ready, frontmatter volta a `current`/`candidate` quando o owner decidir.

### A11 — Platform review execution (`paused` 2026-05-20)

**Pausada com débito conhecido.** 6 ondas, 138 findings de revisão multi-agente. W1 ✅ + W2 ✅ entregues; W3-W6 abertas (~9 itens). Sub-lanes paralelas (competitive-pierre, report-publication) preservadas.

- **Trabalho residual:** [plan/PLATFORM_REVIEW/_README.md](../plan/PLATFORM_REVIEW/_README.md) (W3-W6).
- **Sub-lanes preservadas:** A11.competitive-pierre (Fase 1 ready), A11.report-publication (ADR-187 Proposto), A11.cat-overrides-ux ✅ entregue 2026-05-10.
- **DOC_REORG** ✅ entregue em 2026-05-07 (separado da pausa). Arquivado em [DOC_REORG_PLAN-2026-05-07.md](../archive/DOC_REORG_PLAN-2026-05-07.md), ADR canônica [ADR-182](../adr/182-vault-de-documentacao-operacional-obsidian.md).
- **Retomada:** flip `paused → current` quando decidido retomar.

### A12 — Categorization learning loop + post-A11 follow-up (`paused` 2026-05-20)

**Pausada com débito conhecido.** Cat-learning-loop in_progress: P1-P3 mergeadas (PRs #188, #194, #195-#198); gate dogfood + P4 condicional pendentes. FU-1 + FU-2 entregues, FU-3 absorvido e entregue como A15.

- **Trabalho residual:** gate dogfood (CEO + PM, 0,5d setup + 7d wall-clock — ver [docs/reference/RUNBOOK.md §9](../reference/RUNBOOK.md)) + P4 condicional.
- **Plano:** [plan/CAT_LEARNING_LOOP/_README.md](../plan/CAT_LEARNING_LOOP/_README.md). ADRs: [ADR-186](../adr/186-promocao-override-transacao-para-regra-categorizacao.md) + [ADR-188](../adr/188-evolucao-schema-e-semantica-learning-loop-p3.md).
- **Retomada:** flip `paused → current` (ou `candidate`) quando decidido retomar.

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
| A15 | done | FU-3 imóvel financiado ([ADR-227](../adr/227-imovel-financiado-debt-aggregate-valor-mercado.md)) — 8 PRs, 2 bugs silenciosos resolvidos. Plano arquivado em [archive/IMOVEL_FINANCIADO-2026-05-20.md](../archive/IMOVEL_FINANCIADO-2026-05-20.md). |

> Tracks por sprint disponíveis em [`docs/sprint/A6/tracks/`](../sprint/A6/tracks/), [`A7/tracks/`](../sprint/A7/tracks/), [`A8/tracks/`](../sprint/A8/tracks/), [`A11/tracks/`](../sprint/A11/tracks/), [`A12/tracks/`](../sprint/A12/tracks/), [`F7/tracks/`](../sprint/F7/tracks/), [`F9/tracks/`](../sprint/F9/tracks/), [`W5/tracks/`](../sprint/W5/tracks/), [`W6/tracks/`](../sprint/W6/tracks/). [BACKLOG](../BACKLOG.md) é apenas shim de navegação.
