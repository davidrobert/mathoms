---
id: MOC-sprint-a22
type: moc
title: "Sprint A22 — Launch Trust: Parecer defensável (F3)"
aliases: ["A22", "Sprint A22"]
sprint_status: done
date: "2026-05-31"
theme: "parecer-defensavel"
---

# Sprint A22 — Launch Trust: Parecer defensável (F3)

> **Status:** `done` — fechada em 2026-07-08. Suspensa em 2026-06-02 (transição
> `current → paused`, [[ADR-234]]) em favor de [[MOC-sprint-a23]] (Data Lineage);
> retomada e fechada retroativamente após reconciliação contra o código provar as
> 5 lanes em `main`. Segunda janela de execução do plano [[PLAN-launch-trust]].
>
> **Fechamento 2026-07-08 (todas as 5 lanes em `main`, KRs verdes):** `l1`
> (harness de eval) e `l3` (fallback `needs_review` atômico) já vieram de A23–A27;
> **`l2`** 7 red lines / KR7 ([#690](https://github.com/davidrobert/mathoms/pull/690),
> [[ADR-300]] `Decidido`) + calibração via dogfood (`RED_LINES_VERSION 1.4`,
> #697–#702); **`l5`** dedup de dívida + schema formal
> ([#689](https://github.com/davidrobert/mathoms/pull/689), [[ADR-301]] `Decidido`);
> **`l4`** drift detection (5 sinais) + pin de model
> ([#801](https://github.com/davidrobert/mathoms/pull/801)). O prompt-side das red
> lines (REGRA 14 + `PROMPT_VERSION 2.1.0`) também foi entregue (#700/#701).
> Verificação de fechamento: 337 testes Python + 5 React verdes (7 red lines,
> 24 fixtures holdout, `additionalProperties:false`, fallback backend+React,
> 20 INV-D de dívida, drift 5 sinais + model pin). **KR-a..KR-e todos batidos.**
>
> **Plano dono:** [[PLAN-launch-trust]] ([plan/LAUNCH_TRUST/_README.md](../../plan/LAUNCH_TRUST/_README.md)).
> A21 abriu os dois gates de F3 (F1-O0 verde + defesa de injeção [[ADR-175]] em
> `main`); A22 fechou o **núcleo de F3** — a malha de eval + guardrails que torna
> o Parecer do Planejador defensável diante de um cliente pagante.
>
> **Residual owner-gated (fora do escopo desta janela, não bloqueou o fechamento):**
> KR5 deploy reproduzível (GHCR/Coolify, [[ADR-228]] G3) · KR4 off-site R2
> ([[ADR-228]] G2) · LLM-real nightly como gate (budget de provider) · F1-O5
> dedup de veículo (Defer P2).

## Resumo

A21 entregou a frente F1 inteira (confiabilidade do número) e abriu os gates de
F3 e LGPD. A22 ataca o que sobrou para o cutover: a **Frente 3 — Parecer
defensável**. O Parecer existe e renderiza ([[PLAN-planner-review]], Atos 0-6);
falta provar que **não alucina conselho irresponsável** (eval + 7 red lines com
hard-block) e que **degrada com graça** quando o LLM cai (fallback
`needs_review` atômico). Em paralelo, uma lane barata de F1 fecha a
confiabilidade do número de **dívida cross-year** (F1-O3), agora destravada pelo
contrato `EntityDedup` entregue em A21.l3.

A restrição de design da A21 **permanece**: zero passo humano externo, zero
deploy em produção — só engenharia. Os gates que exigem credencial externa
(deploy GHCR, off-site R2) **não entram como lanes** — ficam rastreados em
[[ADR-228]] G2/G3, owner `sre-devops`, com prazo atrelado ao cutover.

## Sprint goal

> Tornar o Parecer do Planejador **defensável e à prova de falha** — eval em CI
> com 24 goldens e 7 red lines que hard-block (KR7), validação em 3 camadas, e
> fallback atômico quando o LLM cai (KR8). Em paralelo, fechar a dívida
> cross-year (F1-O3). Deploy e off-site permanecem owner-gated ([[ADR-228]]
> G2/G3), explicitamente fora desta janela.

## KRs da janela (mapeiam KR7/KR8/KR2/KR3 do plano dono)

| KR | Métrica | Meta | Mapeia | Gate de fechamento? |
|---|---|---|---|---|
| A22-KR-a | 24 golden fixtures do Parecer em CI + harness de eval verde | 24/24 fixtures, eval roda em CI | KR7 (parcial) | **Sim** |
| A22-KR-b | 7 red lines hard-block disparam em teste; schema do parecer com `additionalProperties:false` | 7/7 red lines testadas e bloqueando | KR7 (completa) | **Sim** |
| A22-KR-c | Fallback atômico: LLM down → relatório renderiza sem o Parecer, sem erro 500 | 1 teste E2E verde provando degradação | KR8 | **Sim** |
| A22-KR-d | Dívida cross-year deduplicada: `max(ano)` saldo + warning de monotonicidade; schema `dividas` formal | 0 double-count em golden multi-ano de dívida | KR2/KR3 (extensão) | Should |
| A22-KR-e | Drift: 3 sinais instrumentados (confidence dist · taxa needs_review · Δtokens/custo entre `PROMPT_VERSION`) + pin de model-snapshot | 3/3 sinais emitindo em dogfood | KR7 (observabilidade) | Should |

> KR4 (backup/restore full) e KR5 (deploy reproduzível) do [[PLAN-launch-trust]]
> **permanecem fora desta janela** — owner-gated, rastreados em [[ADR-228]]
> G2/G3. Aberto, não esquecido.

## Lanes

Hard-rank por **destravamento**. `l1` é pré-requisito duro de `l2` e `l4`
(o harness de eval + fixtures é o que permite testar as red lines e medir
drift). `l3` e `l5` são independentes e arrancam no dia 1.

| Lane | Frente | Status | Prioridade | Effort | ADR | Owner |
|---|---|---|---|---|---|---|
| [[A22.l1]] | F3-O0 | ✅ pré-existente (A23–A27) | P0 | M | — | prompt-engineer |
| [[A22.l2]] | F3-O1 | ✅ #690 | P0 | M | [[ADR-300]] `Decidido` | prompt-engineer + financial-planner |
| [[A22.l3]] | F3-O2 | ✅ pré-existente (A23–A27) | P0 | S–M | — | senior-cto |
| [[A22.l4]] | F3-O4 | ✅ [#801](https://github.com/davidrobert/mathoms/pull/801) | P1 | M | — | prompt-engineer |
| [[A22.l5]] | F1-O3 | ✅ #689 | P1 | S | [[ADR-301]] `Decidido` | data-engineer + financial-planner |

> **Tier:** Must (gate de fechamento) = `l1`, `l2`, `l3`. Should = `l4`, `l5`.
> Se a janela apertar, `l4`/`l5` escorregam para A23 sem perder os KRs de
> fechamento.

## Sequenciamento — 3 trilhas no dia 1

```
F3 eval:  l1 (24 goldens + eval CI) ──→ l2 (validação 3 camadas + 7 red lines)
                              └────────→ l4 (drift + model-pin)   [Should]
F3 falha: l3 (fallback needs_review atômico)   [independente, dia 1]
F1:       l5 (dedup dívida cross-year + schema) [independente, dia 1]
```

- **Onda 1 (dia 1, paralelo):** `l1`, `l3`, `l5` — não compartilham código.
- **Gate interno:** `l1` mergeado antes de abrir `l2` (a validação precisa do
  harness + fixtures) e `l4` (drift precisa do baseline de distribuição).
- **Onda 2:** `l2` (gate de KR7) + `l4` (Should).
- **Ordem de must-merge para fechar:** `l1 → l2` (serial, KR7) · `l3` (KR8,
  paralelo) · `l5` (número, paralelo). `l4` fecha por último ou escorrega.

**Co-review de domínio:** `l2` (as 7 red lines são regra de domínio — o que é
"defensável") e `l5` (a regra `max(ano)` de saldo devedor é regra patrimonial)
invocam `financial-planner` **ao abrir a lane**, não no fim.

**Trade-off de capacidade:** `l2` e `l5` ambas tocam JSON Schema com
`additionalProperties:false` (schemas diferentes — parecer vs. dívidas, sem
colisão de arquivo). Se houver um só agente de schema, sequencie `l5` depois de
`l2` em vez de paralelo.

## Federação (regra anti-drift)

- **l1/l2/l3/l4** implementam o núcleo de F3 do [[PLAN-launch-trust]] (frente
  FEDERADA → [[PLAN-planner-review]] done + [[PLAN-llm-prompts-hardening]]). Não
  reabrem o stage do Parecer; adicionam a malha de eval/guardrails que falta. No
  merge, os checkboxes F3-O0/O1/O2/O4 do plano dono flippam — **não** se
  re-implementa em A23.
- **l5** entrega **F1-O3** do plano dono (frente OWNED). Vira uma
  `EntityDedupPolicy` (~30 linhas) sobre o runner entregue em A21.l3.
- **l4** depende da telemetria de `confidence`/`PROMPT_VERSION` já em `main`
  (`backend/app/models/llm_call_log.py` + `parecer_orchestrator.py`) — sinal
  instrumentado existe, então drift é mensurável (não vira desejo).

## Pré-requisitos (todos verdes em `main`)

- [[MOC-sprint-a21]] `done` — F1-O0 (INV-1..9), F1-O1 (golden fn/fp), F1-O2
  (contrato `EntityDedup`), F3-O3 (injeção, [[ADR-175]]). ✅
- [[PLAN-planner-review]] `done` — Parecer renderiza (Atos 0-6, ADR-199..208). ✅
- Telemetria de prompt (`PROMPT_VERSION`, confidence) em `main`. ✅

## Não-objetivos / Gates owner-gated

Itens do plano dono que **não entram como lanes** desta janela — dependem de
credencial externa que o owner ainda não liberou. Rastreados, com dono e
evidência esperada, **sem ocupar slot de sprint**:

- **F2-2.0 — deploy reproduzível** (`docker-compose.prod.yml` consumir imagem
  GHCR versionada + `trivy image` blocking; reusa A20.l4/l5 pausadas). Exige PAT
  GHCR + webhook Coolify. → [[ADR-228]] **G3**. Move KR5; permanece **aberto**.
- **W4-T01 off-site** — apontar `restore_drill` para R2 real + drill em staging
  (fecha KR4 full). A21.l9 entregou só o **mecanismo** em CI. Exige
  bucket/credencial R2. → [[ADR-228]] **G2**. Move KR4; permanece **parcial**.
- **F1-O5 — dedup veículo cross-year** (chave placa/renavam + FIPE). Âncora
  forte, baixo risco de falso-positivo → Defer (P2). Vira `EntityDedupPolicy`
  sobre o runner de A21.l3 quando priorizado.
- **LLM-real nightly** como gate de fechamento de KR7 — Should (depende de
  orçamento de provider; o gate de PR usa goldens mockados/determinísticos).

## Bloqueios externos

**Nenhum para as 5 lanes** — por design. Os itens owner-gated acima estão fora
do escopo da janela, não bloqueando-a.

## Follow-ups (A23+)

- **F1-O5** veículo cross-year (nova `EntityDedupPolicy`).
- **Deploy + off-site** quando o owner liberar PAT/Coolify/R2 ([[ADR-228]]
  G2/G3) — fecha KR4/KR5 full.
- **LLM-real nightly** do eval do Parecer (drift de provider).
