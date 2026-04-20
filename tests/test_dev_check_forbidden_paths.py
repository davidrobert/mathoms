"""Regression tests para dev/check_forbidden_paths.py.

Contexto: `backend/.env` vazou pra origin/main carregando a FIN_FERNET_KEY
(incidente 2026-04-20). Causa raiz no guardrail: `check_forbidden_paths.check`
usava match exato (`path in FORBIDDEN_FILES`), que só pega `.env` na raiz.
`backend/.env`, `frontend/.env`, etc. passavam silenciosamente.

Estes tests fixam o comportamento esperado: `.env`/`.env.test` são bloqueados
em qualquer diretório, `.env.example` e afins continuam livres.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).parent.parent / "dev" / "check_forbidden_paths.py"
_SPEC = importlib.util.spec_from_file_location("check_forbidden_paths", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
cfp = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cfp)


# ─── Bloqueados ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "path",
    [
        ".env",
        "backend/.env",
        "frontend/.env",
        "infra/secrets/.env",
        ".env.test",
        "backend/.env.test",
        "mathoms.db",
        "config/passwords.txt",
    ],
)
def test_blocks_forbidden_files_at_any_depth(path: str) -> None:
    assert cfp.check(path) is not None, f"deveria bloquear {path!r}"


@pytest.mark.parametrize(
    "path",
    [
        "storage/ws-1/upload.pdf",
        "data/raw/extrato.pdf",
        "inbox/fatura.pdf",
        "_scratch/relatorio.md",
    ],
)
def test_blocks_forbidden_dirs(path: str) -> None:
    assert cfp.check(path) is not None, f"deveria bloquear dir {path!r}"


@pytest.mark.parametrize(
    "path",
    ["app.db", "backend/mathoms.db", "data.sqlite", "dev.sqlite3"],
)
def test_blocks_db_suffixes(path: str) -> None:
    assert cfp.check(path) is not None, f"deveria bloquear suffix de {path!r}"


# ─── Permitidos (não confundir com proibidos) ──────────────────────────

@pytest.mark.parametrize(
    "path",
    [
        ".env.example",
        "backend/.env.example",
        "docs/envs.md",
        "src/env_helpers.py",
        "README.md",
        "backend/app/core/security.py",
    ],
)
def test_allows_legit_paths(path: str) -> None:
    assert cfp.check(path) is None, f"não deveria bloquear {path!r}"


# ─── Delete staged é exceção (remover .env do repo é desejável) ────────

def test_delete_of_env_is_allowed() -> None:
    """Se o commit está DELETANDO um arquivo proibido, passa (limpeza)."""
    assert cfp.check(".env", staged_deletions={".env"}) is None
    assert cfp.check("backend/.env", staged_deletions={"backend/.env"}) is None
