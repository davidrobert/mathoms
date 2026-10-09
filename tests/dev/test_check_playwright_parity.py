"""playwright do lock Python e do frontend precisam ser a mesma versão (Chromium do PDF)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.check_playwright_parity import (  # noqa: E402
    LOCK_FILE,
    NPM_LOCK_FILE,
    npm_playwright_version,
    parity_error,
    python_playwright_version,
)

LOCK_TEXT = (
    "pdfplumber==0.11.9 \\\n    --hash=sha256:abc\nplaywright==1.63.0 \\\n    --hash=sha256:def\n"
)


def _npm_lock(version: str) -> dict:
    return {"packages": {"node_modules/playwright": {"version": version}}}


def test_versao_python_lida_do_pin_do_lock() -> None:
    assert python_playwright_version(LOCK_TEXT) == "1.63.0"
    assert python_playwright_version("pytest-playwright==0.5.0\n") is None


def test_versao_npm_lida_do_pacote_playwright() -> None:
    assert npm_playwright_version(_npm_lock("1.63.0")) == "1.63.0"
    assert npm_playwright_version({"packages": {}}) is None


@pytest.mark.parametrize(
    ("python_version", "npm_version", "reprova"),
    [("1.63.0", "1.63.0", False), ("1.60.0", "1.63.0", True), (None, "1.63.0", True)],
)
def test_par_partido_reprova(python_version: str | None, npm_version: str, reprova: bool) -> None:
    assert (parity_error(python_version, npm_version) is not None) is reprova


def test_repositorio_mantem_o_par() -> None:
    python_version = python_playwright_version(LOCK_FILE.read_text(encoding="utf-8"))
    npm_version = npm_playwright_version(json.loads(NPM_LOCK_FILE.read_text(encoding="utf-8")))
    assert parity_error(python_version, npm_version) is None, (python_version, npm_version)
