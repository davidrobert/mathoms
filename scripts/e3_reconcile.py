#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E3 Reconciliation Stage - Deterministic Account Reconciliation
Reads E2 extracts, groups by account, deduplicates transactions,
validates saldo continuity, and outputs E3 reconciled files.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# =============================================================================
# Configuration & Types
# =============================================================================

# File types that should be skipped (not transaction-bearing accounts)
SKIP_TYPES = {
    'investimentosposicao',
    'carteirarendafixa',
    'cdbdetalhes',
    'cdbresumo',
    'faturaaluguel',
    'informerendimentos',
    'irpf',
}

# Special files to skip
SKIP_FILES = {
    'baseline_patrimonial-1.5_consolidated.json',
    'dados_imoveis-2_extract.json',
}

# Mapping from tipo to a canonical form for output (tipo_conta field)
TIPO_CANONICAL = {
    'extratoconta': 'extratoconta',
    'extratocontapj': 'extratocontapj',
    'extratopoupanca': 'extratopoupanca',
    'extratocontaglobal': 'extratocontaglobal',
    'extratocontaglobalusd': 'extratocontaglobalusd',
    'extratocontaglobaleur': 'extratocontaglobaleur',
    'faturacarbon': 'faturacarbon',
    'faturaunique': 'faturaunique',
    'faturapaoacucar': 'faturapaoacucar',
}


# =============================================================================
# Logging & Progress
# =============================================================================

def log_progress(stage: str, message: str) -> None:
    """Print a timestamped progress message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {stage}: {message}", file=sys.stderr)


# =============================================================================
# File I/O Helpers
# =============================================================================

def read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Safely read a JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log_progress("ERROR", f"Failed to read {path.name}: {e}")
        return None


def write_json(path: Path, data: Dict[str, Any]) -> bool:
    """Safely write JSON with proper formatting."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log_progress("ERROR", f"Failed to write {path.name}: {e}")
        return False


# =============================================================================
# Account Grouping Logic
# =============================================================================

def should_skip_file(filename: str) -> bool:
    """Check if a file should be skipped."""
    if filename in SKIP_FILES:
        return True
    # Check if tipo is in SKIP_TYPES (tipo is usually in the filename)
    for skip_type in SKIP_TYPES:
        if skip_type in filename:
            return True
    return False


def should_skip_extract(data: Dict[str, Any]) -> bool:
    """Check if an extract should be skipped based on its type."""
    if not isinstance(data, dict):
        return True

    tipo = data.get('tipo', '')

    # Check for exact skip types
    if tipo in SKIP_TYPES:
        return True

    # Check if tipo is a fatura that starts with "fatura"
    if tipo.startswith('fatura') and tipo not in {
        'faturacarbon', 'faturaunique', 'faturapaoacucar'
    }:
        return True

    return False


def get_account_key(data: Dict[str, Any]) -> Optional[Tuple]:
    """
    Extract account grouping key from extract.
    Returns None if cannot determine.

    For conta statements: (banco, tipo, moeda)
    For faturas: (banco, tipo)
    """
    banco = data.get('banco', '').strip()
    tipo = data.get('tipo', '').strip()

    if not banco or not tipo:
        return None

    # Fatura types group by (banco, tipo) only
    if tipo.startswith('fatura'):
        return (banco, tipo)

    # Conta types group by (banco, tipo, moeda)
    moeda = data.get('moeda', 'BRL').strip()
    return (banco, tipo, moeda)


# =============================================================================
# Deduplication Logic
# =============================================================================

def transaction_signature(txn: Dict[str, Any]) -> Tuple:
    """
    Create a normalized signature for deduplication.
    Signature = (data, valor, descricao_normalized)
    """
    data = txn.get('data', '').strip()
    valor = txn.get('valor', 0)
    descricao = txn.get('descricao', '').strip().upper()

    return (data, valor, descricao)


def deduplicate_transactions(
    transactions: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Remove duplicate transactions by signature.
    When duplicates exist, keep the last (most recent file) occurrence.

    Returns: (deduplicated_list, count_removed)
    """
    seen = {}
    duplicates_removed = 0

    for txn in transactions:
        sig = transaction_signature(txn)
        if sig in seen:
            duplicates_removed += 1
        seen[sig] = txn

    deduplicated = list(seen.values())
    return deduplicated, duplicates_removed


# =============================================================================
# Saldo Continuity Validation
# =============================================================================

def validate_saldo_continuity(
    file_groups: Dict[str, List[Tuple[Path, Dict[str, Any]]]]
) -> Dict[str, List[str]]:
    """
    Validate saldo continuity across files in chronological order.
    Returns warnings per account.
    """
    warnings = defaultdict(list)

    for account_key_str, group in file_groups.items():
        # Sort by period start date
        sorted_group = sorted(
            group,
            key=lambda x: x[1].get('periodo', {}).get('inicio', '')
        )

        prev_final_saldo = None
        prev_fim = None

        for path, data in sorted_group:
            periodo = data.get('periodo', {})
            inicio = periodo.get('inicio', '')
            fim = periodo.get('fim', '')
            saldo_inicial = data.get('saldo_inicial')
            saldo_final = data.get('saldo_final')

            if prev_final_saldo is not None and saldo_inicial is not None:
                # Allow small floating point differences
                if abs(prev_final_saldo - saldo_inicial) > 0.01:
                    warnings[account_key_str].append(
                        f"Saldo gap: {path.name} "
                        f"(prev_final={prev_final_saldo}, "
                        f"next_initial={saldo_inicial}, "
                        f"gap={abs(prev_final_saldo - saldo_inicial):.2f})"
                    )

            prev_final_saldo = saldo_final
            prev_fim = fim

    return warnings


# =============================================================================
# Main Reconciliation Logic
# =============================================================================

def load_and_group_e2_extracts(e2_dir: Path) -> Tuple[Dict, List[Tuple]]:
    """
    Load all E2 extract files and group by account.

    Returns:
        (file_groups dict, list of (account_key, group_data) tuples)
    """
    file_groups = defaultdict(list)
    load_errors = []

    if not e2_dir.exists():
        log_progress("E3.1", f"E2 directory not found: {e2_dir}")
        return {}, []

    log_progress("E3.1", f"Scanning {e2_dir.name} for E2 extracts...")

    extract_files = sorted([f for f in e2_dir.glob('*-2_extract.json')])
    log_progress("E3.1", f"Found {len(extract_files)} potential extract files")

    for fpath in extract_files:
        if should_skip_file(fpath.name):
            log_progress("E3.1", f"Skipping {fpath.name} (not a transaction account)")
            continue

        data = read_json(fpath)
        if data is None:
            load_errors.append(fpath.name)
            continue

        if should_skip_extract(data):
            log_progress("E3.1", f"Skipping {fpath.name} (type={data.get('tipo')})")
            continue

        # Check for transacoes
        if 'transacoes' not in data:
            log_progress("E3.1", f"Skipping {fpath.name} (no transacoes field)")
            continue

        # Faturas have data_vencimento instead of periodo — synthesize periodo
        if 'periodo' not in data and data.get('tipo', '').startswith('fatura'):
            venc = data.get('data_vencimento', '')
            if venc:
                # Derive periodo from data_vencimento (fatura covers ~30 days before)
                from datetime import timedelta
                try:
                    dt_venc = datetime.strptime(venc, '%Y-%m-%d')
                    dt_start = dt_venc.replace(day=1) - timedelta(days=1)
                    dt_start = dt_start.replace(day=1)  # first day of prev month
                    data['periodo'] = {
                        'inicio': dt_start.strftime('%Y-%m-%d'),
                        'fim': venc
                    }
                    data['saldo_inicial'] = data.get('saldo_anterior', 0)
                    data['saldo_final'] = data.get('saldo_atual', 0)
                except ValueError:
                    pass
            # Also derive periodo from transaction dates if available
            if 'periodo' not in data:
                txns = data.get('transacoes', [])
                dates = [t.get('data', '') for t in txns if t.get('data')]
                if dates:
                    data['periodo'] = {
                        'inicio': min(dates),
                        'fim': max(dates)
                    }

        # Check for periodo (some files might not have it)
        if 'periodo' not in data:
            log_progress("E3.1", f"Skipping {fpath.name} (no periodo field)")
            continue

        key = get_account_key(data)
        if key is None:
            log_progress("E3.1", f"Skipping {fpath.name} (cannot determine account key)")
            continue

        key_str = str(key)
        file_groups[key_str].append((fpath, data))
        log_progress("E3.1", f"Loaded {fpath.name} for {key_str}")

    if load_errors:
        log_progress("E3.1", f"Failed to load {len(load_errors)} files: {load_errors}")

    # Convert to sorted list of tuples
    grouped = sorted(file_groups.items())
    log_progress("E3.1", f"Grouped into {len(grouped)} accounts")

    return file_groups, grouped


def reconcile_account(
    account_key: str,
    file_group: List[Tuple[Path, Dict[str, Any]]]
) -> Optional[Dict[str, Any]]:
    """
    Reconcile a single account:
    1. Sort files by period start
    2. Merge all transactions
    3. Deduplicate by (data, valor, descricao)
    4. Sort chronologically
    5. Return consolidated record
    """
    if not file_group:
        return None

    # Sort by period start
    sorted_group = sorted(
        file_group,
        key=lambda x: x[1].get('periodo', {}).get('inicio', '')
    )

    # Collect metadata from first file
    first_path, first_data = sorted_group[0]
    banco = first_data.get('banco', '').strip()
    tipo = first_data.get('tipo', '').strip()
    moeda = first_data.get('moeda', 'BRL').strip()

    # Use canonical tipo for output
    tipo_conta = TIPO_CANONICAL.get(tipo, tipo)

    # For faturas, get titular from any file (they should all match)
    titular = first_data.get('titular') or first_data.get('cartao')
    if isinstance(titular, str):
        titular = titular.strip()

    # Collect all transactions across files
    all_transactions = []
    for path, data in sorted_group:
        transacoes = data.get('transacoes', [])
        if isinstance(transacoes, list):
            all_transactions.extend(transacoes)

    # Deduplicate
    dedup_txns, dup_count = deduplicate_transactions(all_transactions)

    # Sort chronologically
    dedup_txns.sort(key=lambda x: x.get('data', ''))

    # Determine period coverage
    periodo_inicio = sorted_group[0][1].get('periodo', {}).get('inicio', '')
    periodo_fim = sorted_group[-1][1].get('periodo', {}).get('fim', '')

    # Use first file's saldo_inicial and last file's saldo_final
    saldo_inicial = first_data.get('saldo_inicial', 0)
    saldo_final = sorted_group[-1][1].get('saldo_final', 0)

    # Record source files
    fontes = [path.name for path, _ in sorted_group]

    reconciled = {
        'banco': banco,
        'tipo_conta': tipo_conta,
        'titular': titular,
        'moeda': moeda,
        'periodo_cobertura': {
            'inicio': periodo_inicio,
            'fim': periodo_fim
        },
        'saldo_inicial': saldo_inicial,
        'saldo_final': saldo_final,
        'fontes': fontes,
        'transacoes_total': len(dedup_txns),
        'transacoes_duplicadas_removidas': dup_count,
        'transacoes': dedup_txns
    }

    return reconciled


def generate_output_filename(reconciled: Dict[str, Any]) -> str:
    """
    Generate filename for E3 output.
    For conta types: {banco}_{tipo_conta}_{moeda}_{MMDD}-{MMDD}-3_reconciled.json
    For fatura types: {banco}_{tipo_conta}_{YYYYMM}_{YYYYMM}-3_reconciled.json
    """
    banco = reconciled['banco'].lower().replace(' ', '_')
    tipo_conta = reconciled['tipo_conta'].lower()
    moeda = reconciled['moeda'].upper()

    periodo = reconciled['periodo_cobertura']
    inicio = periodo['inicio']  # YYYY-MM-DD
    fim = periodo['fim']

    if tipo_conta.startswith('fatura'):
        # Faturas use YYYYMM format (without moeda)
        inicio_ym = inicio[:7].replace('-', '')  # YYYY-MM -> YYYYMM
        fim_ym = fim[:7].replace('-', '')
        filename = f"{banco}_{tipo_conta}_{inicio_ym}_{fim_ym}-3_reconciled.json"
    else:
        # Conta types use MMDD format
        inicio_mmdd = inicio[5:10].replace('-', '')  # MM-DD -> MMDD
        fim_mmdd = fim[5:10].replace('-', '')
        filename = f"{banco}_{tipo_conta}_{moeda}_{inicio_mmdd}-{fim_mmdd}-3_reconciled.json"

    return filename


def main():
    """Main reconciliation pipeline."""
    print("=" * 80)
    print("E3 RECONCILIATION STAGE - Deterministic Account Reconciliation")
    print("=" * 80)

    # Paths
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent
    e2_dir = base_dir / 'processed' / 'E2_extracts'
    e3_dir = base_dir / 'processed' / 'E3_reconciled'
    logs_dir = base_dir / 'logs'

    log_progress("E3.0", f"Base directory: {base_dir}")
    log_progress("E3.0", f"E2 input: {e2_dir}")
    log_progress("E3.0", f"E3 output: {e3_dir}")

    # Step 1: Load and group
    file_groups, grouped = load_and_group_e2_extracts(e2_dir)

    if not grouped:
        log_progress("E3", "No accounts to reconcile. Exiting.")
        print("\n[SUMMARY] No accounts found. No files written.")
        return

    # Step 2: Validate saldo continuity
    log_progress("E3.2", f"Validating saldo continuity across {len(grouped)} accounts...")
    continuity_warnings = validate_saldo_continuity(file_groups)

    for account_key, warnings_list in continuity_warnings.items():
        for warning in warnings_list:
            log_progress("E3.2", f"WARNING ({account_key}): {warning}")

    # Step 3: Reconcile each account
    log_progress("E3.3", "Reconciling accounts...")
    reconciled_accounts = []
    reconciliation_errors = []

    for account_key_str, file_group in grouped:
        try:
            reconciled = reconcile_account(account_key_str, file_group)
            if reconciled:
                reconciled_accounts.append(reconciled)
                log_progress(
                    "E3.3",
                    f"Reconciled {reconciled['banco']} {reconciled['tipo_conta']} "
                    f"({reconciled['transacoes_total']} txns, "
                    f"{reconciled['transacoes_duplicadas_removidas']} duplicates)"
                )
        except Exception as e:
            msg = f"Error reconciling {account_key_str}: {e}"
            log_progress("E3.3", f"ERROR: {msg}")
            reconciliation_errors.append(msg)

    if not reconciled_accounts:
        log_progress("E3", "No accounts were successfully reconciled.")
        print("\n[SUMMARY] Reconciliation failed for all accounts.")
        return

    # Step 4: Write output files
    log_progress("E3.4", f"Writing {len(reconciled_accounts)} E3 reconciled files...")
    written_files = []
    write_errors = []

    for reconciled in reconciled_accounts:
        filename = generate_output_filename(reconciled)
        output_path = e3_dir / filename

        if write_json(output_path, reconciled):
            written_files.append(filename)
            log_progress("E3.4", f"Wrote {filename}")
        else:
            write_errors.append(filename)

    # Step 5: Generate reconciliation log
    log_progress("E3.5", "Generating reconciliation summary log...")

    summary_lines = [
        "# E3 Reconciliation Summary",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Statistics",
        f"- Accounts processed: {len(reconciled_accounts)}",
        f"- Total transactions reconciled: {sum(a['transacoes_total'] for a in reconciled_accounts)}",
        f"- Total duplicates removed: {sum(a['transacoes_duplicadas_removidas'] for a in reconciled_accounts)}",
        f"- Files written: {len(written_files)}",
        "",
    ]

    if continuity_warnings:
        summary_lines.append("## Saldo Continuity Warnings")
        for account_key, warnings_list in continuity_warnings.items():
            for warning in warnings_list:
                summary_lines.append(f"- {account_key}: {warning}")
        summary_lines.append("")

    if reconciliation_errors:
        summary_lines.append("## Reconciliation Errors")
        for error in reconciliation_errors:
            summary_lines.append(f"- {error}")
        summary_lines.append("")

    if write_errors:
        summary_lines.append("## Write Errors")
        for error in write_errors:
            summary_lines.append(f"- Failed to write: {error}")
        summary_lines.append("")

    summary_lines.append("## Reconciled Accounts")
    for reconciled in reconciled_accounts:
        summary_lines.append(
            f"- {reconciled['banco']} | {reconciled['tipo_conta']} | "
            f"{reconciled['moeda']} | {reconciled['periodo_cobertura']['inicio']} "
            f"to {reconciled['periodo_cobertura']['fim']} | "
            f"{reconciled['transacoes_total']} txns"
        )

    log_file = logs_dir / 'reconciliation.md'
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(summary_lines))
        log_progress("E3.5", f"Wrote reconciliation log to {log_file.name}")
    except Exception as e:
        log_progress("E3.5", f"ERROR: Failed to write log: {e}")

    # Final summary
    print("\n" + "=" * 80)
    print("E3 RECONCILIATION COMPLETE")
    print("=" * 80)
    print(f"Accounts reconciled:        {len(reconciled_accounts)}")
    print(f"Total transactions:         {sum(a['transacoes_total'] for a in reconciled_accounts)}")
    print(f"Total duplicates removed:   {sum(a['transacoes_duplicadas_removidas'] for a in reconciled_accounts)}")
    print(f"Files written:              {len(written_files)}")
    if write_errors:
        print(f"Write errors:               {len(write_errors)}")
    if reconciliation_errors:
        print(f"Reconciliation errors:      {len(reconciliation_errors)}")
    if continuity_warnings:
        print(f"Saldo continuity warnings:  {len(continuity_warnings)}")
    print("=" * 80)


if __name__ == '__main__':
    main()
