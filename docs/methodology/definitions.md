# Definitions — Pipeline Ferreira Campos
## Versão: 5.3 — abr/2026

---

## MEMBROS DA FAMÍLIA, NOMES E PETS

> **Fonte canônica:** `config/family_members.json`
> Nomes completos, nomes de solteiro/casado, datas de nascimento, variantes de nome, pets e endereço estão centralizados nesse arquivo JSON. Não duplicar aqui — qualquer correção deve ser feita no JSON.

**Referência rápida (derivada do JSON):**

| Membro  | CPF            | Nascimento | Papel                        |
| ------- | -------------- | ---------- | ---------------------------- |
| David   | 287.766.948-36 | 05/09/1981 | Titular, CTO PJ              |
| Mariana | 085.052.396-60 | 30/08/1986 | Cônjuge, enfermeira CLT      |
| Theo    | —              | 18/07/2025 | Filho, dupla cidadania BR/US |

> Documentos emitidos antes do casamento podem conter o nome de solteiro(a).
> O holerite do Hospital Einstein usa o nome fiscal (solteira) de Mariana: "Mariana Teixeira Ferreira".
> Ao encontrar qualquer variante desses nomes em documentos, mapear para o `id` do membro correto sem tratar como divergência.

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
| Kiwify | `kiwify` | Ex-empregador CLT (David). Qualquer receita Kiwify = salário CLT, não receita PJ. |
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
- **Período indeterminado:** `999999` — sentinel para faturas cujo período não pôde ser extraído
- **Sufixos de processamento:** `-0_original`, `-1a_extract`, `-1b_unified`, `-1c_enriched`, `-1.5_consolidated`, `-2_extract`, `-3_reconciled`, `-4_unified`, `-5_analysis`

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

## REGRAS DE CLASSIFICAÇÃO PARA SCREENSHOTS DE APP

> Screenshots do app de bancos (JPG/PNG) frequentemente mostram **posições de investimento**, não extratos bancários.
> A classificação correta é essencial para evitar receitas fantasma.

| Conteúdo do screenshot | Tipo correto | Observação |
|---|---|---|
| Itaú Cofrinhos / Reserva (valor guardado, rendimento, depósitos) | `investimentosposicao` | O "Depósito" exibido no histórico é uma **aplicação interna** (CC→CDB), já capturada pelo XLS como `APLICACAO CDB COFRINHOS`. **NÃO** gerar transação — apenas posição de investimento. |
| Itaú posição de investimentos | `investimentosposicao` | — |
| Binance saldo em crypto | `extratoconta` | Extrair como saldo + transações normais |

**Regra geral:** Se o screenshot mostra um saldo de investimento/poupança com rendimento, classificar como `investimentosposicao`. Se mostra transações de débito/crédito em conta corrente, classificar como `extratoconta`.

---

## IDENTIFICADORES NOS EXTRATOS

| Campo no extrato                                                                     | Significado real                              | Conta             | Cuidado           |
| ------------------------------------------------------------------------------------ | --------------------------------------------- | ----------------- | ----------------- |
| "Sociedade Beneficente Israelita" ou "tr Sal p/poup Sociedade Beneficente Israelita" | Salário Einstein (Mariana)                    | Poupança Bradesco | NÃO aparece no CC |
| "GRPQA Ltda." ou "Grpqa" ou "SISPAG GRPQA" ou "SISPAG GRPQA LTDA"                    | Aluguéis QuintoAndar (Mariana)                | CC Bradesco       | NÃO é salário     |
| "GRPQA Ltda." ou "Grpqa" ou "SISPAG GRPQA" ou "SISPAG GRPQA LTDA"                    | Aluguéis QuintoAndar (David)                  | Itaú Personnalité | —                 |
| "VINDI *ACCOUNTBANKTEC"                                                              | AccountTech contador                          | Fatura C6 Carbon  | —                 |
| "CAMILANAKAMURA"                                                                     | Camila Nakamura dentista                      | Fatura C6 Carbon  | —                 |
| "NATHALIA CASA DE"                                                                   | Açougue Nathalia                              | Fatura C6 Carbon  | —                 |
| "Débito RFB CPF 085.052.396-60"                                                      | IRPF parcelamento Mariana                     | CC Bradesco       | —                 |
| "ABDO MOHAMED"                                                                       | Instituto Dr. Barakat de Medicina Integrativa | Faturas/extratos  | Categoria: Saúde  |

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
| `financiamentos`      | Financiamentos imobiliários                        | (variável)  | —       |
| `impostos`            | Impostos (IRPF, IPTU, IPVA, DAS, DARF)             | (variável)  | —       |

**Total tetos fixos: R$ 34.950/mês (44,5% da renda)**
*Nota: `financiamentos` e `impostos` não têm teto fixo — são obrigações variáveis acompanhadas separadamente.*

### REGRAS DE CATEGORIZAÇÃO POR KEYWORDS (usadas no E4)

Abaixo estão os padrões de texto (case-insensitive, match parcial na descrição da transação) que determinam a categoria. Se mais de uma regra casar, usar a mais específica (mais longa). Se nenhuma regra casar, manter como `nao_identificado`.

**`moradia`** — Condomínio, utilities, manutenção:
`ELETROPAULO`, `ENEL`, `CPFL`, `CESP`, `COMGAS`, `SABESP`, `SANEPAR`, `COPASA`, `CONDOMINIO`, `TELHA NORTE`, `DDDRIN SERVICO DE DESI`, `DE PAULA REALTY`, `APPFOLIO`, `SECRETARIA MUNICIPAL`, `ADMINISTRADORA`

**`alimentacao`** — Supermercados, restaurantes, cafés, padarias, delivery, açougues:
`OXXO`, `SACOLAO`, `MERCADO`, `SAKURA`, `VERDURAS E LEGUMES`, `QUEBEC BAR`, `RAMEN`, `THE VIEW BAR`, `GALPAO DA COSTELA`, `EL PELEGRINO`, `BAR DA JULINHA`, `CANTINA`, `CANTINHO DOS MINEIROS`, `BLMT COMERCIO DE ALIME`, `CARR EXPRESS`, `CASA BAUDUCCO`, `CASA PILAO`, `CHAPEU DE SOL`, `CHOCOLATE`, `CHURRASCARIA`, `DENGO`, `EMPADAKI`, `ENRICOCAFEE`, `CAFETERIA`, `GRAN COFFEE`, `GUIMARAES ALIMENTOS`, `IFD*`, `KINDINPAESEDOCES`, `LAGOS DO SUL`, `LAGOSDOSUL`, `LIKA YACEPS`, `LINDT`, `M A DE CARVALHO CHOCOL`, `MINAS QUEIJO`, `MILKMOO`, `MILKY MOO`, `MINI MERC`, `MINIMART`, `MOZI COMERCIO`, `NATA `, `NATHALIACASADE`, `OFNER`, `PAES E DOCES`, `PASTEISOSHIRO`, `PASTELARIA`, `PIRAJA COMERCIO`, `QUIOSQUE CE QUE`, `RDO CHOCOLATES`, `REAL DA VILLA`, `REDE CAMPEAO`, `REDE OBA`, `REST FRANGOASSADO`, `RM MORUMBI`, `ROP COM ALIM`, `S.R. GONCALVES`, `SAMS*`, `SELVAGEM`, `SODIEDOCES`, `STAR CHICKEN`, `TEMPERODAFE`, `TOSTADO CAFE`, `VEGSIM`, `VISTA IBIRAPUERA`, `YES COFFEE`, `GAMBO CAFE`, `BOGO CAFE`, `NOVO - MUG`, `CASA MURDOCK`, `ERVA DOCE BAR`, `O BADEN BADEN`, `MORUMBI TERREO`, `DON MACEDO CARNE`, `JDM COMERCIO DE ALIM`, `GUARAREMA`, `KERO MAIS`, `CINCO M COMERCIO`, `MM CAMPO BELO`, `BG NORTE`, `DESCAMPADO`, `A CASA DE ANTONIA`, `MOMA MADALENA`, `CACAPAVA`, `EJM REST JAPONES`, `PORTO CAIRES`, `R TRES`, `JIM.COM* MAB FOOD`, `JIM.COM* UMETSU COMER`, `TORRALTA`, `TORRALTACOMERCIO`, `NADIR`, `PADARIA DANIELA`, `BONANZA 0001`, `MERCADINHO BONANZA`, `WM SUPERCENTER`, `WAL-MART`, `PAO DE ACUCAR`, `PAOACUCAR`, `5M COMERCIO ATACADISTA`, `CARREFOUR`, `EXTRA HIPER`, `VAI DE PIZZAS`, `DOMINO'S`, `CONFRARIA DO SUSHI`, `KIRA SUSHI`, `OUTBACK`, `MCDONALD'S`, `ALCHINGER LANCHONETE`, `MOUSTACHE BEAMS`, `LANCHONETE REAL DA VI`, `LANCHONETE CAMPING`, `BOTHANICO RESTAURANTE`, `CUBO BAR E RESTAURANTE`, `ARKO S RESTAURANTE`, `ARKOS RESTAURANTE`, `RESTAURANTE PAND`, `SPACE SETE COM DE ALIM`, `PIZZA HUT`, `DEL NERO E MIRANDEZ`, `EMPORIO PAES`, `EMPORIO PINHEIROS`, `PADARIA SANTA MARINA`, `PADARIA FAMA`, `CAFE DAS COISINHAS`, `HORTIFRUTIRUI`, `GRAAL MARKET`, `PRODUTOS NATURAIS`, `RJB ACAI E TAPIOCA`, `BOBBY'S BURGERS`, `METRO PIZZA`, `CARRINHO DO DUDA`, `AMO AV MORUMBI DRIVE`, `RAPPI*RAPPI BRASIL INT`, `RAPPI *RAPPI RAPPI BR`, `RAPPI BRASIL INTERMEDI`, `DL *DLRAPPI BR`, `DL*DLRAPPI BR`, `DL *DLRAPPIPROBR`, `EJM RESTAURANTE JAPONE`, `PAYGO*LG ESPETOS`, `POINTJABAQUARA`, `M L MATOS CONVENIENCIA`, `EMPORIOMATTERLTDA`, `PAG*MERCADINHOBONANZA`, `DJAPA`, `RAPPI  *RAPPI * BRASI`, `RAPPI*RAPPI BRASIL`

**`transporte`** — Estacionamento, combustível, pedágio, mobilidade:
`PARK`, `AUTOPOSTO`, `AUTOPOSTOKANTAN`, `ULTRAGAS`, `CONCESSIONARIA SPMAR`, `CARRETEIRO REV`, `PUNTO *PRIME AUTO`, `ECOPISTA`, `FELTRIN MOTOS`, `FELTRIN`, `INT LICENC`, `MEGAPASS`, `MC MOBILITY`, `MCOUTINHO MOBILITY`, `EXXON AUTOMATED`, `BANDEIRA PAULISTA PAR`, `AUTOVAGAS`, `MARANATA SERVICOS DE G`, `CORREA CONVENIENCIA`, `PRIME AUTO POSTO`, `AUTO POSTO`, `MINUTO PA`, `SHELL PO`, `SHELL MI`, `POSTO SHELL`, `POSTO LIDER`, `ML20 IMIGRANTES AUTO`, `RACETRAC`, `WAWA`, `ARCO #`, `UBER *TRIP`, `UBER UBER *TRIP`, `LYFT`, `CAMPEAO 28 POSTOS`, `POSTO ACACIAS`, `POSTO CARIJO`, `POSTO PAIN`, `TURISMOIIPOSTODE`, `A POSTO PLATINO`, `AUTO POSTO GALENA`, `AUTO POSTO PARQUE JAB`, `AUTO POSTO IRMAOS`, `AUTO POSTO GUACU`, `AUTO POSTO SONIMAR`, `AUTO POSTO ROTA`, `ESTACIONAMENTO MODELO`, `AN ESTACIONAMENTO`, `MMW ESTACIONAMENTOS`, `ESTAC T*ESTACIONAMENT`, `LTL ESTACIONAMENTO`, `MP *ESTACIONAMENT`, `F.M ESTETICA AUTOMOTIV`, `MAIS DISTR VEICULOS`, `PROPIG *FPS BATERIAS`

**`assinaturas`** — Streaming, apps, software, gym, seguros cartão:
`WELLHUB`, `GYMPASS`, `AMAZONPRIMEBR`, `GLOBO*GLOBOPLAY`, `GLOBO GLOBOPLAY`, `GOOGLE *DUOLINGO`, `SURFSHARK`, `PAYPAL *RESCUETIME`, `PAYPAL *CLEVERBRIDG`, `EBN *SONYPLAYSTATN`, `PADDLE.NET*`, `REGISTROBR`, `EC *MELIMAIS`, `MP *MELIMAIS`, `PRODUTOS GLOBO`, `SP FLIPPER DEVICES`, `ASSOCIATION FOR COMPUT`, `DM *SPOTIFY`, `DM*SPOTIFY`, `EBN *SPOTIFY`, `GOOGLE *GOOGLE ONE`, `APPLE.COM/BILL`, `APPLECOMBILL`, `AMAZON PRIME ALUGUEL`, `AMAZON PRIME*`, `CLUBE LIVELO*CLUBE LIV`, `LIVELO*CLUBE LIVELO`, `CLUBE LIVELO`, `LIVELO S.A.`, `SMILES CLUB`, `ESFERA`, `1PASSWORD*`, `LINKEDIN`, `WIX.COM`, `GOOGLE *TELEGRAM`, `GOOGLE *GOOGLE NEST`, `SQSP* DOMAIN`, `SCP COMPLETO`, `SCP BASICO`, `BRASILP*BRASILPARA`, `BRASIL PARAL*BRAS`

**`saude`** — Farmácia, tratamentos, clínicas, fisioterapia, bem-estar:
`CORPO E VIDA`, `REMEDIOPOPULAR`, `NUTRA BODY`, `MP *FARMAPOPULAR`, `SCRIPTS PHARMACY`, `CAMILANAKAMURA`, `ABDO MOHAMED`, `POUPA MEDI`, `EINSTEIN MORUMBI`, `HOSPITAL ALBERT EINSTE`, `CLINICA DERMATOLOGICA`, `INSTITUTO DR BARAKAT`, `PDV*BARA CLINICA`, `BRENTESINSTITUTO`, `FISIOTERAPIA BEBE EIRE`, `PELVIE FISIOTERAPIA`, `INST TADEU CVINTAL`, `AWADA ESTETICA`, `DROGASIL`, `DROGARIA SAO PAULO`, `DROGARIA_SP DROGARIASA`, `DROGARIA ONLINE`, `DROGARIA GUARANI`, `DROGARIA CRUZEIRO`, `DROGARIA CARREFOUR`, `RDSAUDE ONLINE`, `DPS SUPLEMENTOS`, `RAIA`, `MARCONI BASSO`, `DROGARIA X FARMACIA`, `PG *LIVANCE`, `ESPACO GIRAS`, `IU65 PREMIUM`, `CVS/PHARMACY`, `PT *ORL HLTH PYMT`, `HT SARAGIOTTO SERVICOS MEDICOS`, `LUMMA ROBERTA`, `HELEN SASAKE TAKAGI`, `FULL FACE MEDIC`, `CONCAVO E CONVEXO`, `PACEFIT`, `MOURA ACADEMIA`, `RAPPI *DROGARIA SAO P`, `RAPPI*RAIA DROGASIL`, `DROGASI`, `CLIMEFE`, `SER MED`

**`seguros`** — Seguradoras:
`SUL AMERICA SEG`, `MENSALIDADE DE SEGURO`, `PORTO SEGURO SEGUROS`, `TOKIO MARINE`, `SEGURO CONTA C6`

**`vestuario`** — Roupas, acessórios, cosméticos, joalheria, moda:
`I. M. SATO VESTUARIO`, `LUANA FASHION`, `VICIO FEMININO`, `CARTERS`, `KIKO MILANO`, `PITICAS`, `BAYARD ESPORTES`, `EMY PERFUMARIA`, `SONEDA PERFUMARIA`, `ITRCCABELEIREIROS`, `LOJA OFICIAL`, `TATIANA GIORDANO`, `VIVARA`, `CHILLI BEANS`, `THENORTHFACE`, `ROSS STORES`, `OTICAS RB1`, `IGUASPORT`, `GREAT CLIPS`, `T J MAXX`, `UNDER ARMOUR`, `SEPHORA`, `COLUMBIA 452`, `VICTORIA'S SECRET`, `BURLINGTON STORES`, `GAP OUTLET`, `MICHAEL KORS`, `TNF `, `HNA*OBOTICARIO`, `LUSH`

**`lazer_viagens`** — Turismo, entretenimento, parques, hospedagem, duty-free, aluguel carro:
`AIRBNB`, `SEAWORLD`, `BUSCH GARDENS`, `PORTO DUTY FREE`, `TERMINAL III`, `HN HUDSON`, `WEATHERSTATION`, `WDW DROID DEPOT`, `NIC*-DOH ORA VITAL`, `MINUTE SUITES`, `ZIG*VILLA DI PHOENIX`, `ZIG. THE GLOBAL FUNTEC`, `A NOIESA`, `AEROP. ADOLFO SUAREZ`, `ASSOC COMERCIAL PORT`, `AUDASA VISA`, `CATEDRAL DE SANTIAGO`, `CHEZ LAPIN`, `CPPB-RUA AUGUSTA`, `FUNDACAO CULTURSINTR`, `MANTEIGARIA SILVA`, `ATL PANDA EXPRESS`, `FAST POINT MC`, `DOLLAR TREE`, `AMAZON GROCERY`, `AMAZON TIPS`, `AIR EUROPA`, `LATAM AIR`, `LATAM AIRLINES`, `AMERICAN AIR*`, `HOTEL AT BOOKING.COM`, `HOTEIS.COM`, `BKG*BOOKING.COM`, `HOTELCOM`, `SAN FRANCISCO HOTEL`, `S F FLAT HOTEL`, `HOTEL MUNDIAL`, `HOTEL PORTO JARDIM`, `THE PLATINUM HOTEL`, `DOLLAR RAC`, `NVE*RENTCARSLTDA`, `HERTZ CAR RENTAL`, `WDW TICKETS`, `UNIVERSAL ORLANDO`, `HUDSON NEWS`, `SUNDRY SHOP`, `PRIP MART`, `AREAS PORTUGAL`, `CBD MARTIM`, `SP BAG OF SALT`, `VENETIAN STARBUCKS`, `FEVER*`, `TARGET T-`, `LOJAS AMERICANAS`, `PLAZA SUL`, `ALIANSCE`, `SHOPPING CENTER IBIRAP`, `PARQUE RIBEIRA`, `BOFT BRASIL`, `ITALIA TR`, `STUDIO DANSOU`

**`melhoria_reforma`** — Materiais, construção, manutenção residencial:
`JS MATERIAIS DE CONS`, `ANDRA MATERIAIS`, `FUTURA MADEIRAS`, `DEPOSITO CENTER`, `DEPOSITO GUARANI`, `ROSSE COMERCIO`, `ELETTRICA COMERCIO`, `CONILREM`, `DAISO BRASIL`, `SILETRICA`, `ELETTRICA`, `ELIAS PAIVA`, `REINALDO MARTINS`, `INACIO JOSE MACEDO`, `INACIO JOSE`, `MATEUS SOUZA ARCANJO`, `MANOEL MESSIAS`, `LEROY MERLIN`, `VESALTEC`

**`educacao`** — Livros, papelaria, cursos:
`LEITURA`, `KALUNGA`, `COPICOPIAS`, `PAPELARIA`, `PRIMO RICO`, `FUNDACAO SAO PAULO`, `ANDERSON UNIVERS`, `HARVARD BUS`, `PERUSALL`, `BELT ACADEMY`, `CONSELHO REGIONAL`, `OPEN ENGLISH`

**`servicos_domesticos`** — Equipe doméstica, lavanderia, pet:
`SUECIA`, `ELIANE`, `ANDREA S LAVANDERIA`, `PET DOGSTORE`, `JIM COM* LAVARAPIDO`, `JIM.COM* LAVARAPIDO`, `COBASI`, `PETZ`, `RAPPI*PET CENTER`, `ELAINE APARECIDA BUZZ`, `RK2LAVARAPIDOE`, `4MS`, `SAMUELABNERSANTOSMARC`, `MP *33798933SAMUELABN`, `ANA LUCIA SANTOS`, `GUIA DE EMPREGADO DOMESTICO`, `PAG*PETCENTERCOMERCIO`

**`financeiro`** — Taxas bancárias, IOF, juros, tarifas, anuidades, contador, imigração:
`VINDI *ACCOUNTBANKTEC`, `PAYPAL *DOCUSIGNINC`, `IOF CHEQUE ESPECIAL`, `IOF`, `TARIFA`, `JUROS LIMITE DA CONTA`, `JUROS CHEQUE ESP`, `JUROS SALDO UTILIZ`, `JUROS LIMITE`, `JUROS UTILIZ`, `TAR PACOTE`, `TAXA PERMANENCIA`, `ANUIDADE DIFERENCIADA`, `IOF DESPESA NO EXTERIOR`, `Anuidade Diferenciada`, `Multa Contratual`, `Juros de Mora`, `Encargos`, `D4U IMMIGRATION`, `D4U`, `MORAR EUA`, `IN *CA TRANSLATION SER`, `TABEL`, `CLAUDIA DANTAS TINOCO`

> **Nota v5.0.1:** `DEB AUTOM DE FATURA` foi removido desta lista pois é tratado como transferência interna (pagamento de fatura de cartão — a despesa já foi registrada na fatura).

**`suporte_familiar`** — Transferências para familiares, presentes infantis:
`ALO BEBE`, `ICA*ICASEI`, `MAKOS LEMBRANCAS`, `RUBENS DE CAMPOS`, `PIX TRANSF RUBENS`, `NEUSA CIMAR TEIXEIRA`, `NEUSA CIMAR`, `DOUGLAS CAMARGO DE CAMPOS`, `ERIC VINICIUS`, `SHEILA APARECIDA DA ROCHA DE CAMARGO`, `JAIR DE SOUZA FERREIRA`, `MILTON AUGUSTO DE CAMARGO`, `SUELEN`, `HERMANN RONALDO WECKE`, `HERMANN`, `RAFAEL BARROSO DE CARVALHO`

**`reserva_desejos`** — Eletrônicos, tech, compras online, alto valor:
`AMAZON MKTPLACE`, `AMAZON RETA`, `AMAZONMKTPLC`, `MP *VICTORELETRONICOS`, `AMAZON MARKETPLACE`, `AMAZON BR`, `AMAZON MARK*`, `AMAZON MKTPL`, `AMAZON COMPRA`, `APPLE.COM/US`, `GRUPO CASAS BAHIA`, `LOJAS MEL`, `SHPP BRASIL`, `DISTRIBUIDORA MENEZES`, `VIDESUL`, `TARGET LOJA`, `APPLE STORE`, `MACROBABY`, `MERCADOLIVRE`, `MAGALUPAY`, `MAGALU`, `AMZN MKTP US`, `AMAZON.COM.BR`

**`financiamentos`** — Financiamentos imobiliários:
`FINANC IMOBILIARIO`, `FINANCIAMENTO IMOBILI`

**`impostos`** — Impostos e tributos:
`DEBITO RFB`, `DAS SIMPLES`, `DARF`, `GPS INSS`, `IRPF`, `IPTU`, `IPVA`, `SIMPLES NACIONAL`, `SIMPLES NACIONA`, `RECEITA FEDERAL`, `PGTO ELET TRIB`, `PGTO TRIB`, `INT /SIMPLES`, `SECRETARIA MUNICIPAL DA FAZENDA`, `INT /PM SAO PAU`, `DA  REC FED`, `MINISTERIO DA FAZENDA`, `SECRETARIA DO TESOURO NACIONAL`

**Regras especiais:**
- `NATHALIACASADE` = Açougue Nathalia Casa de Carnes → **alimentacao** (NÃO é serviço doméstico)
- `ABDO MOHAMED` = Instituto Dr. Barakat → **saude**
- `RECEB PAGFOR GRPQA` = Aluguel QuintoAndar → **NÃO é despesa** (é receita)
- `POMPEIA MOTOS` = Venda da Yamaha MT09 → **receita_venda_ativo** (NÃO é receita PJ). Classificar como receita one-time de desinvestimento de ativo.
- `TED D HBANK` (Bradesco) = Transferência para BTG Pactual (Mariana) → **transferência interna**
- Transações com `USD` no final geralmente são gastos em viagem internacional → avaliar se `lazer_viagens` ou a categoria do estabelecimento

**Fallback**: Se a descrição não casar com nenhuma regra acima, o script E4 classifica como `nao_identificado` e registra em `logs/qa_log.md`.

### REGRAS DE CATEGORIZAÇÃO DE RECEITAS (usadas no E4)

O E4 gera `receitas-4_unified.json` agrupado por categoria. Abaixo estão as regras para classificar **créditos** (entradas) nas contas:

| Padrão no extrato (case-insensitive) | Categoria receita | Subcategoria | Conta esperada | Membro |
|---|---|---|---|---|
| `ARVO`, `DAVID ROBERT CAMARGO` (TED/PIX recebido PJ→PF) | `receita_pj` | Pró-labore Arvo | C6 PJ → C6 PF | David |
| `BRANDLOVERS`, `BRAND LOVERS` | `receita_pj` | Advisory BrandLovers | C6 PJ | David |
| `ARBITRALIS` | `receita_pj` | Advisory Arbitralis | C6 PJ | David |
| `LEARNTOFLY`, `LEARN TO FLY` | `receita_pj` | Mentoria LearnToFly | C6 PJ | David |
| `KIWIFY` | `receita_clt` | Salário CLT Kiwify (encerrado mai/2025) | Itaú Personnalité | David |
| `CNRY`, `CANARY` | `receita_pj` | CNRY/Canary (encerrado set/2025) | C6 PJ | David |
| `BARTE` | `receita_pj` | Barte Brasil (encerrado set/2025) | C6 PJ | David |
| `Sociedade Beneficente Israelita` | `receita_clt` | Salário Einstein | Poupança Bradesco | Mariana |
| `GRPQA`, `SISPAG GRPQA`, `RECEB PAGFOR GRPQA` | `receita_aluguel` | Aluguéis QuintoAndar | CC Bradesco / Itaú Personnalité | David + Mariana |
| `ALUGUEL`, `LOCACAO` (em conta CC, não em fatura cartão) | `receita_aluguel` | Aluguel direto (sem QuintoAndar) | Qualquer CC | Ambos |
| `RENDIMENTO`, `JUROS S/CAPITAL`, `DIVIDENDO` | `receita_investimento` | Rendimentos financeiros | Rico, BTG, Itaú, Santander | Ambos |
| `RESGATE`, `LIQUIDACAO` (CDB, fundo, RF) | `receita_resgate` | Resgate de investimento | Qualquer | Ambos |
| `RESTITUICAO`, `RESTIT IRPF` | `receita_restituicao` | Restituição IRPF | Qualquer CC | Ambos |
| `FGTS`, `SAQUE FGTS` | `receita_fgts` | Saque FGTS | Qualquer CC | David |
| `POMPEIA MOTOS` | `receita_venda_ativo` | Venda Yamaha MT09 | Qualquer | David |

> **Nota v5.0.1:** `CAIXA ECONOMICA` removido de `receita_fgts` (genérico demais). `RECEB PAGFOR` sem GRPQA removido de `receita_aluguel` (genérico demais).

**Regras especiais receitas:**
- Créditos PJ→PF do mesmo titular (ex: TED de C6 PJ para C6 PF David) são **transferências internas**, não receita (ver seção abaixo).
- `GRPQA` em CC Bradesco = receita aluguel Mariana. `GRPQA` em Itaú = receita aluguel David. Nunca classificar como despesa.
- Rendimentos de poupança Bradesco (créditos automáticos) = `receita_investimento`, subcategoria "rendimento poupança".

### MAPA DE TRANSFERÊNCIAS INTERNAS (usadas no E4)

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
| Kiwify (CLT, rescisão) | jun/2024–mai/2025 | R$ 407.357 |
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
| 6 | Ap | Living Concept, Av. Alberto Augusto Alves 320, Ap 812 | 25,7m² | Mariana | R$ 270k | R$ 881 | Alugado. Avaliar venda (D15, prazo 2027). Yield 3,9%, pior entre imóveis alugados. |
| 7 | — | (reservado para futuras aquisições) | — | — | — | — | — |

**Total aluguéis: R$ 9.452/mês** (David R$ 3.422 + Mariana R$ 6.030)

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

Estas fórmulas são canônicas e devem ser usadas em E4 e E5. Nunca hardcodar
valores derivados. Detalhamento por categoria em
`docs/methodology/regras_composicao_patrimonial.md` §FÓRMULAS DERIVADAS — esses dois
blocos devem evoluir juntos (incluir ambos no mesmo commit).

```
patrimonio.bruto                = cat_1 + cat_2 + cat_3 + cat_4 + cat_5 + cat_6 + cat_7
patrimonio.dividas              = SUM(dividas de cada membro no baseline)
patrimonio.liquido              = bruto − dividas

# Métrica financeira pura (Perini/AUVP) — usada em score.progresso_if
patrimonio.investivel_financeiro = cat_3 + cat_4 + cat_5 + cat_6

# Métrica total (retro-compat) — bruto excluindo bens de uso pessoal
patrimonio.investivel_total = bruto − cat_1 − cat_7
                            = cat_2 + cat_3 + cat_4 + cat_5 + cat_6
                            ⚠️ SEMPRE < bruto (se violar, há erro)

# Toggle por workspace (pipeline.json:imoveis_no_if) controla qual usar em progresso_if
patrimonio.investivel_efetivo = investivel_financeiro
                              + (cat_2 if workspace.imoveis_no_if else 0)

goals.if_pct = investivel_efetivo / if_meta_liquida × 100
goals.if_gap = MAX(0, if_meta_liquida − investivel_efetivo)
```

**Categorias da tabela patrimonial (devem somar exatamente ao bruto):**

> ⚠️ **Regras detalhadas em `docs/methodology/regras_composicao_patrimonial.md`** — o
> arquivo canônico com tabelas de matching, exemplos e validações. A tabela
> abaixo é um resumo.

| # | Categoria | Cálculo | Conta no `investivel_financeiro`? |
|---|---|---|---|
| 1 | Residência própria | IRPF → imóvel de moradia | Não |
| 2 | Imóveis investimento | SUM(ALL imoveis ALL members) − Residência. **Inclui David E Mariana.** | Toggle `imoveis_no_if` |
| 3 | Investimentos David | baseline.investimentos[] + contas_bancarias[] de tipo investimento (CDB, RDB, RF, Poupança, conta corretora). Hashdex fica aqui (fundo regulado). | Sim |
| 4 | Investimentos Mariana | baseline.investimentos[] + contas_bancarias[] de tipo investimento (mesma regra cat.3) | Sim |
| 5 | Criptoativos | Binance saldo (crypto direta: BTC, ETH, ADA, AXS etc.) — NÃO inclui fundos crypto regulados. **Sempre presente** (saldo zero ⇒ `valor: 0, pct_bruto: 0.0`). | Sim |
| 6 | Caixa + Moeda | bruto − categorias 1-5 − categoria 7 (RESIDUAL). Deve conter apenas CC puras + moeda estrangeira. Se > 5% do bruto → warning. | Sim |
| 7 | Veículos | SUM(ALL veiculos ALL members) | Não |

**Validações (bloquear geração se falhar):**
- `SUM(cat_1..cat_7) == bruto` (tolerância R$ 1,00)
- `SUM(percentuais) == 100,0%`
- `investivel_total < bruto`
- `investivel_financeiro ≤ investivel_total`
- `if_gap + investivel_efetivo == if_meta_liquida`

---

## PROCESSAMENTO DE ARQUIVOS — REGRA TÉCNICA

Todos os arquivos `.pdf` deste projeto são **PDFs reais** (não ZIPs disfarçados). A extração de dados deve usar leitura direta de PDF.

**Nota histórica:** A v4.3 assumia incorretamente que os PDFs eram ZIPs (header `PK\x03\x04`). O setup inicial de abr/2026 confirmou que isso não é o caso (QA-5 do run_log.md). Referências antigas a "desempacotar" ou "unzip" de PDFs estão obsoletas.

**Tipos de arquivo no pipeline:**
- `.pdf` — PDFs reais, leitura direta
- `.xlsx` — Planilhas (imóveis, veículos), leitura com leitor de planilhas
- `.docx` — Documentos Word (currículos), leitura com leitor DOCX
- `.jpg` — Screenshots de apps bancários, leitura com OCR/visão multimodal
