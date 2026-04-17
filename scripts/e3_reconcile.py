#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E3 Reconciliation Stage - Deterministic Account Reconciliation
Reads E2 extracts, groups by account, deduplicates transactions,
validates saldo continuity, and outputs E3 reconciled files.

v2.0 — Fixes applied:
  - #1: Cleanup E3_reconciled/ before writing (removes ghost files)
  - #2: Skip -0_original backup files
  - #3: Dedup only between files, never within same file
  - #4: Fatura periodo adjusted to actual transaction dates
  - #5: extratocontapersonnalite added to TIPO_CANONICAL
  - #6: Filename format YYYYMM for all types (no more MMDD)
  - #7: Baseline patrimonial validation
  - #8: Temporal gap detection → qa_log.md
  - #9: Saldo None handled explicitly
  - #10: Explicit logging for faturas without data_vencimento
"""

import json
import re
import sys
from calendar import monthrange
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

import scripts.pipeline_common as _pc

# =============================================================================
# Configuration & Types
# =============================================================================

_DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent


def _load_json_safe(path: Path) -> dict:
    """Load a JSON file safely, returning {} on any error."""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_progress("WARN", f"Failed to load {path.name}: {e}")
    return {}


def _init_config(base_dir: Path) -> None:
    """(Re)carrega paths e configs a partir de um root_dir.

    Chamado no module level com default, e por main(root_dir=...) quando injetado.
    """
    global _BASE_DIR, ACCOUNT_TYPE_EQUIVALENCES, PIPE_CONFIG
    global _BANCO_DISPLAY_TO_CANONICAL
    global SKIP_TYPES, SKIP_FILES, TIPO_CANONICAL
    global _TOLERANCE_SALDO_DIFF, _TOLERANCE_GAP_DAYS, _TOLERANCE_BASELINE_DIFF

    _BASE_DIR = base_dir
    config_dir = base_dir / "config"

    family_data = _load_json_safe(config_dir / "family_members.json")
    ACCOUNT_TYPE_EQUIVALENCES = family_data.get("account_type_equivalences", {})

    PIPE_CONFIG = _load_json_safe(config_dir / "pipeline.json")

    inst_data = _load_json_safe(config_dir / "institutions.json")
    _BANCO_DISPLAY_TO_CANONICAL = {}
    for code, display in inst_data.get("banco_canonical", {}).items():
        _BANCO_DISPLAY_TO_CANONICAL[display.lower()] = code

    _recon_cfg = PIPE_CONFIG.get("reconciliation", {})

    SKIP_TYPES = set(_recon_cfg.get("skip_types", [])) or {
        'investimentosposicao', 'carteirarendafixa', 'cdbdetalhes', 'cdbresumo',
        'faturaaluguel', 'informerendimentos', 'irpf',
    }
    SKIP_FILES = set(_recon_cfg.get("skip_files", [])) or {
        'baseline_patrimonial-1.5_consolidated.json',
        'dados_imoveis-2_extract.json',
    }
    TIPO_CANONICAL = _recon_cfg.get("tipo_canonical", {}) or {
        'extratoconta': 'extratoconta', 'extratocontapj': 'extratocontapj',
        'extratocontapersonnalite': 'extratocontapersonnalite',
        'extratopoupanca': 'extratopoupanca', 'extratocontaglobal': 'extratocontaglobal',
        'extratocontaglobalusd': 'extratocontaglobalusd', 'extratocontaglobaleur': 'extratocontaglobaleur',
        'faturacarbon': 'faturacarbon', 'faturaunique': 'faturaunique', 'faturapaoacucar': 'faturapaoacucar',
    }

    _tolerances = _recon_cfg.get("tolerances", {})
    _TOLERANCE_SALDO_DIFF = _tolerances.get("saldo_diff", 0.01)
    # Fix 3.6: default 4 days to account for weekends + possible holidays
    _TOLERANCE_GAP_DAYS = _tolerances.get("temporal_gap_days", 4)
    _TOLERANCE_BASELINE_DIFF = _tolerances.get("baseline_irpf_diff", 1.0)


# Module level: carrega defaults (retrocompat com import e CLI direto)
_init_config(_DEFAULT_BASE_DIR)


# =============================================================================
# Logging & Progress
# =============================================================================

def log_progress(stage: str, message: str) -> None:
    """Delegate to pipeline_common structured logger."""
    _pc.log_stage(stage, message)


# =============================================================================
# File I/O Helpers — delegated to pipeline_common (Fix 2.1)
# =============================================================================

def read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Safely read a JSON file."""
    return _pc.read_json(path)


def write_json(path: Path, data: Dict[str, Any]) -> bool:
    """Safely write JSON with proper formatting."""
    return _pc.write_json(path, data)


def normalize_periodo_in_extract(data: Dict[str, Any]) -> None:
    """Ensure ``periodo`` is a dict with ``inicio``/``fim``.

    E2-llm (schema) uses ``period`` as YYYYMM string → JSON field ``periodo`` as str.
    E3 assumes ``periodo`` is ``{inicio, fim}`` and calls ``.get()`` on it — str would raise.
    """
    raw = data.get("periodo")
    if raw is None:
        return
    if isinstance(raw, dict):
        return
    if isinstance(raw, str):
        s = raw.strip()
        if len(s) == 6 and s.isdigit():
            y, m = int(s[:4]), int(s[4:6])
            if 1 <= m <= 12:
                last = monthrange(y, m)[1]
                data["periodo"] = {
                    "inicio": f"{y}-{m:02d}-01",
                    "fim": f"{y}-{m:02d}-{last:02d}",
                }
                return
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            d = s[:10]
            data["periodo"] = {"inicio": d, "fim": d}
            return
        log_progress(
            "E3.0",
            f"Could not parse periodo string; using empty range (value={s[:48]!r})",
        )
        data["periodo"] = {"inicio": "", "fim": ""}
        return
    log_progress(
        "E3.0",
        f"Unexpected periodo type {type(raw).__name__}; coercing to empty dict",
    )
    data["periodo"] = {"inicio": "", "fim": ""}


# =============================================================================
# Directory Cleanup (#1)
# =============================================================================

def cleanup_e3_directory(e3_dir: Path) -> int:
    """
    Remove all existing JSON files from E3_reconciled directory.
    Ensures no ghost files from prior LLM runs interfere with downstream stages.
    Falls back to overwriting with a tombstone marker if delete is not permitted.
    Returns count of files cleaned.
    """
    if not e3_dir.exists():
        return 0

    cleaned = 0
    for file_path in e3_dir.glob('*.json'):
        try:
            file_path.unlink()
            cleaned += 1
        except PermissionError:
            # Filesystem doesn't allow delete — overwrite with tombstone
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({"_tombstone": True}, f)
                cleaned += 1
            except Exception as e:
                log_progress("WARN", f"Cannot delete or tombstone {file_path.name}: {e}")
        except Exception as e:
            log_progress("WARN", f"Unexpected error cleaning {file_path.name}: {e}")

    if cleaned:
        log_progress("E3.0", f"Cleaned {e3_dir.name}: {cleaned} stale files removed/tombstoned")

    return cleaned


# =============================================================================
# Account Grouping Logic
# =============================================================================

def should_skip_file(filename: str) -> bool:
    """Check if a file should be skipped based on filename rules.

    NOTE: Type-based skipping is done in should_skip_extract() using the
    actual ``tipo`` field from the JSON content, not filename substrings.
    This function only checks structural filename rules (Fix 3.5).
    """
    if filename in SKIP_FILES:
        return True
    # Skip -0_original backup files (#2)
    if '-0_original' in filename:
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

    # Check normalized tipo via equivalences (e.g. a file with
    # tipo='extratocontapersonnalite' whose equivalent is an investment type)
    tipo_equiv = ACCOUNT_TYPE_EQUIVALENCES.get(tipo, tipo)
    if tipo_equiv in SKIP_TYPES:
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

    Uses ACCOUNT_TYPE_EQUIVALENCES from config to normalize alias types
    (e.g., extratocontapersonnalite → extratoconta) so that overlapping
    extracts from the same bank account are grouped and deduplicated.
    """
    banco = data.get('banco', data.get('instituicao', '')).strip()
    tipo = data.get('tipo', '').strip()

    if not banco or not tipo:
        return None

    # Normalize tipo using config-driven equivalences
    tipo_normalized = ACCOUNT_TYPE_EQUIVALENCES.get(tipo, tipo)

    # Fatura types group by (banco, tipo) only
    if tipo_normalized.startswith('fatura'):
        return (banco, tipo_normalized)

    # Conta types group by (banco, tipo, moeda)
    moeda = data.get('moeda', '').strip()
    if not moeda:
        # Also check nested conta.moeda
        conta = data.get('conta', {})
        if isinstance(conta, dict):
            moeda = conta.get('moeda', 'BRL').strip()
        else:
            moeda = 'BRL'
    return (banco, tipo_normalized, moeda)


# =============================================================================
# Date Parsing Helper for Sorting
# =============================================================================

def _parse_date_for_sort(date_str: str) -> datetime:
    """Parse date string for sorting, handling various formats."""
    if not date_str:
        return datetime.min
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return datetime.min


# =============================================================================
# Deduplication Logic (#3 — only between files, never within same file)
# =============================================================================

# Regex to strip bank-specific suffixes that vary between overlapping extracts.
# C6 Bank adds various suffixes after "—" depending on export format:
#   PDF: "— TRANSF ENVIADA PIX", "— TRANSF RECEBIDA PIX", "— TRANSF ENVIADA PIX C"
#   CSV: "— 13 Salário", "— Salários PJ", "— NF 26", "— NFS 25", etc.
# These are annotations that differ between CSV and PDF exports of the SAME transaction.
# Stripping everything after "—" makes signatures match across formats.
_DEDUP_SUFFIX_RE = re.compile(
    r'\s*—\s*.*$',
    re.IGNORECASE
)

# Regex to truncate concatenated PIX descriptions at the second "Pix" occurrence.
# C6 Bank sometimes merges consecutive PIX ops into one description in certain exports
# (e.g., "Pix enviado para X Pix enviado para Y") while other exports list them separately.
# For dedup, we keep only the first PIX segment.
_DEDUP_PIX_CONCAT_RE = re.compile(
    r'(Pix\s+(?:enviado|recebido)\s+.*?)\s+Pix\s+(?:enviado|recebido)\s+',
    re.IGNORECASE
)

# v5.7.2: C6 Bank CSV concatenation — the CSV export sometimes merges the description
# of the NEXT transaction onto the current one (no separator). Common patterns:
#   "Pix enviado para RUBENS DE CAMPOS C6TAG ESTACIONAMENTO"
#   "JUROS CHEQUE ESP C6TAG ESTACIONAMENTO"
#   "C6TAG ESTACIONAMENTO C6TAG PEDAGIO"
#   "Pix enviado para X Belt Academy"
#   "Pix enviado para X SEGURO CONTA C6"
#   "Pix enviado para X IOF CHEQUE ESPECIAL"
#   "Pix enviado para X Boleto"
#   "Pix enviado para X Pix estornado"
# We detect known "next-transaction start" markers and truncate there.
_DEDUP_CSV_CONCAT_MARKERS = [
    'C6TAG',
    'Pix enviado',
    'Pix recebido',
    'Belt Academy',
    'SEGURO CONTA C6',
    'IOF CHEQUE ESPECIAL',
    'IOF DESPESA',
    'Boleto',
    'Pix estornado',
    'Pix recusado',
    'Anuidade Diferenciada',
]


def _normalize_description_for_dedup(descricao: str) -> str:
    """
    Normalize a transaction description for deduplication purposes.
    Handles C6 Bank-specific formatting differences between overlapping extracts:
    1. Remove "—" suffix (PDF format annotations)
    2. Truncate concatenated PIX descriptions (keep only first segment)
    3. Strip concatenated next-transaction markers from CSV (C6TAG, Boleto, etc.)
    4. Normalize Unicode (fix Itaú mojibake: "VeÃculo" → "VEICULO")
    5. Collapse multiple whitespace and uppercase
    """
    # Step 1: Remove "—" suffix (PDF export annotations)
    descricao = _DEDUP_SUFFIX_RE.sub('', descricao)

    # Step 2: Truncate at second PIX operation (CSV merges consecutive PIX)
    m = _DEDUP_PIX_CONCAT_RE.match(descricao)
    if m:
        descricao = m.group(1)

    # Step 3: Strip concatenated next-transaction markers from CSV.
    # For each marker, if it appears INSIDE the description (not at the very start),
    # truncate everything from the marker onwards.
    # For markers at the start (e.g. "C6TAG ESTACIONAMENTO C6TAG PEDAGIO"),
    # find the SECOND occurrence and truncate there.
    desc_upper = descricao.upper()
    for marker in _DEDUP_CSV_CONCAT_MARKERS:
        marker_upper = marker.upper()
        first_pos = desc_upper.find(marker_upper)
        if first_pos < 0:
            continue
        if first_pos > 0:
            # Marker is not at the start — truncate everything from marker
            descricao = descricao[:first_pos].rstrip()
            desc_upper = descricao.upper()
        else:
            # Marker IS at the start — look for second occurrence
            second_pos = desc_upper.find(marker_upper, first_pos + len(marker_upper))
            if second_pos > 0:
                descricao = descricao[:second_pos].rstrip()
                desc_upper = descricao.upper()

    # Step 4: Normalize Unicode to ASCII (fixes Itaú mojibake: "VeÃculo" → "VECULO")
    # Drop ALL non-ASCII characters. This handles both:
    #   - Real accents: "í" → dropped, "ã" → dropped (acceptable for dedup)
    #   - Mojibake artifacts: "Ã" (from broken UTF-8) → dropped
    # Since both sides of a duplicate lose the same accent chars, signatures still match.
    descricao = descricao.encode('ascii', 'ignore').decode('ascii')

    # Step 5: Collapse whitespace and uppercase
    descricao = re.sub(r'\s+', ' ', descricao).strip().upper()
    return descricao


def transaction_signature(txn: Dict[str, Any]) -> Tuple:
    """
    Create a normalized signature for deduplication.
    Signature = (data, valor_rounded, descricao_normalized)
    """
    data = txn.get('data', '').strip()
    valor = txn.get('valor', 0)
    if isinstance(valor, float):
        valor = round(valor, 2)
    descricao = _normalize_description_for_dedup(txn.get('descricao', ''))

    return (data, valor, descricao)


def deduplicate_transactions(
    transactions_with_sources: List[Tuple[Dict[str, Any], str]]
) -> Tuple[List[Dict[str, Any]], int, List[str]]:
    """
    Remove duplicate transactions by signature, but ONLY across different files.
    Transactions within the same source file are NEVER deduplicated — they
    represent legitimate distinct operations (e.g., two Amazon purchases
    of R$68.55 on the same day).

    Args:
        transactions_with_sources: List of (transaction_dict, source_filename) tuples

    Returns: (deduplicated_list, count_removed, dedup_details)
        dedup_details: list of human-readable strings describing each dedup action (Fix 3.1)
    """
    deduplicated = []
    duplicates_removed = 0
    dedup_details: List[str] = []

    # Group by (signature, source_file) to count per-file occurrences
    per_file_counts: Dict[Tuple, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_file_txns: Dict[Tuple, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

    for txn, source_file in transactions_with_sources:
        sig = transaction_signature(txn)
        per_file_counts[sig][source_file] += 1
        per_file_txns[sig][source_file].append(txn)

    for sig, file_map in per_file_txns.items():
        if len(file_map) == 1:
            # Only one source file has this signature — keep all
            for source_file, txn_list in file_map.items():
                deduplicated.extend(txn_list)
        else:
            # Multiple source files have this signature — cross-file overlap.
            # Keep transactions from the first source file (deterministic order).
            # Discard occurrences from other source files.
            first_source = sorted(file_map.keys())[0]
            deduplicated.extend(file_map[first_source])
            removed_sources = sorted(src for src in file_map if src != first_source)
            removed_count = sum(len(file_map[src]) for src in removed_sources)
            duplicates_removed += removed_count
            # Fix 3.1: detailed dedup logging for auditability
            if removed_count > 0:
                date_str, valor, desc_norm = sig
                # Recover original descriptions for audit trail
                kept_descs = [t.get('descricao', '')[:60] for t in file_map[first_source][:1]]
                removed_descs = []
                for src in removed_sources:
                    removed_descs.extend(t.get('descricao', '')[:60] for t in file_map[src][:1])
                dedup_details.append(
                    f"DEDUP: {date_str} R${valor} "
                    f"kept='{kept_descs[0] if kept_descs else '?'}' from {first_source}, "
                    f"removed {removed_count} from {','.join(removed_sources)} "
                    f"(removed desc='{removed_descs[0] if removed_descs else '?'}')"
                )

    return deduplicated, duplicates_removed, dedup_details


# =============================================================================
# Saldo Continuity & Temporal Gap Validation (#8)
# =============================================================================

def validate_saldo_and_gaps(
    file_groups: Dict[str, List[Tuple[Path, Dict[str, Any]]]]
) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Validate saldo continuity and detect temporal gaps across files.
    Returns:
        (saldo_warnings per account, temporal_gap_messages for qa_log)
    """
    warnings = defaultdict(list)
    temporal_gaps = []

    for account_key_str, group in file_groups.items():
        # Sort by period start date
        sorted_group = sorted(
            group,
            key=lambda x: x[1].get('periodo', {}).get('inicio') or ''
        )

        prev_final_saldo = None
        prev_fim = None
        prev_name = None

        for path, data in sorted_group:
            periodo = data.get('periodo', {})
            inicio = periodo.get('inicio', '')
            fim = periodo.get('fim', '')
            saldo_inicial = data.get('saldo_inicial')
            saldo_final = data.get('saldo_final')

            # Saldo continuity check
            if prev_final_saldo is not None and saldo_inicial is not None:
                # Allow small floating point differences
                if abs(prev_final_saldo - saldo_inicial) > _TOLERANCE_SALDO_DIFF:
                    warnings[account_key_str].append(
                        f"Saldo gap: {path.name} "
                        f"(prev_final={prev_final_saldo}, "
                        f"next_initial={saldo_inicial}, "
                        f"gap={abs(prev_final_saldo - saldo_inicial):.2f})"
                    )

            # Temporal gap detection (#8)
            if prev_fim and inicio:
                try:
                    prev_fim_dt = datetime.strptime(prev_fim, '%Y-%m-%d')
                    current_inicio_dt = datetime.strptime(inicio, '%Y-%m-%d')
                    days_gap = (current_inicio_dt - prev_fim_dt).days

                    # Allow up to N days gap (weekends, processing delays)
                    if days_gap > _TOLERANCE_GAP_DAYS:
                        gap_msg = (
                            f"{account_key_str}: Temporal gap of {days_gap} days "
                            f"between {prev_name} (fim={prev_fim}) and "
                            f"{path.name} (inicio={inicio})"
                        )
                        warnings[account_key_str].append(
                            f"Temporal gap: {days_gap} days before {path.name} "
                            f"({prev_fim} -> {inicio})"
                        )
                        temporal_gaps.append(gap_msg)
                except ValueError as e:
                    log_progress("WARN", f"Date parsing failed for gap check: {prev_fim} → {inicio}: {e}")

            prev_final_saldo = saldo_final
            prev_fim = fim
            prev_name = path.name

    return warnings, temporal_gaps


# =============================================================================
# Baseline Patrimonial Validation (#7)
# =============================================================================

def validate_against_baseline(
    reconciled_accounts: List[Dict[str, Any]],
    baseline_file: Path
) -> Dict[str, List[str]]:
    """
    Validate account saldos against IRPF baseline data on 31/12 dates.
    Returns: Dict mapping account descriptions to list of discrepancy messages.
    """
    baseline_warnings = defaultdict(list)

    if not baseline_file.exists():
        log_progress("E3.6", f"Baseline file not found: {baseline_file.name}")
        return baseline_warnings

    baseline_data = read_json(baseline_file)
    if baseline_data is None:
        return baseline_warnings

    log_progress("E3.6", f"Validating {len(reconciled_accounts)} accounts against baseline...")

    # Extract baseline saldos per account from members' contas_bancarias
    baseline_saldos = {}
    members = baseline_data.get('members', baseline_data.get('membros', {}))

    # Normalize: if members is a list, convert to dict keyed by nome
    if isinstance(members, list):
        members = {m.get('nome', f'member_{i}'): m for i, m in enumerate(members) if isinstance(m, dict)}

    for member_name, member_data in members.items():
        if not isinstance(member_data, dict):
            continue
        contas = member_data.get('contas_bancarias', [])
        if not isinstance(contas, list):
            continue
        for conta in contas:
            if not isinstance(conta, dict):
                continue
            banco = conta.get('banco', conta.get('banco_origem', '')).strip().lower()
            saldo = conta.get('saldo_31_12', conta.get('saldo_31_12_ano_base'))
            ano_base = conta.get('ano_base', '')

            if saldo is not None and banco:
                key = (banco, str(ano_base))
                baseline_saldos[key] = {
                    'saldo': saldo,
                    'member': member_name,
                    'tipo': conta.get('tipo', ''),
                }

    if not baseline_saldos:
        log_progress("E3.6", "No baseline saldos found to validate against")
        return baseline_warnings

    log_progress("E3.6", f"Found {len(baseline_saldos)} baseline saldo entries")

    # Check each reconciled account for transactions around 31/12 dates
    for account in reconciled_accounts:
        banco = account.get('banco', '').strip().lower()
        tipo = account.get('tipo_conta', '')
        periodo = account.get('periodo_cobertura', {})
        inicio = periodo.get('inicio', '')
        fim = periodo.get('fim', '')

        # Check if this account covers any 31/12 date
        for (bl_banco, bl_ano), bl_info in baseline_saldos.items():
            # Fix 4.4: use canonical bank codes for comparison instead of
            # substring matching which can produce false positives (e.g.
            # "c6" matching "abc6xyz"). Canonicalize both sides.
            bl_canonical = _BANCO_DISPLAY_TO_CANONICAL.get(bl_banco, bl_banco)
            acct_canonical = _BANCO_DISPLAY_TO_CANONICAL.get(banco, banco)
            if bl_canonical != acct_canonical and bl_banco not in banco and banco not in bl_banco:
                continue

            target_date = f"{bl_ano}-12-31"
            if inicio <= target_date <= fim:
                # This account covers the 31/12 date — compare saldos
                # Look for the closest saldo to 31/12 in the account
                account_saldo_on_date = None

                # Check if saldo_final is exactly on 31/12
                if fim == target_date:
                    account_saldo_on_date = account.get('saldo_final')

                if account_saldo_on_date is not None:
                    bl_saldo = bl_info['saldo']
                    diff = abs(bl_saldo - account_saldo_on_date)
                    pct = (diff / abs(bl_saldo) * 100) if bl_saldo != 0 else float('inf')

                    if diff > _TOLERANCE_BASELINE_DIFF:  # More than threshold difference
                        account_desc = f"{account['banco']} {tipo}"
                        baseline_warnings[account_desc].append(
                            f"Saldo em {target_date}: baseline IRPF={bl_saldo:.2f}, "
                            f"extrato={account_saldo_on_date:.2f}, "
                            f"diff={diff:.2f} ({pct:.1f}%) "
                            f"[membro: {bl_info['member']}]"
                        )

    return baseline_warnings


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
            log_progress("E3.1", f"Skipping {fpath.name} (skip rule)")
            continue

        data = read_json(fpath)
        if data is None:
            load_errors.append(fpath.name)
            continue

        normalize_periodo_in_extract(data)

        if should_skip_extract(data):
            log_progress("E3.1", f"Skipping {fpath.name} (type={data.get('tipo')})")
            continue

        # Check for transacoes
        if 'transacoes' not in data:
            log_progress("E3.1", f"Skipping {fpath.name} (no transacoes field)")
            continue

        # Faturas have data_vencimento instead of periodo — synthesize periodo
        if 'periodo' not in data and data.get('tipo', '').startswith('fatura'):
            venc = data.get('data_vencimento', '').strip()

            # (#10) Explicit logging for faturas without data_vencimento
            if not venc:
                txns = data.get('transacoes', [])
                txn_dates = [t.get('data', '') for t in txns if t.get('data')]
                if not txn_dates:
                    log_progress(
                        "E3.1",
                        f"Skipping {fpath.name}: fatura with empty data_vencimento "
                        f"and no transactions"
                    )
                    continue
                else:
                    log_progress(
                        "E3.1",
                        f"Fatura {fpath.name} has empty data_vencimento, "
                        f"deriving periodo from {len(txns)} transactions"
                    )
                    data['periodo'] = {
                        'inicio': min(txn_dates),
                        'fim': max(txn_dates)
                    }
                    data['saldo_inicial'] = data.get('saldo_anterior') or 0
                    data['saldo_final'] = data.get('saldo_atual') or 0

            if venc and 'periodo' not in data:
                # Derive periodo from data_vencimento (fatura covers ~30 days before)
                try:
                    dt_venc = datetime.strptime(venc, '%Y-%m-%d')
                    # Use vencimento minus 30 days as a better approximation
                    dt_start = dt_venc - timedelta(days=30)
                    synth_inicio = dt_start.strftime('%Y-%m-%d')

                    data['periodo'] = {
                        'inicio': synth_inicio,
                        'fim': venc
                    }
                    data['saldo_inicial'] = data.get('saldo_anterior') or 0
                    data['saldo_final'] = data.get('saldo_atual') or 0
                except ValueError:
                    pass

                # (#4) Adjust periodo.inicio if actual transactions start earlier
                if 'periodo' in data:
                    txns = data.get('transacoes', [])
                    txn_dates = [t.get('data', '') for t in txns if t.get('data')]

                    if txn_dates:
                        actual_min_date = min(txn_dates)
                        current_inicio = data['periodo'].get('inicio', '')

                        if actual_min_date and actual_min_date < current_inicio:
                            log_progress(
                                "E3.1",
                                f"Adjusted fatura periodo for {fpath.name}: "
                                f"synth={current_inicio} -> actual={actual_min_date}"
                            )
                            data['periodo']['inicio'] = actual_min_date

            # Final fallback: derive from transaction dates
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

        # Guard: warn and drop transactions whose dates are >6 months
        # before the extract's periodo.inicio (likely misclassified data,
        # e.g. investment position screenshots mistakenly typed as extracts)
        periodo_inicio = data.get('periodo', {}).get('inicio', '')
        if periodo_inicio:
            try:
                dt_inicio = datetime.strptime(periodo_inicio[:10], '%Y-%m-%d')
                cutoff = dt_inicio - timedelta(days=180)
                txns = data.get('transacoes', [])
                anachronic = [
                    t for t in txns
                    if t.get('data', '') and t['data'][:10] < cutoff.strftime('%Y-%m-%d')
                ]
                if anachronic:
                    log_progress(
                        "E3.1",
                        f"WARNING: {fpath.name} has {len(anachronic)} transaction(s) "
                        f">6 months before periodo.inicio ({periodo_inicio}). "
                        f"Dropping anachronic transactions (likely duplicate/misclassified)."
                    )
                    kept = [t for t in txns if t not in anachronic]
                    data['transacoes'] = kept
            except (ValueError, TypeError):
                pass

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
    2. Merge all transactions (with source tracking)
    3. Deduplicate only across files (#3)
    4. Sort chronologically
    5. Return consolidated record
    """
    if not file_group:
        return None

    # Sort by period start
    sorted_group = sorted(
        file_group,
        key=lambda x: x[1].get('periodo', {}).get('inicio') or ''
    )

    # Collect metadata from first file
    first_path, first_data = sorted_group[0]
    banco = first_data.get('banco', first_data.get('instituicao', '')).strip()
    tipo = first_data.get('tipo', '').strip()
    # Normalize tipo using config equivalences (same as get_account_key)
    tipo = ACCOUNT_TYPE_EQUIVALENCES.get(tipo, tipo)
    # v2.1: Use same moeda resolution as get_account_key() — check conta.moeda fallback
    moeda = first_data.get('moeda', '').strip()
    if not moeda:
        conta = first_data.get('conta', {})
        if isinstance(conta, dict):
            moeda = conta.get('moeda', '').strip()
    if not moeda:
        log_progress("E3.3", f"[WARN] moeda ausente em {first_path.name}, usando default BRL")
        moeda = 'BRL'

    # Use canonical tipo for output
    tipo_conta = TIPO_CANONICAL.get(tipo, tipo)

    # For faturas, get titular from any file (they should all match)
    titular = first_data.get('titular') or first_data.get('cartao')
    if isinstance(titular, str):
        titular = titular.strip()

    # Collect all transactions across files, tracking source (#3)
    all_transactions_with_sources = []
    for path, data in sorted_group:
        transacoes = data.get('transacoes', [])
        source_name = path.name
        if isinstance(transacoes, list):
            for txn in transacoes:
                all_transactions_with_sources.append((txn, source_name))

    # Deduplicate (only across files, not within)
    dedup_txns, dup_count, dedup_details = deduplicate_transactions(all_transactions_with_sources)
    # Fix 3.1: log each dedup action for auditability
    for detail in dedup_details:
        log_progress("E3.3", detail)

    # Sort chronologically with proper date parsing
    dedup_txns.sort(key=lambda x: _parse_date_for_sort(x.get('data') or ''))

    # Determine period coverage (v2.1: also try data_inicio/data_fim keys from E2)
    periodo_obj_first = sorted_group[0][1].get('periodo', {})
    periodo_inicio = periodo_obj_first.get('inicio', '') or periodo_obj_first.get('data_inicio', '')
    periodo_obj_last = sorted_group[-1][1].get('periodo', {})
    periodo_fim = periodo_obj_last.get('fim', '') or periodo_obj_last.get('data_fim', '')

    # Use first file's saldo_inicial and last file's saldo_final (#9)
    saldo_inicial = first_data.get('saldo_inicial')
    saldo_final = sorted_group[-1][1].get('saldo_final')

    saldo_inicial_unknown = False
    saldo_final_unknown = False

    if saldo_inicial is None:
        log_progress(
            "E3.3",
            f"WARNING: {banco} {tipo} has saldo_inicial=None, using 0"
        )
        saldo_inicial = 0
        saldo_inicial_unknown = True
    if saldo_final is None:
        log_progress(
            "E3.3",
            f"WARNING: {banco} {tipo} has saldo_final=None, using 0"
        )
        saldo_final = 0
        saldo_final_unknown = True

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
        'saldo_inicial_unknown': saldo_inicial_unknown,
        'saldo_final': saldo_final,
        'saldo_final_unknown': saldo_final_unknown,
        'fontes': fontes,
        'transacoes_total': len(dedup_txns),
        'transacoes_duplicadas_removidas': dup_count,
        'transacoes': dedup_txns
    }

    return reconciled


def generate_output_filename(reconciled: Dict[str, Any]) -> str:
    """
    Generate filename for E3 output.
    All types use YYYYMM format (#6).
    For conta types: {banco}_{tipo_conta}_{moeda}_{YYYYMM}_{YYYYMM}-3_reconciled.json
    For fatura types: {banco}_{tipo_conta}_{YYYYMM}_{YYYYMM}-3_reconciled.json
    """
    banco_raw = reconciled['banco'].strip()
    banco = _BANCO_DISPLAY_TO_CANONICAL.get(banco_raw.lower(), banco_raw.lower().replace(' ', ''))
    tipo_conta = reconciled['tipo_conta'].lower()
    moeda = reconciled['moeda'].upper()

    periodo = reconciled['periodo_cobertura']
    inicio = periodo['inicio']  # YYYY-MM-DD
    fim = periodo['fim']

    # Extract YYYYMM from ISO date
    inicio_ym = inicio[:7].replace('-', '')  # YYYY-MM -> YYYYMM
    fim_ym = fim[:7].replace('-', '')

    if tipo_conta.startswith('fatura'):
        # Faturas: no moeda field
        filename = f"{banco}_{tipo_conta}_{inicio_ym}_{fim_ym}-3_reconciled.json"
    else:
        # Conta types: include moeda
        filename = f"{banco}_{tipo_conta}_{moeda}_{inicio_ym}_{fim_ym}-3_reconciled.json"

    return filename


def main(root_dir: Path = None):
    """Main reconciliation pipeline."""
    if root_dir:
        _init_config(root_dir)

    base_dir = _BASE_DIR

    print("=" * 80)
    print("E3 RECONCILIATION STAGE - Deterministic Account Reconciliation")
    print("=" * 80)

    # Paths
    e2_dir = base_dir / 'processed' / 'E2_extracts'
    e3_dir = base_dir / 'processed' / 'E3_reconciled'
    logs_dir = base_dir / 'logs'

    log_progress("E3.0", f"Base directory: {base_dir}")
    log_progress("E3.0", f"E2 input: {e2_dir}")
    log_progress("E3.0", f"E3 output: {e3_dir}")

    # Step 0: Clean output directory (#1)
    cleanup_e3_directory(e3_dir)

    # Step 1: Load and group
    file_groups, grouped = load_and_group_e2_extracts(e2_dir)

    if not grouped:
        # IRPF-only (baseline) ou só posições de investimento: não há *-2_extract.json
        # com transações de conta/fatura — E3 não tem o que reconciliar, mas o
        # pipeline ainda pode seguir (E4 patrimônio + posições a partir de E2).
        if e2_dir.exists() and any(e2_dir.glob("*.json")):
            log_progress(
                "E3",
                "SKIP: Nenhuma conta corrente/fatura para reconciliar — E2_extracts só tem "
                "baseline IRPF e/ou extratos sem transações reconciliáveis. "
                "Seguindo sem arquivos em E3_reconciled.",
            )
            print(
                "\n[SUMMARY] No bank/card accounts to reconcile; E2 has other JSON — "
                "continuing pipeline (patrimônio/posições via E4).",
                file=sys.stderr,
            )
            sys.exit(0)
        log_progress("E3", "FATAL: No accounts to reconcile — E2_extracts vazio ou corrompido.")
        print("\n[SUMMARY] No accounts found. No files written.", file=sys.stderr)
        sys.exit(1)

    # Step 2: Validate saldo continuity and detect temporal gaps (#8)
    log_progress("E3.2", f"Validating saldo continuity and temporal gaps across {len(grouped)} accounts...")
    continuity_warnings, temporal_gaps = validate_saldo_and_gaps(file_groups)

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
        log_progress("E3", "FATAL: No accounts were successfully reconciled.")
        print("\n[SUMMARY] Reconciliation failed for all accounts.", file=sys.stderr)
        sys.exit(1)

    # Step 4: Write output files
    log_progress("E3.4", f"Writing {len(reconciled_accounts)} E3 reconciled files...")
    written_files = []
    write_errors = []

    for reconciled in reconciled_accounts:
        filename = generate_output_filename(reconciled)
        output_path = e3_dir / filename

        # Fix 2.3: use atomic writes to prevent partial files on crash
        if _pc.write_json_atomic(output_path, reconciled):
            written_files.append(filename)
            _pc.validate_artifact(output_path, "e3_reconciled.schema.json")
            log_progress("E3.4", f"Wrote {filename}")
        else:
            write_errors.append(filename)

    # Step 5: Validate against baseline (#7)
    log_progress("E3.6", "Validating accounts against IRPF baseline...")
    baseline_file = e2_dir / 'baseline_patrimonial-1.5_consolidated.json'
    baseline_warnings = validate_against_baseline(reconciled_accounts, baseline_file)

    for account_name, warnings_list in baseline_warnings.items():
        for warning in warnings_list:
            log_progress("E3.6", f"BASELINE WARNING ({account_name}): {warning}")

    # Step 6: Generate reconciliation log
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
        summary_lines.append("## Saldo Continuity & Temporal Warnings")
        for account_key, warnings_list in continuity_warnings.items():
            for warning in warnings_list:
                summary_lines.append(f"- {account_key}: {warning}")
        summary_lines.append("")

    if baseline_warnings:
        summary_lines.append("## Baseline Validation Warnings")
        for account_name, warnings_list in baseline_warnings.items():
            for warning in warnings_list:
                summary_lines.append(f"- {account_name}: {warning}")
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

    # Write temporal gaps to qa_log.md (#8, Fix #9: clean old E3 sections first)
    if temporal_gaps:
        qa_log_file = logs_dir / 'qa_log.md'
        try:
            # Read existing content and remove old E3 sections to avoid accumulation
            old_content = ""
            if qa_log_file.exists():
                with open(qa_log_file, 'r', encoding='utf-8') as f:
                    old_content = f.read()

            # Strip previous E3 Temporal Gaps sections (everything from header to next ## or EOF)
            cleaned = re.sub(
                r'\n*## E3 Temporal Gaps[^\n]*\n(?:- [^\n]*\n)*',
                '',
                old_content
            )

            # Write back with new E3 section
            with open(qa_log_file, 'w', encoding='utf-8') as f:
                if not cleaned.strip().startswith("# QA Log"):
                    f.write("# QA Log\n\n")
                    f.write(cleaned.strip() + "\n")
                else:
                    f.write(cleaned.rstrip() + "\n")
                f.write(f"\n## E3 Temporal Gaps ({datetime.now().isoformat()})\n")
                for gap in temporal_gaps:
                    f.write(f"- {gap}\n")
            log_progress("E3.5", f"Wrote {len(temporal_gaps)} temporal gaps to {qa_log_file.name} (replaced old E3 section)")
        except Exception as e:
            log_progress("E3.5", f"ERROR: Failed to write qa_log: {e}")

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
        print(f"Saldo/temporal warnings:    {sum(len(v) for v in continuity_warnings.values())}")
    if baseline_warnings:
        print(f"Baseline warnings:          {sum(len(v) for v in baseline_warnings.values())}")
    if temporal_gaps:
        print(f"Temporal gaps logged:       {len(temporal_gaps)}")
    print("=" * 80)

    # Exit with error if any write errors or reconciliation errors occurred
    if write_errors or reconciliation_errors:
        n_errs = len(write_errors) + len(reconciliation_errors)
        log_progress("E3", f"FALHOU com {n_errs} erro(s) — exit code 1")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log_progress("E3", f"FATAL: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
