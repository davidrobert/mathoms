---
id: MOC-sprint-a12
type: moc
title: Sprint A12 — Categorization learning loop + post-A11 follow-up
aliases: ["A12", "Sprint A12"]
sprint_status: paused
---

# Sprint A12 — Categorization learning loop + post-A11 follow-up (origem 2026-05-10)

> **Status:** `paused` desde 2026-05-20 ([[ADR-234]]) — cedeu prioridade
> para [[Sprint A15]] (FU-3 imóvel financiado, originalmente débito desta
> sprint via [[ADR-215]] §Follow-ups). P1-P4 (UI mínima) + gate técnico
> shipped (PRs #188, #194, #195-#198); gate dogfood humano (7d
> wall-clock) é o último bloqueio para fechar DoD. FU-1 + FU-2 entregues,
> FU-3 absorvido como A15. Retomada: flip `paused → candidate` quando
> A15 fechar.
>
> **Reconciliação 2026-07-08:** frontmatter das lanes estava stale desde a
> pausa. Verificação código-contra-DoD confirmou **entregues em `main`**:
> `sunset-disk-artifact` (PRs #262-#268, ADR-212 Decidido),
> `decision-code-autogen` (PR #279, ADR-214 Decidido) e
> `irpf-prefill-bank-accounts` (PRs #345/#347, ADR-229 Decidido — A13 nunca
> abriu; entregue direto). Pendências reais para fechar a sprint:
> (1) gate dogfood humano do cat-learning-loop (CEO, 7d wall-clock);
> (2) destino da lane [[A12.alocacao-v2]] — único escopo de eng aberto,
> decisão do owner (entregar dentro da A12 vs realocar como débito).

## Resumo

Sprint candidate aberta como **destino canônico** da feature
[`cat-learning-loop`](lanes/A12-cat-learning-loop-override-to-rule.md), movida de A11
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
- **A12.sunset-disk-artifact** ✅ **entregue 2026-05-15** — sunset
  `DiskArtifactStore` + flag `MATHOMS_USE_DB_ARTIFACTS` + coluna
  `use_db_artifacts_override` + CLI standalone do pipeline (PRs #262-#268
  + docs). Cleanup pós-cutover desbloqueou [[ADR-211]] lane 3.
  Plano = [[ADR-212]] (`Decidido (A12.sunset-disk-artifact)`).
  Lane: [A12.sunset-disk-artifact](lanes/A12-sunset-disk-artifact-cleanup.md).
  Track: [sunset-disk-artifact](tracks/sunset-disk-artifact.md).
- **A12.decision-code-autogen** ✅ **entregue 2026-05-15** — `Decision.code`
  server-generated com `pg_advisory_xact_lock`; cliente perdeu input
  "Código da decisão" em 3 modais; `SuggestionResponse` ganhou
  `accepted_decision_code`. PR único cross-cutting
  ([#279](https://github.com/davidrobert/mathoms/pull/279)).
  Fechou race condition real + cleanup UX validado por `product-designer`.
  Plano = [[ADR-214]] (`Decidido`, estende [[ADR-136]]).
  Lane: [A12.decision-code-autogen](lanes/A12-decision-code-autogen-server-gen.md).
  Track: [decision-code-autogen](tracks/decision-code-autogen.md).
- **A12.bank-account-disambig** ✅ **entregue 2026-05-20** — desambiguação
  conta bancária → membro (bug latente multi-membro+mesmo banco descoberto
  2026-05-19). `account_number` discriminador + `account_resolver` puro em
  `pipeline/domain/services/` + DI no E4/InvestmentsConsolidator/E1 + UI
  in-app UNIQUE + 409 backend + partial unique index DB + telemetria + FAQ
  produto. 4 PRs sequenciais ([#337](https://github.com/davidrobert/mathoms/pull/337),
  [#339](https://github.com/davidrobert/mathoms/pull/339),
  [#340](https://github.com/davidrobert/mathoms/pull/340)) — PR1 absorvido
  em PR2 squash. Co-design `data-engineer` + `financial-planner` 2026-05-19.
  [[ADR-226]] `Decidido (A12.bank-account-disambig)`.
  Lane: [A12.bank-account-disambig](lanes/A12-bank-account-disambig-multi-member.md).
  Track: [bank-account-disambig](tracks/bank-account-disambig.md).
- **A12.irpf-prefill-bank-accounts** ✅ **entregue 2026-05-20** — pre-fill
  UI com sugestões de contas detectadas no IRPF via E1; remove fricção
  do `/config` → Membros. 2 PRs
  ([#345](https://github.com/davidrobert/mathoms/pull/345) +
  [#347](https://github.com/davidrobert/mathoms/pull/347)). Originalmente
  deferred → A13, mas A13 nunca abriu (numeração pulou A12 → A15) e a lane
  foi entregue direto; permanece nesta pasta como registro histórico.
  Plano = [[ADR-229]] (`Decidido (A13.irpf-prefill-bank-accounts)`).
  Lane: [A12.irpf-prefill-bank-accounts](lanes/A12-irpf-prefill-bank-accounts-deferred-a13.md).
  Track: [irpf-prefill-bank-accounts](tracks/irpf-prefill-bank-accounts.md).
- **A12.alocacao-v2** ⚠️ **aberta — único escopo de eng pendente** —
  migração alocação-alvo schema v1→v2 (7 classes AUVP, `derived.desvio_*`
  backend-driven, remove `alocacaoBucketMapper` client-side). O schema v2
  existe (`config/schemas/goal.alocacao_alvo.v2.schema.json`, [[ADR-141]]),
  mas a migração runtime **não shipou**: backend/wizard/seeds operam em v1
  e o bucketMapper segue referenciado em 3 componentes do relatório
  (o próprio corpo da ADR-141 registra esse débito; o flip em lote
  Proposto→Decidido do PR #668 cobriu só a decisão de schema). ~5d eng,
  P2. Destino (entregar aqui vs realocar como débito) é decisão do owner.
  Lane: [A12.alocacao-v2](lanes/A12-alocacao-v2-migration.md).

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
