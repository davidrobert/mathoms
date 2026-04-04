# Definitions — Pipeline Ferreira Campos
## Versão: 5.2 — abr/2026

---

## MEMBROS DA FAMÍLIA

| Membro  | Nome completo                                                     | CPF            | Nascimento | Papel                        |
| ------- | ----------------------------------------------------------------- | -------------- | ---------- | ---------------------------- |
| David   | David Robert Camargo Ferreira Campos                              | 287.766.948-36 | 05/09/1981 | Titular, CTO PJ              |
| Mariana | Mariana Teixeira Ferreira (nome fiscal) / Mariana Ferreira Campos | 085.052.396-60 | 30/08/1986 | Cônjuge, enfermeira CLT      |
| Theo    | Theo Ferreira Campos                                              | —              | 18/07/2025 | Filho, dupla cidadania BR/US |

---
## ANIMAIS DE ESTIMAÇÃO

| Raça | Nome  | Sexo  |
| ---- | ----- | ----- |
| Gato | Zack  | Macho |
| Gato | Fuzzy | Macho |
| Gato | Nix   | Femea |

---

## STATUS GOV.BR

| Membro | Nível Gov.br | Status |
|---|---|---|
| David | Prata ou Ouro | ✅ Ativo |
| Mariana | Prata ou Ouro | ✅ Ativo |

---

## EMPRESA PJ

| Campo | Valor |
|---|---|
| Razão social | DAVID ROBERT CAMARGO DE CAMPOS LTDA |
| CNPJ | 48.771.488/0001-87 |
| Regime tributário | Simples Nacional (Anexo V — serviços de TI/consultoria) |
| Conta bancária PJ | C6 Bank — Ag. 1, Conta 384366937 |
| Contador | AccountTech (R$390/mês, campo "VINDI *ACCOUNTBANKTEC" na fatura C6 Carbon) |

---

## MAPA DE ENTIDADES (INSTITUIÇÕES)

| Entidade no nome/conteúdo | Código de entidade | Tipo |
|---|---|---|
| C6 Bank, Carbon | `c6bank` | Banco + cartão |
| Itaú, Personnalité | `itau` | Banco (conta PF Personnalité David). Nota: código unificado como `itau` — arquivos no disco usam prefixo `itau_`. O código antigo `itaupersonnalite` é aceito como alias. |
| Santander | `santander` | Banco + cartão |
| Bradesco | `bradesco` | Banco (Mariana) |
| BTG Pactual | `btgpactual` | Corretora (Mariana) |
| Rico, XP Investimentos | `rico` | Corretora (David) |
| PicPay | `picpay` | Conta digital |
| Wise, TransferWise | `wise` | Conta internacional |
| Bank of America | `bankofamerica` | Banco (EUA) |
| QuintoAndar, GRPQA | `quintoandar` | Gestora de aluguéis |
| Binance | `binance` | Exchange crypto |
| Receita Federal, RFB | `receitafederal` | Órgão fiscal |

---

## MAPA DE TIPOS DE DOCUMENTO

| Tipo | Código | Extensão típica |
|---|---|---|
| Extrato conta corrente PF | `extratoconta` | .pdf |
| Extrato conta PJ | `extratocontapj` | .pdf |
| Extrato conta global USD | `extratocontaglobalusd` | .pdf |
| Extrato conta global EUR | `extratocontaglobaleur` | .pdf |
| Extrato poupança | `extratopoupanca` | .pdf |
| Fatura C6 Carbon | `faturacarbon` | .pdf |
| Fatura Santander Unique | `faturaunique` | .pdf |
| Fatura Itaú Pão de Açúcar | `faturapaoacucar` | .pdf |
| Posição de investimentos | `investimentosposicao` | .pdf |
| Carteira renda fixa | `carteirarendafixa` | .pdf |
| Detalhe CDB | `cdbdetalhes` | .pdf |
| Resumo CDB | `cdbresumo` | .pdf |
| Fatura aluguel QuintoAndar | `faturaaluguel` | .pdf |
| Informe rendimentos | `informerendimentos` | .pdf |
| Declaração IRPF | `irpfdeclaracao` | .pdf |
| Recibo IRPF | `irpfrecibo` | .pdf |
| Currículo / CV | `curriculo` | .pdf ou .docx |
| Holerite / Contracheque | `holerite` | .pdf |
| Dados de imóveis | `dados_imoveis` | .xlsx |
| Dados de veículos | `dados_veiculos` | .xlsx |
| RG | `rg` | .pdf ou .jpg |
| CPF | `cpf` | .pdf ou .jpg |
| Passaporte | `passaporte` | .pdf ou .jpg |
| Visto | `visto` | .pdf ou .jpg |
| Certidão de nascimento | `certidao_nascimento` | .pdf |
| Certidão de casamento | `certidao_casamento` | .pdf |
| SSN (Social Security) | `ssn` | .pdf ou .jpg |
| Driver's License (US) | `drivers_license` | .pdf ou .jpg |
| Green Card (US) | `green_card` | .pdf ou .jpg |

---

## MAPA DE DESTINOS

| Tipo de documento | Diretório |
|---|---|
| Extratos CC/PJ/Global/Poupança, faturas cartão, posições investimentos, CDBs, faturas QuintoAndar | `data/financial_statements/` |
| IRPF, informes de rendimento QuintoAndar | `data/income_tax_br/` |
| Planilhas e docs de imóveis | `data/real_estate/` |
| Planilhas de veículos | `data/vehicles/` |
| Currículos, holerites, documentos pessoais (RG, CPF, passaporte, visto, certidões, SSN, driver's license, green card) | `members/` |
| Docs fiscais EUA (Form 1040, FBAR, W-2) | `data/income_tax_us/` |

---

## PADRÃO DE NOMENCLATURA

```
[entidade]_[tipo]_[periodo]-0_original.[ext]
```

- **Período mês único:** `YYYYMM` (ex: `202603`)
- **Período intervalo:** `YYYYMM_YYYYMM` (ex: `202601_202603`)
- **Sufixos de processamento:** `-0_original`, `-1a_extract`, `-1b_unified`, `-1c_enriched`, `-2_extract`, `-2_reconciled`, `-3_unified`, `-4`

---

## CONTAS BANCÁRIAS

### David

| Instituição | Agência | Conta | Tipo | Uso principal |
|---|---|---|---|---|
| C6 Bank PJ | 1 | 384366937 | PJ | Receita PJ, pagamento DAS |
| C6 Bank PF | — | — | PF | Conta operacional |
| Itaú Personnalité | 9652 | 04397-8 | PF | Investimentos + aluguéis David |
| Santander | 1652 | 01001341-6 | PF | CDBs |
| Rico/XP | — | 6742394 | Corretora | Fundos + ações |
| PicPay | — | 4383290 | PF | RDB liquidez |
| Wise | — | — | Internacional | Acumulação USD |
| Bank of America | — | — | Internacional | Dormida EUA |
| C6 Global USD | — | — | Internacional | Cartão viagem |
| C6 Global EUR | — | — | Internacional | Residual |
| Binance | — | — | Exchange | Crypto |

### Mariana

| Instituição | Agência | Conta | Tipo | Uso principal |
|---|---|---|---|---|
| Bradesco | 3221 | 77113-9 | PF (CC + Poupança) | Salário Einstein (poupança) + aluguéis (CC) |
| BTG Pactual | 0001 | 002713513 | Corretora | Investimentos |

---

## IDENTIFICADORES NOS EXTRATOS

| Campo no extrato                           | Significado real               | Conta             | Cuidado           |
| ------------------------------------------ | ------------------------------ | ----------------- | ----------------- |
| "Sociedade Beneficente Israelita"          | Salário Einstein (Mariana)     | Poupança Bradesco | NÃO aparece no CC |
| "GRPQA Ltda." ou "Grpqa" ou "SISPAG GRPQA" | Aluguéis QuintoAndar (Mariana) | CC Bradesco       | NÃO é salário     |
| "GRPQA Ltda." ou "Grpqa" ou "SISPAG GRPQA" | Aluguéis QuintoAndar (David)   | Itaú Personnalité | —                 |
| "VINDI *ACCOUNTBANKTEC"                    | AccountTech contador           | Fatura C6 Carbon  | —                 |
| "CAMILANAKAMURA"                           | Camila Nakamura dentista       | Fatura C6 Carbon  | —                 |
| "NATHALIA CASA DE"                         | Açougue Nathalia               | Fatura C6 Carbon  | —                 |
| "Débito RFB CPF 085.052.396-60"            | IRPF parcelamento Mariana      | CC Bradesco       | —                 |
| "ABDO MOHAMED"                             | Instituto Dr. Barakat de Medicina Integrativa | Faturas/extratos | Categoria: Saúde  |

---

## CATEGORIAS DE DESPESA (ORÇAMENTO PROSPECTIVO)

| Código                | Categoria                                          | Teto mensal | % Renda |
| --------------------- | -------------------------------------------------- | ----------- | ------- |
| `moradia`             | Moradia (sem financiamento)                        | R$ 2.500    | 3,2%    |
| `alimentacao`         | Alimentação                                        | R$ 4.500    | 5,8%    |
| `saude`               | Saúde                                              | R$ 3.000    | 3,9%    |
| `servicos_domesticos` | Serviços domésticos                                | R$ 4.000    | 5,2%    |
| `educacao`            | Educação                                           | R$ 2.000    | 2,6%    |
| `transporte`          | Transporte                                         | R$ 1.700    | 2,2%    |
| `lazer_viagens`       | Lazer e viagens                                    | R$ 3.750    | 4,8%    |
| `vestuario`           | Vestuário e compras                                | R$ 2.000    | 2,6%    |
| `assinaturas`         | Assinaturas                                        | R$ 300      | 0,4%    |
| `suporte_familiar`    | Suporte familiar                                   | R$ 5.000    | 6,3%    |
| `financeiro`          | Financeiro pessoal                                 | R$ 200      | 0,3%    |
| `melhoria_reforma`    | Melhoria/Reforma moradia                           | R$ 1.500    | 1,9%    |
| `reserva_desejos`     | Reserva de desejos                                 | R$ 3.000    | 3,9%    |
| `seguros`             | Seguros (vida, invalidez, residencial, auto, pets) | R$ 1.500    | 1,9%    |

**Total tetos: R$ 32.950/mês (41,9% da renda)**

### REGRAS DE CATEGORIZAÇÃO POR KEYWORDS (usadas no E3)

Abaixo estão os padrões de texto (case-insensitive, match parcial na descrição da transação) que determinam a categoria. Se mais de uma regra casar, usar a mais específica (mais longa). Se nenhuma regra casar, manter como `nao_identificado`.

**`alimentacao`** — Supermercados, restaurantes, cafés, padarias, delivery, açougues:
`OXXO`, `SACOLAO`, `MERCADO`, `SAKURA`, `VERDURAS E LEGUMES`, `QUEBEC BAR`, `RAMEN`, `THE VIEW BAR`, `GALPAO DA COSTELA`, `EL PELEGRINO`, `BAR DA JULINHA`, `CANTINA`, `CANTINHO DOS MINEIROS`, `BLMT COMERCIO DE ALIME`, `CARR EXPRESS`, `CASA BAUDUCCO`, `CASA PILAO`, `CHAPEU DE SOL`, `CHOCOLATE`, `CHURRASCARIA`, `DENGO`, `EMPADAKI`, `ENRICOCAFEE`, `CAFETERIA`, `GRAN COFFEE`, `GUIMARAES ALIMENTOS`, `IFD*`, `KINDINPAESEDOCES`, `LAGOS DO SUL`, `LAGOSDOSUL`, `LIKA YACEPS`, `LINDT`, `M A DE CARVALHO CHOCOL`, `MINAS QUEIJO`, `MILKMOO`, `MILKY MOO`, `MINI MERC`, `MINIMART`, `MOZI COMERCIO`, `NATA `, `NATHALIACASADE`, `OFNER`, `PAES E DOCES`, `PASTEISOSHIRO`, `PASTELARIA`, `PIRAJA COMERCIO`, `QUIOSQUE CE QUE`, `RDO CHOCOLATES`, `REAL DA VILLA`, `REDE CAMPEAO`, `REDE OBA`, `REST FRANGOASSADO`, `RM MORUMBI`, `ROP COM ALIM`, `S.R. GONCALVES`, `SAMS*`, `SELVAGEM`, `SODIEDOCES`, `STAR CHICKEN`, `TEMPERODAFE`, `TOSTADO CAFE`, `VEGSIM`, `VISTA IBIRAPUERA`, `YES COFFEE`, `GAMBO CAFE`, `BOGO CAFE`, `NOVO - MUG`, `CASA MURDOCK`, `ERVA DOCE BAR`, `O BADEN BADEN`, `MORUMBI TERREO`, `DON MACEDO CARNE`, `JDM COMERCIO DE ALIM`, `GUARAREMA`, `KERO MAIS`, `CINCO M COMERCIO`, `MM CAMPO BELO`, `BG NORTE`, `DESCAMPADO`, `A CASA DE ANTONIA`, `MOMA MADALENA`, `CACAPAVA`, `EJM REST JAPONES`, `PORTO CAIRES`, `R TRES`, `JIM.COM* MAB FOOD`, `JIM.COM* UMETSU COMER`, `TORRALTA`, `TORRALTACOMERCIO`, `NADIR`

**`transporte`** — Estacionamento, combustível, pedágio, mobilidade:
`PARK`, `AUTOPOSTO`, `AUTOPOSTOKANTAN`, `ULTRAGAS`, `CONCESSIONARIA SPMAR`, `CARRETEIRO REV`, `PUNTO *PRIME AUTO`, `ECOPISTA`, `FELTRIN MOTOS`, `MEGAPASS`, `MC MOBILITY`, `MCOUTINHO MOBILITY`, `EXXON AUTOMATED`, `BANDEIRA PAULISTA PAR`, `AUTOVAGAS`, `MARANATA SERVICOS DE G`, `CORREA CONVENIENCIA`

**`assinaturas`** — Streaming, apps, software, gym:
`WELLHUB`, `GYMPASS`, `AMAZONPRIMEBR`, `GLOBO*GLOBOPLAY`, `GLOBO GLOBOPLAY`, `GOOGLE *DUOLINGO`, `SURFSHARK`, `PAYPAL *RESCUETIME`, `PAYPAL *CLEVERBRIDG`, `EBN *SONYPLAYSTATN`, `PADDLE.NET*`, `REGISTROBR`, `EC *MELIMAIS`, `MP *MELIMAIS`, `PRODUTOS GLOBO`, `SP FLIPPER DEVICES`, `ASSOCIATION FOR COMPUT`

**`saude`** — Farmácia, tratamentos, bem-estar:
`CORPO E VIDA`, `REMEDIOPOPULAR`, `NUTRA BODY`, `MP *FARMAPOPULAR`, `SCRIPTS PHARMACY`, `CAMILANAKAMURA`, `ABDO MOHAMED`

**`seguros`** — Seguradoras:
`SUL AMERICA SEG`

**`vestuario`** — Roupas, acessórios, cosméticos, joalheria, moda:
`I. M. SATO VESTUARIO`, `LUANA FASHION`, `VICIO FEMININO`, `CARTERS`, `KIKO MILANO`, `PITICAS`, `BAYARD ESPORTES`, `EMY PERFUMARIA`, `SONEDA PERFUMARIA`, `ITRCCABELEIREIROS`, `LOJA OFICIAL`, `TATIANA GIORDANO`

**`lazer_viagens`** — Turismo, entretenimento, parques, hospedagem, duty-free:
`AIRBNB`, `SEAWORLD`, `BUSCH GARDENS`, `PORTO DUTY FREE`, `TERMINAL III`, `HN HUDSON`, `WEATHERSTATION`, `WDW DROID DEPOT`, `NIC*-DOH ORA VITAL`, `MINUTE SUITES`, `ZIG*VILLA DI PHOENIX`, `ZIG. THE GLOBAL FUNTEC`, `A NOIESA`, `AEROP. ADOLFO SUAREZ`, `ASSOC COMERCIAL PORT`, `AUDASA VISA`, `CATEDRAL DE SANTIAGO`, `CHEZ LAPIN`, `CPPB-RUA AUGUSTA`, `FUNDACAO CULTURSINTR`, `MANTEIGARIA SILVA`, `ATL PANDA EXPRESS`, `FAST POINT MC`, `DOLLAR TREE`, `AMAZON GROCERY`, `AMAZON TIPS`

**`melhoria_reforma`** — Materiais, construção, manutenção residencial:
`JS MATERIAIS DE CONS`, `ANDRA MATERIAIS`, `FUTURA MADEIRAS`, `DEPOSITO CENTER`, `DEPOSITO GUARANI`, `ROSSE COMERCIO`, `ELETTRICA COMERCIO`, `CONILREM`, `DAISO BRASIL`

**`educacao`** — Livros, papelaria, cursos:
`LEITURA`, `KALUNGA`, `COPICOPIAS`, `PAPELARIA`

**`servicos_domesticos`** — Equipe doméstica, lavanderia, pet:
`SUECIA`, `ELIANE`, `ANDREA S LAVANDERIA`, `PET DOGSTORE`, `JIM COM* LAVARAPIDO`, `JIM.COM* LAVARAPIDO`

**`financeiro`** — Taxas bancárias, IOF, juros, tarifas, contador:
`VINDI *ACCOUNTBANKTEC`, `PAYPAL *DOCUSIGNINC`

**`suporte_familiar`** — Transferências para familiares, presentes infantis:
`ALO BEBE`, `ICA*ICASEI`, `MAKOS LEMBRANCAS`

**`reserva_desejos`** — Eletrônicos, tech, compras planejadas de alto valor:
`AMAZON MKTPLACE`, `AMAZON RETA`, `AMAZONMKTPLC`, `MP *VICTORELETRONICOS`

**Regras especiais:**
- `NATHALIACASADE` = Açougue Nathalia Casa de Carnes → **alimentacao** (NÃO é serviço doméstico)
- `ABDO MOHAMED` = Instituto Dr. Barakat → **saude**
- `RECEB PAGFOR GRPQA` = Aluguel QuintoAndar → **NÃO é despesa** (é receita)
- Transações com `USD` no final geralmente são gastos em viagem internacional → avaliar se `lazer_viagens` ou a categoria do estabelecimento

**Fallback**: Se a descrição não casar com nenhuma regra acima, o operador E3 deve usar o contexto (nome do estabelecimento, valor, conta de origem) para inferir a categoria. Apenas se realmente não for possível identificar, manter como `nao_identificado` e registrar em `qa_log.md`.

### REGRAS DE CATEGORIZAÇÃO DE RECEITAS (usadas no E3)

O E3 gera `receitas-3_unified.json` agrupado por fonte. Abaixo estão as regras para classificar **créditos** (entradas) nas contas:

| Padrão no extrato (case-insensitive) | Categoria receita | Subcategoria | Conta esperada | Membro |
|---|---|---|---|---|
| `ARVO`, `DAVID ROBERT CAMARGO` (TED/PIX recebido PJ→PF) | `receita_pj` | Pró-labore Arvo | C6 PJ → C6 PF | David |
| `BRANDLOVERS`, `BRAND LOVERS` | `receita_pj` | Advisory BrandLovers | C6 PJ | David |
| `ARBITRALIS` | `receita_pj` | Advisory Arbitralis | C6 PJ | David |
| `LEARNTOFLY`, `LEARN TO FLY` | `receita_pj` | Mentoria LearnToFly | C6 PJ | David |
| `KIWIFY` | `receita_pj` | Kiwify (encerrado mai/2025) | C6 PJ | David |
| `CNRY`, `CANARY` | `receita_pj` | CNRY/Canary (encerrado set/2025) | C6 PJ | David |
| `BARTE` | `receita_pj` | Barte Brasil (encerrado set/2025) | C6 PJ | David |
| `Sociedade Beneficente Israelita` | `receita_clt` | Salário Einstein | Poupança Bradesco | Mariana |
| `GRPQA`, `SISPAG GRPQA`, `RECEB PAGFOR GRPQA` | `receita_aluguel` | Aluguéis QuintoAndar | CC Bradesco / Itaú Personnalité | David + Mariana |
| `ALUGUEL`, `LOCACAO` (em conta CC, não em fatura cartão) | `receita_aluguel` | Aluguel direto (sem QuintoAndar) | Qualquer CC | Ambos |
| `RENDIMENTO`, `JUROS S/CAPITAL`, `DIVIDENDO` | `receita_investimento` | Rendimentos financeiros | Rico, BTG, Itaú, Santander | Ambos |
| `RESGATE`, `LIQUIDACAO` (CDB, fundo, RF) | `receita_resgate` | Resgate de investimento | Qualquer | Ambos |
| `RESTITUICAO`, `RESTIT IRPF` | `receita_restituicao` | Restituição IRPF | Qualquer CC | Ambos |
| `FGTS`, `CAIXA ECONOMICA` (saque) | `receita_fgts` | Saque FGTS | Qualquer CC | David |

**Regras especiais receitas:**
- Créditos PJ→PF do mesmo titular (ex: TED de C6 PJ para C6 PF David) são **transferências internas**, não receita (ver seção abaixo).
- `GRPQA` em CC Bradesco = receita aluguel Mariana. `GRPQA` em Itaú = receita aluguel David. Nunca classificar como despesa.
- Rendimentos de poupança Bradesco (créditos automáticos) = `receita_investimento`, subcategoria "rendimento poupança".

### MAPA DE TRANSFERÊNCIAS INTERNAS (usadas no E3)

Transferências entre contas do casal **NÃO são receita nem despesa**. Devem ser classificadas como `transferencia_interna` e excluídas do fluxo de caixa. O E3 usa este mapa para detectá-las:

**Contas do casal (qualquer movimento entre estas é interno):**

| Código | Titular | Instituição | Identificador |
|---|---|---|---|
| `c6pj` | David | C6 Bank PJ | Ag. 1, Conta 384366937 |
| `c6pf` | David | C6 Bank PF | — |
| `itau` | David | Itaú Personnalité | Ag. 9652, Conta 04397-8 |
| `santander` | David | Santander | Ag. 1652, Conta 01001341-6 |
| `rico` | David | Rico/XP | Conta 6742394 |
| `picpay` | David | PicPay | Conta 4383290 |
| `wise` | David | Wise | — |
| `bofa` | David | Bank of America | — |
| `c6usd` | David | C6 Global USD | — |
| `c6eur` | David | C6 Global EUR | — |
| `binance` | David | Binance | — |
| `bradesco` | Mariana | Bradesco CC + Poupança | Ag. 3221, Conta 77113-9 |
| `btg` | Mariana | BTG Pactual | Ag. 0001, Conta 002713513 |

**Regras de detecção:**
1. **TED/PIX entre contas acima** → `transferencia_interna` (ex: C6 PJ → C6 PF, C6 PF → Itaú, David → Mariana via PIX)
2. **Aplicação/resgate investimento** na mesma instituição → `transferencia_interna` (ex: CC Itaú → CDB Itaú, CC Santander → CDB Santander)
3. **Remessa internacional** entre contas próprias → `transferencia_interna` (ex: C6 PF → Wise, C6 PF → C6 Global USD)
4. **Pagamento de fatura de cartão** → `transferencia_interna` (débito na CC que paga a fatura Carbon/Unique/Pão de Açúcar — a despesa já foi registrada na fatura)
5. **Depósito poupança ↔ CC** no mesmo banco → `transferencia_interna` (ex: Bradesco CC → Bradesco Poupança)

**Exceções (NÃO são transferência interna):**
- Pagamento de DAS/IRPF via CC → é despesa `financeiro` ou `impostos`
- Pagamento de financiamento imobiliário → é despesa `moradia`
- Transferência para terceiros (babá, diarista, familiares) → é despesa na categoria correspondente

---

## CONTRATOS PJ ATIVOS (abr/2026+)

| Contrato                  | Entidade    | Valor mensal                              | Conta recebedora | Status  |
| ------------------------- | ----------- | ----------------------------------------- | ---------------- | ------- |
| Arvo Saúde (CTO)          | arvo        | R$ 47.209 base (R$ 54.958 com 13º/férias) | C6 PJ            | Ativo   |
| BrandLovers (advisor)     | brandlovers | ~R$ 10.000 (acúmulo trimestral)           | C6 PJ            | Ativo   |
| Arbitralis S.A. (advisor) | arbitralis  | R$ 2.000–3.500 (R$500/hora)               | C6 PJ            | Ativo   |
| LearnToFly (mentoria)     | learntofly  | ~R$ 1.750/aparição                        | C6 PJ            | Pontual |

### Contratos encerrados (não projetar)

| Contrato | Período | Total recebido |
|---|---|---|
| Kiwify (rescisão) | jun/2024–mai/2025 | R$ 407.357 |
| CNRY/Canary (advisor) | até set/2025 | R$ 80.000 |
| Barte Brasil (advisory) | até set/2025 | R$ 40.000 |

**CNRY e Barte são fontes pagadoras DIFERENTES.** Ambos encerrados set/2025, não recorrentes.

---

## EQUIPE DOMÉSTICA

| Pessoa                     | Função                 | Valor mensal                                          | Conta pagamento  |
| -------------------------- | ---------------------- | ----------------------------------------------------- | ---------------- |
| Suecia Pereira de Oliveira | Babá do Theo (eSocial) | R$ 3.391,41 (R$3.500 bruto − INSS + R$200 transporte) | C6 PF + Bradesco |
| Eliane Costa Gonçalves     | Diarista Mariana       | R$ 220                                                | Bradesco         |
| Maria Gizelia dos Santos   | Manicure Mariana       | R$ 35–105 (variável)                                  | Bradesco         |

---

## IMÓVEIS (6 + 1 reservado)

| # | Tipo | Imóvel | Área | Proprietário | IRPF (31/12/2024) | Aluguel/mês | Status |
|---|---|---|---|---|---|---|---|
| 1 | Casa | Casa Tasso da Silveira, Rua Tasso da Silveira 61, Vila Guarani | 171m² | David | R$ 997k | — | Residência própria |
| 2 | Ap | Cond. Barão de Capanema, Pça Benedito Calixto 190, Ap 34 | 40,76m² | David | R$ 350k | R$ 1.850 | Alugado (Caroline) |
| 3 | Ap | Ed. Gisele, Rua Major Freire 496, Ap 12 | 68,89m² | David | R$ 213k | R$ 1.572 | Alugado (Gabriel). Financiamento Itaú. |
| 4 | Casa | Casa Leonardo da Vinci, Av. Leonardo da Vinci 2707, Jabaquara | 73m² | David | R$ 80k | — | Usufruto vitalício (Leonilda) |
| 5 | Ap | Living Wish, Av. João Dias 2192, T2 Ap 163 | 88,9m² | Mariana | R$ 530k | R$ 5.149 | Alugado (Wesley) |
| ~~6~~ | ~~Ap~~ | ~~Living Concept, Av. Alberto Augusto Alves 320, Ap 812~~ | ~~25,7m²~~ | ~~Mariana~~ | ~~R$ 270k~~ | ~~R$ 881~~ | **VENDIDO (D15, abr/2026). Yield 3,9% — capital reinvestido em RF/RV.** |
| 7 | — | (reservado para futuras aquisições) | — | — | — | — | — |

**Total aluguéis: R$ 8.571/mês** (David R$ 3.422 + Mariana R$ 5.149) — pós-venda Living Concept

**Notas sobre IRPF dos imóveis:**
- Imóveis 1 e 4 usam código IRPF **01-12** (compra e venda de casa). Os demais usam **01-11** (apartamento).
- O E2 extract deve capturar AMBOS os códigos (01-11 e 01-12) da seção "Bens e Direitos" do IRPF.
- Imóvel 3 (Ed. Gisele): IRPF declara R$ 213k (valor com alienação fiduciária ao Itaú), NÃO o valor total de compra.
- Padrão de nomes: Imóveis 2, 3, 5, 6 são **apartamentos** (Ap). Imóveis 1 e 4 são **casas**.
- Formato: "[Tipo] [Nome cond/ed], [Logradouro] [Número], [Complemento]"

---

## AÇÕES DIRETAS — Rico (David)

| Ticker | Empresa | Qtd Atual | PM (R$) | Custo Total | Lotes de Compra | Fonte PM |
|---|---|---|---|---|---|---|
| PETR4 | Petrobras PN | 1.700 | 22,87 | R$ 38.883 | 400 × R$16,67 (abr/2020) + 900 × R$22,11 (fev/2021) + 400 × R$30,79 (set/2022) | Histórico de compras (usuário) |
| ITSA4 | Itaúsa PN | 763 | 7,63 ¹ | R$ 5.821 | 693 × R$8,40 (abr/2020) + 70 bonificação | Histórico de compras + bonificação |
| BRKM5 | Braskem PNA | 300 | 20,89 | R$ 6.267 | 300 × R$20,89 (abr/2020) | Histórico de compras (usuário) |

¹ PM ajustado por bonificação: compra original 693 × R$8,40 = R$5.821. Itaúsa emitiu bonificação → 763 cotas. PM = R$5.821/763 = R$7,63.

**Notas:**
- Todas as ações estão custodiadas na Rico (conta 6742394).
- O extrato Rico (`rico_investimentosposicao`) fornece `quantity` e `unit_price` (cotação atual), mas NÃO fornece `applied_value` (custo de aquisição) para ações.
- O PM deve ser obtido do campo `lots` no `investimentos-3_unified.json`, que foi alimentado pelo histórico de compras do usuário.
- Se `lots` não estiver disponível, tentar cruzar com IRPF: se `quantity_rico == quantity_irpf`, PM = `valor_irpf / quantity`.
- Na ausência de ambos, marcar PM como "N/D" e adicionar nota no relatório.

**Nota abr/2026:** Manter decisão de venda apesar de upgrade Citi (neutra/alto risco, PT R$10). Risco de RJ real (prejuízo R$10,3bi). Prejuízo de ~R$3.500 utilizável para compensação fiscal.

## ESTRATÉGIA DE APORTES MENSAIS

| Destino | Valor | Classe | Liquidez | Objetivo | Tarefa |
|---|---|---|---|---|---|
| Cofrinhos Itaú | R$ 10.000 | Caixa | D+0 | Reserva emergência (meta 12 meses) | #6 (abr/2026) |
| Tesouro IPCA+ | R$ 5.000 | RF | D+1 (marcação mercado) | Proteção inflação + RF longa | #6 (abr/2026) |
| IVVB11 | R$ 3.000 | Internacional | D+2 (bolsa) | Dolarização indireta + RV global | #6 (abr/2026) |
| Wise USD | R$ 2.000 | Internacional | D+0 (conversão cambial) | Acumulação USD (~US$340/mês) | #6 (abr/2026) |
| PGBL Itaú | R$ 1.800 | Previdência | D+60 (benefício fiscal) | Regime regressivo (economia R$5.940/ano IRPF) | #7 (abr/2026) |
| DCA Crypto | R$ 500 | Crypto | D+0 (alta volatilidade) | Diversificação 0,1% → 1% | #23 (mai/2026) |
| **Total** | **R$ 22.300** | | | | |

**Notas:**
- Os R$20.000 (4 primeiros) são configurados como aporte automático (tarefa #6).
- O PGBL R$1.800 é um setup separado no Itaú (tarefa #7) — R$1.800/mês = R$21.600/ano = 12% da renda tributável (~R$180k).
- O DCA Crypto R$500 inicia em mai/2026 (tarefa #23) — via Binance ou Hashdex, a definir.
- PGBL é **investimento/previdência**, não despesa. Aparece na classe de ativos `previdencia` (meta 5% da carteira).

**Validação aportes → alocação alvo:**
| Classe | Atual | Alvo | Aporte | Cobertura |
|---|---|---|---|---|
| RF | 54,2% | 50% | R$5.000 | Temporário (Cofrinhos migra depois) |
| Fundos | 12% | 10% | — | Reduz com resgate PFIC (~R$181k) |
| Ações | 7,1% | 10% | — | **GAP:** sem aporte direto em RV BR |
| Caixa | 10,1% | 4% | R$10.000 | Temporário (meta reserva 12 meses) |
| Previdência | 1,4% | 5% | R$1.800 | Correto, gradual |
| Crypto | 0,1% | 1% | R$500 | Correto |
| Internacional | 0% | 10% | R$5.000 | Correto |

---

## FÓRMULAS PATRIMONIAIS — REGRA OBRIGATÓRIA

Estas fórmulas são canônicas e devem ser usadas em E4 e E5. Nunca hardcodar valores derivados.

```
patrimonio.bruto       = SUM(total_bens de cada membro no baseline)
patrimonio.dividas     = SUM(dividas de cada membro no baseline)
patrimonio.liquido     = bruto − dividas
patrimonio.investivel  = bruto − residencia_principal − veiculos
                       ⚠️ SEMPRE < bruto (se violar, há erro)
goals.if_pct           = investivel / if_meta × 100
goals.if_gap           = if_meta − investivel
```

**Categorias da tabela patrimonial (devem somar exatamente ao bruto):**

| # | Categoria | Cálculo |
|---|---|---|
| 1 | Residência própria | IRPF David → Tasso da Silveira |
| 2 | Imóveis investimento | E4.imoveis − Residência |
| 3 | Investimentos David | baseline.investimentos[] (inclui Hashdex — é fundo regulado, não crypto direto) |
| 4 | Investimentos Mariana | baseline.investimentos[] (BTG) |
| 5 | Criptoativos | Binance saldo (crypto direta: BTC, ETH, ADA, AXS etc.) |
| 6 | Caixa + Moeda | bruto − categorias 1-5 − categoria 7 (residual) |
| 7 | Veículos | baseline.veiculos[] |

**Validações (bloquear geração se falhar):**
- `SUM(categorias 1–7) == bruto`
- `SUM(percentuais) == 100,0%`
- `investivel < bruto`
- `if_gap + investivel == if_meta`

---

## PROCESSAMENTO DE ARQUIVOS — REGRA TÉCNICA

Todos os arquivos `.pdf` deste projeto são **PDFs reais** (não ZIPs disfarçados). A extração de dados deve usar leitura direta de PDF.

**Nota histórica:** A v4.3 assumia incorretamente que os PDFs eram ZIPs (header `PK\x03\x04`). O setup inicial de abr/2026 confirmou que isso não é o caso (QA-5 do run_log.md). Referências antigas a "desempacotar" ou "unzip" de PDFs estão obsoletas.

**Tipos de arquivo no pipeline:**
- `.pdf` — PDFs reais, leitura direta
- `.xlsx` — Planilhas (imóveis, veículos), leitura com leitor de planilhas
- `.docx` — Documentos Word (currículos), leitura com leitor DOCX
- `.jpg` — Screenshots de apps bancários, leitura com OCR/visão multimodal
