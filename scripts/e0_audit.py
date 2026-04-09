#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E0-audit — Auditoria de integridade entre data/ e E2_extracts/

Detecta problemas de roteamento (E0) que se propagariam pelo pipeline:
  1. Filename vs JSON content mismatch (banco, tipo, período)
  2. Arquivos órfãos (em data/ sem JSON correspondente, ou vice-versa)
  3. Possíveis duplicatas em data/ (mesmo banco+tipo+período)
  4. Cruzamento com inbox_log.md para renames suspeitos
  5. Gaps de saldo no E3
  6. Duplicatas por hash (conteúdo idêntico)
  7. Colisão de nomes no inbox/
  8. HTML disfarçado de XLS (detecção de formato)
  9. Nomes incorretos de extracts E2 (sufixo errado, zero duplicado)

Não altera nenhum arquivo — apenas imprime um relatório.
Use --fix-names para auto-corrigir nomes de extracts da checagem 9.

Usage:
  python scripts/e0_audit.py              # Relatório completo
  python scripts/e0_audit.py --check 1    # Apenas checagem 1
  python scripts/e0_audit.py --check 1,2  # Checagens 1 e 2
  python scripts/e0_audit.py --json       # Saída em JSON (para scripts)

Author: Claude Opus 4.6
Date: 2026-04-05
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# =============================================================================
# Paths
# =============================================================================
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent

DATA_DIR = PROJECT_DIR / "data"
E2_DIR = PROJECT_DIR / "processed" / "E2_extracts"
INBOX_LOG = PROJECT_DIR / "logs" / "inbox_log.md"

# =============================================================================
# Helpers
# =============================================================================

def normalize(s: str) -> str:
    """Lowercase, strip accents, replace spaces/hyphens with underscore."""
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[\s\-]+", "_", s)
    return s


def parse_data_filename(filename: str) -> dict[str, str]:
    """Parse a data/ filename like 'bradesco_extratoconta_202501_202512-0_original.pdf'
    into components: banco, tipo, periodo_raw."""
    # Remove -0_original suffix and extension
    stem = re.sub(r"-0_original$", "", Path(filename).stem)
    parts = stem.split("_")

    if len(parts) < 2:
        return {"banco": parts[0] if parts else "", "tipo": "", "periodo_raw": ""}

    banco = parts[0]
    # tipo is everything between banco and the first date-like segment
    tipo_parts = []
    periodo_parts = []
    for p in parts[1:]:
        if re.match(r"^\d{6}", p) and tipo_parts:
            periodo_parts.append(p)
        elif periodo_parts:
            # Already collecting period, this is an anomaly
            periodo_parts.append(p)
        else:
            tipo_parts.append(p)

    # If no period found, try again: tipo might be just parts[1]
    if not periodo_parts and len(parts) > 2:
        for i, p in enumerate(parts[1:], 1):
            if re.match(r"^\d{6}", p):
                tipo_parts = parts[1:i]
                periodo_parts = parts[i:]
                break

    tipo = "_".join(tipo_parts) if tipo_parts else ""
    periodo_raw = "_".join(periodo_parts) if periodo_parts else ""

    return {"banco": banco, "tipo": tipo, "periodo_raw": periodo_raw}


def parse_e2_filename(filename: str) -> dict[str, str]:
    """Parse an E2 filename like 'bradesco_extratoconta_202501_202512-2_extract.json'."""
    stem = re.sub(r"-2_extract$", "", Path(filename).stem)
    # Also handle -0_original-2_extract (Itaú files with double suffix)
    stem = re.sub(r"-0_original$", "", stem)
    parts = stem.split("_")

    if len(parts) < 2:
        return {"banco": parts[0] if parts else "", "tipo": "", "periodo_raw": ""}

    banco = parts[0]
    tipo_parts = []
    periodo_parts = []
    for p in parts[1:]:
        if re.match(r"^\d{6}", p):
            periodo_parts.append(p)
        elif periodo_parts:
            periodo_parts.append(p)
        else:
            tipo_parts.append(p)

    if not periodo_parts and len(parts) > 2:
        for i, p in enumerate(parts[1:], 1):
            if re.match(r"^\d{6}", p):
                tipo_parts = parts[1:i]
                periodo_parts = parts[i:]
                break

    tipo = "_".join(tipo_parts) if tipo_parts else ""
    periodo_raw = "_".join(periodo_parts) if periodo_parts else ""

    return {"banco": banco, "tipo": tipo, "periodo_raw": periodo_raw}


# Load institution mappings from config/institutions.json
def _load_institutions() -> dict:
    inst_path = PROJECT_DIR / "config" / "institutions.json"
    if not inst_path.exists():
        print(f"  [WARN] config/institutions.json não encontrado — matching de banco/tipo será impreciso")
        return {}
    try:
        with open(inst_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] Erro ao carregar institutions.json: {e}")
        return {}

_INSTITUTIONS = _load_institutions()
BANCO_CANONICAL = _INSTITUTIONS.get("banco_canonical", {})
TIPO_ALIASES = _INSTITUTIONS.get("tipo_aliases", {})


# =============================================================================
# Check 1: Filename vs JSON content mismatch
# =============================================================================

def check_filename_vs_content() -> list[dict[str, Any]]:
    """Compare E2 JSON filename components against JSON content fields."""
    issues: list[dict[str, Any]] = []

    if not E2_DIR.is_dir():
        issues.append({"file": "E2_extracts/", "issue": "Diretório não existe", "severity": "ERROR"})
        return issues

    for fpath in sorted(E2_DIR.glob("*-2_extract.json")):
        fname_parts = parse_e2_filename(fpath.name)
        fname_banco = normalize(fname_parts["banco"])

        # Skip 0-byte files (truncated by e-reset on FS without delete)
        if fpath.stat().st_size == 0:
            issues.append({
                "file": fpath.name,
                "issue": "Arquivo 0 bytes (truncado por e-reset) — skip",
                "severity": "INFO",
            })
            continue

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            issues.append({
                "file": fpath.name,
                "issue": f"JSON inválido: {e}",
                "severity": "ERROR",
            })
            continue

        # Skip non-dict E2 files (e.g., fatura arrays, tombstones, 0-byte)
        if not isinstance(data, dict):
            if isinstance(data, list) and len(data) == 0:
                continue  # empty array from truncated file — silent skip
            issues.append({
                "file": fpath.name,
                "issue": f"JSON é {type(data).__name__} (esperado dict) — skip",
                "severity": "INFO",
            })
            continue

        if "_tombstone" in data:
            continue

        # --- Check banco ---
        json_banco = normalize(data.get("banco", ""))
        canonical = BANCO_CANONICAL.get(fname_banco, fname_banco)
        canonical_norm = normalize(canonical)

        if json_banco and canonical_norm and canonical_norm not in json_banco and json_banco not in canonical_norm:
            issues.append({
                "file": fpath.name,
                "issue": f"Banco no filename '{fname_parts['banco']}' (→ '{canonical}') ≠ JSON '{data.get('banco')}'",
                "severity": "WARNING",
                "filename_banco": fname_parts["banco"],
                "json_banco": data.get("banco"),
            })

        # --- Check tipo ---
        json_tipo = normalize(data.get("tipo", ""))
        fname_tipo = fname_parts["tipo"]
        fname_tipo_norm = normalize(fname_tipo)

        if json_tipo and fname_tipo_norm:
            aliases = TIPO_ALIASES.get(fname_tipo_norm, [fname_tipo_norm])
            aliases_norm = [normalize(a) for a in aliases]
            if not any(a in json_tipo or json_tipo in a for a in aliases_norm):
                issues.append({
                    "file": fpath.name,
                    "issue": f"Tipo no filename '{fname_tipo}' ≠ JSON '{data.get('tipo')}'",
                    "severity": "WARNING",
                    "filename_tipo": fname_tipo,
                    "json_tipo": data.get("tipo"),
                })

    return issues


# =============================================================================
# Check 2: Orphan files (data/ ↔ E2_extracts/)
# =============================================================================

def check_orphans() -> list[dict[str, Any]]:
    """Find files in data/financial_statements/ without corresponding E2 JSONs, and vice-versa."""
    issues: list[dict[str, Any]] = []

    if not DATA_DIR.is_dir():
        issues.append({"file": "data/", "issue": "Diretório não existe", "severity": "ERROR"})
        return issues

    # Build set of data/ file stems across ALL subdirectories
    data_stems: dict[str, Path] = {}
    for f in DATA_DIR.rglob("*"):
        if f.is_file() and not f.name.startswith("."):
            stem = re.sub(r"-0_original$", "", f.stem)
            data_stems[normalize(stem)] = f

    # Build set of E2 stems
    e2_stems: dict[str, Path] = {}
    if E2_DIR.is_dir():
        for f in E2_DIR.glob("*-2_extract.json"):
            stem = re.sub(r"-2_extract$", "", f.stem)
            stem = re.sub(r"-0_original$", "", stem)  # Handle double suffix
            e2_stems[normalize(stem)] = f

    # Files in E2 with no corresponding data/ file
    # (Note: some E2 files like baseline_patrimonial are synthesized, not from data/)
    SYNTHESIZED_PREFIXES = {"baseline_patrimonial", "dados_imoveis"}

    for stem_norm, fpath in sorted(e2_stems.items()):
        if any(stem_norm.startswith(normalize(p)) for p in SYNTHESIZED_PREFIXES):
            continue
        if stem_norm not in data_stems:
            issues.append({
                "file": fpath.name,
                "issue": f"E2 JSON sem arquivo original correspondente em data/financial_statements/",
                "severity": "INFO",
            })

    # Files in data/ with no E2 JSON (might just not have been processed yet)
    for stem_norm, fpath in sorted(data_stems.items()):
        if stem_norm not in e2_stems:
            issues.append({
                "file": fpath.name,
                "issue": f"Arquivo em data/ sem E2 JSON correspondente — talvez não processado?",
                "severity": "INFO",
            })

    return issues


# =============================================================================
# Check 3: Possible duplicates in data/
# =============================================================================

def check_duplicates() -> list[dict[str, Any]]:
    """Find data/ files that might be duplicates (same banco+tipo+period overlap)."""
    issues: list[dict[str, Any]] = []

    fin_dir = DATA_DIR / "financial_statements"
    if not fin_dir.is_dir():
        return issues

    # Group by (banco, tipo)
    groups: dict[tuple[str, str], list[tuple[str, str, Path]]] = defaultdict(list)
    for f in sorted(fin_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            parts = parse_data_filename(f.name)
            key = (normalize(parts["banco"]), normalize(parts["tipo"]))
            groups[key].append((parts["periodo_raw"], f.name, f))

    for (banco, tipo), entries in sorted(groups.items()):
        if len(entries) < 2:
            continue

        # Extract period ranges and check for overlaps
        periods: list[tuple[str, str, str, str]] = []  # (start, end, periodo_raw, filename)
        for periodo_raw, fname, fpath in entries:
            # periodo_raw like "202501_202512" or "202603" or "202603a"
            matches = re.findall(r"(\d{6})", periodo_raw)
            if len(matches) >= 2:
                periods.append((matches[0], matches[-1], periodo_raw, fname))
            elif len(matches) == 1:
                periods.append((matches[0], matches[0], periodo_raw, fname))

        # Check for exact duplicates (same period)
        period_counter = Counter((p[0], p[1]) for p in periods)
        for (start, end), count in period_counter.items():
            if count > 1:
                dupes = [p[3] for p in periods if p[0] == start and p[1] == end]
                issues.append({
                    "file": ", ".join(dupes),
                    "issue": f"Possível duplicata: {banco}/{tipo} período {start}-{end} aparece {count}x",
                    "severity": "WARNING",
                })

        # Check for overlapping periods (one file contained inside another)
        for i, (s1, e1, _, f1) in enumerate(periods):
            for j, (s2, e2, _, f2) in enumerate(periods):
                if i >= j:
                    continue
                # Check if period2 is fully contained in period1 or vice-versa
                if int(s1) <= int(s2) and int(e1) >= int(e2) and (s1, e1) != (s2, e2):
                    issues.append({
                        "file": f"{f1} vs {f2}",
                        "issue": f"Período sobreposto: {f1} ({s1}-{e1}) contém {f2} ({s2}-{e2})",
                        "severity": "INFO",
                    })
                elif int(s2) <= int(s1) and int(e2) >= int(e1) and (s1, e1) != (s2, e2):
                    issues.append({
                        "file": f"{f2} vs {f1}",
                        "issue": f"Período sobreposto: {f2} ({s2}-{e2}) contém {f1} ({s1}-{e1})",
                        "severity": "INFO",
                    })

    return issues


# =============================================================================
# Check 4: inbox_log.md cross-reference
# =============================================================================

def check_inbox_log() -> list[dict[str, Any]]:
    """Check inbox_log.md for suspicious renames (original ≠ final name)."""
    issues: list[dict[str, Any]] = []

    if not INBOX_LOG.exists():
        issues.append({"file": "inbox_log.md", "issue": "Arquivo não encontrado", "severity": "INFO"})
        return issues

    text = INBOX_LOG.read_text(encoding="utf-8")

    # Parse detalhamento table rows: | # | Nome original | Nome final | Destino | Status |
    # Only process lines after "### Detalhamento" and match rows where:
    # - First column is a plain integer
    # - Nome fields look like filenames (contain a dot or dash)
    detalhamento_section = text.split("### Detalhamento")[-1] if "### Detalhamento" in text else ""
    pattern = r"\|\s*(\d+)\s*\|\s*(\S+\.\S+)\s*\|\s*(\S+\.\S+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
    raw_matches = re.findall(pattern, detalhamento_section)
    matches = [(m[1], m[2], m[3], m[4]) for m in raw_matches]

    for original, final, destino, status in matches:
        original = original.strip()
        final = final.strip()

        if original != final:
            issues.append({
                "file": final,
                "issue": f"Renomeado no inbox: '{original}' → '{final}'",
                "severity": "INFO",
                "original_name": original,
                "final_name": final,
            })

    return issues


# =============================================================================
# E3 saldo discontinuity (bonus check)
# =============================================================================

def check_saldo_gaps() -> list[dict[str, Any]]:
    """Check E3 reconciled files for saldo discontinuities across periods
    of the same account (saldo_final of period N ≠ saldo_inicial of period N+1)."""
    issues: list[dict[str, Any]] = []

    e3_dir = PROJECT_DIR / "processed" / "E3_reconciled"
    if not e3_dir.is_dir():
        return issues

    # Group by (banco, tipo_conta, moeda)
    accounts: dict[tuple, list] = defaultdict(list)

    for fpath in sorted(e3_dir.glob("*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        if "_tombstone" in data:
            continue

        banco = data.get("banco", "")
        tipo = data.get("tipo_conta", "")
        moeda = data.get("moeda", "")
        periodo = data.get("periodo_cobertura", {})
        saldo_i = data.get("saldo_inicial")
        saldo_f = data.get("saldo_final")

        if saldo_i is None and saldo_f is None:
            continue

        key = (normalize(banco), normalize(tipo), normalize(moeda))
        accounts[key].append({
            "file": fpath.name,
            "inicio": periodo.get("inicio", ""),
            "fim": periodo.get("fim", ""),
            "saldo_inicial": saldo_i,
            "saldo_final": saldo_f,
        })

    # For each account, sort by period start and check continuity
    for key, entries in sorted(accounts.items()):
        sorted_entries = sorted(entries, key=lambda e: e["inicio"])

        for i in range(len(sorted_entries) - 1):
            curr = sorted_entries[i]
            nxt = sorted_entries[i + 1]

            if curr["saldo_final"] is None or nxt["saldo_inicial"] is None:
                continue

            try:
                diff = abs(float(nxt["saldo_inicial"]) - float(curr["saldo_final"]))
            except (ValueError, TypeError):
                continue

            if diff > 0.01:  # tolerance for rounding
                issues.append({
                    "file": f"{curr['file']} → {nxt['file']}",
                    "issue": (
                        f"Gap de saldo: {key[0]}/{key[1]} ({key[2]}) — "
                        f"fim {curr['fim']} = {curr['saldo_final']}, "
                        f"início {nxt['inicio']} = {nxt['saldo_inicial']} "
                        f"(diff: {diff:.2f})"
                    ),
                    "severity": "WARNING",
                })

    return issues


# =============================================================================
# Check 6: Duplicate files by content hash (SHA-256)
# =============================================================================

def check_hash_duplicates() -> list[dict[str, Any]]:
    """Find files in data/ and inbox/ with identical content (same SHA-256 hash)."""
    import hashlib

    issues: list[dict[str, Any]] = []

    # Collect files from data/ and inbox/
    dirs_to_scan = [DATA_DIR, PROJECT_DIR / "inbox"]
    hash_map: dict[str, list[Path]] = defaultdict(list)

    for scan_dir in dirs_to_scan:
        if not scan_dir.is_dir():
            continue
        for f in scan_dir.rglob("*"):
            if f.is_file() and not f.name.startswith(".") and f.stat().st_size > 0:
                h = hashlib.sha256(f.read_bytes()).hexdigest()
                hash_map[h].append(f)

    for h, files in sorted(hash_map.items()):
        if len(files) < 2:
            continue

        names = [str(f.relative_to(PROJECT_DIR)) for f in files]
        # Cross-directory duplicates (inbox vs data) are more serious
        dirs_involved = {f.relative_to(PROJECT_DIR).parts[0] for f in files}
        if len(dirs_involved) > 1:
            severity = "WARNING"
            msg = f"Conteúdo idêntico entre diretórios (SHA256: {h[:12]}...): {', '.join(names)}"
        else:
            severity = "WARNING"
            msg = f"Conteúdo idêntico dentro de {dirs_involved.pop()}/ (SHA256: {h[:12]}...): {', '.join(names)}"

        issues.append({
            "file": ", ".join(f.name for f in files),
            "issue": msg,
            "severity": severity,
        })

    return issues


# =============================================================================
# Check 7: Name collision detection in inbox/
# =============================================================================

def check_name_collisions() -> list[dict[str, Any]]:
    """Detect files in inbox/ that would generate the same destination name,
    but have different content (different SHA-256 hash).
    Also checks against files already in data/ to catch collisions with
    previously routed files."""
    import hashlib

    issues: list[dict[str, Any]] = []

    inbox_dir = PROJECT_DIR / "inbox"
    if not inbox_dir.is_dir():
        return issues

    inbox_files = [f for f in inbox_dir.rglob("*") if f.is_file() and not f.name.startswith(".")]
    if not inbox_files:
        return issues

    def compute_dest_name(filename: str) -> str:
        """Simulate the E0 naming: strip path, normalize to the canonical
        destination name that E0 would generate.
        Since E0 is LLM-driven and names are often already in final form,
        we use the filename as-is (which is typically already renamed).
        For files that already have -0_original, that IS the dest name.
        For files without it, we add -0_original before the extension."""
        stem = Path(filename).stem
        ext = Path(filename).suffix
        if "-0_original" in stem:
            return filename
        return f"{stem}-0_original{ext}"

    # Group inbox files by their would-be destination name
    dest_groups: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    for f in inbox_files:
        dest_name = compute_dest_name(f.name)
        file_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        dest_groups[dest_name].append((f, file_hash))

    # Check for collisions within inbox/
    for dest_name, entries in sorted(dest_groups.items()):
        if len(entries) < 2:
            continue

        # Get unique hashes
        unique_hashes = set(h for _, h in entries)
        if len(unique_hashes) == 1:
            # Same content — this is a pure duplicate (check 6 handles this)
            continue

        # Different content, same dest name → COLLISION
        file_names = [f.name for f, _ in entries]
        issues.append({
            "file": ", ".join(file_names),
            "issue": (
                f"COLISÃO: {len(entries)} arquivos no inbox/ gerariam o mesmo nome "
                f"'{dest_name}' mas têm conteúdo diferente ({len(unique_hashes)} hashes distintos). "
                f"Necessário sufixo de letra (a, b, c...)."
            ),
            "severity": "ERROR",
            "dest_name": dest_name,
            "files": file_names,
        })

    # Also check inbox files against existing data/ files
    data_files: dict[str, str] = {}  # name → hash
    for scan_dir in [DATA_DIR / "financial_statements", DATA_DIR / "income_tax_br",
                     DATA_DIR / "real_estate", DATA_DIR / "vehicles",
                     PROJECT_DIR / "members"]:
        if not scan_dir.is_dir():
            continue
        for f in scan_dir.iterdir():
            if f.is_file() and not f.name.startswith("."):
                data_files[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()

    for dest_name, entries in sorted(dest_groups.items()):
        if len(entries) != 1:
            continue  # Multi-file collisions already handled above

        inbox_file, inbox_hash = entries[0]
        if dest_name in data_files:
            existing_hash = data_files[dest_name]
            if inbox_hash != existing_hash:
                issues.append({
                    "file": inbox_file.name,
                    "issue": (
                        f"COLISÃO com data/: '{dest_name}' já existe em data/ com conteúdo "
                        f"diferente. Inbox hash: {inbox_hash[:12]}..., data/ hash: {existing_hash[:12]}... "
                        f"Necessário sufixo de letra."
                    ),
                    "severity": "ERROR",
                    "dest_name": dest_name,
                })

    return issues


# =============================================================================
# Check 8: HTML-disguised-as-XLS detection
# =============================================================================

def check_html_as_xls() -> list[dict[str, Any]]:
    """Detect .xls files that are actually HTML (exported by Santander/Itaú internet banking).

    Some banks export files with .xls extension that are actually HTML tables.
    xlrd cannot read these, causing parsing failures. This check identifies them
    so they can be handled by an HTML parser or converted before processing.
    """
    issues = []

    # Scan all .xls files in data/ and inbox/
    scan_dirs = [
        DATA_DIR / "financial_statements",
        PROJECT_DIR / "inbox",
    ]

    html_signatures = [b'<html', b'<!doctype', b'<!DOCTYPE', b'<HTML', b'<?xml']

    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        for f in sorted(scan_dir.iterdir()):
            if not f.is_file() or not f.name.lower().endswith('.xls'):
                continue
            if f.stat().st_size == 0:
                continue

            try:
                # Read first 256 bytes to check file signature
                header = f.read_bytes()[:256]

                is_html = any(sig in header for sig in html_signatures)
                if is_html:
                    # Determine relative path for display
                    try:
                        rel = f.relative_to(PROJECT_DIR)
                    except ValueError:
                        rel = f.name

                    issues.append({
                        "file": str(rel),
                        "issue": (
                            f"HTML disfarçado de XLS: '{f.name}' tem extensão .xls mas é "
                            f"na verdade um arquivo HTML. xlrd não consegue ler este formato. "
                            f"Necessário converter via BeautifulSoup ou usar parser HTML dedicado."
                        ),
                        "severity": "WARNING",
                    })
            except Exception as e:
                issues.append({
                    "file": f.name,
                    "issue": f"Erro ao verificar formato de '{f.name}': {e}",
                    "severity": "INFO",
                })

    return issues


def check_extract_naming() -> list[dict[str, Any]]:
    """Check 9: Detect E2 extract files with incorrect naming conventions.

    Valid patterns:
      - *-2_extract.json  (standard E2 extract)
      - *-1.5_consolidated.json  (E1.5 baseline)
      - *-0_original-2_extract.json  (extract from backup original)

    Invalid patterns (common LLM agent mistakes):
      - *-0_extract.json  (wrong suffix — should be -2_extract)
      - *-0-0_original-2_extract.json  (double zero — LLM naming bug)
    """
    issues = []
    if not E2_DIR.exists():
        return issues

    for f in sorted(E2_DIR.glob("*.json")):
        name = f.name

        # Skip valid patterns
        if name.endswith("-2_extract.json"):
            continue
        if name.endswith("-1.5_consolidated.json"):
            continue

        # Detect -0_extract (should be -2_extract)
        if re.search(r"-0_extract\.json$", name):
            correct_name = re.sub(r"-0_extract\.json$", "-2_extract.json", name)
            correct_path = E2_DIR / correct_name
            if correct_path.exists() and correct_path.stat().st_size > 10:
                issues.append({
                    "file": name,
                    "issue": (
                        f"Nome incorreto: '{name}' usa sufixo '-0_extract' em vez de '-2_extract'. "
                        f"Arquivo correto '{correct_name}' já existe — este pode ser removido."
                    ),
                    "severity": "WARNING",
                })
            else:
                issues.append({
                    "file": name,
                    "issue": (
                        f"Nome incorreto: '{name}' usa sufixo '-0_extract' em vez de '-2_extract'. "
                        f"Renomear para '{correct_name}'."
                    ),
                    "severity": "ERROR",
                    "auto_fix": {"action": "rename", "from": name, "to": correct_name},
                })

        # Detect -0-0_original (double zero — LLM naming bug)
        if "-0-0_original-" in name:
            correct_name = name.replace("-0-0_original-", "-0_original-")
            correct_path = E2_DIR / correct_name
            if correct_path.exists() and correct_path.stat().st_size > 10:
                issues.append({
                    "file": name,
                    "issue": (
                        f"Nome duplicado: '{name}' tem '-0-0_original' (zero duplicado). "
                        f"Arquivo correto '{correct_name}' já existe — este pode ser removido."
                    ),
                    "severity": "WARNING",
                })
            else:
                issues.append({
                    "file": name,
                    "issue": (
                        f"Nome duplicado: '{name}' tem '-0-0_original' (zero duplicado). "
                        f"Renomear para '{correct_name}'."
                    ),
                    "severity": "ERROR",
                    "auto_fix": {"action": "rename", "from": name, "to": correct_name},
                })

    return issues


def fix_extract_naming(dry_run: bool = False) -> int:
    """Auto-fix E2 extract files with incorrect naming.

    Returns number of files fixed.
    """
    issues = check_extract_naming()
    fixed = 0
    for issue in issues:
        fix = issue.get("auto_fix")
        if not fix or fix["action"] != "rename":
            continue
        src = E2_DIR / fix["from"]
        dst = E2_DIR / fix["to"]
        if dry_run:
            print(f"  [DRY-RUN] Renomearia: {fix['from']} → {fix['to']}")
        else:
            src.rename(dst)
            print(f"  [FIX] Renomeado: {fix['from']} → {fix['to']}")
        fixed += 1

    # Clean up duplicates with correct version already existing
    for issue in issues:
        if "pode ser removido" in issue["issue"]:
            f = E2_DIR / issue["file"]
            if dry_run:
                print(f"  [DRY-RUN] Removeria duplicata: {issue['file']}")
            elif f.exists():
                f.unlink()
                print(f"  [FIX] Removida duplicata: {issue['file']}")
                fixed += 1

    return fixed


# =============================================================================
# Main
# =============================================================================

ALL_CHECKS = {
    1: ("Filename vs JSON content", check_filename_vs_content),
    2: ("Arquivos órfãos (data/ ↔ E2)", check_orphans),
    3: ("Possíveis duplicatas em data/", check_duplicates),
    4: ("Cross-reference inbox_log.md", check_inbox_log),
    5: ("Gaps de saldo no E3", check_saldo_gaps),
    6: ("Duplicatas por hash (conteúdo idêntico)", check_hash_duplicates),
    7: ("Colisão de nomes no inbox/ (conteúdo diferente, mesmo destino)", check_name_collisions),
    8: ("HTML disfarçado de XLS (detecção de formato)", check_html_as_xls),
    9: ("Nomes incorretos de extracts E2 (sufixo errado, zero duplicado)", check_extract_naming),
}


def main():
    parser = argparse.ArgumentParser(
        description="E0-audit — Auditoria de integridade data/ ↔ E2 ↔ E3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Checagens disponíveis:
  1 — Filename vs JSON content (banco/tipo mismatch)
  2 — Arquivos órfãos (data/ sem E2, ou E2 sem data/)
  3 — Possíveis duplicatas em data/ (mesmo banco+tipo+período)
  4 — Cross-reference com inbox_log.md (renames)
  5 — Gaps de saldo no E3 (descontinuidade entre períodos)
  6 — Duplicatas por hash SHA-256 (conteúdo idêntico em data/ e inbox/)
  7 — Colisão de nomes no inbox/ (conteúdo diferente, mesmo nome destino)
  8 — HTML disfarçado de XLS (detecção de formato incorreto)
  9 — Nomes incorretos de extracts E2 (sufixo -0_extract, zero duplicado)

Exemplos:
  python scripts/e0_audit.py              # Todas as checagens
  python scripts/e0_audit.py --check 1,3  # Só checagens 1 e 3
  python scripts/e0_audit.py --json       # Saída JSON
        """,
    )
    parser.add_argument(
        "--check", type=str, default=None,
        help="Checagens específicas (separadas por vírgula). Ex: --check 1,3",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Saída em formato JSON (para processamento automático).",
    )
    parser.add_argument(
        "--fix-names", action="store_true",
        help="Corrige automaticamente nomes incorretos de extracts E2 (check 9).",
    )

    args = parser.parse_args()

    # --fix-names: run check 9 + auto-fix
    if args.fix_names:
        print("=" * 60)
        print("  E0-audit — fix-names (correção automática de nomes E2)")
        print("=" * 60)
        issues = check_extract_naming()
        if not issues:
            print("  [OK] Nenhum problema de nomes encontrado.")
        else:
            for iss in issues:
                sev = iss["severity"]
                icon = {"ERROR": "!!!", "WARNING": " ! ", "INFO": " i "}.get(sev, " ? ")
                print(f"  [{icon}] {iss['file']}")
                print(f"        {iss['issue']}")
            fixed = fix_extract_naming(dry_run=False)
            print(f"\n  Corrigidos: {fixed} arquivo(s)")
        print("=" * 60)
        return

    # Determine which checks to run
    if args.check:
        check_ids = [int(c.strip()) for c in args.check.split(",")]
        invalid_ids = [cid for cid in check_ids if cid not in ALL_CHECKS]
        if invalid_ids:
            print(f"  [WARN] Checagem(ns) {invalid_ids} não existe(m). Disponíveis: {list(ALL_CHECKS.keys())}")
        check_ids = [cid for cid in check_ids if cid in ALL_CHECKS]
    else:
        check_ids = list(ALL_CHECKS.keys())

    all_issues: dict[int, list[dict]] = {}
    total_warnings = 0
    total_errors = 0
    total_info = 0

    for cid in check_ids:

        name, func = ALL_CHECKS[cid]
        issues = func()
        all_issues[cid] = issues

        for issue in issues:
            if issue["severity"] == "ERROR":
                total_errors += 1
            elif issue["severity"] == "WARNING":
                total_warnings += 1
            else:
                total_info += 1

    # Output
    if args.json:
        output = {
            "summary": {
                "errors": total_errors,
                "warnings": total_warnings,
                "info": total_info,
                "total": total_errors + total_warnings + total_info,
            },
            "checks": {
                str(cid): {
                    "name": ALL_CHECKS[cid][0],
                    "issues": issues,
                }
                for cid, issues in all_issues.items()
            },
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print("=" * 60)
        print("  E0-audit — Relatório de integridade")
        print(f"  Projeto: {PROJECT_DIR.name}")
        print("=" * 60)

        for cid in check_ids:
            if cid not in all_issues:
                continue
            name = ALL_CHECKS[cid][0]
            issues = all_issues[cid]
            print(f"\n--- Checagem {cid}: {name} ---")

            if not issues:
                print("  [OK] Nenhum problema encontrado.")
                continue

            for issue in issues:
                sev = issue["severity"]
                icon = {"ERROR": "!!!", "WARNING": " ! ", "INFO": " i "}[sev]
                print(f"  [{icon}] {issue['file']}")
                print(f"        {issue['issue']}")

        # Summary
        print(f"\n{'=' * 60}")
        total = total_errors + total_warnings + total_info
        print(f"  Resumo: {total} achado(s) — {total_errors} erros, {total_warnings} avisos, {total_info} info")
        if total_errors > 0:
            print("  AÇÃO REQUERIDA: há erros que precisam de correção.")
        elif total_warnings > 0:
            print("  RECOMENDAÇÃO: revisar avisos antes do próximo E-reset.")
        else:
            print("  [OK] Nenhum problema significativo detectado.")
        print("=" * 60)


if __name__ == "__main__":
    main()
