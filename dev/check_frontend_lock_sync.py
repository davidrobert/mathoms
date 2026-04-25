#!/usr/bin/env python3
"""Gate de pre-commit: frontend/package-lock.json em sync com package.json (incidente cb0ff11)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONT_DIR = REPO_ROOT / "frontend"


def _print_failure(stderr_or_stdout: str) -> None:
    print("\n🛑 frontend/package-lock.json dessincronizado de package.json.", file=sys.stderr)
    print(
        "\nCorrija com:\n"
        "  cd frontend && npm install\n"
        "  git add frontend/package-lock.json\n"
        "\nIncidente histórico: 2026-04-25 (cb0ff11) — CI rejeitou `npm ci` por ~5h.",
        file=sys.stderr,
    )
    print("\nDetalhes do npm:", file=sys.stderr)
    for line in stderr_or_stdout.strip().splitlines()[-15:]:
        print(f"  {line}", file=sys.stderr)


def main() -> int:
    if shutil.which("npm") is None or not (FRONT_DIR / "package.json").exists():
        return 0
    result = subprocess.run(
        ["npm", "ci", "--dry-run", "--ignore-scripts"],
        cwd=str(FRONT_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return 0
    _print_failure(result.stderr or result.stdout)
    return 1


if __name__ == "__main__":
    sys.exit(main())
