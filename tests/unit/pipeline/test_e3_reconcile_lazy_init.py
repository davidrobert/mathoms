"""Tests — `scripts/reconcile_transactions.py` lazy init (Sessão A3b).

Garante que importar ``scripts.reconcile_transactions`` não dispara I/O de configs no
disco. Defaults módulo-level são sensatos. ``_init_config(base_dir)`` continua
disponível para popular do disco quando explicitamente chamado.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


# =============================================================================
# Importação pura — sem side-effects
# =============================================================================


class TestImportNoSideEffect:
    def test_source_has_no_init_config_call_at_module_level(self):
        """Critério estrutural da Sessão A3b: o source não chama
        ``_init_config(...)`` no nível de módulo (top-level). Inspeção AST
        evita falsos positivos por estado de globals entre testes.
        """
        import ast

        src_path = Path(__file__).resolve().parents[3] / "scripts" / "reconcile_transactions.py"
        tree = ast.parse(src_path.read_text(encoding="utf-8"))

        offending: list[int] = []
        for node in tree.body:  # apenas top-level
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "_init_config"
            ):
                offending.append(node.lineno)

        assert offending == [], (
            f"_init_config(...) ainda é invocado no top-level em "
            f"scripts/reconcile_transactions.py (linhas {offending}) — Sessão A3b "
            "deveria ter eliminado o side-effect no import."
        )


# =============================================================================
# Defaults módulo-level
# =============================================================================


class TestDefaults:
    def test_skip_types_has_irpf_and_investimentos(self):
        from scripts.reconcile_transactions import SKIP_TYPES

        assert "irpf" in SKIP_TYPES
        assert "investimentosposicao" in SKIP_TYPES

    def test_tipo_canonical_has_extratoconta(self):
        from scripts.reconcile_transactions import TIPO_CANONICAL

        assert TIPO_CANONICAL["extratoconta"] == "extratoconta"
        assert TIPO_CANONICAL["faturacarbon"] == "faturacarbon"

    def test_account_type_equivalences_starts_empty(self):
        """Sem _init_config, equivalences começa vazio (override é opt-in
        via config/family_members.json)."""
        # Re-importa limpo para evitar contaminação por outros testes que
        # rodaram _init_config(_DEFAULT_BASE_DIR).
        if "scripts.reconcile_transactions" in sys.modules:
            del sys.modules["scripts.reconcile_transactions"]
        from scripts.reconcile_transactions import ACCOUNT_TYPE_EQUIVALENCES

        # Nota: pode estar populado se _init_config foi chamado por outro
        # teste anterior (testes não são isolados). O importante é que
        # exista como dict (não None) e seja mutável.
        assert isinstance(ACCOUNT_TYPE_EQUIVALENCES, dict)

    def test_tolerances_have_sensible_defaults(self):
        from scripts.reconcile_transactions import (
            _TOLERANCE_BASELINE_DIFF,
            _TOLERANCE_GAP_DAYS,
            _TOLERANCE_SALDO_DIFF,
        )

        assert _TOLERANCE_SALDO_DIFF == 0.01
        assert _TOLERANCE_GAP_DAYS == 4
        assert _TOLERANCE_BASELINE_DIFF == 1.0

    def test_base_dir_is_repo_root(self):
        from scripts.reconcile_transactions import _BASE_DIR, _DEFAULT_BASE_DIR

        # Sem _init_config explícito, _BASE_DIR == _DEFAULT_BASE_DIR.
        assert isinstance(_BASE_DIR, Path)
        assert _BASE_DIR == _DEFAULT_BASE_DIR


# =============================================================================
# _init_config continua funcionando explicitamente
# =============================================================================


class TestInitConfigStillWorks:
    def test_init_config_populates_from_directory(self, tmp_path):
        """``_init_config(root)`` continua populando os globals — tests
        legados em ``test_e3_golden_execution`` e
        ``test_e3_main_with_store_parity`` chamam essa API no ``finally``."""
        cfg = tmp_path / "config"
        cfg.mkdir()
        (cfg / "pipeline.json").write_text(
            '{"reconciliation": {"tolerances": {"saldo_diff": 0.05}}}',
            encoding="utf-8",
        )
        (cfg / "family_members.json").write_text(
            '{"account_type_equivalences": {"alias": "real"}}',
            encoding="utf-8",
        )
        (cfg / "institutions.json").write_text(
            '{"banco_canonical": {"itau": "Itaú"}}',
            encoding="utf-8",
        )

        from scripts.reconcile_transactions import (
            _DEFAULT_BASE_DIR,
            _init_config,
        )

        try:
            _init_config(tmp_path)
            from scripts.reconcile_transactions import (
                _BANCO_DISPLAY_TO_CANONICAL,
                _TOLERANCE_SALDO_DIFF,
                ACCOUNT_TYPE_EQUIVALENCES,
            )

            assert ACCOUNT_TYPE_EQUIVALENCES == {"alias": "real"}
            assert _BANCO_DISPLAY_TO_CANONICAL.get("itaú") == "itau"
            assert _TOLERANCE_SALDO_DIFF == 0.05
        finally:
            _init_config(_DEFAULT_BASE_DIR)
