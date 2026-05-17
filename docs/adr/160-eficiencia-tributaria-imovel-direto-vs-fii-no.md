---
id: ADR-160
type: adr
title: "Eficiência tributária imóvel direto vs FII no relatório premium (Roadmap)"
status: Roadmap
date: "2026-05-04"
relates_to: ["[[ADR-076]]", "[[ADR-136]]", "[[ADR-153]]", "[[ADR-157]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 160"]
tags:
  - area/money
  - area/pipeline
  - area/report
  - methodology/auvp
  - methodology/cerbasi
  - methodology/perini
  - phase/a2
  - status/roadmap
  - type/adr
size_lines: 72
---

# ADR-160 — Eficiência tributária imóvel direto vs FII no relatório premium (Roadmap)

**Status:** Roadmap • **Data:** 2026-05-04 • **Relaciona** [ADR-076](#adr-076--design-tokens-unificados-site--relatório), [ADR-136](#adr-136--decision-aggregate-event-sourced-com-supersede-chain), [ADR-153](#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples), [ADR-157](#adr-157--schema-irpf-completo-stage-extract_irpf_full).

**Contexto:** Cliente alvo do Mathoms (alta-renda BR) frequentemente tem 1-3 imóveis locados. O produto hoje mostra alocação por classe de ativo mas não compara **eficiência tributária** entre imóvel direto e FII — gap clássico ignorado em ferramentas de planejamento brasileiras (Perini *Viver de Renda*, AUVP módulo FII, Cerbasi *Casais Inteligentes* cap. renda passiva). Imóvel direto carrega IR sobre aluguel até 27,5%, vacância ~8% histórica, custos 1,8-2,5% a.a.; FII tijolo entrega 8-11% bruto isento PF (Lei 11.033/04 art. 3 II) com mark-to-market diário. Investigação 2026-05-04 com sign-off G0 (financial-planner) e G4 (product-designer) materializa fórmulas, layout, copy e ações canônicas.

**Decisão (Roadmap):** Implementar nova feature "Imóveis × Eficiência tributária" no relatório premium. Implementação fica para outra sessão (prompt self-contained em [`docs/agent_prompts/track_real_estate_efficiency.md`](../plan/S4_REAL_ESTATE_ENRICHMENT/_README.md)). Esta ADR fixa fórmulas + UX + threshold + integrações + anti-patterns para destravar execução sem nova rodada de revisão.

**Sub-decisões:**

1. **Posicionamento (G4):** **Renomear S4 existente** (hoje `"Real Estate — Imóveis e Renda Passiva"`) para `"Real Estate — Imóveis e Eficiência Tributária"` em `config/report_layout.yaml` e popular `cards[]` (vazio hoje). NÃO criar `S_IMOVEIS` nova nem aterrissar em S7. Justificativa: S4 tem chart `yield_imoveis` ligado e navegação `{section_id: "S4", num: "4"}` em `navigation.estrategico.Detalhes`; cards de eficiência são complemento natural, custo-zero de navegação.

2. **Fórmulas canônicas (G0 sign-off com correções obrigatórias aplicadas):**
   - **Yield bruto** = aluguel_anual / `valor_mercado_brl`. Exigir campo `valor_mercado_brl` distinto de `valor_aquisicao_brl` no `baseline_patrimonial.itens[type=imovel]`. Se ausente → fallback `valor_brl` + warning visível "Valor de mercado não informado — usando valor declarado IRPF (R$X). Estimativa pode estar desatualizada. [Override]".
   - **Aluguel anual** = soma móvel 12m de E4 categoria `aluguel_recebido`. Se múltiplos imóveis sem subcategoria por imóvel-key, MVP rateia proporcional a `valor_mercado` com warning "rateio proporcional, não real". Subcategoria por imóvel é follow-up.
   - **Yield líquido imóvel** = yield_bruto × (1 − `aliquota_marginal_aluguel`) − `custos_pct`, onde:
     - `aliquota_marginal_aluguel` é derivada da faixa RFB sobre `imposto_apurado.base_calculo_brl + aluguel_anual_projetado` (ADR-157). **NÃO usar `aliquota_efetiva`** — subestima IR sistematicamente em 5-10pp para alta-renda (alíquota efetiva é média ponderada de todas as fontes; aluguel cai marginal).
     - `custos_pct` default **2,0% a.a. do valor de mercado** (IPTU 0,5% + manutenção 0,75% + vacância 0,4% + administradora 0,4% + seguro 0,1%). Owner pode override em `/admin`. **NÃO usar 1%** — otimista demais.
   - **Custo de saída total** = corretagem 5,5% + IR ganho de capital 15% × (valor_mercado − valor_aquisicao_brl). **Remover ITBI** quando destino é FII (ITBI é pago pelo comprador da próxima compra; migração para FII não tem). Disclaimer: "não considera fatores de redução Lei 11.196/05 art. 40 para imóveis pré-1988/1996-2005".
   - **Renda FII equivalente anual** = (valor_mercado − custo_saida_total) × yield_fii × (1 − 0) [isento PF]. Principal pós-saída, não principal cheio.
   - **Payback** = custo_saida_total / (renda_fii_anual − renda_imovel_liquida_anual). Se delta ≤ 0 → "FII não compensaria mesmo no longo prazo dadas as premissas"; evitar div/0.

3. **Yield FII benchmark:** IFIX 12m móvel via [Brapi.dev](https://brapi.dev) cacheado em DB (refresh semanal); fallback hard-coded **8% conservador** se API falhar. Configurável pelo usuário com slider+input acoplado por imóvel (range 2-12%, step 0,1%, persiste em `localStorage['mathoms:report:imovel:<id>:fii_yield']`). Cache de market data externo é **ADR irmã pendente** (ver Follow-ups #1) — não bloqueia esta.

4. **Threshold de exibição:** seção S4 ativa se `valor_imoveis_locados / patrimonio_total > 15%`. **Configurável em UI de operação interna** (`/admin`). Imóvel de moradia (sem aluguel registrado em E4) **NÃO entra na conta**.

5. **Agrupamento >6 imóveis (G4):** top 5 individuais (por valor de mercado) + 1 card agregado "Demais imóveis · N unidades" (variant `neutral`) com tabela inline (1 linha/imóvel) + linha total. NÃO drawer/dialog (perde no PDF export Playwright). NÃO 6 individuais (vira muro vertical).

6. **Ações canônicas (4 templates) — virar `Suggestion` (ADR-153) + `Decision` (ADR-136):**
   - **A1 — Avaliar conversão para FII**: yield_liquido < 3% AND payback ≤ 5 anos AND delta_renda_anual > 0. Severidade `warn`.
   - **A2 — Risco de inadimplência detectado**: ausência de transação `aluguel_recebido` por ≥60d consecutivos onde havia padrão mensal nos 12m anteriores. Severidade `alert`. Anomaly detection sazonal — implementação não-trivial; aceitável diferir para iteração 2.
   - **A3 — Concentração imobiliária acima do alvo AUVP**: imoveis_locados / patrimonio > 30% (não 15% — 15% é threshold de exibição; 30% é threshold de risco real, regra AUVP "1 classe ≤ 30% em LP"). Severidade `info`. Não diz vender; sugere próximos aportes em outras classes.
   - **A4 — Reajuste de aluguel desalinhado com mercado**: ❌ **REMOVIDO do MVP** — depende de yield-mercado por região (FipeZap/Quinto Andar) que não existe no produto. Volta quando houver fonte. Originalmente proposto por financial-planner mas vetado no próprio sign-off.
   - **Janela de isenção R$440k**: ❌ **REMOVIDO** — Lei 11.196/05 art. 39 isenta venda apenas se reaplica em **outro imóvel residencial** em 180d (não FII). Regra técnica fácil de errar + baixa frequência no público-alvo (alta-renda raramente tem único imóvel ≤R$440k). Originalmente proposto, vetado no sign-off G0.
   - Chips horizontais no card (máx 3 visíveis + "+N mais"); click abre dialog inline com CTA "Marcar como decisão" → cria `Decision` no aggregate. NÃO navega para `/acao` (quebra leitura do relatório + perde no PDF).

7. **Wireframe do card (G4):** ReportCard `variant="feature" size="full"` com hierarquia: header (heading_md + badge tipo) → 4 KPIs (mono_value_lg, grid 4 col → 2×2 em <md): Valor mercado, Aluguel/mês, Yield líquido, Gap vs FII signed → tabela comparativa 2 col × 4 linhas (Renda anual líquida, Capital alocado, Custo de saída, Payback) → calculadora colapsada (`<details>` fechado por default; slider+input; reset IFIX visível) → chips de ação → disclaimer caption muted. **Zero token novo** — usa `--brand-info`, `--semantic-alert`, `--semantic-loss`, `--badge-yellow-*` existentes; iconografia `lucide-react` (`Building2`, `Calculator`, `Info`, `AlertTriangle`, `AlertOctagon`, `RotateCcw`).

8. **Copy editorial canônica (G0+G4 aprovaram):** `narrativas.S4.context` + `.conclusion` lidos pelo `SectionSummary` existente.
   - **Context:** `"Os {N} imóveis locados representam {pct}% do patrimônio líquido familiar e geram R$ {renda_liq_anual} anuais em renda passiva, com yield líquido médio de {yield_liq}% a.a. — abaixo do IFIX 12m ({ifix}%) e do CDI ({cdi}%)."`
   - **Conclusion:** `"A análise abaixo compara cada imóvel com renda equivalente em FIIs, considerando custo de saída (IR sobre ganho de capital). O exercício é estritamente financeiro — decisões reais ponderam moradia futura, herança e relacionamento com inquilinos, dimensões fora deste relatório."`
   - **Disclaimer por card:** `"Custo de saída inclui IR sobre ganho de capital (15%) e corretagem 5,5%. Valor de aquisição reflete declaração IRPF {ano} e pode estar defasado vs. mercado."`
   - **Proibições editoriais:** zero ocorrência de "venda/perda/incrível/excelente/deveria/erro". Tom private banking sério, número específico do cliente, reconhece dimensão não-financeira.

9. **Anti-patterns documentados (G0):**
   1. Comparar yield bruto FII com yield líquido imóvel — sempre líquido vs líquido, com cálculo do líquido visível.
   2. Tratar yield FII trailing como permanente — IFIX é cíclico com Selic; nota "premissa em ciclo Selic intermediário".
   3. Ignorar volatilidade de cota FII vs imóvel — FII tem mark-to-market visível; imóvel tem volatilidade equivalente porém invisível na ausência de avaliação.
   4. Esquecer que FII isento PF perde isenção se cotista detém >10% das cotas OU FII tem <50 cotistas OU cotista é PJ.
   5. Não considerar inadimplência/vacância como drag estrutural — yield líquido já desconta vacância 8% histórica; reforço no copy.

**Consequências:**

- ✅ Insight novo, raramente numerificado, para perfil alta-renda — usa 100% dado já disponível (baseline + E4 + IRPF E1.6).
- ✅ Fórmulas têm sign-off G0 (Perini/Cerbasi/AUVP citados) e UX tem G4. Implementação destravada sem nova revisão.
- ✅ Reusa primitivos existentes: `ReportCard`, `MonetaryValue` signed, `SectionSummary`, `<details>`, `Suggestion` aggregate, `Decision` aggregate. Zero modelo de domínio novo.
- ⚠️ `valor_mercado_brl` separado de `valor_aquisicao_brl` no schema E1.5 é mudança que precisa migration ou tratamento de fallback. Diferimento ok no MVP via warning visível.
- ⚠️ Subcategoria de aluguel por imóvel (rateio proporcional como fallback) é débito declarado.
- ⚠️ Cache Brapi em DB precisa ADR irmã antes de ligar IFIX dinâmico — fallback 8% hard-coded sustenta MVP.
- ❌ Anomaly detection de inadimplência (A2) é não-trivial — diferir iteração 2.
- ❌ Reajuste regional (A4 original) e janela R$440k removidos — sem fonte de dado / regra técnica errada.

**Follow-ups (executar em outra sessão):**

1. **Implementação canônica** seguindo prompt em [`docs/agent_prompts/track_real_estate_efficiency.md`](../plan/S4_REAL_ESTATE_ENRICHMENT/_README.md). Estima 3-5 dias dev (G0+G4 já feitos).
2. **ADR irmã: cache de market data externo (Brapi/B3)** — yield IFIX dinâmico precisa decidir refresh strategy + fallback + DPA Brapi. Bloqueador para A3 IFIX dinâmico, não para o MVP (8% hard-coded sustenta).
3. **Schema E1.5 evolution: separar `valor_mercado_brl` de `valor_aquisicao_brl`** + migration. Mantém retrocompat via fallback (`if not valor_mercado_brl: use valor_brl + warning`).
4. **Subcategoria de aluguel por imóvel-key** em `categorization.json` + UI de mapeamento. Substitui rateio proporcional por dado real.
5. **Anomaly detection sazonal de inadimplência** (ação A2) — iteração 2 da feature.
6. **Fatores de redução IR Lei 11.196/05 art. 40** para imóveis antigos — refinamento de A2.
