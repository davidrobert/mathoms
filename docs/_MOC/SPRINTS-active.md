---
type: moc
title: SPRINTS-active — Sprint corrente + curating de prioridade
aliases: ["SPRINTS-active", "sprints-active"]
---

# SPRINTS-active — Sprint corrente + curating de prioridade

> **Editorial.** Resumo narrativo da sprint atual. Status detalhado: `_generated/SPRINT_CURRENT.md`.
>
> **Fonte de verdade da sprint corrente:** o campo `sprint_status` no frontmatter de cada `docs/sprint/<X>/_README.md`. Valores: `current` (única) · `candidate` (próxima) · `paused` (escopo aberto, ceu prioridade — múltiplas permitidas) · `done` (encerrada). Validado por `python3 dev/build_doc_index.py --check` — falha se houver 2+ MOCs com `current` ou status fora do vocabulário. Ao virar a sprint, edite os `_README.md` envolvidos **antes** de regenerar. Transições típicas: `current → done` (escopo entregue) · `candidate → current` (promoção); transições com débito conhecido: `current → paused` ou `candidate → paused` ([[ADR-234]]).

## Sprint corrente

### A26 — Data Lineage: consolidação (`current` 2026-06-16)

**Promovida em 2026-06-16, sucedendo A25 (`done`).** 5ª janela do plano [[PLAN-data-lineage]]:
**remove as redes de segurança** da frente (shims de identidade v1, modo `warn` do
`evidencia_path`) após observação de produção. 5 lanes em 2 regimes: **Regime A** —
[[A26.l1]] (fix de citação do `evidencia_path`, **única `open`, sem gate — ponto de
entrada**) + **Regime B** — l2 flip strict · l3 drop shim dedup · l4 override v2 ON +
instrumentação · l5 M2 override destrutiva (todas `blocked` por **volume de tráfego**:
≥20 gerações de parecer; ≥1 sprint com flags v2 a 100% + `dualread.v1_fallback` zerado
com uso real). Co-design 2026-06-16 (PM + IA + data-engineer + prompt-engineer +
sre-devops). Sem ADR nova (ADR-279/287 cobrem; ADR-282 flippa `Decidido` quando a M2
override fechar). **Insumos para destravar l2–l5:** `ANTHROPIC_API_KEY` + ~20 gerações
de parecer + exercício do override v2 por ≥1 sprint + confirmar PITR do Postgres.

- **Sprint:** [sprint/A26/_README.md](../sprint/A26/_README.md) (5 lanes) · **Plano:**
  [plan/DATA_LINEAGE/_README.md](../plan/DATA_LINEAGE/_README.md) §Onda 5 · **Prompt:**
  [agent_prompts/orchestrator_a26_consolidacao.md](../agent_prompts/orchestrator_a26_consolidacao.md).
- **Precedência de corte:** Must l1+l2 · Should l3+l4 · Could/cortável l5 (→ A27).

## Sprint recém-fechada

### A25 — Data Lineage: reverso + produto N1/N2 + debug LLM (`done` 2026-06-16)

**Encerrada em 2026-06-16 — 7/7 lanes shipped.** Cutover do flip dedup `natural_key`
v2 + `member_hashes` reais (l2/l6, #648), query reversa (l3, #600), debug LLM/eval
(l4, #603), produto N1/N2 (l5, #602), cutover override (l1, #604). A l7 (decisão do
flip `warn→strict` do `evidencia_path`) fechou como **carry-over A26** (#649) — o gate
exige ≥20 gerações e só há 3 com telemetria (taxa ~89%, 81% conformidade de path) →
flip vira lane própria na A26. Requisito de done cumprido; modo segue `warn`.

- **Carry-overs A26:** flip strict `evidencia_path` (foco prompt/whitelist via
  `prompt-engineer`) + drop do shim v1 do dedup (M2, [[ADR-287]]).
- **Plano:** [plan/DATA_LINEAGE/_README.md](../plan/DATA_LINEAGE/_README.md) ·
  **Sprint:** [sprint/A25/_README.md](../sprint/A25/_README.md).

## Sprint anterior

### A24 — Data Lineage: extração limpa + walking skeleton (`done` 2026-06-10)

**Fechada em 2026-06-10 — 6 lanes em `main` (#578/#580/#585/#586/#588/#590), G3 atingido, KR2 4/6, zero rebaseline de valor, G-f validado pelo owner.** Promovida em 2026-06-09, sucedendo A23 (`done` — Ondas 0–1 / contrato aditivo, 7 lanes em `main`). A **fase de RISCO** do plano [[PLAN-data-lineage]]: de-leak da extração ([[ADR-280]] — toca goldens E2/E3/E4 + dedup [[ADR-246]]/[[ADR-271]]) + walking skeleton do lineage ([[ADR-279]]) + `evidencia_path` E5→E6 (∥). Recortada em sprint própria (product-manager 2026-06-09) para isolar o perfil de risco da fundação aditiva já estável.

- **Plano dono:** [plan/DATA_LINEAGE/_README.md](../plan/DATA_LINEAGE/_README.md) (§"Blockers da F2 (gate G2)").
- **Sprint:** [sprint/A24/_README.md](../sprint/A24/_README.md). **Prompt:** [agent_prompts/archive/orchestrator_a24_f2f3-2026-06-10.md](../agent_prompts/archive/orchestrator_a24_f2f3-2026-06-10.md).
- **Sprint goal:** G3 / **KR2 1/6** — patrimônio líquido localizável por 1 comando CLI, `check_lineage_sum` verde.
- **Revisão de risco (senior-cto + data-engineer, 2026-06-09):** de-leak é cirúrgico (`tipo_lancamento` dead-downstream; `numero_conta_norm` já re-normalizado). Risco real na rede de rebaseline → substrato endurecido (invariante por categoria, manifesto `reason`/`adr`, `check_golden_rebaseline_isolation`) ANTES do 1º rebaseline. Discovery é o 1º gate.

## Sprint candidate (próxima)

### A27 — Data Lineage Onda 6 (conclusão): citação confiável do parecer (`candidate` 2026-06-19)

**Sucessora direta da A26.** 6ª e última janela do plano [[PLAN-data-lineage]]: fecha a
raiz que a A26 contornou — o LLM para de autorar o número do parecer e o pipeline
renderiza o valor da folha ([[ADR-296]], executada via [[A26.l9]]) — e materializa a
citação verificada como **edge de lineage por chave natural** ([[ADR-293]], lane nativa
[[A27.l1]]). Ordem: edge slices 1+3 ∥ l9 → slices 2+4 após o merge da l9 (acoplamento de
contrato da âncora). Condicional: [[A26.l5]] `m2-override-drop` se não fechar na A26.

- **Plano:** [sprint/A27/_README.md](../sprint/A27/_README.md) · **Dono:** [plan/DATA_LINEAGE/_README.md](../plan/DATA_LINEAGE/_README.md) §Onda 6.

### A18 — Comprovantes de Bem + Apólices + FIPE refresh (`candidate` 2026-05-21)

**Próxima na fila.** 3 lanes coordenadas que destravam ingestão de CRLV-e, apólices polimórficas (combinada multi-bem como caso V1), e refresh assíncrono de valor de mercado via BrasilAPI. ADR canônica [[ADR-239]] (`Proposto`). Diagnóstico dogfood 2026-05-21: 6 PDFs (3 CRLV + 3 apólices) todos em `.other` silencioso.

- **Plano:** [sprint/A18/_README.md](../sprint/A18/_README.md).

### A19 — Card S_PROTECAO no relatório (`candidate`, downstream de A18)

**Reservada pós-A18.** Card S_PROTECAO no relatório React como **4º pilar AUVP (Proteção Patrimonial)**, posicionado entre S2 (Reserva) e S4 (Patrimônio). 4 KPIs V1, 3 subgrupos, linguagem CRC. ADR canônica [[ADR-240]] (`Proposto`). Depende de A18 (apólices) para alimentar inputs reais.

- **Plano:** [sprint/A19/_README.md](../sprint/A19/_README.md).

## Sprints pausadas

Sprints com escopo aberto cujo trabalho foi suspenso. Retomada não-bloqueada: lanes ready continuam ready, frontmatter volta a `current`/`candidate` quando o owner decidir.

### A22 — Launch Trust: Parecer defensável (F3) (`paused` 2026-06-02)

**Suspensa em 2026-06-02 em favor de A23 (Data Lineage)** — re-priorização do owner (transição `current → paused`, [[ADR-234]]). Débito conhecido: 5 lanes abertas (`l1`/`l3`/`l5` open, `l2`/`l4` planned), **nenhuma shipped**. Fecha o núcleo da Frente 3 (Parecer defensável): eval em CI com 24 goldens + 7 red lines hard-block (KR7), validação em 3 camadas, fallback `needs_review` atômico (KR8). Restrição mantida: zero passo humano, zero deploy.

- **Plano dono:** [plan/LAUNCH_TRUST/_README.md](../plan/LAUNCH_TRUST/_README.md) · **Sprint:** [sprint/A22/_README.md](../sprint/A22/_README.md).
- **ADR Proposto antes do PR (ao retomar):** l2 (7 red lines), l5 (schema formal de `dividas`).
- **Retomada:** flip `paused → current` quando o owner decidir retomar F3.

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
