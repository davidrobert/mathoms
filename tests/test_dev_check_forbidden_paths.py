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
        # `docs/archive/` e afins NÃO são `archive/` na raiz (A34.l6).
        "docs/archive/BACKLOG-pre-shim-2026-05-07.md",
        "docs/agent_prompts/archive/track_antigo.md",
    ],
)
def test_allows_legit_paths(path: str) -> None:
    assert cfp.check(path) is None, f"não deveria bloquear {path!r}"


# ─── Delete staged é exceção (remover .env do repo é desejável) ────────


def test_delete_of_env_is_allowed() -> None:
    """Se o commit está DELETANDO um arquivo proibido, passa (limpeza)."""
    assert cfp.check(".env", staged_statuses={".env": "D"}) is None
    assert cfp.check("backend/.env", staged_statuses={"backend/.env": "D"}) is None


# ─── _archive/ + archive/ (A34.l6 · ADR-319) ───────────────────────────


@pytest.mark.parametrize(
    "path",
    ["_archive/novo_extrato.pdf", "archive/relatorio.md", "_archive/sub/dir/doc.md"],
)
def test_blocks_archive_staged_addition(path: str) -> None:
    """Adição staged em _archive//archive/ é barrada — recriação proibida."""
    reason = cfp.check(path, staged_statuses={path: "A"})
    assert reason is not None, f"deveria bloquear {path!r}"
    assert "ADR-319" in reason


def test_blocks_archive_staged_modification() -> None:
    """Modificação staged sob _archive/ também é barrada."""
    path = "_archive/doc_legado.md"
    assert cfp.check(path, staged_statuses={path: "M"}) is not None


def test_archive_blocked_even_unstaged() -> None:
    """Pós-A34.l7 (diretório deletado), o bloqueio é incondicional — o grace
    de legado tracked da A34.l6 saiu junto com a deleção."""
    assert cfp.check("_archive/doc_legado.md", staged_statuses={}) is not None
    assert cfp.check("_archive/qualquer.md") is not None
    assert cfp.check("archive/novo.md") is not None


def test_archive_staged_deletion_allowed() -> None:
    """A A34.l7 deleta _archive/ inteiro — deleção staged não é violação."""
    path = "_archive/docs_legacy/plano_correcao_e2.md"
    assert cfp.check(path, staged_statuses={path: "D"}) is None


def test_delete_of_db_suffix_is_allowed() -> None:
    """Paridade da exceção de deleção para sufixos (remover .db é limpeza)."""
    assert cfp.check("backend/mathoms.db", staged_statuses={"backend/mathoms.db": "D"}) is None
