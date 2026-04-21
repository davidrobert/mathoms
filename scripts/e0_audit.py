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

Modo padrão: apenas imprime um relatório (read-only).
Use --fix-names para auto-corrigir nomes de extracts da checagem 9 (altera arquivos).

Usage:
  python scripts/e0_audit.py              # Relatório completo
  python scripts/e0_audit.py --check 1    # Apenas checagem 1
  python scripts/e0_audit.py --check 1,2  # Checagens 1 e 2
  python scripts/e0_audit.py --json       # Saída em JSON (para scripts)

Author: Claude Opus 4.6
Date: 2026-04-05

A6g.2 — T1.c: checks movidos para ``scripts/e0/audit_*.py``; este arquivo
fica só como CLI + orchestrator. ``pipeline/stages/e0_audit.py`` continua
chamando ``scripts.e0_audit.main`` sem mudança de contrato.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from scripts.e0 import audit_helpers as _h
from scripts.e0.audit_filename import (
    check_extract_naming,
    check_filename_vs_content,
    check_html_as_xls,
    check_name_collisions,
    fix_extract_naming,
)
from scripts.e0.audit_integrity import (
    check_duplicates,
    check_hash_duplicates,
    check_orphans,
)
from scripts.e0.audit_ledger import check_inbox_log, check_saldo_gaps


# Re-export para compat — tests/test_stage_wrappers.py importa _init_config
# e os globais ``PROJECT_DIR``/``DATA_DIR`` daqui. Mantemos ambos bindings
# sincronizados com ``_h``.
PROJECT_DIR = _h.PROJECT_DIR
DATA_DIR = _h.DATA_DIR
E2_DIR = _h.E2_DIR
INBOX_LOG = _h.INBOX_LOG
SCRIPTS_DIR = _h.SCRIPTS_DIR


def _init_config(base_dir: Path) -> None:
    """Wrapper que propaga init para ``_h`` e rebina globais deste módulo."""
    global PROJECT_DIR, DATA_DIR, E2_DIR, INBOX_LOG, SCRIPTS_DIR
    _h.init_config(base_dir)
    PROJECT_DIR = _h.PROJECT_DIR
    DATA_DIR = _h.DATA_DIR
    E2_DIR = _h.E2_DIR
    INBOX_LOG = _h.INBOX_LOG
    SCRIPTS_DIR = _h.SCRIPTS_DIR


ALL_CHECKS: dict[int, tuple[str, Callable[[], list[dict]]]] = {
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="E0-audit — Auditoria de integridade data/ ↔ E2 ↔ E3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
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
    return parser


def _run_fix_names() -> None:
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


def _resolve_check_ids(raw: str | None) -> list[int]:
    if not raw:
        return list(ALL_CHECKS.keys())
    check_ids = [int(c.strip()) for c in raw.split(",")]
    invalid_ids = [cid for cid in check_ids if cid not in ALL_CHECKS]
    if invalid_ids:
        print(
            f"  [WARN] Checagem(ns) {invalid_ids} não existe(m). "
            f"Disponíveis: {list(ALL_CHECKS.keys())}"
        )
    return [cid for cid in check_ids if cid in ALL_CHECKS]


def _run_checks(check_ids: list[int]) -> tuple[dict[int, list[dict]], int, int, int]:
    all_issues: dict[int, list[dict]] = {}
    total_errors = total_warnings = total_info = 0
    for cid in check_ids:
        _, func = ALL_CHECKS[cid]
        issues = func()
        all_issues[cid] = issues
        for issue in issues:
            if issue["severity"] == "ERROR":
                total_errors += 1
            elif issue["severity"] == "WARNING":
                total_warnings += 1
            else:
                total_info += 1
    return all_issues, total_errors, total_warnings, total_info


def _emit_json(all_issues: dict[int, list[dict]], errors: int, warnings: int, info: int) -> None:
    output = {
        "summary": {
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "total": errors + warnings + info,
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


def _emit_text_report(
    check_ids: list[int],
    all_issues: dict[int, list[dict]],
    errors: int, warnings: int, info: int,
) -> None:
    print("=" * 60)
    print("  E0-audit — Relatório de integridade")
    print(f"  Projeto: {_h.PROJECT_DIR.name}")
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

    print(f"\n{'=' * 60}")
    total = errors + warnings + info
    print(f"  Resumo: {total} achado(s) — {errors} erros, {warnings} avisos, {info} info")
    if errors > 0:
        print("  AÇÃO REQUERIDA: há erros que precisam de correção.")
    elif warnings > 0:
        print("  RECOMENDAÇÃO: revisar avisos antes do próximo E-reset.")
    else:
        print("  [OK] Nenhum problema significativo detectado.")
    print("=" * 60)


def main(root_dir: Path | None = None) -> None:
    if root_dir:
        _init_config(root_dir)

    parser = _build_parser()
    args = parser.parse_args([] if root_dir else None)

    if args.fix_names:
        _run_fix_names()
        return

    check_ids = _resolve_check_ids(args.check)
    all_issues, errors, warnings_count, info = _run_checks(check_ids)

    if args.json:
        _emit_json(all_issues, errors, warnings_count, info)
    else:
        _emit_text_report(check_ids, all_issues, errors, warnings_count, info)


if __name__ == "__main__":
    main()
