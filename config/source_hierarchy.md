# Source Hierarchy — Pipeline Ferreira Campos
## Versão: 5.3 — abr/2026

---

## PRINCÍPIO FUNDAMENTAL

Os dados pré-preenchidos são baseados em extratos bancários, faturas e declarações de IR efetivamente processados nas análises de mar/2026 e na sessão de revisão. Ainda assim, **novos extratos fornecidos são sempre a fonte primária de verdade** e têm precedência sobre qualquer informação do prompt.

---

## HIERARQUIA DE PRECEDÊNCIA

| Nível | Fonte | Exemplo | Quando usar |
|---|---|---|---|
| **1 — Primária** | Documento original (.pdf leitura direta, .jpg OCR, .xlsx planilha, .docx) | PDF de `c6bank_extratoconta_202603` | Sempre que disponível |
| **2 — Secundária** | Dados consolidados no manual_operacao.md v3.0 (este prompt) | Tabela de receita mês a mês | Quando extrato original não está disponível para o período |
| **3 — Terciária** | Relatório HTML anterior (v4.2, v4.3) | KPIs, gráficos, tabelas do HTML | Para manter consistência visual; dados devem ser revalidados |
| **4 — Estimativa** | Projeção ou cálculo derivado | Renda projetada abr/26+ = R$78.611/mês | Sinalizar explicitamente como estimativa |

---

## REGRAS PRÁTICAS

### R1 — Extrato vence prompt
Se um extrato mostrar um valor diferente do descrito no prompt, **usar o valor do extrato** e registrar a divergência:

```
⚠️ DIVERGÊNCIA: o prompt indica X, os extratos mostram Y
```

### R2 — Prompt como contexto
Usar as informações do prompt como contexto e ponto de partida — **nunca como dado final**.

### R3 — Sinalizar estimativas
Quando um dado não puder ser confirmado pelos extratos, sinalizar explicitamente:

```
⚠️ ESTIMATIVA: valor baseado em [fonte/método], não confirmado por extrato
```

### R4 — Divergências relevantes
Ao identificar divergências relevantes (>5% ou que afetam decisões), destacar com o padrão:

```
⚠️ DIVERGÊNCIA: o prompt indica X, os extratos mostram Y
   Impacto: [descrever efeito em cascata: receita, sobra, taxa poupança, prazo IF]
```

### R5 — Disclaimers obrigatórios
Os seguintes dados devem sempre carregar disclaimer:

| Contexto | Disclaimer |
|---|---|
| Indicadores fundamentalistas (P/L, DY ações) | "⚠️ Valores estimados — confirmar antes de agir" |
| DY de FIIs de referência | "⚠️ DY passado não garante DY futuro" |
| Projeção renda passiva 2035 | "⚠️ Premissas: IGPM 4%/ano, DY ações 5-8%, DY FIIs 9%, retorno real 6%. Revisar anualmente." |
| Taxa PGBL | "⚠️ Confirmar taxa real de administração" |
| Benchmark de fundos | "⚠️ Períodos variam por fundo — retorno acumulado desde aporte" |

---

## ERROS HISTÓRICOS CORRIGIDOS

Estas correções foram feitas entre v3.0 e v4.3 e devem ser mantidas. Se um extrato futuro contradizer, investigar antes de reverter.

| Erro | Versão corrigida | Detalhe |
|---|---|---|
| GRPQA Ltda. = salário Einstein | v4.2 | GRPQA = QuintoAndar (aluguéis Mariana). Salário Einstein vai para poupança Bradesco ("Sociedade Beneficente Israelita"). |
| Dupla contagem salário/aluguéis Mariana | v4.2 | "Salário" R$53.808 era na verdade GRPQA (aluguéis) já contados. Eliminada. |
| Salário Mariana R$6.720/mês | v4.2 | Corrigido para R$8.000/mês (poupança Bradesco). |
| ITSA4 = 778 ações | v4.0→v4.3 | Corrigido para 763 ações (693 compradas + 70 bonificação, PM R$7,63). |
| Patrimônio investível R$3.407.041 | v4.0 | Corrigido para R$3.648.716 (pós-quitação). |
| Score Financeiro 6,4/10 | v4.2 | Corrigido para 6,8/10 (receita recorrente maior). |
| Taxa de poupança 11,9% | v4.2 | Corrigido para 18,8% (salário Mariana real adicionado). |
| POMPEIA MOTOS = receita PJ | v5.1 | Corrigido para `receita_venda_ativo` (venda Yamaha MT09, desinvestimento de ativo). |

---

## FONTES POR TIPO DE DADO

### Receitas

| Fonte de receita | Documento primário | Conta | Identificador no extrato |
|---|---|---|---|
| PJ David (Arvo, BrandLovers, etc.) | Extrato C6 PJ | C6 PJ 384366937 | Nome do pagador (TED/PIX) |
| Kiwify (rescisão, encerrado) | Extrato Itaú Personnalité | Itaú 9652/04397-8 | — |
| Aluguéis David | Extrato Itaú Personnalité + Informe QuintoAndar | Itaú 9652/04397-8 | "SISPAG GRPQA" |
| Salário Mariana (Einstein CLT) | Extrato **poupança** Bradesco | Bradesco 3221/77113-9 (poupança) | "Sociedade Beneficente Israelita" |
| Aluguéis Mariana | Extrato **CC** Bradesco + Informe QuintoAndar | Bradesco 3221/77113-9 (CC) | "GRPQA Ltda." |
| Investimentos Mariana | Extrato BTG Pactual | BTG 0001/002713513 | — |
| Rendimentos financeiros | Extratos diversos (Itaú, Santander, Rico, PicPay) | Vários | — |

### Despesas

| Fonte de despesa | Documento primário | Identificação |
|---|---|---|
| Cartão C6 Carbon | Fatura C6 Carbon mensal | Descrição do estabelecimento |
| Cartão Santander Unique | Fatura Santander Unique mensal | Descrição do estabelecimento |
| Cartão Itaú Pão de Açúcar | Fatura Itaú Pão de Açúcar mensal | Descrição do estabelecimento |
| Débitos C6 PF | Extrato C6 PF | PIX, TED, débito automático |
| Débitos Bradesco (Mariana) | Extrato CC Bradesco | PIX, condomínios, diarista |
| DAS/Impostos PJ | Extrato C6 PJ (deveria) | Campo "DAS" ou "Simples" |
| IRPF Mariana | Extrato CC Bradesco | "Débito RFB CPF 085.052.396-60" |

### Patrimônio

| Ativo | Documento primário | Frequência |
|---|---|---|
| Investimentos Itaú | Posição investimentos Itaú | Trimestral |
| CDBs Santander | Detalhe CDB + Resumo CDB Santander | Trimestral |
| Fundos/ações Rico | Screenshot "Meus Investimentos" Rico | Trimestral |
| Investimentos BTG (Mariana) | Posição investimentos BTG | Trimestral |
| PicPay | Extrato PicPay | Trimestral |
| Crypto Binance | Screenshot posição Binance | Trimestral |
| Imóveis (dados cadastrais) | `dados_imoveis-0_original.xlsx` | Anual |
| Imóveis (valor declarado IRPF) | Declarações IRPF David + Mariana | Anual |
| Imóveis (valor mercado) | Avaliação corretora ou estimativa | Anual |
| Veículos | `dados_veiculos-0_original.xlsx` (quando presente) | Anual |
| Todos os bens (baseline) | `baseline_patrimonial-1.5_consolidated.json` | Trimestral |

---

## CHECKLIST PRÉ-ATUALIZAÇÃO

Documentos a coletar antes de cada ciclo trimestral:

```
□ C6 PJ — extrato 3 meses
□ C6 PF — extrato 3 meses
□ C6 Carbon — faturas 3 meses
□ Itaú Personnalité — extrato + posição investimentos
□ Itaú Pão de Açúcar — faturas 3 meses
□ Santander — extrato + faturas Unique + posição CDBs
□ BTG Pactual — extrato + posição investimentos (Mariana)
□ Bradesco — extrato CC + poupança (Mariana)
□ Rico/XP — posição investimentos
□ PicPay — extrato
□ Wise — extrato BRL + USD
□ Bank of America — extrato
□ C6 Global — extrato USD + EUR
□ QuintoAndar — informes de rendimento (David + Mariana)
□ Binance — screenshot posição
□ IRPF — declaração + recibo (se período de declaração)
□ Holerite Mariana (Einstein) — se disponível
□ Dados imóveis — XLSX atualizado (se mudanças)
□ Dados veículos — XLSX (se aplicável)
□ Documentos pessoais — RG, CPF, passaporte, visto (se novos/renovados)
□ Tarefas concluídas — lista do que foi feito desde última atualização
```
