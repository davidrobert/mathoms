#!/usr/bin/env python3
"""A6g.6 slice 5 · ADR-114 — gate progressivo: audit baseline decrescente.

Roda ``audit_code_style.py`` e compara contagens por categoria com
``dev/code_style_baseline.json``. Exit 1 se QUALQUER categoria tem
MAIS ofensores que baseline — legado pode apenas diminuir.

Exit 0 se todos os counts <= baseline. Se count < baseline, avisa
(sugere atualizar baseline via ``--save-baseline``).

Usado em CI para impedir regressão dos sweeps A6g.2/.4/.5 sem forçar
sweep de todas as ~2200 ocorrências restantes agora.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE = REPO_ROOT / "dev" / "code_style_baseline.json"


def _run_audit(out_dir: Path) -> dict:
    """Roda audit_code_style.py e carrega JSON resultante."""
    subprocess.check_call(
        [
            sys.executable,
            str(REPO_ROOT / "dev" / "audit_code_style.py"),
            "--format",
            "json",
            "--output-dir",
            str(out_dir),
        ],
        cwd=str(REPO_ROOT),
    )
    # Arquivo único emitido pelo audit
    jsons = sorted(out_dir.glob("code_style_audit_*.json"))
    if not jsons:
        print("ERRO: audit não produziu JSON", file=sys.stderr)
        sys.exit(2)
    return json.loads(jsons[-1].read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Atualiza baseline (use após sweep que melhora counts).",
    )
    args = parser.parse_args(argv)

    if not BASELINE.exists():
        print(f"ERRO: baseline ausente: {BASELINE}", file=sys.stderr)
        print("Rode: python3 dev/check_code_style_regression.py --save-baseline", file=sys.stderr)
        return 2

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    baseline_counts: dict[str, int] = baseline["summary"]["offenders_by_category"]

    with tempfile.TemporaryDirectory() as td:
        current = _run_audit(Path(td))
    current_counts: dict[str, int] = current["summary"]["offenders_by_category"]

    regressions: list[tuple[str, int, int]] = []
    improvements: list[tuple[str, int, int]] = []

    all_cats = set(baseline_counts) | set(current_counts)
    for cat in sorted(all_cats):
        old = baseline_counts.get(cat, 0)
        new = current_counts.get(cat, 0)
        if new > old:
            regressions.append((cat, old, new))
        elif new < old:
            improvements.append((cat, old, new))

    if args.save_baseline:
        BASELINE.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"baseline atualizado: {BASELINE}")
        return 0

    if regressions:
        print("REGRESSÃO detectada vs baseline:", file=sys.stderr)
        for cat, old, new in regressions:
            print(f"  {cat}: {old} → {new} (+{new - old})", file=sys.stderr)
        print(
            "\nOpções:\n"
            "  1. Corrija o(s) ofensor(es) novo(s).\n"
            "  2. Se a regra foi intencionalmente ampliada, rode:\n"
            "     python3 dev/check_code_style_regression.py --save-baseline",
            file=sys.stderr,
        )
        return 1

    if improvements:
        print("melhorias vs baseline (sugere atualizar baseline):")
        for cat, old, new in improvements:
            print(f"  {cat}: {old} → {new} (−{old - new})")
        print(
            "Para congelar melhoria (impedir regressão futura), rode:\n"
            "  python3 dev/check_code_style_regression.py --save-baseline"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
