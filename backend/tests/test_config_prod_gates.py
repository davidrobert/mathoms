# Production fail-fast invariants em Settings (W1-T05 · SR-022 / SR-021).
#
# Em ENVIRONMENT=production, o model_validator em
# backend/app/core/config.py rejeita configurações conhecidamente
# inseguras antes do app subir:
#  - SECRET_KEY default de dev → JWT forjável.
#  - SECRET_KEY <32 chars → entropia insuficiente para HS256.
#  - DATABASE_URL com sqlite → driver não tolera prod multi-worker.
# Defaults de dev continuam funcionando intactos.
"""Production fail-fast invariants em Settings (W1-T05 · SR-022 / SR-021)."""

from __future__ import annotations

import pytest

from backend.app.core.config import Settings


def _prod_kwargs(**overrides: object) -> dict[str, object]:
    """Kwargs base para Settings em ENVIRONMENT=production — inclui DATABASE_URL
    não-sqlite por default para isolar cada gate sob teste."""
    base: dict[str, object] = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "A" * 64,
        "DATABASE_URL": "postgresql+asyncpg://user:pass@host/db",
    }
    base.update(overrides)
    return base


def test_prod_rejects_default_secret() -> None:
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(**_prod_kwargs(SECRET_KEY="dev-secret-key-change-in-production"))


def test_prod_rejects_change_me_secret() -> None:
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(**_prod_kwargs(SECRET_KEY="change-me"))


def test_prod_rejects_short_secret() -> None:
    with pytest.raises(RuntimeError, match="32 chars"):
        Settings(**_prod_kwargs(SECRET_KEY="x" * 16))


def test_prod_rejects_sqlite_database_url() -> None:
    with pytest.raises(RuntimeError, match="sqlite"):
        Settings(
            **_prod_kwargs(
                DATABASE_URL="sqlite+aiosqlite:///mathoms.db",
            )
        )


def test_prod_accepts_proper_config() -> None:
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="A" * 64,
        DATABASE_URL="postgresql+asyncpg://user:pass@host/db",
    )
    assert s.ENVIRONMENT == "production"
    assert s.SECRET_KEY == "A" * 64


def test_dev_defaults_still_work() -> None:
    """Dev mode não dispara nenhum gate, mesmo com defaults inseguros."""
    s = Settings(ENVIRONMENT="development")
    assert s.ENVIRONMENT == "development"
    assert s.SECRET_KEY == "dev-secret-key-change-in-production"
    # SQLite default em dev é OK
    assert "sqlite" in s.DATABASE_URL.lower()


def test_dev_with_short_secret_still_works() -> None:
    """Dev permite SECRET_KEY curta — gate só aplica em production."""
    s = Settings(ENVIRONMENT="development", SECRET_KEY="short")
    assert s.SECRET_KEY == "short"
