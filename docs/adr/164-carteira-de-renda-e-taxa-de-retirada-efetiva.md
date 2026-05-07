---
id: ADR-164
type: adr
title: "Carteira de renda e taxa de retirada efetiva"
status: Decidido
phase: "A8.3"
date: "2026-05-05"
relates_to: ["[[ADR-090]]", "[[ADR-153]]", "[[ADR-157]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 164"]
tags:
  - type/adr
  - status/decidido
size_lines: 52
---

# ADR-164 — Carteira de renda e taxa de retirada efetiva

**Status:** Decidido (A8.3) • **Data:** 2026-05-05 • **Relaciona** [ADR-090](#adr-090--decimal-para-valores-monetários), [ADR-153](#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples), [ADR-157](#adr-157--schema-irpf-completo-stage-extract_irpf_full).

**Contexto:** A Independência Financeira do Perini só fecha quando o produto confronta **TRS meta** (5%/4% — D15) com **TRS efetiva** (yield real do patrimônio investido). Hoje o pipeline mostra apenas projeção: `if_projector.py` calcula `renda_passiva_estimada_4pct = investivel * 4%`, e `ratios_calculator.rentabilidade_pct` ficou `"N/D"` desde A5a. A regra `rule_trs_desalinhada` em `suggestion_rules.py` está dormente — espera `goals.taxa_retirada_efetiva_pct` populado, ninguém popula. O resultado é que o relatório premium não responde a "minha carteira sustenta retirada hoje?" — o que é a pergunta canônica do Perini.

**Decisão:** Introduzir o conceito de **carteira de renda** (`patrimonio_gerador_brl`) e **TRS efetiva** (`renda_passiva_anual_observada / patrimonio_gerador_brl × 100`) como métricas de primeira-classe no E5/S7. PR-A entrega o `PassiveIncomeCalculator`, PR-B re-classifica aluguéis (trabalho → capital) no `IRPFAnalyzer`, PR-C wire ao adapter + UI no S7 + esta ADR.

**Sub-decisões:**

1. **Carteira de renda (`patrimonio_gerador_brl`)** — denominador da TRS efetiva.
   - **Inclusos sempre:** `investimentos_titular` + `investimentos_conjuge` + caixa excedente acima da reserva de emergência.
   - **Inclusos por config (default ON):** `imoveis_investimento`.
   - **Inclusos com yield 0% (sinal pedagógico):** cripto sem staking, ações growth sem dividendo, PGBL/VGBL em acumulação. Excluí-los mascararia concentração.
   - **Excluídos sempre:** residência principal, veículos, derivativos, parcela de caixa = reserva alvo.

2. **Renda passiva observada** — agregado por bucket RFB do IRPF do último ano-base (`IRPFAnalyzer.declarations_for_year`):
   - Dividendos (cod 09 isentos), JCP (cod 10 exclusiva), aplicações (cod 12 isentos + exclusiva), ganho de capital (cod 06 exclusiva), exterior (`rendimentos_exterior`), aluguéis (delta `split_trabalho_vs_capital.capital_brl − explicit`).

3. **Aluguéis re-classificados de trabalho → capital** — Perini classifica aluguel como capital imobiliário; AUVP idem. Manter em `_bucket_trabalho` era artefato. Impacto: `split_trabalho_vs_capital`, `irpf_renda` chart e S8 mudam para todo workspace com aluguel declarado. Migração: nenhuma — recomputação automática no próximo run E5.

4. **Yield 0% explícito** para cripto/growth/PGBL é o sinal pedagógico — usuário vê "BTC: R$ 200k gerador, R$ 0/ano". Esconder esses ativos faria a TRS efetiva subir artificialmente e mascararia concentração. Trinity Study e Perini não excluem growth do denominador.

5. **Filtro de fase em `rule_trs_desalinhada`** — regra só dispara com `goals.if_pct >= 50`. Em acumulação, TRS alta artificial (denominador pequeno, IRPF antigo declarando carteira ínfima vs. atual) não é sinal real de retirada acima do sustentável. Risco evitado: ruído tóxico em todos os iniciantes do dogfood.

6. **Terminologia UI ≠ chave JSON** — UI usa "Carteira de renda" (financial-planner referência) e "Patrimônio investido" (Cerbasi referência); backend usa `patrimonio_gerador_brl` (estável, semanticamente preciso). Não cruzar — UI evolui linguagem, JSON evolui esquema, e ambos escapam de quebras mútuas.

**Mitigações UX obrigatórias** (validadas pelo financial-planner — sem elas, M1 induz erro #1 do iniciante "vender growth para perseguir DY"):

- Renda passiva R$/mês visível **antes** do %.
- Tooltip via ``Info`` icon ao lado do label "TRS efetiva" (WCAG 2.1.1 + 1.4.13).
- Caption permanente quando ``progresso < 50`` substitui tooltip como veículo principal.
- Tom ``warning`` no card "Em acumuladores" + sublabel "&gt;40% subestima TRS" (loop visual com `AcumuladoresBanner`).
- ``DefasagemWarningBanner`` quando IRPF tem ≥ 15 meses (CTA "Importar IRPF mais recente").

**Consequências:**

- ✅ Regra dormente `rule_trs_desalinhada` finalmente dispara — com filtro de fase evita ruído.
- ✅ S7 responde "minha carteira sustenta retirada hoje?" com dado real, não estimativa.
- ✅ Status enum (`ok` / `sem_irpf` / `gerador_zero`) trata empty states como first-class — métrica errada > sem métrica.
- ✅ `PassiveIncomeCalculator` é service puro (R9/ISP), testável sem rede/DB. 15+ unit tests cobrem cada bucket + cada filtro de patrimônio + 3 cenários de acumuladores.
- ⚠️ Aluguéis no bucket capital muda `split_trabalho_vs_capital` em produção — chart `irpf_renda` e S8 vão exibir números diferentes para todo workspace com aluguel declarado. Documentado como decisão consciente, não regression.
- ⚠️ TRS efetiva exibida sem mitigações induz erro do iniciante; mitigações UX (caption permanente em acumulação, tom condicionado à fase, banner acumuladores) não são opcionais.
- ❌ Yield-on-cost por classe (FII vs ação vs renda fixa) fica para M3 (premium) — escopo M1 fechado em agregado total + 6 fontes para chart v2.

**Follow-ups:**

1. **Yield-on-cost por classe** (M3) — decompor TRS efetiva por classe de ativo (FII / dividendos / renda fixa / exterior) com benchmark Perini por bucket. Habilita `rule_trs_baixa_em_aproximacao` (oposta da `rule_trs_desalinhada`).
2. **Pro-rata em edge cases** — imóvel uso misto, ouro físico, USD em conta exterior. v1 é binário; v2 pode introduzir factor de exposição.
3. **Refatoração dos 18 hex hardcoded de Onda 9** — não introduzimos novos hex em S7, mas baseline existente continua. Track separado.
