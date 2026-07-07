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

### A30 — Ops FinOps: budget LLM editável no console interno (`done` 2026-07-07)

Origem: dogfood do owner 2026-07-06 — run do pipeline (executor Go, F2 do
ADR-150) abortou no hard-stop de budget LLM ([[ADR-173]]: cap $5, gasto
$5.57) e o único unblock foi UPDATE manual via SQL. 1 lane P1
([[MOC-sprint-a30]]): editor de `monthly_llm_budget_usd` por workspace no
console ops (service + PATCH + UI com contexto mês-calendário + audit
hard-fail) — **shipped no PR #815 (2026-07-07, CI verde)**. KR1: 0 unblocks
de budget via SQL após a lane. Co-design:
`product-manager` + `sre-devops`; sem ADR nova ([[ADR-116]] + [[ADR-173]]).

Na fila do owner: retomar [[MOC-sprint-a26]] (`paused → current`) quando as
≥20 gerações qualificadas de parecer acumularem, ou promover a A27
(`candidate`).

## Sprint recém-fechada

### A29 — Review UX: conferência de pipeline centrada em documentos (`done` 2026-07-06)

Origem: dogfood do owner 2026-07-06 — run E3 pausou em `needs_review` com 18
strings duplicadas sem documento + JSON 29KB; owner aprovou às cegas. 3 lanes
sequenciais ([[MOC-sprint-a29]]): l1 tela de review v1.5 (agrupamento +
consequência explícita + telemetria `review_action`) · l2 cobertura
`ReviewReason` completa em E3 + projeção `validation_issues` (fecha ADR-272
crit. 6) · l3 inbox de pendências em `/documents` + banner de análise pausada.
ADR canônica: [[ADR-308]] (Decidido no fechamento).

**Encerrada em 2026-07-06 — 3/3 lanes shipped no mesmo dia** (l1 #800 · l2
#802 · l3 #803; docs/ADR em #798). Gate F0 de medição overridden pelo owner
("atuar em tudo"); KR1 (≥70% resoluções construtivas) instrumentado via evento
`review_action` aguardando uso; baseline KR2 registrado no #800. Fila do owner
pós-A28 segue válida em paralelo: re-gerar parecer com dados corrigidos ·
`G-owner-reclassify` · `G-owner-label` · re-eval golden do parecer
(owner-gated, US$12).

### A28 — Report Trust: o relatório para de afirmar precisão que os dados não sustentam (`done` 2026-07-06)

**Encerrada em 2026-07-06 — 11/11 lanes shipped** (l2 #754 · l3 #755+ADR-305 ·
l4 #756+ADR-306 · l10 #753 · l7 #779 · l5 #782 · l6 #783+manifest 1.7 · l8 #786 ·
l9 #790 · l11 #788+manifest 1.8 · l1 #787). KR1/KR3 atendidos por teste de
invariante; KR2 e re-medição da l7 aguardam gates de owner (por design); KR4
entregue (banner + âncoras tipadas + ressalva de fallback). Reserva: 86,7 meses
"Excessiva" → 53,3 vs alvo 18m (perfil PJ-dominante); TRS 22,63% → universo
consistente + guardrail >8%; PGBL: 1 recomendação por relatório; ADR-240 ativada.

**Promovida em 2026-07-03; A26 → `paused` ([[ADR-234]]).** 1ª janela do plano
[[PLAN-report-trust]], nascida da revisão completa do relatório dogfood `72883bde`:
três recomendações do relatório atual **pioram** a situação do cliente (TRS fictícia
22,63% a.a. → desacelerar aporte; reserva "Excessiva" de 31,6 meses com numerador =
todo o investível → desmobilizar carteira; Cerbasi "Gastador" sobre R$ 401k de despesa
opaca → cortar gasto errado). Duas são violação de contrato escrito (FORMULAS.md
§Reserva · [[ADR-191]]). Co-design 2026-07-03 (PM + IA + data-engineer +
prompt-engineer; financial-planner + product-designer no parecer de origem).

**11 lanes em 3 ondas:** Onda 0 (fórmula, Must, `[l4→l1] ∥ l2 ∥ l3` — ADRs `Proposto`
em l3/l4) → Onda 1 (loop de dados: categorização [[A28.l5]], proteção/apólices
[[A28.l6]], dedup de imóveis excluídos [[A28.l7]], higiene de períodos [[A28.l8]]) ∥
Onda 2 (apresentação honesta: banner de qualidade [[A28.l9]], formatter de âncoras
[[A28.l10]], guardrails pós-LLM [[A28.l11]] — l10 livre; l9/l11 mergem pós-Onda 0).
Gates de owner: `G-owner-reclassify` + `G-owner-label`.

- **Sprint:** [sprint/A28/_README.md](../sprint/A28/_README.md) (11 lanes) · **Plano:**
  [plan/REPORT_TRUST/_README.md](../plan/REPORT_TRUST/_README.md) · **Prompt (arquivado):**
  [agent_prompts/archive/orchestrator_a28_report_trust-2026-07-06.md](../agent_prompts/archive/orchestrator_a28_report_trust-2026-07-06.md).
- **Precedência de corte:** Must l1+l2+l3+l4 (nunca cortar l1/l2) · Should
  l5+l6+l7+l8+l9+l10+l11 · Could re-medição pós-gate da l7.
- **Sinergia A26:** cada iteração re-gera o parecer → acumula as ≥20 gerações que
  destravam [[A26.l2]]/[[A26.l4]]. Reavaliar retomada da A26 ao fim da janela.

## Sprint anterior

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

## Sprint candidate (próxima)

### A27 — Data Lineage Onda 6 (conclusão): citação confiável do parecer (`candidate` 2026-06-19)

**Sucessora direta da A26 — escopo Must já entregue antecipadamente (2026-07-02),
executado durante a janela A26.** 6ª e última janela do plano [[PLAN-data-lineage]]:
fechou a raiz que a A26 contornou — o LLM parou de autorar o número do parecer e o
pipeline renderiza o valor da folha ([[ADR-296]] `Decidido`, executada via [[A26.l9]]
✅ #687) — e materializou a citação verificada como **edge de lineage por chave
natural** ([[ADR-293]] `Decidido (A27.l1)`, lane [[A27.l1]] ✅ #715/#716/#718; KR3
provado por teste de reordenação de `top_ativos`). Follow-up do KR1: pureza monetária
da prosa (persona 1.1.0, 61→7 violações) + doutrina [[ADR-304]] (#729 ✅). Resta a
**promoção formal** (A26 retoma de `paused`, fecha gates de tráfego → `done`; então
A27→`current`→`done`) — a A28 (`current`) é quem gera esse tráfego. Condicional:
[[A26.l5]] `m2-override-drop` se não fechar na A26.

- **Plano:** [sprint/A27/_README.md](../sprint/A27/_README.md) · **Dono:** [plan/DATA_LINEAGE/_README.md](../plan/DATA_LINEAGE/_README.md) §Onda 6.

### A18 — Comprovantes de Bem + Apólices + FIPE refresh (`candidate` 2026-05-21)

**Próxima na fila.** 3 lanes coordenadas que destravam ingestão de CRLV-e, apólices polimórficas (combinada multi-bem como caso V1), e refresh assíncrono de valor de mercado via BrasilAPI. ADR canônica [[ADR-239]] (`Proposto`). Diagnóstico dogfood 2026-05-21: 6 PDFs (3 CRLV + 3 apólices) todos em `.other` silencioso.

- **Plano:** [sprint/A18/_README.md](../sprint/A18/_README.md).

### A19 — Card S_PROTECAO no relatório (`candidate`, downstream de A18)

**Reservada pós-A18.** Card S_PROTECAO no relatório React como **4º pilar AUVP (Proteção Patrimonial)**, posicionado entre S2 (Reserva) e S4 (Patrimônio). 4 KPIs V1, 3 subgrupos, linguagem CRC. ADR canônica [[ADR-240]] (`Proposto`). Depende de A18 (apólices) para alimentar inputs reais.

- **Plano:** [sprint/A19/_README.md](../sprint/A19/_README.md).

## Sprints pausadas

Sprints com escopo aberto cujo trabalho foi suspenso. Retomada não-bloqueada: lanes ready continuam ready, frontmatter volta a `current`/`candidate` quando o owner decidir.

### A26 — Data Lineage: consolidação (`paused` 2026-07-03)

**Suspensa em 2026-07-03 em favor de A28 (Report Trust)** — re-priorização do owner
(transição `current → paused`, [[ADR-234]]). Estado ao pausar: **6/10 lanes shipped**
(Regime A todo entregue: [[A26.l1]] #654 · [[A26.l6]] #660 · [[A26.l7]] #662 ·
[[A26.l8]] #666 · [[A26.l9]] #687 · [[A26.l3]] #709) + [[A26.l10]] #732; [[A26.l4]]
`in_progress` (flip default #735 ✅; resta observação ≥1 sprint). Restam **blocked por
tráfego**: [[A26.l2]] (flip strict — falta ≥20 gerações reais p/ budget `needs_review`
≤15%) e [[A26.l5]] (M2 destrutiva — G1/G2/G3 + PITR + go/no-go).

**A pausa não atrasa a A26 — acelera:** as lanes restantes esperam tráfego que só o
dogfood do owner gera, e a A28 é a máquina desse tráfego (cada iteração re-gera o
parecer E6 e exercita o override v2).

- **Plano dono:** [plan/DATA_LINEAGE/_README.md](../plan/DATA_LINEAGE/_README.md) §Onda 5 ·
  **Sprint:** [sprint/A26/_README.md](../sprint/A26/_README.md) ·
  **Prompt:** [agent_prompts/orchestrator_a26_consolidacao.md](../agent_prompts/orchestrator_a26_consolidacao.md).
- **Retomada:** flip `paused → current` quando as gerações qualificadas ≥20 (reavaliar
  ao fim da A28) + observação da l4 completar 1 sprint.

### A22 — Launch Trust: Parecer defensável (F3) (`paused` 2026-06-02)

**Suspensa em 2026-06-02 em favor de A23 (Data Lineage)** — re-priorização do owner (transição `current → paused`, [[ADR-234]]). Fecha o núcleo da Frente 3 (Parecer defensável): eval em CI + 7 red lines hard-block (KR7), validação em 3 camadas, fallback `needs_review` atômico (KR8).

**Atualização 2026-06-29 — núcleo entregue (sprint segue `paused`):** ao retomar, a reconciliação contra o código mostrou `l1` (harness eval) e `l3` (fallback atômico) **já entregues em A23–A27**. As duas lanes de gap fecharam: **`l5`** dedup de dívida + schema ([#689](https://github.com/davidrobert/mathoms/pull/689), [[ADR-301]] `Decidido`) e **`l2`** 7 red lines / KR7 ([#690](https://github.com/davidrobert/mathoms/pull/690), [[ADR-300]] `Decidido`). KR7+KR8 verdes. Resta `l4` (drift, Should) + prompt-side das red lines (**owner-gated**, exige re-eval LLM).

- **Plano dono:** [plan/LAUNCH_TRUST/_README.md](../plan/LAUNCH_TRUST/_README.md) · **Sprint:** [sprint/A22/_README.md](../sprint/A22/_README.md).
- **Retomada:** flip `paused → current` quando o owner decidir retomar o residual de F3.

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

**Pausada com débito conhecido.** 6 ondas, 138 findings de revisão multi-agente. W1 ✅ + W2 ✅ entregues. **Reconciliação factual 2026-07-06:** boa parte de W3-W6 shipou via outras sprints — W3-T01/W3-T04 (#718), W4-T04 (#720), W6-T04 (#111), W6-T06 (#110 + ADR-150 `Decidido`); W4-T01/W4-T02/W6-T01/W6-T03 parciais. Residual real: W3-T02 + W4-T01/T02 restos (owner-gated: Resend, token Coolify, off-site R2), W4-T03/T05 (Sentry, status page), W5 (re-verificar no pickup), W6-T02 (destravado)/T05/T07. Sub-lanes paralelas (competitive-pierre, report-publication) preservadas.

- **Trabalho residual:** [plan/PLATFORM_REVIEW/_README.md](../plan/PLATFORM_REVIEW/_README.md) (Index reconciliado por task, com PR/ADR por linha).
- **Sub-lanes preservadas:** A11.competitive-pierre (Fase 1 ready), A11.report-publication (ADR-187 Proposto), A11.cat-overrides-ux ✅ entregue 2026-05-10.
- **DOC_REORG** ✅ entregue em 2026-05-07 (separado da pausa). Arquivado em [DOC_REORG_PLAN-2026-05-07.md](../archive/DOC_REORG_PLAN-2026-05-07.md), ADR canônica [ADR-182](../adr/182-vault-de-documentacao-operacional-obsidian.md).
- **Retomada:** flip `paused → current` quando decidido retomar.

### A12 — Categorization learning loop + post-A11 follow-up (`paused` 2026-05-20)

**Escopo concluído (reconciliação 2026-07-06).** Cat-learning-loop MVP V1 completo: P1-P4 mergeadas (PRs #188, #194, #195-#198, #203); gate dogfood **PASS por decisão do owner 2026-07-02** (gate técnico 11/11 invariantes como evidência); sunset do CRUD legado `/config/categories` + drop do `monthly_cap` Float entregue (#573, ADR-283 §B). FU-1 + FU-2 entregues, FU-3 absorvido e entregue como A15. V2.A/B/C ficam pós-tração (backlog, não débito).

- **Trabalho residual:** nenhum — sprint é candidata a flip `paused → done` (decisão editorial do owner).
- **Plano:** [plan/CAT_LEARNING_LOOP/_README.md](../plan/CAT_LEARNING_LOOP/_README.md) (`status: done`). ADRs: [ADR-186](../adr/186-promocao-override-transacao-para-regra-categorizacao.md) + [ADR-188](../adr/188-evolucao-schema-e-semantica-learning-loop-p3.md).


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
