"""Resolver da flag ``dedup_natural_key_v2`` (ADR-287 · A25.l2): DB soberana com DB; env único override sem DB; sentinela anti-perenidade (ADR-282 §1)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts import categorize_transactions  # noqa: E402

_ENV = "MATHOMS_DEDUP_NATURAL_KEY_V2"


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)


def _ctx(workspace_id="ws-1"):
    return SimpleNamespace(workspace_id=workspace_id)


def _db_store():
    """Store com ``.session`` — o resolver passa ``store.session`` a ``is_enabled_sync``."""
    return SimpleNamespace(session=None)


class TestHasDbStore:
    def test_workspace_none_is_false(self):
        assert categorize_transactions._e4_has_db_store(_ctx(workspace_id=None), object()) is False

    def test_non_db_store_is_false(self):
        assert categorize_transactions._e4_has_db_store(_ctx(), object()) is False


class TestNoDbStoreEnvIsSoleOverride:
    """Sem DB, o env é o único override — substitui o antigo ``False`` morto."""

    def test_env_1_enables(self, monkeypatch):
        monkeypatch.setattr(categorize_transactions, "_e4_has_db_store", lambda c, s: False)
        monkeypatch.setenv(_ENV, "1")
        assert categorize_transactions._e4_dedup_v2_enabled(_ctx(), object()) is True

    def test_env_unset_disabled(self, monkeypatch):
        monkeypatch.setattr(categorize_transactions, "_e4_has_db_store", lambda c, s: False)
        assert categorize_transactions._e4_dedup_v2_enabled(_ctx(), object()) is False

    def test_only_literal_1_enables(self, monkeypatch):
        monkeypatch.setattr(categorize_transactions, "_e4_has_db_store", lambda c, s: False)
        for raw in ("0", "true", "True", "yes", ""):
            monkeypatch.setenv(_ENV, raw)
            assert categorize_transactions._e4_dedup_v2_enabled(_ctx(), object()) is False


class TestDbStoreIsSovereign:
    """Em produção (DBArtifactStore + workspace) a flag DB manda; env é ignorado."""

    def _patch(self, monkeypatch, db_flag):
        monkeypatch.setattr(categorize_transactions, "_e4_has_db_store", lambda c, s: True)
        import backend.app.services.feature_flags_service as ff

        monkeypatch.setattr(ff, "is_enabled_sync", lambda ws, key, db=None: db_flag)

    def test_db_true_holds_even_with_env_unset(self, monkeypatch):
        self._patch(monkeypatch, True)
        assert categorize_transactions._e4_dedup_v2_enabled(_ctx(), _db_store()) is True

    def test_db_false_ignores_env_on(self, monkeypatch):
        self._patch(monkeypatch, False)
        monkeypatch.setenv(_ENV, "1")  # env tenta forçar ON e deve ser ignorado
        assert categorize_transactions._e4_dedup_v2_enabled(_ctx(), _db_store()) is False


class TestResolutionPathsAreExactlyTwo:
    """Sentinela anti-perenidade (ADR-282 §1): o resultado é determinado por
    EXATAMENTE ``db_flag if has_db else env=='1'`` — nenhum terceiro fator.
    Introduzir um quarto caminho de resolução (env consultado no ramo DB,
    fallback novo, etc.) quebra a matriz."""

    def test_matrix_fully_determined_by_two_branches(self, monkeypatch):
        import itertools

        import backend.app.services.feature_flags_service as ff

        for has_db, db_flag, env in itertools.product(
            (True, False), (True, False), (None, "1", "0")
        ):
            monkeypatch.setattr(
                categorize_transactions, "_e4_has_db_store", lambda c, s, _h=has_db: _h
            )
            monkeypatch.setattr(ff, "is_enabled_sync", lambda ws, k, db=None, _v=db_flag: _v)
            monkeypatch.delenv(_ENV, raising=False)
            if env is not None:
                monkeypatch.setenv(_ENV, env)
            got = categorize_transactions._e4_dedup_v2_enabled(_ctx(), _db_store())
            expected = db_flag if has_db else (env == "1")
            assert got is expected, (has_db, db_flag, env, got, expected)
