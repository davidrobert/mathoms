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

### A22 — Launch Trust: Parecer defensável (F3) (`current` 2026-05-31)

**Promovida em 2026-05-31, sucedendo A21 (`done`).** Segunda janela do plano [[PLAN-launch-trust]] — fecha o **núcleo da Frente 3** (Parecer defensável): eval em CI com 24 goldens + 7 red lines hard-block (KR7), validação em 3 camadas, fallback `needs_review` atômico (KR8), drift detection (Should). Em paralelo, a lane F1-O3 fecha a dívida cross-year sobre o contrato `EntityDedup` de A21.l3. Restrição da A21 mantida: **zero passo humano, zero deploy**. Deploy GHCR + off-site R2 permanecem owner-gated ([[ADR-228]] G2/G3), fora da janela. 5 lanes em 3 trilhas; gate interno `l1` (goldens) antes de `l2`/`l4`.

- **Plano dono:** [plan/LAUNCH_TRUST/_README.md](../plan/LAUNCH_TRUST/_README.md).
- **Sprint:** [sprint/A22/_README.md](../sprint/A22/_README.md).
- **ADR Proposto antes do PR:** l2 (7 red lines = invariante + boundary schema), l5 (schema formal de `dividas`).

## Sprint candidate (próxima)

### A18 — Comprovantes de Bem + Apólices + FIPE refresh (`candidate` 2026-05-21)

**Próxima na fila.** 3 lanes coordenadas que destravam ingestão de CRLV-e, apólices polimórficas (combinada multi-bem como caso V1), e refresh assíncrono de valor de mercado via BrasilAPI. ADR canônica [[ADR-239]] (`Proposto`). Diagnóstico dogfood 2026-05-21: 6 PDFs (3 CRLV + 3 apólices) todos em `.other` silencioso.

- **Plano:** [sprint/A18/_README.md](../sprint/A18/_README.md).

### A19 — Card S_PROTECAO no relatório (`candidate`, downstream de A18)

**Reservada pós-A18.** Card S_PROTECAO no relatório React como **4º pilar AUVP (Proteção Patrimonial)**, posicionado entre S2 (Reserva) e S4 (Patrimônio). 4 KPIs V1, 3 subgrupos, linguagem CRC. ADR canônica [[ADR-240]] (`Proposto`). Depende de A18 (apólices) para alimentar inputs reais.

- **Plano:** [sprint/A19/_README.md](../sprint/A19/_README.md).

## Sprints pausadas

Sprints com escopo aberto cujo trabalho foi suspenso. Retomada não-bloqueada: lanes ready continuam ready, frontmatter volta a `current`/`candidate` quando o owner decidir.

### A20 — Docker dev↔prod parity + P0 production gates (`paused` 2026-05-29)

**Pausada pelo owner** após entregar o objetivo de DX: Docker como caminho opt-in de dev local (`make dev-up-docker` sobe a stack completa numa banda de porta que coexiste com a nativa; docs SETUP/README/`make help` atualizadas). Sprint de infra dedicada, 10 lanes em 2 ondas + gate final, 7 ADRs `Proposto` (ADR-248 a ADR-254). Diagnóstico: review independente `sre-devops` 2026-05-22 (maturidade Docker 2.5/5; 5 blockers P0).

- **Entregue:** Onda A (L10 lockfile → L2 SHA pin; L3 pipeline-service non-root ∥ L6 compose dev) → Gate A → Onda B (L1 multi-stage + Playwright, L7 Makefile+SETUP, L8 driver Postgres psycopg3) + ajuste de coexistência de porta da stack dev (PR #513).
- **Trabalho residual (requer confirmação externa do owner):** L4 (GHCR token + Coolify webhook), L5 (Trivy — depende de L4), L9 (smoke gate — depende de tudo).
- **Plano:** [sprint/A20/_README.md](../sprint/A20/_README.md).
- **Retomada:** flip `paused → current` quando o owner liberar token/Coolify.

### A17 — Ingestão de Informes Anuais Avulsos (`paused` 2026-05-29)

**Suspensa em favor de A20** (priorização do owner; transição `current → paused` por [[ADR-234]]). L1 entregue (ADR canônica [[ADR-238]] `Decidido (Sprint A17 L1)`, 5 PRs [#402](https://github.com/davidrobert/mathoms/pull/402) → [#407](https://github.com/davidrobert/mathoms/pull/407)).

- **Trabalho residual:** L2-L4 abertas em [sprint/A17/_README.md](../sprint/A17/_README.md).
- **Fila reservada pós-A17:** A18 (CRLV + apólices + FIPE, [[ADR-239]]) → A19 (S_PROTECAO 4º pilar AUVP, [[ADR-240]]).
- **Retomada:** flip `paused → current` quando o owner decidir retomar.

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
| A16 | done | L1 ADR-235 `nu_proprietario` ([apps#388](https://github.com/davidrobert/mathoms/pull/388)) + L2 ADR-236 cascata fiscal PJ (PRs #390, #392, #393, #394, #395, #398) — ambas entregues 2026-05-21. |
| A21 | done | Launch Trust F1 inteira (confiabilidade do número) — 9/9 lanes entregues (PRs #524–#538). Contrato `EntityDedup` (ADR-276), dedup imóveis/investimentos/previdência (ADR-277), backup/restore drill CI (ADR-275), goldens+métricas dedup. Gates F3/LGPD migram para A22; off-site/deploy permanecem owner-gated ([[ADR-228]] G2/G3). Encerrada 2026-05-31, sucedida por [[MOC-sprint-a22]]. |

> Tracks por sprint disponíveis em [`docs/sprint/A6/tracks/`](../sprint/A6/tracks/), [`A7/tracks/`](../sprint/A7/tracks/), [`A8/tracks/`](../sprint/A8/tracks/), [`A11/tracks/`](../sprint/A11/tracks/), [`A12/tracks/`](../sprint/A12/tracks/), [`A16/tracks/`](../sprint/A16/tracks/), [`F7/tracks/`](../sprint/F7/tracks/), [`F9/tracks/`](../sprint/F9/tracks/), [`W5/tracks/`](../sprint/W5/tracks/), [`W6/tracks/`](../sprint/W6/tracks/). [BACKLOG](../BACKLOG.md) é apenas shim de navegação.
