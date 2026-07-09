---
id: MOC-sprint-a33
type: moc
title: "Sprint A33 — Autonomia total: débito executável sem nenhuma ação do owner (LLM hardening + fechamento A17 + retenção)"
aliases: ["A33", "Sprint A33"]
sprint_status: done
date: "2026-07-07"
closed: "2026-07-08"
theme: "autonomous-debt"
---

# Sprint A33 — Autonomia total: débito executável sem ação do owner

> **Status:** `done` (fechada 2026-07-08 — 8/8 lanes shipped em ~20h de
> execução, **zero ações do owner**; executada durante a janela da
> [[MOC-sprint-a32]] `current`, precedente A27 — ver §Fechamento).
> Origem: pedido do owner 2026-07-07 — "sprint focada em
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

Três fontes de débito executável, verificadas 1 a 1 em 2026-07-07 —
**incluindo reconciliação contra o código** (revisão de kickoff por
`product-manager` + `data-engineer`: o drift plano-de-maio ↔ código-de-
julho era sistemático):

1. **[[PLAN-llm-prompts-hardening]]** (draft aprovado 2026-05-22):
   restam **W1β residual** (ADR-090 no `e2_llm_extract` — o
   `e15_baseline` já migrou via #718), **W3** (OTLP) e **W4-T01/T02**
   (catálogo via protocol + códigos RFB YAML). Já entregues por outras
   sprints: W1α (LGPD, 2026-07-06), W4-T00 (seed, [[A17.l5]] #451) e
   **W2 inteira** (semver + telemetria SQL + goldens fiscais — migration
   `a20l12semver`, A20.l12/l13; a lane l3 desta sprint foi **cortada na
   revisão de kickoff** por já estar entregue, evidência nos 35 goldens
   de `tests/fixtures/llm_golden/` incluindo o caso PGBL+VGBL mesmo CPF).
2. **Sprint A17** (`paused`, "Bloqueios externos: Nenhum"): residual
   [[A17.l3]] P3-P5 (financeiro PF + Wise/PTAX) e [[A17.l4]]
   (**só a integração com S3** — schema/prompt/classifier já existem).
   Fechar as duas flipa A17 → `done`.
3. **[PLAN-platform-review](../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md)**: W6-T05 (retenção de artifacts, track
   `scoped`) e W6-T07 (taxonomy de services, [[ADR-285]], gate de
   entrada explícito).

## Lanes

| Onda | Lane | Título | Prioridade | Status |
|---|---|---|---|---|
| A | [[A33.l1]] | ADR-090 no boundary LLM: `e2_llm_extract` sem `float` monetário + gate no pacote (W1β residual) | P0 | open |
| A | [[A33.l2]] | Fechar [[A17.l3]]: financeiro PF P3-P5 (consolidate_baseline + PTAX + UI S4 + Wise) | P1 | open |
| B | [[A33.l4]] | Fechar [[A17.l4]]: integrar proventos (schema/prompt/classifier prontos) ao S3 | P1 | planned |
| B | [[A33.l5]] | Nightly drift do `extract_with_llm` (Celery beat, follow-up F2 da [[ADR-307]]) | P2 | planned |
| B | [[A33.l6]] | Retenção de artifacts: `retention_until` + prune diário + cascade (W6-T05) | P2 | planned |
| C | [[A33.l7]] | OTLP `mathoms.llm.*` por `{prompt_name, prompt_version}` (W3) | P2 | planned |
| C | [[A33.l8]] | Catálogo via `InstitutionCatalogProvider` + códigos RFB em YAML anual (W4-T01/T02) | P2 | planned |
| C | [[A33.l9]] | Services taxonomy: split em subpacotes ([[ADR-285]]) — gate ≤1 PR em voo em `services/` | P2 | planned |

> **l3 (W2 semver + telemetria SQL) foi cortada na revisão de kickoff**
> (`data-engineer`, 2026-07-07): escopo já entregue por A20.l12/l13
> (migration `a20l12semver`, colunas em `llm_call_log`, 9/9 prompts em
> semver puro, goldens fiscais completos). A numeração mantém o gap
> como trilha de auditoria da revisão.

Dependências: l4 independente (padrão validado em [[A17.l1]]) · l5
independente ([[ADR-307]] F1 mergeada) · l6 sequencia **após**
[[A32.l5]] mergear **e** [[ADR-311]] flipar `Decidido` (mesma tabela
`pipeline_artifacts`; predicado de prune depende da decisão — ver lane)
· l7 independente (persistência SQL já shipou via A20.l12/l13) ·
l8 ← W4-T00 ✅ · l9 é cauda (gate de entrada só abre quando A32 parar
de gerar PRs em `services/`).

Precedência de corte: **Must** l1+l2 (nunca cortar l1) · **Should**
l4+l5+l6 · **Could** l7+l8+l9.

**Nota de carry-over (protege a leitura do KR1):** l6 e l9 dependem de
a A32 desacelerar (l6 espera l5 dela mergear; l9 espera a árvore
`services/` zerar). Se a A32 arrastar, l6/l9 viram carry-over — é
dependência entre sprints de agente, **não** ação do owner; não conta
contra o KR1.

## KR

- **KR1 (meta-guardrail da sprint — processo, não valor):** 100% das
  lanes shipped **sem nenhuma ação do owner**. Anti-Goodhart: lane que
  descobrir gate de owner escondido flipa `blocked` com nota nomeando o
  gate no mesmo dia — descobrir gate não é falha; esperar em silêncio é.
  No fechamento, o sucesso da sprint se mede por KR2-KR4 (valor); KR1 é
  o gate satisfeito, não o troféu.
- **KR2 (l1):** zero `float` monetário em `pipeline/llm/schemas/**`
  (fora de exceção documentada com WHY), verificado por gate
  automatizado (extensão do scan de [[ADR-283]] ao pacote LLM), não por
  leitura manual.
- **KR3 (l2+l4):** sprint A17 flipa `done` — informes financeiro PF
  (incl. Wise multi-moeda com PTAX 31/12) e proventos integrados ao S3,
  medido por goldens sintéticos PII-zero em CI (não depende de dogfood).
- **KR4 (l5+l6):** prune diário de artifacts com teste de cascade +
  predicado (versão corrente/tombstone sobrevivem) verde + job nightly
  de drift do extractLLM com 1ª execução e **resultado do drift-check
  registrado consultável** (roda em ambiente com key existente; CI de
  PR continua sem chamada Anthropic real).
- *(KR de semver/telemetria SQL, que seria da l3 cortada, foi
  **satisfeito antes da sprint** — evidência: migration `a20l12semver` +
  9/9 prompts semver + `llm_call_log.confidence`/`prompt_version`.)*

## Fora de escopo (nomeado, com motivo)

- **COMPETITIVE_PIERRE Fase 1** — recon exige assinatura paga (R$ 120) e
  credenciais fornecidas pelo owner → viola o critério da sprint.
- **A26.l2/l5 e promoção A27** — gated por tráfego de dogfood (≥20
  gerações qualificadas) que só o owner gera.
- **A20 L4/L5/L9, Resend EU (W3-T02), off-site R2 (W4-T01), Sentry/status
  page (W4-T03/T05)** — token/conta/aprovação externa do owner.
- **LGPD G2/G3 ([[ADR-228]])** — triagem legal é do owner.
- **Go F2 cutover ([[ADR-150]])** — decisão do owner.
- **A22.l4 (monitor de drift do parecer)** — já shipou (#801,
  2026-07-06; monitor de 5 sinais + pin test). O residual da A22 é só
  prompt-side das red lines, owner-gated (re-eval LLM).
- **W6-T03 (stage rename)** — já shipou (reconciliação 2026-07-06).
- **W2 do [[PLAN-llm-prompts-hardening]]** — já shipou (A20.l12/l13);
  ver nota do corte da l3 acima.
- **Re-verificação factual da Wave 5 do [PLAN-platform-review](../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md)** —
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

## Fechamento (2026-07-08)

Executada integralmente **durante a janela da A32 `current`** (precedente
A27), aberta 2026-07-07 ~17h45 e fechada 2026-07-08 ~11h30. Nunca flipou
`current` — foi de `candidate` direto a `done` com a A32 ainda ativa.

**Lanes (8/8 shipped):** l1 #827 · l2 #833+#835+#850 · l4 #830 ·
l5 #831 · l6 #844 · l7 #834 · l8 #836 · l9 #849+#852+#853+#854+#855.
Os gates de sequenciamento funcionaram como desenhados: l6 abriu ~4h
após o kickoff (merge da [[A32.l5]] #837 + [[ADR-311]] `Decidido`) e
l9 abriu na manhã seguinte (tráfego em `services/` zerado) — **nenhum
carry-over**.

**KRs verificados:**

- **KR1 ✅ (zero ações do owner):** nenhuma lane flipou `blocked`;
  nenhum gate de owner escondido descoberto. A única incógnita
  (ANTHROPIC_API_KEY para a 1ª execução real do nightly) existia no env
  do backend dev.
- **KR2 ✅:** gate `check_float_money.py --scan-schemas
  pipeline/llm/schemas` em pre-commit (`always_run`), exit 0 — zero
  float monetário fora de allowlist nominal documentada (única exceção:
  `parecer_planejador.valor_estimado_brl`, WHY = cents no persist,
  decisão co-design data-engineer).
- **KR3 ✅:** [[MOC-sprint-a17]] flipou `done` (#850); goldens
  sintéticos PII-zero (Wise multi-moeda + proventos JCP/FII) verdes em
  CI, sem dependência de dogfood.
- **KR4 ✅:** prune diário com predicado + cascade testados e dry-run
  registrado no #844 (6.049 rows/~110,8 MB candidatos, gate "zero
  correntes marcadas" = 0, idempotência confirmada; flip
  `prune_mode=delete` fica gated no relatório dry-run de produção, por
  design); nightly drift com 1ª execução real 4/4 PASS consultável em
  `llm_drift_check` + custo US$0,077/execução (~US$2,30/mês vs cap
  US$20 do [[ADR-173]], janela mês-calendário).

**Bônus de escopo:** [[ADR-285]] flipou `Decidido` (l9); emenda datada
na [[ADR-135]] (PTAX compra como invariante de `market_rates` + re-seed
31/12 real); correção do bootstrap de câmbio que devolvia cotação de
2026 para consultas de 2024 silenciosamente (achado do co-design).
