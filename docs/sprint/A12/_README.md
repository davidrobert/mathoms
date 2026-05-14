---
id: MOC-sprint-a12
type: moc
title: Sprint A12 — Categorization learning loop + post-A11 follow-up
aliases: ["A12", "Sprint A12"]
sprint_status: candidate
---

# Sprint A12 — Categorization learning loop + post-A11 follow-up (origem 2026-05-10)

> **Status:** in_progress (desde 2026-05-10) — lane única ativa
> `A12.cat-learning-loop` com P1-P4 (UI mínima) + gate técnico shipped.
> Gate dogfood humano (7d wall-clock) é o último bloqueio para fechar DoD.

## Resumo

Sprint candidate aberta como **destino canônico** da feature
[`cat-learning-loop`](lanes/A12-cat-learning-loop.md), movida de A11
após review `product-manager` (sessão 2026-05-10) — A11 está
sobrecarregada (138 findings de PLATFORM_REVIEW + COMPETITIVE_PIERRE +
DOC_REORG); inserir feature de 19d em sprint de hardening dilui foco e
atrasa P0 latentes (security pré-prod).

**Plano canônico ancorado:** [docs/plan/CAT_LEARNING_LOOP/_README.md](../../plan/CAT_LEARNING_LOOP/_README.md).

**ADRs Proposto:**

- [[ADR-186]] — Promoção de override de transação para regra de
  categorização (learning loop).
- [[ADR-187]] — Mês fechado: imutabilidade de relatório publicado
  (**implementada em A11.report-publication**, lane standalone, **pré-requisito externo** desta sprint).

## Por que esta sprint existe

Lições críticas do co-design `financial-planner` + `product-designer`
(sessão 2026-05-10):

- **Cerbasi:** categorização errada destrói diagnóstico comportamental
  (estilo de vida vs essenciais).
- **Perini:** custo de vida bias direto na regra dos 300 (patrimônio-alvo
  IF).
- **AUVP:** snapshot mensal precisa ser estável — invariante atendido
  por A11.report-publication.
- **Mercado:** Mint morreu por categorização ruim que nunca aprendia;
  Monarch acerta o tom (descoberta passiva + Rules tela própria); YNAB
  não tem learning e gera reclamação histórica.

## Lanes

- **A12.cat-learning-loop** — promoção override → regra. 5 fases (P1-P4
  + dogfood gate; P5/P6 são V2 pós-tração).
  Plano: [CAT_LEARNING_LOOP](../../plan/CAT_LEARNING_LOOP/_README.md).
  ADR: [[ADR-186]].
- **A12.sunset-disk-artifact** — sunset `DiskArtifactStore` + flag
  `MATHOMS_USE_DB_ARTIFACTS` + coluna `use_db_artifacts_override` + CLI
  standalone do pipeline (5 PRs sequenciais, ~5d eng em ~3 sem
  calendário). Cleanup pós-cutover desbloqueia [[ADR-211]] lane 3.
  Plano = [[ADR-212]] (a ADR é o plano).
  Lane: [A12.sunset-disk-artifact](lanes/A12-sunset-disk-artifact-cleanup.md).
  Track: [sunset-disk-artifact](tracks/sunset-disk-artifact.md).

Lanes adicionais entram aqui conforme A11 fecha trabalho que naturalmente
empurra continuação para A12.

## Pré-requisitos externos (out-of-sprint)

- **A11.report-publication** ([[ADR-187]]) — DEVE mergear em `main`
  antes de iniciar P2 (Pipeline E4) de A12.cat-learning-loop. P1
  (Schema) pode rodar em paralelo.

## Gates

- Workspaces sem regras promovidas mantêm comportamento E4 idêntico ao
  legado (paridade goldens).
- Override manual permanece **sticky** (regra nunca atropela).
- Re-categorização retroativa **recusada** em meses com
  `report_publication` viva.
- **Gate dogfood** (entre P3 e P4): 5 regras criadas no workspace do
  CEO em ≤7d com `revert_rate ≤ 30%` antes de investir em UX polida.
  Se falhar, pausar P4 e reavaliar feature.

## Definition of Done

Esta sprint fecha quando:

- ☑ [[ADR-186]] flippada para `Decidido (A12)` — confirmada PR #194 (2026-05-11).
- ☑ [[ADR-188]] flippada para `Decidido (A12)` — confirmada PR #198 (2026-05-11).
- ☑ P1-P4 (UI mínima) mergeados em `main` com gates verdes (PRs #188/#194/#195-#198/#203).
- ☑ Gate técnico dogfood com verdict PASS (PR #202, 11/11 invariantes).
- ☐ Gate dogfood humano passou (CEO 7d wall-clock no `5@5.com`).
- ☑ KPIs `mathoms.categorization.*` instrumentados na versão MVP (P3 backend).
- ☐ Plano canônico arquivado em `docs/archive/CAT_LEARNING_LOOP-YYYY-MM-DD.md`.

V2 (P5 inbox de sugestões + P6 detector offline + alertas SRE +
side-panel 480px + highlight-to-extract) entra em sprint posterior,
condicional a sinais positivos da feature MVP.
