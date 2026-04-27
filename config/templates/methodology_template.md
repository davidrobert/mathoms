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

## PIPELINE DE DADOS (E0 a E3)

Ver scripts em `scripts/` e configs em `config/` para detalhes completos.

| Etapa | Objetivo | Input | Output |
|---|---|---|---|
| E0.A | Rotear e renomear arquivos do inbox | inbox/* | Arquivos em data/, members/ |
| E1 | Mapeamento de membros | Currículos, holerites, docs pessoais | members-1c_enriched.md |
| E1.5 | Baseline patrimonial | IRPF + XLSX imóveis/veículos | baseline_patrimonial-1.5_consolidated.json |
| E2 | Extração de extratos financeiros | PDFs de extratos, faturas, posições | -2_extract.json por arquivo |
| E3 | Reconciliação por conta | Todos os -2_extract.json | -3_reconciled.json por conta |

---

## SCORE FINANCEIRO

Score em escala **0-10** com 1 decimal, fonte única em `config/scoring.json`.
Componentes (consultar `scoring.json:score_componentes` para ranges e pesos):

| Componente | Peso | Fonte metodológica |
|---|---|---|
| Taxa Poupança Recorrente | 2.0 | Cerbasi |
| Cobertura Despesas (meses) | 1.5 | Cerbasi + Perini |
| Taxa Endividamento | 1.5 | Cerbasi |
| Progresso Independência Financeira | 2.0 | Perini |
| Diversificação Patrimonial | 1.0 | AUVP |

Classificação: 0–2 Crítico · 2–4 Atenção · 4–6 Regular · 6–8 Bom · 8–10 Excelente.

> Não duplicar ranges/pesos aqui — `scoring.json` é canônico. Esta tabela
> é apenas índice de leitura.

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
