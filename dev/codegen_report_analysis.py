#!/usr/bin/env python3
"""Gera o tipo bruto do artefato E5 a partir do JSON Schema canônico."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.report_analysis_codegen import GENERATED_PATH, render_typescript


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render_typescript()
    if args.check:
        if not GENERATED_PATH.is_file() or GENERATED_PATH.read_text(encoding="utf-8") != rendered:
            print(
                "✗ report-analysis.ts fora de sync — rode python3 dev/codegen_report_analysis.py",
                file=sys.stderr,
            )
            return 1
        print("✓ report-analysis.ts em sync")
        return 0
    GENERATED_PATH.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_PATH.write_text(rendered, encoding="utf-8")
    print(f"✓ escrito {GENERATED_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
