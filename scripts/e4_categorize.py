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
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


# ============================================================================
# LOAD CONFIGURATION FROM JSON FILES
# ============================================================================

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"

def _load_json_config(filename: str) -> dict:
    """Load a JSON config file from config/ directory."""
    path = CONFIG_DIR / filename
    if not path.exists():
        print(f"FATAL: Config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

_categorization = _load_json_config("categorization.json")
_family = _load_json_config("family_members.json")

EXPENSE_KEYWORDS = _categorization["expense_keywords"]
INCOME_KEYWORDS = _categorization["income_keywords"]
INTERNAL_TRANSFER_PATTERNS = _categorization["internal_transfer_patterns"]
# PIX patterns from family config (items like "PIX TRANSF DAVID")
INTERNAL_TRANSFER_PATTERNS += _family.get("transferencias_internas", {}).get("patterns_pix", [])

INTERNAL_TRANSFER_RECIPIENTS = _family.get("transferencias_internas", {}).get("recipients", [])

PJ_SOURCE_MAPPING = {"receita_pj": _categorization["pj_source_mapping"]}
CLT_SOURCE_MAPPING = _categorization["clt_source_mapping"]


# NOTE: All keyword data, transfer patterns, PJ/CLT mappings, and transfer
# recipients are now loaded from config/categorization.json and
# config/family_members.json. See those files to add/edit keywords.
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
                if norm_desc.startswith(pattern):
                    if longest_match is None or len(norm_keyword) > len(longest_match):
                        longest_match = norm_keyword
                        longest_category = category
            elif norm_keyword.startswith("*"):
                pattern = norm_keyword[1:]
                if norm_desc.endswith(pattern):
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

    # v4.7: Bank-specific patterns (too generic to use globally)
    # "Pagamento" alone in C6 Bank extrato = credit card bill payment
    norm_banco = normalize_text(banco)
    if "C6" in norm_banco and norm_desc.strip() == normalize_text("Pagamento"):
        return True

    # v5.0.1: TED to Hbank (Bradesco → BTG Pactual, Mariana investment transfer)
    if "TED D HBANK" in norm_desc:
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


def categorize_income(description: str, account_type: str = "",
                      banco: str = "", titular: str = "") -> Optional[str]:
    """Categorize a credit transaction as income."""
    norm_desc = normalize_text(description)
    norm_titular = normalize_text(titular)
    norm_banco = normalize_text(banco)

    # All income categorization is driven by config keywords in categorization.json
    # (income_keywords.receita_aluguel has GRPQA, RECEB PAGFOR GRPQA, etc.)
    # (income_keywords.receita_clt has SOCIEDADE BENEFICENTE ISRAELITA, *3221, etc.)
    category, _ = find_longest_matching_keyword(description, INCOME_KEYWORDS)
    return category


def get_pj_origin(description: str) -> str:
    """Map PJ income description to origin source."""
    norm_desc = normalize_text(description)

    for keyword, origin in PJ_SOURCE_MAPPING.get("receita_pj", {}).items():
        if normalize_text(keyword) in norm_desc:
            return origin

    return "Outras Receitas PJ"


def get_clt_origin(description: str) -> str:
    """Map CLT income description to origin source. v5.3"""
    norm_desc = normalize_text(description)

    for keyword, origin in CLT_SOURCE_MAPPING.items():
        if normalize_text(keyword) in norm_desc:
            return origin

    # v5.3.1: fallback to first CLT mapping value or generic label
    if CLT_SOURCE_MAPPING:
        return next(iter(CLT_SOURCE_MAPPING.values()))
    return "Receita CLT"


def format_periodo(start_date: str, end_date: str) -> str:
    """Format period from dates like 2025-01-01 to 2026-03-29."""
    try:
        start = start_date[:7]  # YYYY-MM
        end = end_date[:7]
        return f"{start} a {end}"
    except (ValueError, TypeError, IndexError) as e:
        print(f"  [WARN] Erro ao parsear data: {e}")
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
                # Skip tombstoned files from E3 cleanup
                if data.get('_tombstone'):
                    continue
                transacoes = data.get('transacoes_total', data.get('transacoes'))
                if transacoes is None:
                    print(f"  [WARN] {file_path.name}: campo transacoes ausente — pulando")
                    continue
                # Note: transacoes can be 0 or [] for legitimate empty months — don't skip those
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

        # v5.3: Normalize all string fields from E3 to remove accents upfront.
        # E2 LLM output may include accented values (crédito, débito, Itaú, etc.)
        # that would fail against hardcoded comparisons downstream.
        banco_raw = account_data.get("banco", "Unknown")
        banco = normalize_text(banco_raw).lower() if banco_raw else "unknown"
        tipo_conta_raw = account_data.get("tipo_conta", "")
        tipo_conta = normalize_text(tipo_conta_raw).lower() if tipo_conta_raw else ""
        titular = account_data.get("titular", "")
        moeda = account_data.get("moeda", "BRL")

        for tx in account_data["transacoes"]:
            data = tx.get("data", "")
            descricao_raw = tx.get("descricao", "")
            descricao = descricao_raw  # keep original for output; normalize_text used in matching fns
            valor = tx.get("valor", 0.0)
            # Type validation for valor
            if isinstance(valor, str):
                try:
                    valor = float(valor.replace(".", "").replace(",", "."))
                except (ValueError, TypeError):
                    print(f"  [WARN] valor não-numérico: '{valor}' em {tx.get('descricao', '?')}")
                    valor = 0.0
            tipo = tx.get("tipo")  # For faturas, may be missing (treat as debito)
            # v5.2: Normalize tipo to remove accents (E2/E3 may store "crédito"/"débito")
            if tipo is not None:
                tipo = normalize_text(tipo).lower()  # "crédito" → "CREDITO" → "credito"
            # v5.1: Infer tipo from valor sign when missing (E2 extracts may omit it)
            # Faturas excluded: positive values in faturas are purchases (expenses)
            if tipo is None and valor is not None:
                is_fatura = tipo_conta.startswith("fatura")
                if not is_fatura:
                    tipo = "credito" if valor > 0 else "debito"
            saldo_apos = tx.get("saldo_apos")

            # Detect internal transfers first
            # (is_internal_transfer already normalizes internally)
            if is_internal_transfer(descricao, tipo):
                transferencias.append({
                    "data": data,
                    "descricao": descricao,
                    "valor": valor,
                    "banco": banco_raw,
                    "tipo_conta": tipo_conta_raw,
                    "titular": titular,
                    "tipo": tipo or "debito",
                    "moeda": moeda
                })
                continue

            # Categorize based on tipo (credito/debito)
            # tipo is already normalized (no accents, lowercase)
            if tipo == "credito":
                category = categorize_income(descricao, tipo_conta, banco, titular)
                # v4.8: unmatched creditos default to "outras_receitas" instead of being dropped
                if not category:
                    category = "outras_receitas"

                origin = "Outras Receitas"
                if category == "receita_pj":
                    origin = get_pj_origin(descricao)
                elif category == "receita_clt":
                    origin = get_clt_origin(descricao)
                elif category == "receita_aluguel":
                    origin = "Aluguéis"
                elif category == "receita_investimento":
                    origin = "Rendimentos Financeiros"
                elif category == "receita_resgate":
                    origin = "Resgates"
                elif category == "receita_venda_ativo":
                    origin = "Venda de Ativo"
                elif category == "receita_restituicao":
                    origin = "Restituições"
                elif category == "receita_fgts":
                    origin = "FGTS"
                elif category == "outras_receitas":
                    origin = "Outras Receitas"

                receitas.append({
                    "data": data,
                    "descricao": descricao,
                    "valor": valor,
                    "banco": banco_raw,
                    "categoria": category,
                    "origem": origin,
                    "tipo_conta": tipo_conta_raw,
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
                            "banco": banco_raw,
                            "tipo_conta": tipo_conta_raw,
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
                    "banco": banco_raw,
                    "categoria": category,
                    "tipo_conta": tipo_conta_raw,
                    "titular": titular,
                    "moeda": moeda
                })

    return receitas, despesas, transferencias, len(receitas), len(despesas), len(transferencias)


def compute_periodo(transactions: List[Dict]) -> str:
    """Compute period string from transaction dates."""
    dates = [tx.get("data", "")[:7] for tx in transactions if tx.get("data")]
    if dates:
        return f"{min(dates)} a {max(dates)}"
    return "N/D"


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

    BRT = timezone(timedelta(hours=-3))
    return {
        "consolidation_date": datetime.now(BRT).isoformat(),
        "periodo": compute_periodo(receitas),
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

    BRT = timezone(timedelta(hours=-3))
    return {
        "consolidation_date": datetime.now(BRT).isoformat(),
        "periodo": compute_periodo(despesas),
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

    # Fill zeros for missing origins and round to 2 decimals
    for month in months_sorted:
        for origem in receita_origens:
            if origem not in receita_por_mes[month]:
                receita_por_mes[month][origem] = 0.0
            else:
                receita_por_mes[month][origem] = round(receita_por_mes[month][origem], 2)
        receita_por_mes[month]["_total"] = round(sum(v for k, v in receita_por_mes[month].items() if k != "_total"), 2)

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

    # Fill zeros for missing categories and round to 2 decimals
    for month in months_sorted:
        for categoria in despesa_categorias:
            if categoria not in despesa_por_mes[month]:
                despesa_por_mes[month][categoria] = 0.0
            else:
                despesa_por_mes[month][categoria] = round(despesa_por_mes[month][categoria], 2)
        despesa_por_mes[month]["_total"] = round(sum(v for k, v in despesa_por_mes[month].items() if k != "_total"), 2)

    return {
        "periodo": compute_periodo(receitas + despesas),
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
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except (IOError, OSError) as e:
        print(f"  [ERROR] Falha ao salvar {file_path}: {e}", file=sys.stderr)
        raise


def preserve_existing_file(file_path: Path) -> bool:
    """Check if file exists and is substantial (>100 bytes)."""
    if file_path.exists():
        size = file_path.stat().st_size
        return size > 100
    return False


# ============================================================================
# QA LOG GENERATION
# ============================================================================

def generate_qa_log(despesas: List[Dict], log_path: Path) -> None:
    """Generate qa_log.md with unidentified transactions for manual review."""
    nao_id = [tx for tx in despesas if tx.get("categoria") == "nao_identificado"]
    total_despesas = len(despesas)
    taxa = (len(nao_id) / total_despesas * 100) if total_despesas > 0 else 0.0

    lines = []
    lines.append("# QA Log — E4 Categorização")
    lines.append(f"## Execução: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append(f"### Transações não identificadas: {len(nao_id)}")
    lines.append("")
    lines.append("| Data | Descrição | Valor | Banco | Fonte |")
    lines.append("|---|---|---|---|---|")

    for tx in sorted(nao_id, key=lambda x: x.get("data", "")):
        data = tx.get("data", "")
        desc = tx.get("descricao", "")
        valor = tx.get("valor", 0.0)
        banco = tx.get("banco", "")
        fonte = tx.get("tipo_conta", "")
        lines.append(f"| {data} | {desc} | R${valor:,.2f} | {banco} | {fonte} |")

    lines.append("")
    meta_status = "✅ DENTRO DA META" if taxa < 10.0 else "⚠️ ACIMA DA META (<10%)"
    lines.append(f"### Taxa: {taxa:.1f}% {meta_status}")
    lines.append("")

    # Notes for specific items to investigate
    notas = []
    for tx in nao_id:
        desc_up = tx.get("descricao", "").upper()
        if "ZS RES PREMI" in desc_up:
            notas.append(f"- **ZS RES PREMI** (R${tx['valor']:,.2f}, {tx['banco']}): Investigar — possível resgate de prêmio de seguro ou programa de pontos Santander.")
    if notas:
        lines.append("### Notas para investigação")
        lines.append("")
        # Deduplicate
        for nota in sorted(set(notas)):
            lines.append(nota)
        lines.append("")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


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

    if not reconciled_data:
        print("[E4.1] FATAL: Nenhum arquivo E3 reconciliado encontrado. Abortando.", file=sys.stderr)
        sys.exit(1)

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

    # Patrimonio: always regenerate from baseline
    patrimonio_path = output_dir / "patrimonio-4_unified.json"
    patrimonio = load_patrimonio(baseline_path)
    if patrimonio:
        save_json(patrimonio_path, patrimonio)
        print("[E4.4] Saved patrimonio-4_unified.json (from baseline)")
    else:
        save_json(patrimonio_path, {"dados": []})
        print("[E4.4] Saved empty patrimonio placeholder (no baseline found)")

    # Placeholder files: always regenerate (allows clean reprocessing via e-reset)
    for placeholder_file in ["investimentos-4_unified.json", "seguros-4_unified.json", "pontos_milhas-4_unified.json"]:
        file_path = output_dir / placeholder_file
        save_json(file_path, {"dados": []})
        print(f"[E4.4] Created empty {placeholder_file} placeholder")

    # Generate QA log
    qa_log_path = base_dir / "logs" / "qa_log.md"
    generate_qa_log(despesas, qa_log_path)
    print(f"[E4.5] Generated qa_log.md")

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
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"[E4] FATAL: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
