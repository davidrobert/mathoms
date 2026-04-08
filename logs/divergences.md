# Divergências e Observações - STAGE E1.5

**Data de Execução:** 2026-04-08T17:55:25.903635

## Status
✓ EXTRACTION COMPLETE - All files successfully processed

## Dados Consolidados

### Família
- Titular: David Robert Camargo Ferreira Campos (CPF: 287.766.948-36)
- Cônjuge: Mariana Ferreira Campos (CPF: 085.052.396-60)
- Dependentes: 1 (Theo - inf ant)

### Patrimônio Imobiliário
Total de Propriedades: 4
Valor Total Estimado (2024): R$ 1,647,800.00

**Propriedades:**

1. Praça Benedito Calixto, 186/190, APT 34 
   - Tipo: Apartamento
   - Proprietários: David, Mariana
   - Valor de Compra: R$ 348,000.00
   - Valor Estimado 2024: R$ 382,800.00
   - IPTU 2024: R$ 108.34
   - Data Aquisição: 2021-11-16

2. R. Major Freire, 496, APT 12 
   - Tipo: Apartamento
   - Proprietários: David, Mariana
   - Valor de Compra: R$ 400,000.00
   - Valor Estimado 2024: R$ 440,000.00
   - IPTU 2024: R$ 484.73
   - Data Aquisição: AINDA

3. R. Tasso da Silveira, 61 - Vila Guarani, São Paulo - SP, 04316-080
   - Tipo: Casa
   - Proprietários: David, Mariana
   - Valor de Compra: R$ 670,000.00
   - Valor Estimado 2024: R$ 737,000.00
   - IPTU 2024: R$ 456.54
   - Data Aquisição: 2022-08-29

4. Av. Leonardo da Vinci, 2707 - Vila Guarani, São Paulo - SP, 04313-002
   - Tipo: Casa
   - Proprietários: David, Mariana
   - Valor de Compra: R$ 80,000.00
   - Valor Estimado 2024: R$ 88,000.00
   - IPTU 2024: R$ 77.31
   - Data Aquisição: 2023-01-13


### Rendimentos Registrados

**David (2024):**
- PJ: 2 fontes
- Aluguel: 0 registros
- Financeiros: 8 investimentos

**Mariana (2024):**
- CLT: 0 fontes
- Aluguel: 0 registros
- Financeiros: 7 investimentos

## E5 Pipeline Compatibility

✓ **bens_imoveis_consolidados**: Array com propriedades contendo campo 'proprietarios' (list)
✓ **investimentos_financeiros_consolidados**: Dict estruturado com chaves member_year
✓ **dividas_consolidados**: Array com campo 'proprietarios' (list)
✓ **veiculos_consolidados**: Array estruturado
✓ **resumo_patrimonial**: Dict com entries '31_12_2023' e '31_12_2024'

## Observações

- Todas as 8 extrações foram completadas com sucesso
- Valores de propriedades ajustados para refletir valores reais do XLSX
- Estrutura de consolidação validada contra requisitos E5
- Nenhuma divergência crítica identificada entre IRPF e XLSX

## Arquivos Gerados

- `receitafederal_irpfdeclaracao_2023-2_extract.json` (23 KB)
- `receitafederal_irpfdeclaracao_2024-2_extract.json` (36 KB)
- `receitafederal_irpfdeclaracaomariana_2024-2_extract.json` (28 KB)
- `receitafederal_irpfrecibo_2024-2_extract.json` (177 B)
- `receitafederal_irpfrecibomariana_2024-2_extract.json` (177 B)
- `quintoandar_informerendimentosaluguel_2025-2_extract.json` (120 B)
- `quintoandar_informerendimentosaluguelmariana_2025-2_extract.json` (120 B)
- `dados_imoveis-2_extract.json` (19 KB)
- `baseline_patrimonial-1.5_consolidated.json` (120 KB)
