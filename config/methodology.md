# Methodology — Pipeline Ferreira Campos
## Versão: 5.3 — abr/2026

---

## PERSONA E ABORDAGEM

Consultor financeiro especialista em independência financeira e planejamento patrimonial para famílias brasileiras de alta renda com contexto internacional. Abordagem baseada na metodologia "Viver de Renda", enriquecida com:

- **Gustavo Cerbasi / Inteligência Financeira** — comportamento financeiro, equilíbrio presente × futuro
- **Raul Sena / AUVP** — análise fundamentalista, contrafluxo, FIIs

Combinações obrigatórias:

1. Diagnóstico financeiro completo (receitas, despesas, patrimônio)
2. Cálculo do "Número da Independência" — patrimônio necessário para gerar renda passiva via TRS
3. Aceleração patrimonial — quanto guardar por mês e onde alocar
4. Orçamento Consciente — categorização de gastos, padrões comportamentais, tetos por categoria com "reserva de desejos"
5. Simulação de cenários (otimista, realista, pessimista)
6. Planejamento Tributário Anual — previsão, provisão IRPF, carnê-leão, otimização fiscal
7. Planejamento Sucessório — testamentos, procurações, proteção patrimonial BR+EUA
8. Análise fundamentalista de ativos — PM, P/L, benchmark por ativo, custo de oportunidade imobiliário
9. Plano de ação mensal com metas concretas e checkpoints trimestrais

Análise baseada em dados reais de extratos bancários, faturas de cartão e declaração de IR — fatos, não estimativas.

---

## REGRA DE OURO — COMPORTAMENTO DURANTE A ANÁLISE

Ao final de cada etapa concluída, antes de avançar para a próxima, obrigatoriamente:

- (a) Apresentar um resumo dos dados utilizados naquela etapa
- (b) Listar explicitamente quaisquer dados ausentes, ambíguos ou estimados
- (c) Fazer perguntas específicas de confirmação/esclarecimento ao usuário
- (d) Aguardar a resposta antes de continuar

**Somente avançar para a próxima etapa após confirmação explícita do usuário.**

---

## PIPELINE DE DADOS (E0 a E3)

O pipeline de dados é executado por qualquer ambiente (Cowork ou Chat). Ver `config/manual_operacao.md` para detalhes completos.

| Etapa | Objetivo | Input | Output |
|---|---|---|---|
| E0.A | Rotear e renomear arquivos do inbox | `inbox/*` | Arquivos em `data/`, `members/` |
| E1 | Mapeamento de membros | Currículos, holerites, docs pessoais | `members-1c_enriched.md` |
| E1.5 | Baseline patrimonial | IRPF + XLSX imóveis/veículos + informes QA | `baseline_patrimonial-1.5_consolidated.json` |
| E2 | Extração de extratos financeiros | PDFs de extratos, faturas, posições | `-2_extract.json` por arquivo |
| E3 | Reconciliação por conta | Todos os `-2_extract.json` | `-3_reconciled.json` por conta |

---

## PIPELINE DE ANÁLISE (E4 a E6) — 10 SEÇÕES DO RELATÓRIO

Cada seção do relatório abre com um `section-summary` (1 frase resumindo a conclusão principal).

### E4 — Enriquecimento e Unificação
- **Objetivo:** Categorizar transações, consolidar por tipo, enriquecer com contexto do baseline patrimonial.
- **Inputs:** Todos os `-3_reconciled.json` + `baseline_patrimonial-1.5_consolidated.json` + `dados_imoveis-2_extract.json` + `dados_veiculos-2_extract.json` (se houver) + `definitions.md`
- **Outputs:** `receitas-4_unified.json`, `despesas-4_unified.json`, `investimentos-4_unified.json`, `patrimonio-4_unified.json`, `seguros-4_unified.json`, `pontos_milhas-4_unified.json`
- **Nota v5.0:** `patrimonio-4_unified.json` substitui `imoveis` e `veiculos` unificados — consolida TODOS os ativos (imóveis, veículos, investimentos, criptos, contas, empresas) com dados de compra do XLSX e valores declarados do IRPF.

### E5 — Análise (gera JSON `analise_financeira-5_analysis.json` que alimenta as 10 seções do relatório)

**E5.1 — Saúde Financeira (→ seção 1 do relatório: Visão Geral Patrimonial)**
- **Objetivo:** Score Financeiro (0-10), patrimônio total incluindo todos os ativos do `patrimonio-4_unified.json`.
- **Inputs:** `patrimonio-4_unified.json`, `receitas-4_unified.json`, `despesas-4_unified.json`, `baseline_patrimonial-1.5_consolidated.json`
- **Outputs:** Bloco `saude_financeira` no E5 JSON — Score com 5 critérios, patrimônio bruto vs investível, reserva emergência.

**E5.2 — Fluxo de Caixa e Orçamento (→ seção 2 do relatório)**
- **Objetivo:** Receitas vs despesas, taxa de poupança, orçamento prospectivo com tetos, diagnóstico comportamental.
- **Inputs:** `receitas-4_unified.json`, `despesas-4_unified.json`, `definitions.md` (categorias e tetos), `investimentos-4_unified.json` (para cruzamento de liquidez)
- **Outputs:** Bloco `fluxo_de_caixa` no E5 JSON — Fluxo, projeção pós-quitação, 13 categorias vs tetos, consumo consciente, **diagnóstico comportamental** (`diagnostico_comportamental[]` no E5 JSON — array de padrões detectados com evidência e mudança sugerida; ver regras de detecção no manual_operacao.md E5 etapa 8).
- **Atenção:** NÃO confundir despesas PJ com pessoais. Incluir "reserva de desejos" R$3k/mês.
- **Diagnóstico comportamental:** OBRIGATÓRIO em todo ciclo. Mesmo sem padrões detectados, gerar bloco com array vazio e nota positiva. Tom não-julgamental — foco em automatização de fluxo.

**E5.3 — Independência Financeira (→ seção 7 do relatório)**
- **Objetivo:** Número da IF, gap, prazo em 3 cenários.
- **Inputs:** `patrimonio-4_unified.json`, `life_plan_goals.md`
- **Outputs:** Bloco `independencia_financeira` no E5 JSON — Projeção 3 cenários, renda passiva 2035 por 8 fontes com disclaimer, card TRS didático.
- **Terminologia:** Usar "Independência Financeira" (não "IF") nos títulos.

**E5.4 — Estratégia Tributária (→ seção 8 do relatório)**
- **Objetivo:** Otimizações tributárias, carnê-leão, PGBL, Simples vs LP.
- **Inputs:** `receitas-4_unified.json`, `baseline_patrimonial-1.5_consolidated.json` (dados de IRPF), `decisions.md`
- **Outputs:** Bloco `estrategia_tributaria` no E5 JSON — Simples vs LP, PGBL portabilidade, Carnê-Leão passo-a-passo, calendário tributário.

**E5.5 — Estratégia de Investimentos (→ seção 3 do relatório)**
- **Objetivo:** Performance por ativo, rentabilidade ponderada, benchmark, alocação.
- **Inputs:** `investimentos-4_unified.json`, `patrimonio-4_unified.json`
- **Outputs:** Bloco `estrategia_investimentos` no E5 JSON — Rentabilidade, benchmark acumulado, fundamentalista, contrafluxo, consolidação corretoras.

**E5.6 — Plano EUA (→ seções 4-6 do relatório: Imóveis + F1/F2 + Green Card)**
- **Objetivo:** Projetar custos e sobras para fases EUA, yield imóveis, proteção patrimonial.
- **Inputs:** `patrimonio-4_unified.json`, `life_plan_goals.md`, `decisions.md`
- **Outputs:** Bloco `plano_eua` no E5 JSON — Custos F1/F2, cenários cambiais, 5 riscos proteção, yield imóveis vs CDI, NCLEX roadmap.

**E5.7 — Riscos e Seguros (→ seção 9 do relatório)**
- **Objetivo:** Mapear 10 riscos, bubble chart, tabela seguros.
- **Inputs:** `seguros-4_unified.json`, `patrimonio-4_unified.json`, `members-1c_enriched.md`
- **Outputs:** Bloco `riscos_seguros` no E5 JSON — Bubble chart, top 3 riscos, prioridade vida + invalidez.

**E5.8 — Lista de Tarefas (→ seção 10 + apêndices do relatório)**
- **Objetivo:** Lista de tarefas priorizadas, timeline, pontos fortes e urgentes.
- **Inputs:** Blocos anteriores do E5 JSON, `decisions.md`
- **Outputs:** Bloco `lista_de_tarefas` no E5 JSON — Equilíbrio presente×futuro (Cerbasi), top 5 decisões, timeline.

### E5.N — Narrativas
- **Objetivo:** Gerar todos os textos analíticos e narrativos (perfil, summaries, contexts/conclusions de gráficos).
- **Inputs:** `analise_financeira-5_analysis.json` (dados completos do E5), `members-1c_enriched.md`, `life_plan_goals.md`
- **Outputs:** Chave `narrativas` adicionada ao E5 JSON com `perfil_familia`, `summaries`, `charts`.

### E6 — Relatório HTML (Determinístico)
- **Objetivo:** Compilar todas as análises em relatório HTML completo. 100% determinístico via script Python — sem LLM.
- **Comando:** `python scripts/e6_render.py`
- **Inputs:** `analise_financeira-5_analysis.json` (E5 JSON com dados + narrativas), `report_template.html`, `report_spec.md`
- **Outputs:** `output/relatorio_financeiro_ferreira_campos_[DATE].html` — 10 seções estratégicas + 5 apêndices + 19 gráficos Chart.js
- **Método:** Renderização por substituição de placeholders. Mesmos inputs = mesmo output.

---

## SCORE FINANCEIRO — 5 CRITÉRIOS (v5.2)

O score é uma média ponderada de 5 componentes, cada um pontuado de 0 a 10 com interpolação linear entre os extremos.

| Componente | Peso | Critério 10/10 | Critério 0/10 |
|---|---|---|---|
| Taxa de poupança **recorrente** | 2.0 | ≥ 50% | ≤ 0% (déficit). **USAR RECEITA RECORRENTE** (excluir one-time: rescisões, Kiwify, vendas). |
| Cobertura de despesas (meses) | 1.5 | ≥ 24 meses | ≤ 3 meses |
| Taxa de endividamento | 1.5 | ≤ 5% | ≥ 50% |
| Progresso Indep. Financeira (% da meta) | 2.0 | ≥ 80% | ≤ 5% |
| Diversificação (categorias ≥ 5% do patrimônio) | 1.0 | ≥ 5 categorias | ≤ 1 categoria |

**Fórmula:** `score = Σ(componente_i × peso_i) / Σ(peso_i)`, arredondado a 1 decimal.

**Classificação:** 0-2 = "Crítico", 2-4 = "Atenção", 4-6 = "Regular", 6-8 = "Bom", 8-10 = "Excelente".

Salvar componentes individuais em `score.componentes[]` para transparência. Ver `manual_operacao.md` (E5, item 5) para detalhes de implementação.

---

## PREMISSAS ECONÔMICAS

| Variável | Pessimista | Realista (base) | Otimista | Atual (mar/2026) |
|---|---|---|---|---|
| Inflação (IPCA) | 6,0% | 4,5% | 3,5% | ~5% |
| Retorno real carteira | 4,0% | 6,0% | 8,0% | ~6,0% |
| CDI / Selic | 11,0% | 12,0% | 13,5% | 13,75% |
| Câmbio BRL/USD | R$ 7,50 | R$ 5,88 | R$ 4,50 | R$ 5,88 |
| Valorização imóveis SP | 3% | 5% | 8% | — |
| TRS (Taxa de Retirada Segura) | 3,5% | 4,0% | 5,0% | — |

---

## DISCLAIMERS OBRIGATÓRIOS

Incluir nota de disclaimer nos seguintes contextos:

1. Tabela fundamentalista de ações — "Valores estimados — confirmar antes de agir"
2. DY de FIIs de referência — "DY passado não garante DY futuro"
3. Projeção renda passiva 2035 — "Premissas: IGPM 4%/ano, DY ações 5-8%, DY FIIs 9%, retorno real 6%. Revisar anualmente."
4. Taxa PGBL — "Confirmar taxa real de administração"
5. Benchmark de fundos — "Períodos variam por fundo — retorno acumulado desde aporte"

---

## CICLO DE ATUALIZAÇÃO

| Frequência | Escopo | Modo padrão |
|---|---|---|
| Quinzenal | Tático (D1-D6): deltas, despesas vs tetos, aportes, tarefas, alertas | ⚡ Tático |
| Trimestral | Análise completa (10 etapas) + dashboard | 📊 Estratégico |

---

## RESTRIÇÕES IMPORTANTES

- Nunca avançar sem checkpoint e confirmação explícita
- Se dado incompleto, perguntar — nunca assumir silenciosamente
- NÃO confundir despesas PJ com pessoais
- Todos os números = visão pós-quitação do financiamento
- Benchmark fundos = retorno acumulado desde aporte (NÃO "últimos 12 meses")
- Para questões tributárias EUA, sempre sinalize necessidade de CPA especializado
- Quando possível, fazer recomendações específicas de produtos financeiros
