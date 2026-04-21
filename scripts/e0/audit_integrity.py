"""Checks 2, 3, 6 — integridade de arquivos e conteúdo (A6g.2 — T1.c)."""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.e0 import audit_helpers as _h


def check_orphans() -> list[dict[str, Any]]:
    """Find files in data/financial_statements/ without corresponding E2 JSONs, and vice-versa."""
    issues: list[dict[str, Any]] = []

    if not _h.DATA_DIR.is_dir():
        issues.append({"file": "data/", "issue": "Diretório não existe", "severity": "ERROR"})
        return issues

    # Build set of data/ file stems across ALL subdirectories
    data_stems: dict[str, Path] = {}
    for f in _h.DATA_DIR.rglob("*"):
        if f.is_file() and not f.name.startswith("."):
            stem = re.sub(r"-0_original$", "", f.stem)
            data_stems[_h.normalize(stem)] = f

    # Build set of E2 stems
    e2_stems: dict[str, Path] = {}
    if _h.E2_DIR.is_dir():
        for f in _h.E2_DIR.glob("*-2_extract.json"):
            stem = re.sub(r"-2_extract$", "", f.stem)
            stem = re.sub(r"-0_original$", "", stem)  # Handle double suffix
            e2_stems[_h.normalize(stem)] = f

    # Files in E2 with no corresponding data/ file
    # (Note: some E2 files like baseline_patrimonial are synthesized, not from data/)
    SYNTHESIZED_PREFIXES = {"baseline_patrimonial", "dados_imoveis"}

    for stem_norm, fpath in sorted(e2_stems.items()):
        if any(stem_norm.startswith(_h.normalize(p)) for p in SYNTHESIZED_PREFIXES):
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


def check_duplicates() -> list[dict[str, Any]]:
    """Find data/ files that might be duplicates (same banco+tipo+period overlap)."""
    issues: list[dict[str, Any]] = []

    fin_dir = _h.DATA_DIR / "financial_statements"
    if not fin_dir.is_dir():
        return issues

    # Group by (banco, tipo)
    groups: dict[tuple[str, str], list[tuple[str, str, Path]]] = defaultdict(list)
    for f in sorted(fin_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            parts = _h.parse_data_filename(f.name)
            key = (_h.normalize(parts["banco"]), _h.normalize(parts["tipo"]))
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


def check_hash_duplicates() -> list[dict[str, Any]]:
    """Find files in data/ and inbox/ with identical content (same SHA-256 hash)."""
    issues: list[dict[str, Any]] = []

    # Collect files from data/ and inbox/
    dirs_to_scan = [_h.DATA_DIR, _h.PROJECT_DIR / "inbox"]
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

        names = [str(f.relative_to(_h.PROJECT_DIR)) for f in files]
        # Cross-directory duplicates (inbox vs data) are more serious
        dirs_involved = {f.relative_to(_h.PROJECT_DIR).parts[0] for f in files}
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


__all__ = [
    "check_duplicates",
    "check_hash_duplicates",
    "check_orphans",
]
