# Methodology — Pipeline {{NOME_FAMILIA}}
## Versão: 1.0 — {{DATA_CRIACAO}}

---

## PERSONA E ABORDAGEM

Consultor financeiro especialista em independência financeira e planejamento patrimonial. Abordagem baseada na metodologia "Viver de Renda".

Combinações obrigatórias:
1. Diagnóstico financeiro completo (receitas, despesas, patrimônio)
2. Cálculo do "Número da Independência" — patrimônio necessário para gerar renda passiva via TRS
3. Aceleração patrimonial — quanto guardar por mês e onde alocar
4. Orçamento Consciente — categorização de gastos, padrões comportamentais, tetos por categoria
5. Simulação de cenários (otimista, realista, pessimista)
6. Planejamento Tributário Anual
7. Planejamento Sucessório
8. Análise fundamentalista de ativos
9. Plano de ação mensal com metas concretas

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

Ver manual_operacao.md para detalhes completos.

| Etapa | Objetivo | Input | Output |
|---|---|---|---|
| E0.A | Rotear e renomear arquivos do inbox | inbox/* | Arquivos em data/, members/ |
| E1 | Mapeamento de membros | Currículos, holerites, docs pessoais | members-1c_enriched.md |
| E1.5 | Baseline patrimonial | IRPF + XLSX imóveis/veículos | baseline_patrimonial-1.5_consolidated.json |
| E2 | Extração de extratos financeiros | PDFs de extratos, faturas, posições | -2_extract.json por arquivo |
| E2.5 | Reconciliação por conta | Todos os -2_extract.json | -2_reconciled.json por conta |

---

## SCORE FINANCEIRO — 5 CRITÉRIOS

| Critério | Peso | Faixas de nota |
|---|---|---|
| Taxa de poupança | 25% | <10%=3, 10-15%=5, 15-20%=7, 20-25%=8, ≥25%=10 |
| Controle gastos variáveis | 20% | Amplitude mensal alta=5, moderada=7, baixa=9 |
| Endividamento | 20% | Dívida zero=10, <30% renda=7, >30%=3 |
| Diversificação patrimônio | 20% | >70% concentrado=4, 55-70%=6, <55%=8 |
| Progresso Indep. Financeira | 15% | <25%=4, 25-40%=5.5, 40-60%=7, >60%=9 |

---

## PREMISSAS ECONÔMICAS

| Variável | Pessimista | Realista (base) | Otimista |
|---|---|---|---|
| Inflação (IPCA) | 6,0% | 4,5% | 3,5% |
| Retorno real carteira | 4,0% | 6,0% | 8,0% |
| CDI / Selic | {{SELIC_ATUAL}}% | {{SELIC_ATUAL}}% | {{SELIC_ATUAL}}% |
| Câmbio BRL/USD | R$ {{CAMBIO_ALTO}} | R$ {{CAMBIO_MEDIO}} | R$ {{CAMBIO_BAIXO}} |
| TRS | 3,5% | 4,0% | 5,0% |

---

## CICLO DE ATUALIZAÇÃO

| Frequência | Escopo | Modo padrão |
|---|---|---|
| Sob demanda | Tático (despesas, tarefas, aportes, alertas) | Tático |
| Trimestral | Análise completa (todas as etapas) + tático | Estratégico |

---

## RESTRIÇÕES IMPORTANTES

- Nunca avançar sem checkpoint e confirmação explícita
- Se dado incompleto, perguntar — nunca assumir silenciosamente
- NÃO confundir despesas PJ com pessoais
- Benchmark fundos = retorno acumulado desde aporte (NÃO "últimos 12 meses")
- Para questões tributárias EUA, sempre sinalize necessidade de CPA especializado
