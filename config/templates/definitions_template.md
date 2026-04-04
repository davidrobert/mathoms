# Definitions — Pipeline {{NOME_FAMILIA}}
## Versão: 1.0 — {{DATA_CRIACAO}}

---

## MEMBROS DA FAMÍLIA

| Membro | Nome completo | CPF | Nascimento | Papel |
|---|---|---|---|---|
{{#MEMBROS}}
| {{APELIDO}} | {{NOME_COMPLETO}} | {{CPF}} | {{DATA_NASCIMENTO}} | {{PAPEL}} |
{{/MEMBROS}}

---

## EMPRESA PJ (se aplicável)

| Campo | Valor |
|---|---|
| Razão social | {{RAZAO_SOCIAL}} |
| CNPJ | {{CNPJ}} |
| Regime tributário | {{REGIME_TRIBUTARIO}} |
| Conta bancária PJ | {{CONTA_PJ}} |
| Contador | {{CONTADOR}} |

---

## MAPA DE ENTIDADES (INSTITUIÇÕES)

<!-- Preencher com as instituições financeiras da família -->
| Entidade | Código | Tipo |
|---|---|---|
{{#ENTIDADES}}
| {{NOME_ENTIDADE}} | {{CODIGO}} | {{TIPO_ENTIDADE}} |
{{/ENTIDADES}}

---

## MAPA DE TIPOS DE DOCUMENTO

<!-- Tipos padrão do pipeline — não modificar -->
| Tipo | Código | Extensão típica |
|---|---|---|
| Extrato conta corrente PF | extratoconta | .pdf |
| Extrato conta PJ | extratocontapj | .pdf |
| Extrato conta global USD | extratocontaglobalusd | .pdf |
| Extrato conta global EUR | extratocontaglobaleur | .pdf |
| Extrato poupança | extratopoupanca | .pdf |
| Fatura cartão de crédito | faturacc | .pdf |
| Posição de investimentos | investimentosposicao | .pdf |
| Carteira renda fixa | carteirarendafixa | .pdf |
| Detalhe CDB | cdbdetalhes | .pdf |
| Resumo CDB | cdbresumo | .pdf |
| Fatura aluguel | faturaaluguel | .pdf |
| Informe rendimentos | informerendimentos | .pdf |
| Declaração IRPF | irpfdeclaracao | .pdf |
| Recibo IRPF | irpfrecibo | .pdf |
| Currículo / CV | curriculo | .pdf ou .docx |
| Holerite / Contracheque | holerite | .pdf |
| Dados de imóveis | dados_imoveis | .xlsx |
| Dados de veículos | dados_veiculos | .xlsx |

---

## MAPA DE DESTINOS

| Tipo de documento | Diretório |
|---|---|
| Extratos, faturas, posições, CDBs, faturas de aluguel | data/financial_statements/ |
| IRPF, informes de rendimento | data/income_tax_br/ |
| Planilhas de imóveis | data/real_estate/ |
| Planilhas de veículos | data/vehicles/ |
| Currículos, holerites, documentos pessoais | members/ |
| Documentos fiscais EUA | data/income_tax_us/ |

---

## PADRÃO DE NOMENCLATURA

```
[entidade]_[tipo]_[periodo]-0_original.[ext]
```

---

## CONTAS BANCÁRIAS

<!-- Preencher com as contas de cada membro -->
{{#MEMBROS}}
### {{APELIDO}}
| Instituição | Agência | Conta | Tipo | Uso principal |
|---|---|---|---|---|
{{#CONTAS}}
| {{INSTITUICAO}} | {{AGENCIA}} | {{NUMERO_CONTA}} | {{TIPO_CONTA}} | {{USO}} |
{{/CONTAS}}
{{/MEMBROS}}

---

## CATEGORIAS DE DESPESA (ORÇAMENTO PROSPECTIVO)

| Código | Categoria | Teto mensal | % Renda |
|---|---|---|---|
| moradia | Moradia | R$ {{TETO_MORADIA}} | {{PCT_MORADIA}}% |
| alimentacao | Alimentação | R$ {{TETO_ALIMENTACAO}} | {{PCT_ALIMENTACAO}}% |
| saude | Saúde | R$ {{TETO_SAUDE}} | {{PCT_SAUDE}}% |
| servicos_domesticos | Serviços domésticos | R$ {{TETO_SERVICOS}} | {{PCT_SERVICOS}}% |
| educacao | Educação | R$ {{TETO_EDUCACAO}} | {{PCT_EDUCACAO}}% |
| transporte | Transporte | R$ {{TETO_TRANSPORTE}} | {{PCT_TRANSPORTE}}% |
| lazer_viagens | Lazer e viagens | R$ {{TETO_LAZER}} | {{PCT_LAZER}}% |
| vestuario | Vestuário e compras | R$ {{TETO_VESTUARIO}} | {{PCT_VESTUARIO}}% |
| assinaturas | Assinaturas | R$ {{TETO_ASSINATURAS}} | {{PCT_ASSINATURAS}}% |
| suporte_familiar | Suporte familiar | R$ {{TETO_SUPORTE}} | {{PCT_SUPORTE}}% |
| financeiro | Financeiro pessoal | R$ {{TETO_FINANCEIRO}} | {{PCT_FINANCEIRO}}% |
| melhoria_reforma | Melhoria/Reforma moradia | R$ {{TETO_MELHORIA}} | {{PCT_MELHORIA}}% |
| reserva_desejos | Reserva de desejos | R$ {{TETO_RESERVA}} | {{PCT_RESERVA}}% |
| seguros | Seguros (vida, invalidez, residencial, auto) | R$ {{TETO_SEGUROS}} | {{PCT_SEGUROS}}% |

---

## PROCESSAMENTO DE ARQUIVOS — REGRA TÉCNICA

Todos os arquivos .pdf deste projeto são PDFs reais (não ZIPs disfarçados). A extração de dados deve usar leitura direta de PDF.
