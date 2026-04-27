"""seed category_templates v1 from config/categorization.json (A7.3 · ADR-137)

Revision ID: a5b6c7d8e9f0
Revises: z4a5b6c7d8e9
Create Date: 2026-04-27

ADR-137: popula ``category_templates`` v1 com a taxonomia base do produto
oriunda de ``config/categorization.json``. Inclui:

- 16 expense categories (moradia, alimentacao, transporte, …)
- 8 income categories (receita_pj, receita_clt, …)
- 1 metadata row com ``key='__categorization_metadata__'`` carregando
  ``internal_transfer_patterns``, ``pj_source_mapping``, ``clt_source_mapping``,
  ``one_time_income_keywords``, ``one_time_income_categories``,
  ``qa_investigation_patterns`` em ``metadata_json`` — o resolver retorna
  esse blob via ``get_categorization_metadata`` quando o consumer precisa
  dos auxiliares.

Idempotente: skip silencioso se rows já existem (UNIQUE
``(template_version, key)``).
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, None] = "aa1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TEMPLATE_VERSION = 1
_METADATA_KEY = "__categorization_metadata__"

# ---------------------------------------------------------------------------
# Conteúdo histórico — derivado de ``config/categorization.json`` 2026-04-27.
# Mantido inline para imutabilidade do seed (alterações futuras → v2).
# ---------------------------------------------------------------------------

_EXPENSE_KEYWORDS: dict[str, list[str]] = {
    "moradia": [
        "ELETROPAULO", "ENEL", "CPFL", "CESP", "COMGAS", "SABESP", "SANEPAR",
        "COPASA", "CONDOMINIO", "TELHA NORTE", "DDDRIN SERVICO DE DESI",
        "DE PAULA REALTY", "APPFOLIO", "SECRETARIA MUNICIPAL", "ADMINISTRADORA",
    ],
    "financiamentos": ["FINANC IMOBILIARIO", "FINANCIAMENTO IMOBILI"],
    "alimentacao": [
        "OXXO", "SACOLAO", "MERCADO", "SAKURA", "VERDURAS E LEGUMES",
        "QUEBEC BAR", "RAMEN", "THE VIEW BAR", "GALPAO DA COSTELA",
        "EL PELEGRINO", "BAR DA JULINHA", "CANTINA", "CANTINHO DOS MINEIROS",
        "BLMT COMERCIO DE ALIME", "CARR EXPRESS", "CASA BAUDUCCO", "CASA PILAO",
        "CHAPEU DE SOL", "CHOCOLATE", "CHURRASCARIA", "DENGO", "EMPADAKI",
        "ENRICOCAFEE", "CAFETERIA", "GRAN COFFEE", "GUIMARAES ALIMENTOS",
        "IFD*", "KINDINPAESEDOCES", "LAGOS DO SUL", "LAGOSDOSUL",
        "LIKA YACEPS", "LINDT", "M A DE CARVALHO CHOCOL", "MINAS QUEIJO",
        "MILKMOO", "MILKY MOO", "MINI MERC", "MINIMART", "MOZI COMERCIO",
        "NATA ", "NATHALIACASADE", "OFNER", "PAES E DOCES", "PASTEISOSHIRO",
        "PASTELARIA", "PIRAJA COMERCIO", "QUIOSQUE CE QUE", "RDO CHOCOLATES",
        "REAL DA VILLA", "REDE CAMPEAO", "REDE OBA", "REST FRANGOASSADO",
        "RM MORUMBI", "ROP COM ALIM", "S.R. GONCALVES", "SAMS*", "SELVAGEM",
        "SODIEDOCES", "STAR CHICKEN", "TEMPERODAFE", "TOSTADO CAFE", "VEGSIM",
        "VISTA IBIRAPUERA", "YES COFFEE", "GAMBO CAFE", "BOGO CAFE",
        "NOVO - MUG", "CASA MURDOCK", "ERVA DOCE BAR", "O BADEN BADEN",
        "MORUMBI TERREO", "DON MACEDO CARNE", "JDM COMERCIO DE ALIM",
        "GUARAREMA", "KERO MAIS", "CINCO M COMERCIO", "MM CAMPO BELO",
        "BG NORTE", "DESCAMPADO", "A CASA DE ANTONIA", "MOMA MADALENA",
        "CACAPAVA", "EJM REST JAPONES", "PORTO CAIRES", "R TRES",
        "JIM.COM* MAB FOOD", "JIM.COM* UMETSU COMER", "TORRALTA",
        "TORRALTACOMERCIO", "NADIR", "PADARIA DANIELA", "BONANZA 0001",
        "MERCADINHO BONANZA", "WM SUPERCENTER", "WAL-MART", "PAO DE ACUCAR",
        "PAOACUCAR", "5M COMERCIO ATACADISTA", "CARREFOUR", "EXTRA HIPER",
        "VAI DE PIZZAS", "DOMINO'S", "CONFRARIA DO SUSHI", "KIRA SUSHI",
        "OUTBACK", "MCDONALD'S", "ALCHINGER LANCHONETE", "MOUSTACHE BEAMS",
        "LANCHONETE REAL DA VI", "LANCHONETE CAMPING", "BOTHANICO RESTAURANTE",
        "CUBO BAR E RESTAURANTE", "ARKO S RESTAURANTE", "ARKOS RESTAURANTE",
        "RESTAURANTE PAND", "SPACE SETE COM DE ALIM", "PIZZA HUT",
        "DEL NERO E MIRANDEZ", "EMPORIO PAES", "EMPORIO PINHEIROS",
        "PADARIA SANTA MARINA", "PADARIA FAMA", "CAFE DAS COISINHAS",
        "HORTIFRUTIRUI", "GRAAL MARKET", "PRODUTOS NATURAIS",
        "RJB ACAI E TAPIOCA", "BOBBY'S BURGERS", "METRO PIZZA",
        "CARRINHO DO DUDA", "AMO AV MORUMBI DRIVE", "RAPPI*RAPPI BRASIL INT",
        "RAPPI *RAPPI RAPPI BR", "RAPPI BRASIL INTERMEDI", "DL *DLRAPPI BR",
        "DL*DLRAPPI BR", "DL *DLRAPPIPROBR", "EJM RESTAURANTE JAPONE",
        "PAYGO*LG ESPETOS", "POINTJABAQUARA", "M L MATOS CONVENIENCIA",
        "EMPORIOMATTERLTDA", "SAMS CLUB", "SAM'S CLUB", "FIVE GUYS",
        "TEXAS ROADHOUSE", "GHIRARDELLI", "BEN JERRY", "HAAGEN-DAZS",
        "WICKED LICK", "PARMUKH CORNER", "PAG*MERCADINHOBONANZA", "DJAPA",
        "RAPPI  *RAPPI * BRASI", "RAPPI*RAPPI BRASIL",
    ],
    "transporte": [
        "PARK", "AUTOPOSTO", "AUTOPOSTOKANTAN", "ULTRAGAS",
        "CONCESSIONARIA SPMAR", "CARRETEIRO REV", "PUNTO *PRIME AUTO",
        "ECOPISTA", "FELTRIN MOTOS", "FELTRIN", "INT LICENC", "FELTRIN",
        "INT LICENC SP", "MEGAPASS", "MC MOBILITY", "MCOUTINHO MOBILITY",
        "EXXON AUTOMATED", "BANDEIRA PAULISTA PAR", "AUTOVAGAS",
        "MARANATA SERVICOS DE G", "CORREA CONVENIENCIA", "MULTA DE VEICULO",
        "MULTA VEICULO", "DETRAN", "LICENCIAMENTO DE VEICULO",
        "LICENCIAMENTO VEICULO", "PRIME AUTO POSTO", "AUTO POSTO", "MINUTO PA",
        "SHELL PO", "SHELL MI", "POSTO SHELL", "POSTO LIDER",
        "ML20 IMIGRANTES AUTO", "RACETRAC", "WAWA", "EXXON", "ARCO #",
        "CIRCLE K", "SUNOCO", "C6TAG PEDAGIO", "C6TAG", "TAPECAR", "TURO INC",
        "UBER *TRIP", "UBER UBER *TRIP", "LYFT", "CAMPEAO 28 POSTOS",
        "POSTO ACACIAS", "POSTO CARIJO", "POSTO PAIN", "TURISMOIIPOSTODE",
        "A POSTO PLATINO", "AUTO POSTO GALENA", "AUTO POSTO PARQUE JAB",
        "AUTO POSTO IRMAOS", "AUTO POSTO GUACU", "AUTO POSTO SONIMAR",
        "AUTO POSTO ROTA", "ESTACIONAMENTO MODELO", "AN ESTACIONAMENTO",
        "MMW ESTACIONAMENTOS", "ESTAC T*ESTACIONAMENT", "LTL ESTACIONAMENTO",
        "MP *ESTACIONAMENT", "CITY OF CLEARWATER PAR", "CITY OF ORLANDO PKG",
        "F.M ESTETICA AUTOMOTIV", "MAIS DISTR VEICULOS", "PROPIG *FPS BATERIAS",
        "MOTO DAKAR", "MULTA DE VE", "PAG MULTA", "LICENCIAMENTO DE VE",
        "PAG LICENCIAMENTO", "PAGTO LICENCIAMENTO", "ENTERPRISE RENT",
        "LOCALIZA RAC", "LOCALIZA RENT", "MAIS DISTRIB VEICULOS",
    ],
    "assinaturas": [
        "WELLHUB", "GYMPASS", "AMAZONPRIMEBR", "GLOBO*GLOBOPLAY",
        "GLOBO GLOBOPLAY", "GOOGLE *DUOLINGO", "SURFSHARK", "PAYPAL *RESCUETIME",
        "PAYPAL *CLEVERBRIDG", "EBN *SONYPLAYSTATN", "PADDLE.NET*",
        "REGISTROBR", "EC *MELIMAIS", "MP *MELIMAIS", "PRODUTOS GLOBO",
        "SP FLIPPER DEVICES", "ASSOCIATION FOR COMPUT", "TELEFONE CELULAR VIVO",
        "VIVO MOVEL", "CONTA TELEFONE", "CLARO CELULAR", "TIM CELULAR",
        "NET SERVICOS", "DM *SPOTIFY", "DM*SPOTIFY", "EBN *SPOTIFY",
        "GOOGLE *GOOGLE ONE", "APPLE.COM/BILL", "APPLECOMBILL",
        "AMAZON PRIME ALUGUEL", "AMAZON PRIME*", "CLUBE LIVELO*CLUBE LIV",
        "LIVELO*CLUBE LIVELO", "CLUBE LIVELO", "LIVELO S.A.", "SMILES CLUB",
        "ESFERA", "1PASSWORD*", "LINKEDIN", "WIX.COM", "GOOGLE *TELEGRAM",
        "GOOGLE *GOOGLE NEST", "SQSP*", "SCP COMPLETO", "SCP BASICO",
        "BRASILP*BRASILPARA", "BRASIL PARAL*BRAS", "GOOGLE FI", "GOOGLE *FI",
        "FREEPIK", "MIDJOURNEY", "CANVA", "WIX", "FIBRA",
    ],
    "saude": [
        "CORPO E VIDA", "REMEDIOPOPULAR", "NUTRA BODY", "MP *FARMAPOPULAR",
        "SCRIPTS PHARMACY", "CAMILANAKAMURA", "POUPA MEDI", "EINSTEIN MORUMBI",
        "HOSPITAL ALBERT EINSTE", "CLINICA DERMATOLOGICA", "INSTITUTO DR BARAKAT",
        "PDV*BARA CLINICA", "ABDO MOHAMED", "BRENTESINSTITUTO",
        "FISIOTERAPIA BEBE EIRE", "PELVIE FISIOTERAPIA", "INST TADEU CVINTAL",
        "AWADA ESTETICA", "DROGASIL", "DROGARIA SAO PAULO",
        "DROGARIA_SP DROGARIASA", "DROGARIA ONLINE", "DROGARIA GUARANI",
        "DROGARIA CRUZEIRO", "DROGARIA CARREFOUR", "RDSAUDE ONLINE",
        "DPS SUPLEMENTOS", "RAIA", "MARCONI BASSO", "DROGARIA X FARMACIA",
        "PG *LIVANCE", "ESPACO GIRAS", "IU65 PREMIUM", "CVS/PHARMACY",
        "PT *ORL HLTH PYMT", "HT SARAGIOTTO SERVICOS MEDICOS", "LUMMA ROBERTA",
        "HELEN SASAKE TAKAGI", "FULL FACE MEDIC", "CONCAVO E CONVEXO",
        "PACEFIT", "MOURA ACADEMIA", "RAPPI *DROGARIA SAO P", "RAPPI*RAIA DROGASIL",
        "DROGASI", "CLIMEFE", "SER MED",
    ],
    "seguros": [
        "SUL AMERICA SEG", "MENSALIDADE DE SEGURO", "PORTO SEGURO SEGUROS",
        "TOKIO MARINE", "SEGURO CONTA C6",
    ],
    "vestuario": [
        "I. M. SATO VESTUARIO", "LUANA FASHION", "VICIO FEMININO", "CARTERS",
        "KIKO MILANO", "PITICAS", "BAYARD ESPORTES", "EMY PERFUMARIA",
        "SONEDA PERFUMARIA", "ITRCCABELEIREIROS", "LOJA OFICIAL",
        "TATIANA GIORDANO", "VIVARA", "CHILLI BEANS", "THENORTHFACE",
        "ROSS STORES", "OTICAS RB1", "IGUASPORT", "GREAT CLIPS", "T J MAXX",
        "UNDER ARMOUR", "SEPHORA", "COLUMBIA 452", "VICTORIA'S SECRET",
        "BURLINGTON STORES", "GAP OUTLET", "MICHAEL KORS", "TNF ",
        "HNA*OBOTICARIO", "LUSH",
    ],
    "lazer_viagens": [
        "AIRBNB", "SEAWORLD", "BUSCH GARDENS", "PORTO DUTY FREE", "TERMINAL III",
        "RESORT FLORIDA", "DISNEY RESORT", "BOUTIQUE MIAMI",
        "RESTAURANTE ORLANDO", "HN HUDSON", "WEATHERSTATION", "WDW DROID DEPOT",
        "NIC*-DOH ORA VITAL", "MINUTE SUITES", "ZIG*VILLA DI PHOENIX",
        "ZIG. THE GLOBAL FUNTEC", "A NOIESA", "AEROP. ADOLFO SUAREZ",
        "ASSOC COMERCIAL PORT", "AUDASA VISA", "CATEDRAL DE SANTIAGO",
        "CHEZ LAPIN", "CPPB-RUA AUGUSTA", "FUNDACAO CULTURSINTR",
        "MANTEIGARIA SILVA", "ATL PANDA EXPRESS", "FAST POINT MC", "DOLLAR TREE",
        "AMAZON GROCERY", "AMAZON TIPS", "AIR EUROPA", "LATAM AIR",
        "LATAM AIRLINES", "AMERICAN AIR*", "HOTEL AT BOOKING.COM", "HOTEIS.COM",
        "BKG*BOOKING.COM", "HOTELCOM", "SAN FRANCISCO HOTEL", "S F FLAT HOTEL",
        "HOTEL MUNDIAL", "HOTEL PORTO JARDIM", "THE PLATINUM HOTEL", "DOLLAR RAC",
        "NVE*RENTCARSLTDA", "HERTZ CAR RENTAL", "WDW TICKETS", "UNIVERSAL ORLANDO",
        "HUDSON NEWS", "SUNDRY SHOP", "PRIP MART", "AREAS PORTUGAL",
        "CBD MARTIM", "SP BAG OF SALT", "VENETIAN STARBUCKS", "FEVER*",
        "TARGET T-", "LOJAS AMERICANAS", "PLAZA SUL", "ALIANSCE",
        "SHOPPING CENTER IBIRAP", "PARQUE RIBEIRA", "BOFT BRASIL",
        "FURY ADVENTURES", "UNIVERSAL STORE", "BISUTTI", "PLATAFORMA S*BISUTTI",
        "PLATAFORMA S BISUTTI", "ICASEI", "NUVEM CUTELARIAORI", "CLEIDIANY",
        "CHEESECAKE ORLANDO", "HOB CLUB ORLANDO", "FORDS GARAGE",
        "TOOTHSOME CHOC", "ORLANDO PREM OUTL", "ORLANDO PREMIUM OUTL",
        "LEVI'S OUTLET", "DD'S DISCOUNT", "POPSHELF", "PUBLIX", "CHITOWN LOCK",
        "USCES LLC", "BREEZA BEACHWEAR", "CITY OF MIAMI BEACH",
        "CHILDRENS PLACE", "THE CHILDRENS PLACE", "SHELL OIL", "WALGREENS",
        "STARBUCKS STORE", "MACY", "WDW", "CARTER'S", "IONE GIAMBRUNI",
        "GETYOURGUIDE", "EURO DISNEY", "AGAXTUR", "HOTELSCOM", "HOTELS.COM",
        "HOTELS COM", "LE CESAR HOTEL", "MONOPRIX", "SNCF", "RATP",
        "COFIROUTE", "AUTOROUTE", "SANEF", "INDIGO07", "LISBON DUTY FREE",
        "SPECIALLY AEROPORTO", "BIGLIETTERIAMUSEI", "LEGO STORE DISNEY",
        "KEOLIS MONT", "ETS NICOLAS", "LE RECRUTEMENT", "TOTAL MKT FR",
        "HEADOUTEURO", "SNC SIRIUS", "SAPN", "LIS 8327", "AGF CABINES",
        "DECATHLON", "PARAISO AGENCIA", "LATAM SITE", "SIMON & SONS",
        "BISTROT PULCINELLA", "DUFRITAL", "VE.LA. S.P.A", "ANTICO CAFFE",
        "DANIEL MURANO", "TRATTORIA AL PANTHEON", "ARBOGEL SAS",
        "FABBRICA DI SAN PIE", "MERCATO CENTRALE", "AGO & LILLO", "HOTEL ARTDECO",
        "A D S BADIA NUOVA", "RIVA DEL VIN", "FABRIS LEDA", "MASSENZIO AI FORI",
        "FCO1", "HARD ROCK CAFE ITALY", "MUSEO PALAZZO VECCHIO", "BAR POLIZIANA",
        "MOLESKINE SRL", "FELICE 2", "BAR AL CAMPANILE", "MUOVIAMO PARKING",
        "HOTEL SAN LUCA", "NON SOLO VETRO", "VINOVIP SRL", "HOTEL PERSEO",
        "GINO S BAKERY", "ASPIT VENEZIA", "LA BOTTEGA DEL TARTUFO",
        "ALBA VENETA", "MC DONALD'S SPAGNA", "AUTOGRILL", "FLORENCE LEATHER",
        "BRICIOLE AEROPORTO", "BOOKSHOP MERCATI", "TUTTO DI NAPOLI",
        "ASPIT ROMA", "MUSEI VATICANI", "CASSA AUTOMATICA BASIL",
        "G.MARCATO SNC", "DITTA ERMENEGILDO", "GRAN CAFFE LAGUNA",
        "LA BOTTEGA DI GIOTTO", "GIUNTI EDITORE", "FOOD COURT IMBARCHI",
        "SILVESTRI SIMONE", "F611 RISTOP", "GEDAC SRL", "DUFRY LOJAS FRANCAS",
        "ITALIA TR", "STUDIO DANSOU",
    ],
    "melhoria_reforma": [
        "JS MATERIAIS DE CONS", "ANDRA MATERIAIS", "FUTURA MADEIRAS",
        "DEPOSITO CENTER", "DEPOSITO GUARANI", "ROSSE COMERCIO",
        "ELETTRICA COMERCIO", "CONILREM", "DAISO BRASIL", "SILETRICA",
        "ELETTRICA", "ELIAS PAIVA", "REINALDO MARTINS", "INACIO JOSE MACEDO",
        "INACIO JOSE", "MATEUS SOUZA ARCANJO", "MANOEL MESSIAS", "LEROY MERLIN",
        "VESALTEC",
    ],
    "educacao": [
        "LEITURA", "KALUNGA", "COPICOPIAS", "PAPELARIA", "PRIMO RICO",
        "FUNDACAO SAO PAULO", "ANDERSON UNIVERS", "HARVARD BUS", "PERUSALL",
        "BELT ACADEMY", "CONSELHO REGIONAL", "OPEN ENGLISH",
    ],
    "servicos_domesticos": [
        "SUECIA", "ELIANE", "ANDREA S LAVANDERIA", "PET DOGSTORE",
        "JIM COM* LAVARAPIDO", "JIM.COM* LAVARAPIDO", "COBASI", "PETZ",
        "RAPPI*PET CENTER", "ELAINE APARECIDA BUZZ", "RK2LAVARAPIDOE", "4MS",
        "SAMUELABNERSANTOSMARC", "MP *33798933SAMUELABN", "ANA LUCIA SANTOS",
        "GUIA DE EMPREGADO DOMESTICO", "PAG*PETCENTERCOMERCIO",
    ],
    "financeiro": [
        "VINDI *ACCOUNTBANKTEC", "PAYPAL *DOCUSIGNINC", "IOF CHEQUE ESPECIAL",
        "IOF", "TARIFA", "JUROS LIMITE DA CONTA", "JUROS CHEQUE ESP",
        "JUROS SALDO UTILIZ", "JUROS LIMITE", "JUROS UTILIZ", "TAR PACOTE",
        "TAXA PERMANENCIA", "ANUIDADE DIFERENCIADA", "IOF DESPESA NO EXTERIOR",
        "Anuidade Diferenciada", "Multa Contratual", "Juros de Mora", "Encargos",
        "D4U IMMIGRATION", "D4U", "MORAR EUA", "IN *CA TRANSLATION SER",
        "TABEL", "CLAUDIA DANTAS TINOCO",
    ],
    "impostos": [
        "DEBITO RFB", "DAS SIMPLES", "DARF", "GPS INSS", "IRPF", "IPTU", "IPVA",
        "SIMPLES NACIONAL", "SIMPLES NACIONA", "RECEITA FEDERAL",
        "PGTO ELET TRIB", "PGTO TRIB", "INT /SIMPLES",
        "SECRETARIA MUNICIPAL DA FAZENDA", "INT /PM SAO PAU", "DA  REC FED",
        "MINISTERIO DA FAZENDA", "SECRETARIA DO TESOURO NACIONAL",
    ],
    "suporte_familiar": [
        "ALO BEBE", "ICA*ICASEI", "MAKOS LEMBRANCAS", "RUBENS DE CAMPOS",
        "PIX TRANSF RUBENS", "NEUSA CIMAR TEIXEIRA", "NEUSA CIMAR",
        "DOUGLAS CAMARGO DE CAMPOS", "ERIC VINICIUS",
        "SHEILA APARECIDA DA ROCHA DE CAMARGO", "JAIR DE SOUZA FERREIRA",
        "MILTON AUGUSTO DE CAMARGO", "SUELEN", "HERMANN RONALDO WECKE",
        "HERMANN", "RAFAEL BARROSO DE CARVALHO",
    ],
    "reserva_desejos": [
        "AMAZON MKTPLACE", "AMAZON RETA", "AMAZONMKTPLC",
        "MP *VICTORELETRONICOS", "AMAZON MARKETPLACE", "AMAZON BR",
        "AMAZON MARK*", "AMAZON MKTPL", "AMAZON COMPRA", "APPLE.COM/US",
        "GRUPO CASAS BAHIA", "LOJAS MEL", "SHPP BRASIL", "DISTRIBUIDORA MENEZES",
        "VIDESUL", "TARGET LOJA", "APPLE STORE", "MACROBABY", "MERCADOLIVRE",
        "MAGALUPAY", "MAGALU", "AMZN MKTP US", "AMAZON.COM.BR",
    ],
}

_INCOME_KEYWORDS: dict[str, list[str]] = {
    "receita_pj": [
        "ARVO", "BRANDLOVERS", "BRAND LOVERS", "BRANDLOVRS", "ARBITRALIS",
        "LEARNTOFLY", "LEARN TO FLY", "CNRY", "CANARY", "BARTE", "LEARNTOEIV",
    ],
    "receita_clt": [
        "SOCIEDADE BENEFICENTE ISRAELITA", "KIWIFY", "SALÁRIO DEPOSITO",
        "SALARIO DEPOSITO", "*3221", "tr Sal p/poup",
    ],
    "receita_aluguel": [
        "GRPQA", "SISPAG GRPQA", "RECEB PAGFOR GRPQA", "ALUGUEL", "LOCACAO",
    ],
    "receita_investimento": [
        "RENDIMENTO", "JUROS S/CAPITAL", "JUROS S/ CAPITAL", "DIVIDENDO",
        "RENT.INV.FACIL", "RENDIMENTO DISPONIVEL", "RENDIMENTO DE CONTA",
        "CUPOM - CRA", "CUPOM - CRI", "REND PAGO APLIC", "FRACOES DE ACOES",
        "SALDO INVEST FÁCIL", "SALDO INVEST FACIL", "LIQ BOLSA",
    ],
    "receita_resgate": [
        "RESGATE", "LIQUIDACAO", "RESGL/VENCTO CDB", "RESGL/VENCTO",
    ],
    "receita_venda_ativo": ["POMPEIA MOTOS"],
    "receita_restituicao": ["RESTITUICAO", "RESTIT IRPF", "DEVOLUCAO PIX"],
    "receita_fgts": ["FGTS", "SAQUE FGTS"],
}

_LABELS: dict[str, str] = {
    "moradia": "Moradia",
    "financiamentos": "Financiamentos",
    "alimentacao": "Alimentação",
    "transporte": "Transporte",
    "assinaturas": "Assinaturas",
    "saude": "Saúde",
    "seguros": "Seguros",
    "vestuario": "Vestuário",
    "lazer_viagens": "Lazer & Viagens",
    "melhoria_reforma": "Melhoria & Reforma",
    "educacao": "Educação",
    "servicos_domesticos": "Serviços Domésticos",
    "financeiro": "Financeiro",
    "impostos": "Impostos",
    "suporte_familiar": "Suporte Familiar",
    "reserva_desejos": "Reserva & Desejos",
    "receita_pj": "Receita PJ",
    "receita_clt": "Receita CLT",
    "receita_aluguel": "Receita Aluguel",
    "receita_investimento": "Receita Investimento",
    "receita_resgate": "Receita Resgate",
    "receita_venda_ativo": "Receita Venda de Ativo",
    "receita_restituicao": "Receita Restituição",
    "receita_fgts": "Receita FGTS",
}

_AUX_METADATA: dict[str, Any] = {
    "internal_transfer_patterns": [
        "bx Aut Poupanca", "Transf p/ Poupanca", "Apl.invest Fac", "Apl.invest",
        "Aplicacao CDB", "Resgate Inv Fac", "Resgate CDB", "COMPRA - CRA",
        "COMPRA DE NTNB", "COMPRA DE LFT", "COMPRA DE NTN", "COMPRA DE LCI",
        "COMPRA DE LCA", "DEBITO MARGEM", "Cambio", "Ted Dif.litud",
        "Pagto Cobranca", "Pagamento de fatura", "ITAU VISA ITAUCARD",
        "FAT.CARTAO MASTER", "FAT.CARTAO VISA", "FAT CARTAO", "PGTO CARTAO",
        "Debito de Cartao", "Inclusao de Pagamento", "Gasto c Credito",
        "DEB AUTOM DE FATURA", "RECEBIMENTO TRANSFERENCIA", "RECEBIMENTO DE TED",
        "Dinheiro adicionado à conta", "Dinheiro adicionado a conta",
        "Transf C6 Conta Global", "bx Aut Cta Cor",
        "Reserva - Seu dinheiro guardado rende", "PAGAMENTO CARTAO CREDITO",
        "SALDO DO DIA", "TRANSFERENCIA INTERNACIONAL", "TRANSFERENCIA PESSOAL",
        "Total - Os dados aci", "PIX QRS WISE", "WISE BRASIL", "INT ITAU VISA",
        "01-FIN VENDA", "Transf. Internacional", "PIX TRANSF Poupa",
        "EMISSAO DE CDB", "INT TED",
    ],
    "pj_source_mapping": {
        "ARVO": "Arvo (David - PJ)",
        "BRANDLOVERS": "BrandLovers (David - PJ)",
        "BRAND LOVERS": "BrandLovers (David - PJ)",
        "BRANDLOVRS": "BrandLovers (David - PJ)",
        "ARBITRALIS": "Arbitralis (David - PJ)",
        "LEARNTOFLY": "Learn To Fly (David - PJ)",
        "LEARN TO FLY": "Learn To Fly (David - PJ)",
        "CNRY": "CNRY (David - PJ)",
        "CANARY": "CNRY (David - PJ)",
        "BARTE": "Barte (David - PJ)",
        "LEARNTOEIV": "LearnToEiv (David - PJ)",
    },
    "clt_source_mapping": {
        "KIWIFY": "Kiwify (David - CLT)",
        "SOCIEDADE BENEFICENTE ISRAELITA": "Einstein (Mariana - CLT)",
        "3221": "Einstein (Mariana - CLT)",
        "tr Sal p/poup": "Einstein (Mariana - CLT)",
    },
    "one_time_income_keywords": [
        "kiwify", "fgts", "restituicao", "bolsa", "bonus", "pompeia", "venda",
    ],
    "one_time_income_categories": [
        "receita_venda_ativo", "receita_resgate", "receita_fgts",
        "receita_restituicao",
    ],
    "qa_investigation_patterns": [
        {"pattern": "ZS RES PREMI",
         "note": "Investigar — possível resgate de prêmio de seguro ou programa de pontos Santander."}
    ],
}


def upgrade() -> None:
    if context.is_offline_mode():
        op.execute(
            "-- A7.3 seed (category_templates v1) skipped in offline mode; "
            "run via online migration on target DB."
        )
        return

    template_table = sa.table(
        "category_templates",
        sa.column("id", sa.String),
        sa.column("template_version", sa.Integer),
        sa.column("key", sa.String),
        sa.column("parent_key", sa.String),
        sa.column("label", sa.String),
        sa.column("category_type", sa.String),
        sa.column("default_keywords", sa.JSON),
        sa.column("default_monthly_cap_brl_cents", sa.BigInteger),
        sa.column("sort_order", sa.Integer),
        sa.column("metadata_json", sa.JSON),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    existing_keys = _query_existing_keys()
    rows = list(_build_seed_rows(existing_keys))
    if rows:
        op.bulk_insert(template_table, rows)


def _build_seed_rows(existing_keys: set[str]):
    now = datetime.now(timezone.utc)
    sort_order = 0
    for key, keywords in _EXPENSE_KEYWORDS.items():
        if key in existing_keys:
            sort_order += 1
            continue
        yield _row(key, "expense", keywords, sort_order, now)
        sort_order += 1
    for key, keywords in _INCOME_KEYWORDS.items():
        if key in existing_keys:
            sort_order += 1
            continue
        yield _row(key, "income", keywords, sort_order, now)
        sort_order += 1
    if _METADATA_KEY not in existing_keys:
        yield _metadata_row(now)


def _row(
    key: str,
    category_type: str,
    keywords: list[str],
    sort_order: int,
    now: datetime,
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "template_version": _TEMPLATE_VERSION,
        "key": key,
        "parent_key": None,
        "label": _LABELS.get(key, key.replace("_", " ").title()),
        "category_type": category_type,
        "default_keywords": list(keywords),
        "default_monthly_cap_brl_cents": None,
        "sort_order": sort_order,
        "metadata_json": {},
        "created_at": now,
        "updated_at": now,
    }


def _metadata_row(now: datetime) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "template_version": _TEMPLATE_VERSION,
        "key": _METADATA_KEY,
        "parent_key": None,
        "label": "(metadata reservada — não exibir)",
        "category_type": "expense",
        "default_keywords": [],
        "default_monthly_cap_brl_cents": None,
        "sort_order": 9999,
        "metadata_json": _AUX_METADATA,
        "created_at": now,
        "updated_at": now,
    }


def _query_existing_keys() -> set[str]:
    try:
        bind = op.get_bind()
        return {
            r[0]
            for r in bind.execute(
                sa.text(
                    "SELECT key FROM category_templates WHERE template_version = :v"
                ),
                {"v": _TEMPLATE_VERSION},
            ).fetchall()
        }
    except (AttributeError, Exception):
        return set()


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM category_templates WHERE template_version = :v"
        ),
        {"v": _TEMPLATE_VERSION},
    )
