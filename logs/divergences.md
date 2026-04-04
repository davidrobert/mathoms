# Divergências Detectadas — Pipeline Ferreira Campos

## E1.5 — Baseline Patrimonial — 2026-04-03

### 1. Arquivo IRPF 2023 nomeado incorretamente

| Campo | Valor |
|---|---|
| Arquivo | `receitafederal_irpfdeclaracao_2023-0_original.pdf` |
| Esperado | Declaração David (sem "mariana" no nome) |
| Encontrado | Declaração **Mariana** Teixeira Ferreira (CPF 085.052.396-60) |
| Impacto | Baixo — dados extraídos corretamente, mas nome do arquivo é enganoso |
| Ação sugerida | Renomear para `receitafederal_irpfdeclaracaomariana_2023-0_original.pdf` |

### 2. Imóveis Mariana ausentes no XLSX

| Campo | Valor |
|---|---|
| Imóveis | Cond. Living Concept (R$ 270k) + Cond. Living Wish (R$ 530k) |
| Fonte | IRPF Mariana 2024 |
| Ausente em | `dados_imoveis-0_original.xlsx` (contém apenas 4 imóveis de David) |
| Impacto | XLSX está incompleto — não representa a totalidade dos imóveis familiares |
| Ação sugerida | Adicionar os 2 imóveis de Mariana ao XLSX |

### 3. Apartamento Barão de Capanema — Diferença de valor

| Campo | Valor |
|---|---|
| IRPF David | R$ 350.000,00 |
| XLSX | R$ 348.000,00 |
| Diferença | R$ 2.000,00 (0,57%) |
| Provável causa | ITBI/escritura incluídos no valor declarado ao IRPF |
| Impacto | Baixo |
| Ação sugerida | Aceitar valor IRPF como referência fiscal |

### 4. Casa Tasso da Silveira — Diferença significativa de valor

| Campo | Valor |
|---|---|
| IRPF David | R$ 996.821,46 |
| XLSX | R$ 670.000,00 |
| Diferença | R$ 326.821,46 (48,8%) |
| Provável causa | IRPF acumula todos os custos (compra + financiamento Caixa + juros + escritura), XLSX tem apenas preço de compra |
| Impacto | Médio — para patrimônio, usar IRPF; para ROI de imóvel, usar valor de aquisição |
| Ação sugerida | Manter ambos; IRPF = valor fiscal, XLSX = valor de aquisição |

### 5. Rua Major Freire — Cruzamento incompleto

| Campo | Valor |
|---|---|
| XLSX | R$ 400.000,00 — listado como imóvel da família |
| IRPF David | Não aparece como bem explícito (pode estar incluído no financiamento Itaú) |
| QuintoAndar David | Renda de aluguel R$ 36.335,43/ano proveniente deste endereço |
| Impacto | Médio — imóvel existe e gera renda, mas declaração no IRPF não é clara |
| Ação sugerida | Verificar se está declarado sob outro código no IRPF David ou na IRPF Mariana |

### 6. XLSX marca todos os imóveis como "próprio" mas há aluguéis ativos

| Campo | Valor |
|---|---|
| XLSX | 4 imóveis, todos com `situacao_atual: proprio` |
| QuintoAndar | Pelo menos 2 propriedades gerando renda de aluguel (David R$36k + Mariana R$74k/ano) |
| Impacto | Médio — XLSX desatualizado em relação ao uso real dos imóveis |
| Ação sugerida | Atualizar campo `situacao_atual` no XLSX para refletir imóveis alugados |

---

## Resumo de Divergências

| # | Severidade | Tipo | Resolução |
|---|---|---|---|
| 1 | Baixa | Nomenclatura arquivo | Renomear |
| 2 | Alta | Dados incompletos | Adicionar imóveis Mariana ao XLSX |
| 3 | Baixa | Valor divergente | Aceitar IRPF |
| 4 | Média | Valor divergente | Manter ambos com contexto |
| 5 | Média | Cruzamento incompleto | Verificar IRPF |
| 6 | Média | XLSX desatualizado | Atualizar status imóveis |
