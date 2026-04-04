# Methodology — Pipeline Ferreira Campos
## Versão: 5.0 — abr/2026

---

## PERSONA E ABORDAGEM

Consultor financeiro especialista em independência financeira e planejamento patrimonial para famílias brasileiras de alta renda com contexto internacional. Abordagem baseada na metodologia "Viver de Renda", enriquecida com:

- **Gustavo Cerbasi** — comportamento financeiro, equilíbrio presente × futuro
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

## PIPELINE DE DADOS (E0 a E2.5)

O pipeline de dados é executado por qualquer ambiente (Cowork ou Chat). Ver `config/manual_operacao.md` para detalhes completos.

| Etapa | Objetivo | Input | Output |
|---|---|---|---|
| E0.A | Rotear e renomear arquivos do inbox | `inbox/*` | Arquivos em `data/`, `members/` |
| E1 | Mapeamento de membros | Currículos, holerites, docs pessoais | `members-1c_enriched.md` |
| E1.5 | Baseline patrimonial | IRPF + XLSX imóveis/veículos + informes QA | `baseline_patrimonial-1.5_consolidated.json` |
| E2 | Extração de extratos financeiros | PDFs de extratos, faturas, posições | `-2_extract.json` por arquivo |
| E2.5 | Reconciliação por conta | Todos os `-2_extract.json` | `-2_reconciled.json` por conta |

---

## PIPELINE DE ANÁLISE (E3 a E5) — 10 SEÇÕES DO RELATÓRIO

Cada seção do relatório abre com um `section-summary` (1 frase resumindo a conclusão principal).

### E3 — Enriquecimento e Unificação
- **Objetivo:** Categorizar transações, consolidar por tipo, enriquecer com contexto do baseline patrimonial.
- **Inputs:** Todos os `-2_reconciled.json` + `baseline_patrimonial-1.5_consolidated.json` + `dados_imoveis-2_extract.json` + `dados_veiculos-2_extract.json` (se houver) + `definitions.md`
- **Outputs:** `receitas-3_unified.json`, `despesas-3_unified.json`, `investimentos-3_unified.json`, `patrimonio-3_unified.json`, `seguros-3_unified.json`, `pontos_milhas-3_unified.json`
- **Nota v5.0:** `patrimonio-3_unified.json` substitui `imoveis-3_unified.json` e `veiculos-3_unified.json` — consolida TODOS os ativos (imóveis, veículos, investimentos, criptos, contas, empresas) com dados de compra do XLSX e valores declarados do IRPF.

### E4 — Análise (gera 8 arquivos -4.md que alimentam as 10 seções do relatório)

**E4.1 — Saúde Financeira (→ seção 1 do relatório: Visão Geral Patrimonial)**
- **Objetivo:** Score Financeiro (0-10), patrimônio total incluindo todos os ativos do `patrimonio-3_unified.json`.
- **Inputs:** `patrimonio-3_unified.json`, `receitas-3_unified.json`, `despesas-3_unified.json`, `baseline_patrimonial-1.5_consolidated.json`
- **Outputs:** `saude_financeira-4.md` — Score com 5 critérios, patrimônio bruto vs investível, reserva emergência.

**E4.2 — Fluxo de Caixa e Orçamento (→ seção 2 do relatório)**
- **Objetivo:** Receitas vs despesas, taxa de poupança, orçamento prospectivo com tetos, diagnóstico comportamental.
- **Inputs:** `receitas-3_unified.json`, `despesas-3_unified.json`, `definitions.md` (categorias e tetos), `investimentos-3_unified.json` (para cruzamento de liquidez)
- **Outputs:** `fluxo_de_caixa-4.md` — Fluxo, projeção pós-quitação, 13 categorias vs tetos, consumo consciente, **diagnóstico comportamental** (`diagnostico_comportamental[]` no E4 JSON — array de padrões detectados com evidência e mudança sugerida; ver regras de detecção no manual_operacao.md E4 etapa 8).
- **Atenção:** NÃO confundir despesas PJ com pessoais. Incluir "reserva de desejos" R$3k/mês.
- **Diagnóstico comportamental:** OBRIGATÓRIO em todo ciclo. Mesmo sem padrões detectados, gerar bloco com array vazio e nota positiva. Tom não-julgamental — foco em automatização de fluxo.

**E4.3 — Independência Financeira (→ seção 7 do relatório)**
- **Objetivo:** Número da IF, gap, prazo em 3 cenários.
- **Inputs:** `patrimonio-3_unified.json`, `life_plan_goals.md`
- **Outputs:** `independencia_financeira-4.md` — Projeção 3 cenários, renda passiva 2035 por 8 fontes com disclaimer, card TRS didático.
- **Terminologia:** Usar "Independência Financeira" (não "IF") nos títulos.

**E4.4 — Estratégia Tributária (→ seção 8 do relatório)**
- **Objetivo:** Otimizações tributárias, carnê-leão, PGBL, Simples vs LP.
- **Inputs:** `receitas-3_unified.json`, `baseline_patrimonial-1.5_consolidated.json` (dados de IRPF), `decisions.md`
- **Outputs:** `estrategia_tributaria-4.md` — Simples vs LP, PGBL portabilidade, Carnê-Leão passo-a-passo, calendário tributário.

**E4.5 — Estratégia de Investimentos (→ seção 3 do relatório)**
- **Objetivo:** Performance por ativo, rentabilidade ponderada, benchmark, alocação.
- **Inputs:** `investimentos-3_unified.json`, `patrimonio-3_unified.json`
- **Outputs:** `estrategia_investimentos-4.md` — Rentabilidade, benchmark acumulado, fundamentalista, contrafluxo, consolidação corretoras.

**E4.6 — Plano EUA (→ seções 4-6 do relatório: Imóveis + F1/F2 + Green Card)**
- **Objetivo:** Projetar custos e sobras para fases EUA, yield imóveis, proteção patrimonial.
- **Inputs:** `patrimonio-3_unified.json`, `life_plan_goals.md`, `decisions.md`
- **Outputs:** `plano_eua-4.md` — Custos F1/F2, cenários cambiais, 5 riscos proteção, yield imóveis vs CDI, NCLEX roadmap.

**E4.7 — Riscos e Seguros (→ seção 9 do relatório)**
- **Objetivo:** Mapear 10 riscos, bubble chart, tabela seguros.
- **Inputs:** `seguros-3_unified.json`, `patrimonio-3_unified.json`, `members-1c_enriched.md`
- **Outputs:** `riscos_seguros-4.md` — Bubble chart, top 3 riscos, prioridade vida + invalidez.

**E4.8 — Lista de Tarefas (→ seção 10 + apêndices do relatório)**
- **Objetivo:** Lista de tarefas priorizadas, timeline, pontos fortes e urgentes.
- **Inputs:** Todos os -4.md anteriores, `decisions.md`
- **Outputs:** `lista_de_tarefas-4.md` — Equilíbrio presente×futuro (Cerbasi), top 5 decisões, timeline.

### E5 — Relatório HTML
- **Objetivo:** Compilar todas as análises em relatório HTML completo conforme `report_spec.md`.
- **Inputs:** Todos os `-4.md`, `report_spec.md`, `members-1c_enriched.md`, `life_plan_goals.md`
- **Outputs:** `output/relatorio_[YYYYMM].html` — 10 seções estratégicas + 5 apêndices + 6 seções dashboard + 18 gráficos Chart.js
- **Método:** Gerar em 8 blocos sequenciais conforme definido no `report_spec.md`.

---

## SCORE FINANCEIRO — 5 CRITÉRIOS

| Critério | Peso | Faixas de nota |
|---|---|---|
| Taxa de poupança **recorrente** | 25% | <10%=3, 10-15%=5, 15-20%=7, 20-25%=8, ≥25%=10. **USAR RECEITA RECORRENTE** (excluir one-time: rescisões, Kiwify, vendas). Ver nota abaixo. |
| Controle gastos variáveis | 20% | Amplitude mensal alta=5, moderada=7, baixa=9 |
| Endividamento | 20% | Dívida zero=10, <30% renda=7, >30%=3 |
| Diversificação patrimônio | 20% | >70% concentrado=4, 55-70%=6, <55%=8 |
| Progresso Indep. Financeira | 15% | <25%=4, 25-40%=5.5, 40-60%=7, >60%=9 |

Score = média ponderada.

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
