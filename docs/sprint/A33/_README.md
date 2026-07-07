---
id: MOC-sprint-a33
type: moc
title: "Sprint A33 — Autonomia total: débito executável sem nenhuma ação do owner (LLM hardening + fechamento A17 + retenção)"
aliases: ["A33", "Sprint A33"]
sprint_status: candidate
date: "2026-07-07"
theme: "autonomous-debt"
---

# Sprint A33 — Autonomia total: débito executável sem ação do owner

> **Status:** `candidate` (aberta 2026-07-07; [[MOC-sprint-a32]] é a
> `current`). Origem: pedido do owner 2026-07-07 — "sprint focada em
> elementos que não demandem ações minhas". Critério de inclusão único:
> **zero ações do owner** — sem token, sem key nova, sem assinatura paga,
> sem decisão pendente, sem tráfego de dogfood. Toda lane é executável por
> agentes de ponta a ponta (branch → PR → CI verde → auto-merge).
> Co-design 2026-07-07: `product-manager` (composição/KR) +
> `information-architect` (forma/MOC) + `data-engineer` (retenção, drift,
> cadeia Decimal). Nenhuma ADR nova — a sprint executa ADRs existentes
> ([[ADR-090]], [[ADR-233]], [[ADR-238]], [[ADR-285]], [[ADR-307]]) e
> ondas já revisadas do [[PLAN-llm-prompts-hardening]].

## Composição (de onde vem cada lane)

Três fontes de débito executável, verificadas 1 a 1 em 2026-07-07:

1. **[[PLAN-llm-prompts-hardening]]** (draft aprovado 2026-05-22, ondas
   nunca abertas como lanes): W1β (ADR-090 nos schemas LLM — P0), W2
   (semver + telemetria SQL), W3 (OTLP), W4-T01/T02 (catálogo via
   protocol + códigos RFB YAML). W1α (LGPD) fechou 2026-07-06; W4-T00
   (seed) fechou como [[A17.l5]] (#451).
2. **Sprint A17** (`paused`, "Bloqueios externos: Nenhum"): residual
   [[A17.l3]] P3-P5 (financeiro PF + Wise/PTAX) e [[A17.l4]] (proventos).
   Fechar as duas flipa A17 → `done`.
3. **[[PLAN-platform-review]]**: W6-T05 (retenção de artifacts, track
   `scoped`) e W6-T07 (taxonomy de services, [[ADR-285]], gate de
   entrada explícito).

## Lanes

| Onda | Lane | Título | Prioridade | Status |
|---|---|---|---|---|
| A | [[A33.l1]] | ADR-090 no boundary LLM: `e15_baseline` + `e2_llm` sem `float` monetário (W1β) | P0 | open |
| A | [[A33.l2]] | Fechar [[A17.l3]]: financeiro PF P3-P5 (consolidate_baseline + PTAX + UI S4 + Wise) | P1 | open |
| A | [[A33.l3]] | `PROMPT_VERSION` semver puro + telemetria `confidence`/`prompt_version` em SQL (W2) | P1 | open |
| B | [[A33.l4]] | Fechar [[A17.l4]]: proventos de ações (XP + Itaúsa) → S3 | P1 | planned |
| B | [[A33.l5]] | Nightly drift do `extract_with_llm` (Celery beat, follow-up F2 da [[ADR-307]]) | P2 | planned |
| B | [[A33.l6]] | Retenção de artifacts: `retention_until` + prune diário + cascade (W6-T05) | P2 | planned |
| C | [[A33.l7]] | OTLP `mathoms.llm.*` por `{prompt_name, prompt_version}` (W3) | P2 | planned |
| C | [[A33.l8]] | Catálogo via `InstitutionCatalogProvider` + códigos RFB em YAML anual (W4-T01/T02) | P2 | planned |
| C | [[A33.l9]] | Services taxonomy: split em subpacotes ([[ADR-285]]) — gate ≤1 PR em voo em `services/` | P2 | planned |

Dependências: l4 independente (padrão validado em [[A17.l1]]) · l5
independente ([[ADR-307]] F1 mergeada) · l6 sequencia **após**
[[A32.l5]] mergear (mesma tabela `pipeline_artifacts`; ver lane) ·
l7 ← l3 (persistência SQL precede OTLP) · l8 ← W4-T00 ✅ · l9 é cauda
(gate de entrada só abre quando A32 parar de gerar PRs em `services/`).

Precedência de corte: **Must** l1+l2+l3 (nunca cortar l1) · **Should**
l4+l5+l6 · **Could** l7+l8+l9.

## KR

- **KR1 (meta da sprint):** 100% das lanes shipped **sem nenhuma ação do
  owner**. Anti-Goodhart: lane que descobrir gate de owner escondido flipa
  `blocked` com nota nomeando o gate no mesmo dia — descobrir gate não é
  falha; esperar em silêncio é.
- **KR2 (l1):** zero `float` monetário em `pipeline/llm/schemas/**`,
  verificado por gate automatizado (extensão do scan de modelos ao pacote
  LLM), não por leitura manual.
- **KR3 (l3+l7):** 9/9 prompts com `PROMPT_VERSION` semver puro
  ([[ADR-233]]) e `confidence` + `prompt_version` persistidos em
  `llm_call_log` consultável por SQL.
- **KR4 (l2+l4):** sprint A17 flipa `done` — informes financeiro PF
  (incl. Wise multi-moeda com PTAX 31/12) e proventos integrados, medido
  por goldens sintéticos PII-zero em CI (não depende de dogfood).
- **KR5 (l5+l6):** prune diário de artifacts com teste de cascade verde +
  job nightly de drift do extractLLM com 1ª execução registrada em
  `llm_call_log` (roda em ambiente com key existente; CI de PR continua
  sem chamada Anthropic real).

## Fora de escopo (nomeado, com motivo)

- **COMPETITIVE_PIERRE Fase 1** — recon exige assinatura paga (R$ 120) e
  credenciais fornecidas pelo owner → viola o critério da sprint.
- **A26.l2/l5 e promoção A27** — gated por tráfego de dogfood (≥20
  gerações qualificadas) que só o owner gera.
- **A20 L4/L5/L9, Resend EU (W3-T02), off-site R2 (W4-T01), Sentry/status
  page (W4-T03/T05)** — token/conta/aprovação externa do owner.
- **LGPD G2/G3 ([[ADR-228]])** — triagem legal é do owner.
- **Go F2 cutover ([[ADR-150]])** — decisão do owner.
- **W6-T03 (stage rename)** — já shipou (reconciliação 2026-07-06).
- **Re-verificação factual da Wave 5 do [[PLAN-platform-review]]** —
  spike docs-only barato, fica como follow-up de fechamento da sprint
  (não é lane; cabe no PR de close).

## Promoção e convivência com a A32

`candidate → current` é flip do owner (ou automático no fechamento da
A32, se o owner delegar). As lanes A (l1-l3) não tocam arquivos das
lanes da A32 (verificado no kickoff: A32 mexe em
`reconciliation_validators`, parsers de fatura, readers E2 e review UX;
A33 onda A mexe em `pipeline/llm/schemas/`, `consolidate_baseline`,
prompts e telemetria) — se o owner quiser antecipar a onda A em paralelo
à A32, o risco de merge é baixo e está declarado aqui. l6 e l9 têm gates
de sequenciamento explícitos por causa da A32.
