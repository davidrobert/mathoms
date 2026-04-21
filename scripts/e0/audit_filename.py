"""Checks 1, 7, 8, 9 — auditoria de naming e formato (A6g.2 — T1.c).

Cada função retorna ``list[dict]`` com chaves padronizadas
(``file``, ``issue``, ``severity``, …).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts.e0 import audit_helpers as _h


def check_filename_vs_content() -> list[dict[str, Any]]:
    """Compare E2 JSON filename components against JSON content fields."""
    issues: list[dict[str, Any]] = []

    if not _h.E2_DIR.is_dir():
        issues.append({"file": "E2_extracts/", "issue": "Diretório não existe", "severity": "ERROR"})
        return issues

    for fpath in sorted(_h.E2_DIR.glob("*-2_extract.json")):
        fname_parts = _h.parse_e2_filename(fpath.name)
        fname_banco = _h.normalize(fname_parts["banco"])

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
        json_banco = _h.normalize(data.get("banco", ""))
        canonical = _h.BANCO_CANONICAL.get(fname_banco, fname_banco)
        canonical_norm = _h.normalize(canonical)

        if json_banco and canonical_norm and canonical_norm not in json_banco and json_banco not in canonical_norm:
            issues.append({
                "file": fpath.name,
                "issue": f"Banco no filename '{fname_parts['banco']}' (→ '{canonical}') ≠ JSON '{data.get('banco')}'",
                "severity": "WARNING",
                "filename_banco": fname_parts["banco"],
                "json_banco": data.get("banco"),
            })

        # --- Check tipo ---
        json_tipo = _h.normalize(data.get("tipo", ""))
        fname_tipo = fname_parts["tipo"]
        fname_tipo_norm = _h.normalize(fname_tipo)

        if json_tipo and fname_tipo_norm:
            aliases = _h.TIPO_ALIASES.get(fname_tipo_norm, [fname_tipo_norm])
            aliases_norm = [_h.normalize(a) for a in aliases]
            if not any(a in json_tipo or json_tipo in a for a in aliases_norm):
                issues.append({
                    "file": fpath.name,
                    "issue": f"Tipo no filename '{fname_tipo}' ≠ JSON '{data.get('tipo')}'",
                    "severity": "WARNING",
                    "filename_tipo": fname_tipo,
                    "json_tipo": data.get("tipo"),
                })

    return issues


def check_name_collisions() -> list[dict[str, Any]]:
    """Detect files in inbox/ that would generate the same destination name,
    but have different content (different SHA-256 hash).
    Also checks against files already in data/ to catch collisions with
    previously routed files."""
    issues: list[dict[str, Any]] = []

    inbox_dir = _h.PROJECT_DIR / "inbox"
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
    for scan_dir in [_h.DATA_DIR / "financial_statements", _h.DATA_DIR / "income_tax_br",
                     _h.DATA_DIR / "real_estate", _h.DATA_DIR / "vehicles",
                     _h.PROJECT_DIR / "members"]:
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


def check_html_as_xls() -> list[dict[str, Any]]:
    """Detect .xls files that are actually HTML (exported by Santander/Itaú internet banking).

    Some banks export files with .xls extension that are actually HTML tables.
    xlrd cannot read these, causing parsing failures. This check identifies them
    so they can be handled by an HTML parser or converted before processing.
    """
    issues = []

    # Scan all .xls files in data/ and inbox/
    scan_dirs = [
        _h.DATA_DIR / "financial_statements",
        _h.PROJECT_DIR / "inbox",
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
                        rel = f.relative_to(_h.PROJECT_DIR)
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
    if not _h.E2_DIR.exists():
        return issues

    for f in sorted(_h.E2_DIR.glob("*.json")):
        name = f.name

        # Skip valid patterns
        if name.endswith("-2_extract.json"):
            continue
        if name.endswith("-1.5_consolidated.json"):
            continue

        # Detect -0_extract (should be -2_extract)
        if re.search(r"-0_extract\.json$", name):
            correct_name = re.sub(r"-0_extract\.json$", "-2_extract.json", name)
            correct_path = _h.E2_DIR / correct_name
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
            correct_path = _h.E2_DIR / correct_name
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
        src = _h.E2_DIR / fix["from"]
        dst = _h.E2_DIR / fix["to"]
        if dry_run:
            print(f"  [DRY-RUN] Renomearia: {fix['from']} → {fix['to']}")
        else:
            src.rename(dst)
            print(f"  [FIX] Renomeado: {fix['from']} → {fix['to']}")
        fixed += 1

    # Clean up duplicates with correct version already existing
    for issue in issues:
        if "pode ser removido" in issue["issue"]:
            f = _h.E2_DIR / issue["file"]
            if dry_run:
                print(f"  [DRY-RUN] Removeria duplicata: {issue['file']}")
            elif f.exists():
                f.unlink()
                print(f"  [FIX] Removida duplicata: {issue['file']}")
                fixed += 1

    return fixed


__all__ = [
    "check_extract_naming",
    "check_filename_vs_content",
    "check_html_as_xls",
    "check_name_collisions",
    "fix_extract_naming",
]
