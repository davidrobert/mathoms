#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-commit hook: playwright do lock Python == playwright do frontend."""

# O PDF de prod sai do Chromium do playwright Python (backend/app/services/
# pdf_renderer.py); o job `frontend-print-visual` valida o PDF com o Chromium
# do playwright npm do frontend. Cada versão do playwright fixa uma build do
# Chromium, então a baseline do CI só vale para prod com as duas versões iguais.
# O Dependabot sobe cada lado num PR separado (pip e npm) — este hook reprova o
# PR que partir o par.

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCK_FILE = REPO_ROOT / "requirements.lock"
NPM_LOCK_FILE = REPO_ROOT / "frontend" / "package-lock.json"
_PY_PIN = re.compile(r"^playwright==([^\s\\]+)", re.MULTILINE)


def python_playwright_version(lock_text: str) -> str | None:
    match = _PY_PIN.search(lock_text)
    return match.group(1) if match else None


def npm_playwright_version(npm_lock: dict) -> str | None:
    package = npm_lock.get("packages", {}).get("node_modules/playwright", {})
    return package.get("version")


def parity_error(python_version: str | None, npm_version: str | None) -> str | None:
    if python_version is None or npm_version is None:
        return f"playwright ausente: requirements.lock={python_version!r}, frontend={npm_version!r}"
    if python_version == npm_version:
        return None
    return (
        f"playwright do requirements.lock ({python_version}) != do frontend/package-lock.json "
        f"({npm_version}). Suba os dois juntos: `-P playwright` no lock (runbook "
        "python_dependencies.md, Tarefa 1) + @playwright/test no frontend."
    )


def main() -> int:
    error = parity_error(
        python_playwright_version(LOCK_FILE.read_text(encoding="utf-8")),
        npm_playwright_version(json.loads(NPM_LOCK_FILE.read_text(encoding="utf-8"))),
    )
    if error:
        print(f"[playwright-parity] {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
