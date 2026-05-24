---
id: MOC-sprint-a17
type: moc
title: "Sprint A17 — Ingestão de Informes de Rendimentos anuais avulsos (4 ondas)"
aliases: ["A17", "Sprint A17"]
sprint_status: current
---

# Sprint A17 — Ingestão de Informes Anuais Avulsos

> **Status:** `current` (promovida 2026-05-21, após A16 L1+L2 entregues). ADR canônica [[ADR-238]] flippada `Decidido (Sprint A17 L1)` em 2026-05-21 após L1 entregue em 5 PRs ([#402](https://github.com/davidrobert/mathoms/pull/402) → [#407](https://github.com/davidrobert/mathoms/pull/407)). L2-L4 são onda de continuação.

## Resumo

Sprint dedicada a **4 ondas (lanes) que destravam ingestão de Informes de Rendimentos anuais avulsos** — fonte fiscal primária paralela ao E1.6 ([[ADR-157]]) e generalização do padrão [[ADR-216]] (informe de aluguel). Diagnóstico em sessão dogfood 2026-05-21 com 15 PDFs reais: ~13 caem em `.other` silencioso ou são mal-classificados como `irpf`.

[[ADR-238]] decidiu **stage único `extract_informes_anuais` paralelo ao `extract_irpf_full`**, com 5 tipos canônicos polimórficos (`previdencia_privada`, `financeiro_pj`, `financeiro_pf`, `proventos_acoes`, `aluguel_imobiliaria`), cascade de fontes com declaração entregue vencendo informe, e rampup em 4 ondas com sinergia explícita com [[ADR-236]].

## Escopo

### L1 — `previdencia_privada` (1 PR Proposto + 4-5 PRs Decidido)

Valida o padrão arquitetural completo. Onda mais valiosa por destravar S8 PGBL ([[ADR-189]]) pré-IR — workspaces que adotam Mathoms em jan-fev sem ter declaração ainda.

Entrega: classifier + `InformeRendimentosBase` polimórfico + sub-schema `informe_previdencia.schema.json` + parser LLM (Claude Sonnet) + `FiscalAnalyzer` polimórfico + UI integration em S8 + migration Alembic catálogo (`brasilprev`).

### L2 — `financeiro_pj` (3-4 PRs · paralela a A16 L2 P5-P6)

**Sinergia direta com [[ADR-236]] em construção.** Alimenta cascata fiscal PJ via `InformeQuery` service antes de A16 L2 cutover — evita ADR-236 mergear sem fonte de dado real.

Entrega: sub-schema `informe_pj.schema.json` (receita bruta + retenções IR/CSLL/PIS/COFINS/ISS por regime), parser LLM, `InformeQuery` service em `backend/app/application/informes/`, integração com [`irpf_renda_tributavel.py`](../../../pipeline/domain/services/tributario/irpf_renda_tributavel.py), catálogo (C6 PJ, Stone PJ via `tax_regime`).

### L3 — `financeiro_pf` (4-5 PRs · 6 bancos + corretora + Wise)

Snapshot 31/12 alimenta `consolidate_baseline` (E1.5c). Maior volume de PDFs (8 dos 15 do batch). **Inclui Wise (multi-moeda, conta no exterior)** — schema modela campo `moeda` (BRL default, aceita USD/EUR/GBP) e ponteiro PTAX 31/12 via `market_rates` ([[ADR-135]]); pegadinhas de código RFB 62, ganho de capital cambial e CBE BACEN documentadas em [[ADR-238]] §D1.

Entrega: sub-schema `informe_pf.schema.json` (4 quadros RFB + `moeda`), parser LLM (Haiku — layout padronizado), regra "informe 31/12 vence extrato D+1", catálogo (Itaú, Santander, Caixa, Nubank, PicPay, C6 PF, XP Investimentos, **Wise** — todos já no seed atual menos `xpinvestimentos`).

### L4 — `proventos_acoes` (2-3 PRs · XP Proventos + Itaúsa)

Yield-on-cost por ativo enriquece S3 (Perini "viver de renda"). Onda final.

Entrega: sub-schema `informe_proventos.schema.json` (eventos por ativo: dividendo, JCP, rendimento FII, bonificação; cuidado com CNPJ pagador ≠ CNPJ fonte), parser LLM, integração [`passive_income_calculator.py`](../../../pipeline/domain/services/passive_income_calculator.py), catálogo (Itaúsa).

## Lanes

- ✅ [[A17.l1]] (`shipped` 2026-05-21) — L1: previdência privada (PGBL/VGBL). Entregue em 5 PRs ([#402](https://github.com/davidrobert/mathoms/pull/402), [#403](https://github.com/davidrobert/mathoms/pull/403), [#404](https://github.com/davidrobert/mathoms/pull/404), [#406](https://github.com/davidrobert/mathoms/pull/406), [#407](https://github.com/davidrobert/mathoms/pull/407)). Padrão arquitetural validado.
- ✅ [[A17.l2]] (`shipped` 2026-05-23) — L2: financeiro PJ. Entregue em 2 PRs ([#453](https://github.com/davidrobert/mathoms/pull/453) schema/prompt + [#454](https://github.com/davidrobert/mathoms/pull/454) classifier + InformeQuery cascata). Stone PJ real do dogfood classifica confidence 1.0.
- [[A17.l3]] (`in_progress`) — L3: financeiro PF + Wise multi-moeda. P1+P2 entregues ([#458](https://github.com/davidrobert/mathoms/pull/458) schema/prompt + [#459](https://github.com/davidrobert/mathoms/pull/459) classifier); P3 (consolidate_baseline + PTAX), P4 (UI S4), P5 (validações Wise) pendentes.
- [[A17.l4]] (`planned`) — L4: proventos ações + holding. Depende de L1.
- ✅ [[A17.l5]] (`shipped` 2026-05-22) — L5: seed expandido institution_catalog (18 entries alta renda PJ). Entregue em 1 PR ([#451](https://github.com/davidrobert/mathoms/pull/451)).
- ✅ [[A17.l6]] (`shipped` 2026-05-24) — L6: hotfix off-theme `RECEBIMENTO DE TED` / `RECEBIMENTO TRANSFERENCIA` no seed `internal_transfer_patterns` engolia salário CLT recebido via TED (Einstein, etc.) silenciosamente. Entregue em 2 PRs ([#475](https://github.com/davidrobert/mathoms/pull/475) lane open + [#480](https://github.com/davidrobert/mathoms/pull/480) fix: seed limpo + migration `a17l6tedfix` + 8 testes de regressão).
- ✅ **A17.canonical-fuzzy** (`shipped` 2026-05-23) — Fuzzy lookup PropertyIdentity por proximidade numérica ([[ADR-265]]). Resolve "Case C" da [[ADR-225]] §Follow-ups: variação numérica leve entre fontes (IRPF cod=11 traz torre/condomínio; comprovante de bem cod=01 traz prédio). Entregue em 1 PR ([#471](https://github.com/davidrobert/mathoms/pull/471)). Track: [[TRACK-a17-canonical-fuzzy-adr225]].

## Pré-requisitos

- [[ADR-238]] mergeada em `main` como `Proposto`.
- [[ADR-236]] L2 P5-P6 idealmente fechadas antes de L2 começar (não bloqueia — `InformeQuery` abstrai o acoplamento, mas reduz risco de retrabalho).

## Bloqueios externos

Nenhum. Não introduz dependência externa nem altera infra de armazenamento ([[ADR-212]] DB-only mantido).

## Não-objetivos

- VGBL como capacidade PGBL ([[ADR-238]] D8 — schema distingue, calculator nunca conta).
- Tabela regressiva PGBL por aporte (V2 condicional).
- Aporte do empregador em PGBL (informe separado, V2).
- Histórico > 2 anos retrospectivos no onboarding.
- Lucro Real PJ (consistente com [[ADR-236]] V1).
- Reforma tributária / PEC dividendos.
- Seção S_FISCAL_AVULSO dedicada no relatório — enriquecimento inline em S3/S4/S8.
- Pré-preenchimento de declaração / DARF / Carnê-Leão.

## Follow-ups potenciais (post-A17)

- **FU-1 · Cutover [[ADR-216]] aluguel → `extract_informes_anuais` com `tipo_informe="aluguel_imobiliaria"`.** Sprint A18.
- **FU-2 · `tipo_informe="patrocinador_pgbl"`** se ICP materializar (informe do empregador, complementa BrasilPrev).
- **FU-3 · Eval de acurácia LLM** com dataset privado fora do git (débito separado, citado em [[ADR-238]] D9).
- **FU-4 · Histórico 5 anos retrospectivos** só com sinal de demanda do beta.
- **FU-5 · Diff informe vs declaração persistido** (hoje efêmero em E5 por LGPD — V2 com criptografia adequada se valor materializar).
