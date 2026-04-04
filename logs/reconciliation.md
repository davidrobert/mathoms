# Reconciliation Log — Pipeline Ferreira Campos

## E2.5 — Reconciliação por Conta — 2026-04-03

### Resumo Geral

| Métrica | Valor |
|---|---|
| Contas identificadas | 27 |
| Arquivos reconciliados gerados | 27 |
| Transações brutas (total) | 1.924 |
| Duplicatas removidas | 27 |
| Transações únicas (total) | 1.903 |

### Detalhamento por Conta

| Conta | Tipo | Arq | Brut | Dup | Uniq | Período |
|---|---|---|---|---|---|---|
| bankofamerica_conta_USD | Extrato CC | 1 | 0 | 0 | 0 | fev-mar/2026 |
| binance_conta_USD | Extrato exchange | 3 | 0 | 0 | 0 | mar/2026 (OCR) |
| bradesco_conta_BRL | Extrato CC | 2 | 0 | 0 | 0 | jan/2025-mar/2026 |
| bradesco_poupanca_BRL | Poupança | 7 | 27 | 0 | 27 | jan/2025-mar/2026 |
| btg_pactual_conta_BRL | Extrato CC | 1 | 0 | 0 | 0 | fev-mar/2026 |
| btg_pactual_investimentos | Posição inv. | 1 | 0 | 0 | 0 | mar/2026 |
| c6_bank_carbon_credit | Fatura cartão | 12 | 995 | 0 | 995 | mai/2025-abr/2026 |
| c6_bank_conta_BRL | Extrato CC | 1 | 0 | 0 | 0 | mar/2026 |
| c6_bank_global_EUR | Conta global | 2 | 56 | 3 | 53 | nov/2025-mar/2026 |
| c6_bank_global_USD | Conta global | 4 | 388 | 15 | 373 | mai/2025-mar/2026 |
| c6_bank_pj_BRL | Conta PJ | 1 | 53 | 0 | 53 | mar/2025-mar/2026 |
| c6_bank_rendafixa | Renda fixa | 1 | 0 | 0 | 1 | mar/2026 |
| itau_conta_BRL | Extrato CC | 2 | 114 | 1 | 113 | jul/2025-jan/2026 |
| itau_investimentos | Posição inv. | 1 | 0 | 0 | 2 | mar/2026 |
| itau_personnalite_BRL | Extrato CC | 1+2jpg | 235 | 1 | 234 | mai/2025-mar/2026 |
| itau_pao_acucar_credit | Fatura cartão | 11 | 22 | 7 | 15 | mai/2025-mar/2026 |
| picpay_conta_BRL | Extrato CC | 1 | 0 | 0 | 0 | dez/2025-mar/2026 |
| quintoandar_calixto_aluguel | Fatura aluguel | 1 | 0 | 0 | 0 | fev/2026 |
| quintoandar_major_freire_aluguel | Fatura aluguel | 1 | 0 | 0 | 0 | fev/2026 |
| rico_conta_BRL | Extrato CC | 1 | 0 | 0 | 0 | out/2025-mar/2026 |
| rico_investimentos | Posição inv. | 1 | 0 | 0 | 0 | mar/2026 |
| santander_cdb | CDB detalhes | 4 | 0 | 0 | 3 | mar/2026 |
| santander_conta_BRL | Extrato CC | 2 | 0 | 0 | 0 | nov/2025-mar/2026 |
| santander_unique_credit | Fatura cartão | 12 | 34 | 0 | 34 | mar/2025-fev/2026 |
| wise_conta_BRL | Extrato CC | 1 | 0 | 0 | 0 | jan/2025-mar/2026 |
| wise_conta_USD | Extrato CC | 1 | 0 | 0 | 0 | jan/2025-mar/2026 |

### Deduplicações Detectadas

| Conta | Duplicatas | Razão |
|---|---|---|
| c6_bank_global_USD | 15 | Períodos sobrepostos entre 4 extratos (dez/2025 aparece em 2 arquivos) |
| itau_pao_acucar_credit | 7 | Transações com datas/valores idênticos entre faturas consecutivas |
| c6_bank_global_EUR | 3 | Período sobreposição nov-dez/2025 |
| itau_conta_BRL | 1 | Transação duplicada entre jul/2025 e jan/2026 |
| itau_personnalite_BRL | 1 | Transação duplicada |

### Gaps Identificados

| Conta | Gap | Detalhes |
|---|---|---|
| bradesco_conta_BRL | Transações não extraídas | PDF com layout de tabela complexo — 0 transações extraídas apesar de períodos longos |
| santander_conta_BRL | Transações não extraídas | Mesmo problema de parsing de tabelas |
| picpay_conta_BRL | Transações não extraídas | PDF layout especial |
| wise_conta_BRL/USD | Transações não extraídas | Wise usa formato de relatório diferente |
| bankofamerica_conta_USD | Transações não extraídas | Apenas saldos disponíveis |

### Observações

- **Contas com mais transações:** C6 Carbon (995), C6 Global USD (373), Itaú Personnalité (234), Itaú CC (113)
- **Posições de investimento** são snapshots pontuais (mar/2026), não séries temporais
- **Alguns bancos** têm PDFs com layouts que dificultam extração automatizada de transações — dados de saldos e resumos foram extraídos mesmo quando transações individuais não puderam ser parseadas
