#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E4 Categorization Stage — Deterministic Transaction Categorization
Reads E3 reconciled files and produces unified E4 output files.

This stage:
1. Reads all *-3_reconciled.json files from processed/E3_reconciled/
2. Reads baseline patrimonio from E2 extracts
3. Applies keyword-based categorization rules (hardcoded from definitions.md)
4. Detects internal transfers and excludes them
5. Generates 7 unified JSON output files to processed/E4_unified/

Author: Claude
Date: 2026-04-05
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


# ============================================================================
# KEYWORD CATEGORIZATION RULES (from definitions.md)
# ============================================================================

EXPENSE_KEYWORDS = {
    "moradia": [
        # Financiamento imobiliário (definitions.md: "financ imobiliário → moradia")
        "FINANC IMOBILIARIO", "FINANCIAMENTO IMOBILI",
        # Utilities (água, luz, gás)
        "ELETROPAULO", "ENEL", "CPFL", "CESP", "COMGAS",
        "SABESP", "SANEPAR", "COPASA",
        # Condomínio
        "CONDOMINIO",
    ],
    "alimentacao": [
        "OXXO", "SACOLAO", "MERCADO", "SAKURA", "VERDURAS E LEGUMES", "QUEBEC BAR",
        "RAMEN", "THE VIEW BAR", "GALPAO DA COSTELA", "EL PELEGRINO", "BAR DA JULINHA",
        "CANTINA", "CANTINHO DOS MINEIROS", "BLMT COMERCIO DE ALIME", "CARR EXPRESS",
        "CASA BAUDUCCO", "CASA PILAO", "CHAPEU DE SOL", "CHOCOLATE", "CHURRASCARIA",
        "DENGO", "EMPADAKI", "ENRICOCAFEE", "CAFETERIA", "GRAN COFFEE",
        "GUIMARAES ALIMENTOS", "IFD*", "KINDINPAESEDOCES", "LAGOS DO SUL", "LAGOSDOSUL",
        "LIKA YACEPS", "LINDT", "M A DE CARVALHO CHOCOL", "MINAS QUEIJO", "MILKMOO",
        "MILKY MOO", "MINI MERC", "MINIMART", "MOZI COMERCIO", "NATA ", "NATHALIACASADE",
        "OFNER", "PAES E DOCES", "PASTEISOSHIRO", "PASTELARIA", "PIRAJA COMERCIO",
        "QUIOSQUE CE QUE", "RDO CHOCOLATES", "REAL DA VILLA", "REDE CAMPEAO", "REDE OBA",
        "REST FRANGOASSADO", "RM MORUMBI", "ROP COM ALIM", "S.R. GONCALVES", "SAMS*",
        "SELVAGEM", "SODIEDOCES", "STAR CHICKEN", "TEMPERODAFE", "TOSTADO CAFE",
        "VEGSIM", "VISTA IBIRAPUERA", "YES COFFEE", "GAMBO CAFE", "BOGO CAFE",
        "NOVO - MUG", "CASA MURDOCK", "ERVA DOCE BAR", "O BADEN BADEN", "MORUMBI TERREO",
        "DON MACEDO CARNE", "JDM COMERCIO DE ALIM", "GUARAREMA", "KERO MAIS",
        "CINCO M COMERCIO", "MM CAMPO BELO", "BG NORTE", "DESCAMPADO", "A CASA DE ANTONIA",
        "MOMA MADALENA", "CACAPAVA", "EJM REST JAPONES", "PORTO CAIRES", "R TRES",
        "JIM.COM* MAB FOOD", "JIM.COM* UMETSU COMER", "TORRALTA", "TORRALTACOMERCIO", "NADIR"
    ],
    "transporte": [
        "PARK", "AUTOPOSTO", "AUTOPOSTOKANTAN", "ULTRAGAS", "CONCESSIONARIA SPMAR",
        "CARRETEIRO REV", "PUNTO *PRIME AUTO", "ECOPISTA", "FELTRIN MOTOS",
        "MEGAPASS", "MC MOBILITY", "MCOUTINHO MOBILITY", "EXXON AUTOMATED",
        "BANDEIRA PAULISTA PAR", "AUTOVAGAS", "MARANATA SERVICOS DE G", "CORREA CONVENIENCIA",
        # Multas e licenciamento
        "MULTA DE VEICULO", "MULTA VEICULO", "DETRAN",
        "LICENCIAMENTO DE VEICULO", "LICENCIAMENTO VEICULO",
    ],
    "assinaturas": [
        "WELLHUB", "GYMPASS", "AMAZONPRIMEBR", "GLOBO*GLOBOPLAY", "GLOBO GLOBOPLAY",
        "GOOGLE *DUOLINGO", "SURFSHARK", "PAYPAL *RESCUETIME", "PAYPAL *CLEVERBRIDG",
        "EBN *SONYPLAYSTATN", "PADDLE.NET*", "REGISTROBR", "EC *MELIMAIS", "MP *MELIMAIS",
        "PRODUTOS GLOBO", "SP FLIPPER DEVICES", "ASSOCIATION FOR COMPUT",
        # Telecomunicações
        "TELEFONE CELULAR VIVO", "VIVO MOVEL", "CONTA TELEFONE",
        "CLARO CELULAR", "TIM CELULAR", "NET SERVICOS",
    ],
    "saude": [
        "CORPO E VIDA", "REMEDIOPOPULAR", "NUTRA BODY", "MP *FARMAPOPULAR",
        "SCRIPTS PHARMACY", "CAMILANAKAMURA", "ABDO MOHAMED",
        # Planos de saúde
        "POUPA MEDI",
    ],
    "seguros": [
        "SUL AMERICA SEG",
        "MENSALIDADE DE SEGURO",
    ],
    "vestuario": [
        "I. M. SATO VESTUARIO", "LUANA FASHION", "VICIO FEMININO", "CARTERS",
        "KIKO MILANO", "PITICAS", "BAYARD ESPORTES", "EMY PERFUMARIA", "SONEDA PERFUMARIA",
        "ITRCCABELEIREIROS", "LOJA OFICIAL", "TATIANA GIORDANO"
    ],
    "lazer_viagens": [
        "AIRBNB", "SEAWORLD", "BUSCH GARDENS", "PORTO DUTY FREE", "TERMINAL III",
        "HN HUDSON", "WEATHERSTATION", "WDW DROID DEPOT", "NIC*-DOH ORA VITAL",
        "MINUTE SUITES", "ZIG*VILLA DI PHOENIX", "ZIG. THE GLOBAL FUNTEC", "A NOIESA",
        "AEROP. ADOLFO SUAREZ", "ASSOC COMERCIAL PORT", "AUDASA VISA", "CATEDRAL DE SANTIAGO",
        "CHEZ LAPIN", "CPPB-RUA AUGUSTA", "FUNDACAO CULTURSINTR", "MANTEIGARIA SILVA",
        "ATL PANDA EXPRESS", "FAST POINT MC", "DOLLAR TREE", "AMAZON GROCERY", "AMAZON TIPS"
    ],
    "melhoria_reforma": [
        "JS MATERIAIS DE CONS", "ANDRA MATERIAIS", "FUTURA MADEIRAS", "DEPOSITO CENTER",
        "DEPOSITO GUARANI", "ROSSE COMERCIO", "ELETTRICA COMERCIO", "CONILREM", "DAISO BRASIL"
    ],
    "educacao": [
        "LEITURA", "KALUNGA", "COPICOPIAS", "PAPELARIA"
    ],
    "servicos_domesticos": [
        "SUECIA", "ELIANE", "ANDREA S LAVANDERIA", "PET DOGSTORE",
        "JIM COM* LAVARAPIDO", "JIM.COM* LAVARAPIDO"
    ],
    "financeiro": [
        "VINDI *ACCOUNTBANKTEC", "PAYPAL *DOCUSIGNINC",
        # Juros e taxas bancárias
        "IOF CHEQUE ESPECIAL", "IOF", "TARIFA",
        "JUROS LIMITE DA CONTA", "JUROS CHEQUE ESP", "JUROS SALDO UTILIZ",
        "JUROS LIMITE", "JUROS UTILIZ",
        "TAR PACOTE", "TAXA PERMANENCIA",
    ],
    "impostos": [
        "DEBITO RFB", "DAS SIMPLES", "DARF", "GPS INSS", "IRPF", "IPTU", "IPVA",
        "SIMPLES NACIONAL", "SIMPLES NACIONA",
        # Pagamentos tributários
        "RECEITA FEDERAL", "PGTO ELET TRIB", "PGTO TRIB",
        "INT /SIMPLES",
    ],
    "suporte_familiar": [
        "ALO BEBE", "ICA*ICASEI", "MAKOS LEMBRANCAS", "RUBENS DE CAMPOS",
        "PIX TRANSF RUBENS",
    ],
    "reserva_desejos": [
        "AMAZON MKTPLACE", "AMAZON RETA", "AMAZONMKTPLC", "MP *VICTORELETRONICOS"
    ]
}

INCOME_KEYWORDS = {
    "receita_pj": [
        "ARVO", "DAVID ROBERT CAMARGO", "BRANDLOVERS", "BRAND LOVERS",
        "ARBITRALIS", "LEARNTOFLY", "LEARN TO FLY", "KIWIFY", "CNRY", "CANARY", "BARTE"
    ],
    "receita_clt": [
        "SOCIEDADE BENEFICENTE ISRAELITA"
    ],
    "receita_aluguel": [
        "GRPQA", "SISPAG GRPQA", "RECEB PAGFOR GRPQA", "ALUGUEL", "LOCACAO"
    ],
    "receita_investimento": [
        "RENDIMENTO", "JUROS S/CAPITAL", "DIVIDENDO", "RENT.INV.FACIL",
        "RENDIMENTO DISPONIVEL", "RENDIMENTO DE CONTA"
    ],
    "receita_resgate": [
        "RESGATE", "LIQUIDACAO"
    ],
    "receita_restituicao": [
        "RESTITUICAO", "RESTIT IRPF"
    ],
    "receita_fgts": [
        "FGTS", "CAIXA ECONOMICA"
    ]
}

# Internal transfer detection patterns
# These are CLEARLY internal (between family accounts or investment applications)
# PIX/TED to third parties are NOT transfers — they're expenses or nao_identificado
INTERNAL_TRANSFER_PATTERNS = [
    # Poupança sweeps
    "bx Aut Poupanca",          # Bradesco CC ↔ Poupança auto sweep
    "Transf p/ Poupanca",       # Transfer to poupança
    # Investment applications/redemptions
    "Apl.invest Fac",           # Investment application (Bradesco)
    "Apl.invest",               # Investment application
    "Aplicacao CDB",            # CDB application
    "Resgate Inv Fac",          # Investment redemption (Bradesco)
    "Resgate CDB",              # CDB redemption
    # Investment purchases (renda fixa, renda variável)
    "COMPRA - CRA",             # CRA (Certificado de Recebíveis do Agronegócio)
    "COMPRA DE NTNB",           # NTN-B (Tesouro IPCA+)
    "COMPRA DE LFT",            # LFT (Tesouro Selic)
    "COMPRA DE NTN",            # NTN (Tesouro Direto)
    "COMPRA DE LCI",            # LCI
    "COMPRA DE LCA",            # LCA
    "LIQ BOLSA",                # Stock market liquidation (debit/credit margem)
    "DEBITO MARGEM",            # Margin debit (brokerage)
    # Currency exchange between own accounts
    "Cambio",                   # FX conversion (C6 PF → C6 Global)
    # TED to known internal accounts
    "Ted Dif.litud",            # TED to BTG (Mariana internal)
    # Credit card bill payments (expense already in fatura)
    "Pagto Cobranca",           # Boleto payment (card bill or internal)
    "Pagamento de fatura",      # Card bill payment from CC
    "ITAU VISA ITAUCARD",       # Itaú card bill via auto-debit
    "FAT.CARTAO MASTER",        # Mastercard bill auto-debit
    "FAT.CARTAO VISA",          # Visa bill auto-debit
    "FAT CARTAO",               # Generic card bill
    "PGTO CARTAO",              # Card payment
    "Debito de Cartao",         # Card debit (PicPay/similar)
    # PIX to self (Itaú format: "PIX TRANSF DAVID R03/07")
    "PIX TRANSF DAVID",         # David to self across accounts
    "PIX TRANSF MARIANA",       # Mariana to self across accounts
]

# Extended internal transfer patterns that check recipient/context
# (PIX transfers to known family accounts)
INTERNAL_TRANSFER_RECIPIENTS = [
    "DAVID ROBERT CAMARGO DE CAMPOS",      # David's PJ → PF
    "DAVID ROBERT CAMARGO FERREIRA CAMPOS", # David full name variant
    "MARIANA TEIXEIRA FERREIRA",            # Between spouses
    "MARIANA FERREIRA CAMPOS",              # Between spouses
    "C6 BANK",                              # Transfer to C6
    "PICPAY",                               # Transfer to PicPay
]


# ============================================================================
# PJ INCOME SOURCE MAPPING
# ============================================================================

PJ_SOURCE_MAPPING = {
    "receita_pj": {
        "ARVO": "Arvo (David - PJ)",
        "DAVID ROBERT CAMARGO": "Arvo (David - PJ)",
        "BRANDLOVERS": "BrandLovers (David - PJ)",
        "BRAND LOVERS": "BrandLovers (David - PJ)",
        "ARBITRALIS": "Arbitralis (David - PJ)",
        "LEARNTOFLY": "Learn To Fly (David - PJ)",
        "LEARN TO FLY": "Learn To Fly (David - PJ)",
        "KIWIFY": "Kiwify (David - PJ)",
        "CNRY": "CNRY (David - PJ)",
        "CANARY": "CNRY (David - PJ)",
        "BARTE": "Barte (David - PJ)"
    }
}


def normalize_text(text: str) -> str:
    """Normalize text for matching: uppercase, remove accents."""
    if not text:
        return ""
    import unicodedata
    text = text.upper().strip()
    # Remove accents (NFD decomposes, then strip combining marks)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text


def find_longest_matching_keyword(description: str, keywords_dict: Dict[str, List[str]]) -> Tuple[Optional[str], Optional[str]]:
    """
    Find the longest matching keyword in description for a category.
    Returns (category, matched_keyword) or (None, None) if no match.
    """
    norm_desc = normalize_text(description)
    longest_match = None
    longest_category = None

    for category, keywords in keywords_dict.items():
        for keyword in keywords:
            norm_keyword = normalize_text(keyword)
            # Handle wildcard patterns (* at start/end)
            if norm_keyword.endswith("*"):
                pattern = norm_keyword[:-1]
                if norm_desc.startswith(pattern) or pattern in norm_desc:
                    if longest_match is None or len(norm_keyword) > len(longest_match):
                        longest_match = norm_keyword
                        longest_category = category
            elif norm_keyword.startswith("*"):
                pattern = norm_keyword[1:]
                if norm_desc.endswith(pattern) or pattern in norm_desc:
                    if longest_match is None or len(norm_keyword) > len(longest_match):
                        longest_match = norm_keyword
                        longest_category = category
            else:
                if norm_keyword in norm_desc:
                    if longest_match is None or len(norm_keyword) > len(longest_match):
                        longest_match = norm_keyword
                        longest_category = category

    return longest_category, longest_match


def is_internal_transfer(description: str, tipo: Optional[str] = None, banco: str = "") -> bool:
    """
    Detect if transaction is an internal transfer.
    Conservative: only mark as internal if clearly between family accounts.
    Generic PIX/TED with unknown recipients should NOT be classified as internal.
    """
    norm_desc = normalize_text(description)

    # Check exact internal patterns
    for pattern in INTERNAL_TRANSFER_PATTERNS:
        if normalize_text(pattern) in norm_desc:
            return True

    # Check if PIX/TED to known family accounts
    for recipient in INTERNAL_TRANSFER_RECIPIENTS:
        if normalize_text(recipient) in norm_desc:
            return True

    return False


def categorize_expense(description: str) -> Optional[str]:
    """Categorize a debit transaction as expense."""
    # Special cases first
    if normalize_text("NATHALIACASADE") in normalize_text(description):
        return "alimentacao"
    if normalize_text("ABDO MOHAMED") in normalize_text(description):
        return "saude"

    # If it looks like an internal transfer, don't categorize as expense
    if is_internal_transfer(description):
        return None

    category, _ = find_longest_matching_keyword(description, EXPENSE_KEYWORDS)
    return category


def categorize_income(description: str, account_type: str = "") -> Optional[str]:
    """Categorize a credit transaction as income."""
    # Special case: RECEB PAGFOR GRPQA = aluguel, not another category
    if "RECEB PAGFOR GRPQA" in normalize_text(description):
        return "receita_aluguel"
    if "GRPQA" in normalize_text(description):
        return "receita_aluguel"

    # Einstein salary only in Bradesco Poupanca
    if "SOCIEDADE BENEFICENTE ISRAELITA" in normalize_text(description) and "poupanca" in account_type:
        return "receita_clt"

    category, _ = find_longest_matching_keyword(description, INCOME_KEYWORDS)
    return category


def get_pj_origin(description: str) -> str:
    """Map PJ income description to origin source."""
    norm_desc = normalize_text(description)

    for keyword, origin in PJ_SOURCE_MAPPING.get("receita_pj", {}).items():
        if normalize_text(keyword) in norm_desc:
            return origin

    return "Outras Receitas PJ"


def format_periodo(start_date: str, end_date: str) -> str:
    """Format period from dates like 2025-01-01 to 2026-03-29."""
    try:
        start = start_date[:7]  # YYYY-MM
        end = end_date[:7]
        return f"{start} a {end}"
    except:
        return "N/D"


# ============================================================================
# MAIN PROCESSING FUNCTIONS
# ============================================================================

def load_reconciled_files(input_dir: Path) -> List[Dict]:
    """Load all *-3_reconciled.json files from E3 output directory."""
    files = list(input_dir.glob("*-3_reconciled.json"))
    reconciled_data = []

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                reconciled_data.append(data)
        except Exception as e:
            print(f"[E4.0] WARNING: Failed to load {file_path.name}: {e}")

    return reconciled_data


def load_patrimonio(baseline_path: Path) -> Dict:
    """Load baseline patrimonio consolidated file."""
    if baseline_path.exists():
        try:
            with open(baseline_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[E4.0] WARNING: Failed to load patrimonio: {e}")
    return {}


def process_transactions(reconciled_data: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict], int, int, int]:
    """
    Process all transactions: categorize, detect transfers.
    Returns (receitas, despesas, transferencias, count_receitas, count_despesas, count_transfers)
    """
    receitas = []
    despesas = []
    transferencias = []

    for account_data in reconciled_data:
        if "transacoes" not in account_data:
            continue

        banco = account_data.get("banco", "Unknown")
        tipo_conta = account_data.get("tipo_conta", "")
        titular = account_data.get("titular", "")
        moeda = account_data.get("moeda", "BRL")

        for tx in account_data["transacoes"]:
            data = tx.get("data", "")
            descricao = tx.get("descricao", "")
            valor = tx.get("valor", 0.0)
            tipo = tx.get("tipo")  # For faturas, may be missing (treat as debito)
            saldo_apos = tx.get("saldo_apos")

            # Detect internal transfers first
            if is_internal_transfer(descricao, tipo):
                transferencias.append({
                    "data": data,
                    "descricao": descricao,
                    "valor": valor,
                    "banco": banco,
                    "tipo_conta": tipo_conta,
                    "titular": titular,
                    "tipo": tipo or "debito",
                    "moeda": moeda
                })
                continue

            # Categorize based on tipo (credito/debito)
            if tipo == "credito":
                category = categorize_income(descricao, tipo_conta)
                if category:
                    origin = "Rendimentos Financeiros"
                    if category == "receita_pj":
                        origin = get_pj_origin(descricao)
                    elif category == "receita_clt":
                        origin = "Einstein (Mariana - CLT)"
                    elif category == "receita_aluguel":
                        origin = "Aluguéis"
                    elif category == "receita_restituicao":
                        origin = "Restituições"
                    elif category == "receita_fgts":
                        origin = "FGTS"
                    else:
                        origin = "Outras Receitas"

                    receitas.append({
                        "data": data,
                        "descricao": descricao,
                        "valor": valor,
                        "banco": banco,
                        "categoria": category,
                        "origem": origin,
                        "tipo_conta": tipo_conta,
                        "titular": titular,
                        "moeda": moeda
                    })
            else:  # debito or fatura (no tipo field)
                category = categorize_expense(descricao)
                if category is None:
                    # categorize_expense returns None for internal transfers too
                    # Check if it's a known internal transfer
                    if is_internal_transfer(descricao, tipo, banco):
                        transferencias.append({
                            "data": data,
                            "descricao": descricao,
                            "valor": valor,
                            "banco": banco,
                            "tipo_conta": tipo_conta,
                            "titular": titular,
                            "tipo": tipo or "debito",
                            "moeda": moeda
                        })
                        continue
                    # If no keyword match and not internal → nao_identificado
                    category = "nao_identificado"

                # Use absolute value for expenses (debits often stored as negative)
                valor_abs = abs(valor)
                despesas.append({
                    "data": data,
                    "descricao": descricao,
                    "valor": valor_abs,
                    "banco": banco,
                    "categoria": category,
                    "tipo_conta": tipo_conta,
                    "titular": titular,
                    "moeda": moeda
                })

    return receitas, despesas, transferencias, len(receitas), len(despesas), len(transferencias)


def build_receitas_unified(receitas: List[Dict]) -> Dict:
    """Build unified receitas output file."""
    # Group by category
    by_category = defaultdict(list)
    totals_por_categoria = defaultdict(float)

    for tx in receitas:
        categoria = tx["categoria"]
        by_category[categoria].append(tx)
        totals_por_categoria[categoria] += tx["valor"]

    total_geral = sum(totals_por_categoria.values())

    return {
        "consolidation_date": datetime.utcnow().isoformat(),
        "periodo": "2025-01 a 2026-03",
        "categorias": sorted(by_category.keys()),
        "total_categorias": len(by_category),
        "total_transacoes": len(receitas),
        "totais_por_categoria": dict(totals_por_categoria),
        "total_geral": round(total_geral, 2),
        "dados": {cat: sorted(txs, key=lambda x: x["data"]) for cat, txs in by_category.items()}
    }


def build_despesas_unified(despesas: List[Dict]) -> Dict:
    """Build unified despesas output file."""
    # Group by category
    by_category = defaultdict(list)
    totals_por_categoria = defaultdict(float)

    for tx in despesas:
        categoria = tx["categoria"]
        by_category[categoria].append(tx)
        totals_por_categoria[categoria] += tx["valor"]

    total_geral = sum(totals_por_categoria.values())

    return {
        "consolidation_date": datetime.utcnow().isoformat(),
        "periodo": "2025-01 a 2026-03",
        "categorias": sorted(by_category.keys()),
        "total_categorias": len(by_category),
        "total_transacoes": len(despesas),
        "totais_por_categoria": dict(totals_por_categoria),
        "total_geral": round(total_geral, 2),
        "dados": {cat: sorted(txs, key=lambda x: x["data"]) for cat, txs in by_category.items()}
    }


def build_fluxo_mensal_detalhado(receitas: List[Dict], despesas: List[Dict]) -> Dict:
    """Build detailed monthly flow file."""
    # Collect months
    months = set()
    for tx in receitas + despesas:
        if tx.get("data"):
            months.add(tx["data"][:7])

    months_sorted = sorted(months)

    # Build receitas by source and month
    receita_origens = set()
    receita_por_mes = {}

    for month in months_sorted:
        receita_por_mes[month] = {}

        for tx in receitas:
            if tx["data"][:7] == month:
                origem = tx["origem"]
                receita_origens.add(origem)
                if origem not in receita_por_mes[month]:
                    receita_por_mes[month][origem] = 0.0
                receita_por_mes[month][origem] += tx["valor"]

    # Fill zeros for missing origins
    for month in months_sorted:
        for origem in receita_origens:
            if origem not in receita_por_mes[month]:
                receita_por_mes[month][origem] = 0.0
        receita_por_mes[month]["_total"] = sum(v for k, v in receita_por_mes[month].items() if k != "_total")

    # Build despesas by category and month
    despesa_categorias = set()
    despesa_por_mes = {}

    for month in months_sorted:
        despesa_por_mes[month] = {}

        for tx in despesas:
            if tx["data"][:7] == month:
                categoria = tx["categoria"]
                despesa_categorias.add(categoria)
                if categoria not in despesa_por_mes[month]:
                    despesa_por_mes[month][categoria] = 0.0
                despesa_por_mes[month][categoria] += tx["valor"]

    # Fill zeros for missing categories
    for month in months_sorted:
        for categoria in despesa_categorias:
            if categoria not in despesa_por_mes[month]:
                despesa_por_mes[month][categoria] = 0.0
        despesa_por_mes[month]["_total"] = sum(v for k, v in despesa_por_mes[month].items() if k != "_total")

    return {
        "periodo": "2025-01 a 2026-03",
        "meses_ordenados": months_sorted,
        "receitas": {
            "origens": sorted(receita_origens),
            "por_mes": receita_por_mes
        },
        "despesas": {
            "categorias": sorted(despesa_categorias),
            "por_mes": despesa_por_mes
        }
    }


def save_json(file_path: Path, data: Dict) -> None:
    """Save JSON file with nice formatting."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def preserve_existing_file(file_path: Path) -> bool:
    """Check if file exists and is substantial (>100 bytes)."""
    if file_path.exists():
        size = file_path.stat().st_size
        return size > 100
    return False


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main processing function."""
    print("[E4.0] Starting E4 Categorization Stage...")

    # Setup paths
    scripts_dir = Path(__file__).parent
    base_dir = scripts_dir.parent
    processed_dir = base_dir / "processed"
    input_dir = processed_dir / "E3_reconciled"
    output_dir = processed_dir / "E4_unified"
    baseline_path = processed_dir / "E2_extracts" / "baseline_patrimonial-1.5_consolidated.json"

    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("[E4.1] Loading E3 reconciled files...")
    reconciled_data = load_reconciled_files(input_dir)
    print(f"[E4.1] Loaded {len(reconciled_data)} reconciled account files")

    print("[E4.2] Processing transactions...")
    receitas, despesas, transferencias, n_receitas, n_despesas, n_transfers = process_transactions(reconciled_data)
    print(f"[E4.2] Processed: {n_receitas} receitas, {n_despesas} despesas, {n_transfers} internal transfers")

    # Build output files
    print("[E4.3] Building unified output files...")

    receitas_unified = build_receitas_unified(receitas)
    despesas_unified = build_despesas_unified(despesas)
    fluxo_unified = build_fluxo_mensal_detalhado(receitas, despesas)

    # Save files
    save_json(output_dir / "receitas-4_unified.json", receitas_unified)
    print("[E4.3] Saved receitas-4_unified.json")

    save_json(output_dir / "despesas-4_unified.json", despesas_unified)
    print("[E4.3] Saved despesas-4_unified.json")

    save_json(output_dir / "fluxo_mensal_detalhado-4_unified.json", fluxo_unified)
    print("[E4.3] Saved fluxo_mensal_detalhado-4_unified.json")

    # Patrimonio: preserve existing if non-empty
    patrimonio_path = output_dir / "patrimonio-4_unified.json"
    if not preserve_existing_file(patrimonio_path):
        patrimonio = load_patrimonio(baseline_path)
        if patrimonio:
            save_json(patrimonio_path, patrimonio)
            print("[E4.4] Saved patrimonio-4_unified.json (from baseline)")
        else:
            save_json(patrimonio_path, {"dados": []})
            print("[E4.4] Saved empty patrimonio placeholder")
    else:
        print("[E4.4] Preserved existing patrimonio-4_unified.json (>100 bytes)")

    # Placeholder files: preserve existing if non-empty, else create empty
    for placeholder_file in ["investimentos-4_unified.json", "seguros-4_unified.json", "pontos_milhas-4_unified.json"]:
        file_path = output_dir / placeholder_file
        if not preserve_existing_file(file_path):
            save_json(file_path, {"dados": []})
            print(f"[E4.4] Created empty {placeholder_file} placeholder")
        else:
            print(f"[E4.4] Preserved existing {placeholder_file} (>100 bytes)")

    # Summary
    print("\n" + "="*70)
    print("E4 CATEGORIZATION SUMMARY")
    print("="*70)
    print(f"Total receitas categorized: {n_receitas}")
    print(f"Total despesas categorized: {n_despesas}")
    print(f"Total internal transfers: {n_transfers}")
    print(f"Receita categories: {len(receitas_unified['categorias'])}")
    print(f"Despesa categories: {len(despesas_unified['categorias'])}")
    print(f"Total receita geral: R$ {receitas_unified['total_geral']:,.2f}")
    print(f"Total despesa geral: R$ {despesas_unified['total_geral']:,.2f}")
    print(f"Output directory: {output_dir}")
    print("="*70)
    print("[E4.9] E4 Categorization Stage COMPLETE")


if __name__ == "__main__":
    main()
