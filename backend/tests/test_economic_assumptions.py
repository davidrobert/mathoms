"""``EconomicAssumption`` models + repo + service (ADR-219 wave 1)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.economic_assumption import (
    EconomicAssetClass,
    EconomicAssumption,
    WorkspaceEconomicAssumptionOverride,
)
from backend.app.repositories.economic_assumption_repository import (
    EconomicAssumptionRepository,
)
from backend.app.services.economic_assumptions_service import (
    EconomicAssumptionsService,
)


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "test_econ.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


def _make_class(
    *, code: str, label: str, sort_order: int = 10, active: bool = True
) -> EconomicAssetClass:
    return EconomicAssetClass(
        code=code,
        label=label,
        sort_order=sort_order,
        active=active,
        deprecated_at=None,
        description=None,
        created_at=datetime.now(timezone.utc),
    )


def _make_assumption(
    *,
    classe_auvp: str,
    effective_from: date,
    effective_to: date | None = None,
    retorno: Decimal = Decimal("4.500"),
    sigma: Decimal = Decimal("3.000"),
    fonte: str = "test",
) -> EconomicAssumption:
    return EconomicAssumption(
        id=str(uuid.uuid4()),
        classe_auvp=classe_auvp,
        retorno_real_esperado_pct_anual=retorno,
        sigma_anual_pct=sigma,
        fonte=fonte,
        effective_from=effective_from,
        effective_to=effective_to,
        created_by="test_setup",
        created_at=datetime.now(timezone.utc),
    )


def _make_override(
    *,
    workspace_id: str,
    classe_auvp: str,
    effective_from: date,
    retorno: Decimal = Decimal("6.000"),
    justificativa: str = "test workspace tem perfil mais arrojado",
) -> WorkspaceEconomicAssumptionOverride:
    return WorkspaceEconomicAssumptionOverride(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        classe_auvp=classe_auvp,
        retorno_real_esperado_pct_anual=retorno,
        sigma_anual_pct=Decimal("4.000"),
        fonte="test_override",
        justificativa=justificativa,
        effective_from=effective_from,
        effective_to=None,
        created_at=datetime.now(timezone.utc),
    )


def _seed_class_global(
    s, code: str, *, label: str = "X", order: int = 10, retorno: Decimal = Decimal("4.500")
) -> None:
    """Helper: insere class + global assumption vigente em 2026-01-01."""
    s.add(_make_class(code=code, label=label, sort_order=order))
    s.add(_make_assumption(classe_auvp=code, effective_from=date(2026, 1, 1), retorno=retorno))


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class TestEconomicAssumptionRepository:
    def test_list_active_classes_filters_inactive(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="rf_pos", label="RF Pós", sort_order=10))
            s.add(_make_class(code="extinct", label="Extinto", sort_order=99, active=False))
            s.commit()
            rows = EconomicAssumptionRepository(s).list_active_classes()
            assert [r.code for r in rows] == ["rf_pos"]

    def test_list_active_classes_orders_by_sort_order(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="b", label="B", sort_order=20))
            s.add(_make_class(code="a", label="A", sort_order=10))
            s.commit()
            rows = EconomicAssumptionRepository(s).list_active_classes()
            assert [r.code for r in rows] == ["a", "b"]

    def test_list_global_vigentes_em_picks_covering_window(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="rf_pos", label="RF Pós"))
            s.add(
                _make_assumption(
                    classe_auvp="rf_pos",
                    effective_from=date(2026, 1, 1),
                    effective_to=date(2026, 12, 31),
                )
            )
            s.commit()
            rows = EconomicAssumptionRepository(s).list_global_vigentes_em(date(2026, 6, 1))
            assert len(rows) == 1
            assert rows[0].classe_auvp == "rf_pos"

    def test_list_global_vigentes_em_open_ended(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="rf_pos", label="RF Pós"))
            s.add(_make_assumption(classe_auvp="rf_pos", effective_from=date(2026, 1, 1)))
            s.commit()
            rows = EconomicAssumptionRepository(s).list_global_vigentes_em(date(2030, 1, 1))
            assert len(rows) == 1

    def test_list_global_vigentes_em_excludes_expired(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="rf_pos", label="RF Pós"))
            s.add(
                _make_assumption(
                    classe_auvp="rf_pos",
                    effective_from=date(2024, 1, 1),
                    effective_to=date(2024, 12, 31),
                )
            )
            s.commit()
            rows = EconomicAssumptionRepository(s).list_global_vigentes_em(date(2026, 1, 1))
            assert rows == []

    def test_list_workspace_overrides_isolated_per_workspace(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="acoes_br", label="Ações BR"))
            s.add(
                _make_override(
                    workspace_id="ws-A", classe_auvp="acoes_br", effective_from=date(2026, 1, 1)
                )
            )
            s.add(
                _make_override(
                    workspace_id="ws-B", classe_auvp="acoes_br", effective_from=date(2026, 1, 1)
                )
            )
            s.commit()
            repo = EconomicAssumptionRepository(s)
            a = repo.list_workspace_overrides_vigentes_em("ws-A", date(2026, 6, 1))
            b = repo.list_workspace_overrides_vigentes_em("ws-B", date(2026, 6, 1))
            assert len(a) == 1 and a[0].workspace_id == "ws-A"
            assert len(b) == 1 and b[0].workspace_id == "ws-B"

    def test_unique_classe_effective_from(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="rf_pos", label="RF Pós"))
            s.add(_make_assumption(classe_auvp="rf_pos", effective_from=date(2026, 1, 1)))
            s.commit()
            s.add(_make_assumption(classe_auvp="rf_pos", effective_from=date(2026, 1, 1)))
            with pytest.raises(Exception):
                s.commit()


# ---------------------------------------------------------------------------
# Service — get_vigentes_em consolidando (global ∪ override)
# ---------------------------------------------------------------------------


class TestEconomicAssumptionsService:
    def test_returns_empty_when_no_classes(self, sync_db):
        with sync_db() as s:
            assert EconomicAssumptionsService(s).get_vigentes_em(date(2026, 6, 1)) == ()

    def test_emits_indisponivel_when_no_assumption_for_class(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="cripto", label="Cripto", sort_order=90))
            s.commit()
            result = EconomicAssumptionsService(s).get_vigentes_em(date(2026, 6, 1))
            assert len(result) == 1
            assert result[0].classe_auvp == "cripto"
            assert result[0].status == "indisponivel"
            assert result[0].razao_indisponivel is not None
            assert "2026-06-01" in result[0].razao_indisponivel

    def test_returns_global_when_no_workspace_override(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="rf_pos", label="RF Pós", sort_order=10))
            s.add(
                _make_assumption(
                    classe_auvp="rf_pos",
                    effective_from=date(2026, 1, 1),
                    retorno=Decimal("3.500"),
                )
            )
            s.commit()
            result = EconomicAssumptionsService(s).get_vigentes_em(date(2026, 6, 1))
            assert len(result) == 1
            r = result[0]
            assert r.status == "emitted"
            assert r.fonte_origem == "global"
            assert r.retorno_real_esperado_pct_anual == Decimal("3.500")

    def test_workspace_override_wins_over_global(self, sync_db):
        with sync_db() as s:
            _seed_class_global(s, "acoes_br", label="Ações BR", order=40, retorno=Decimal("7.000"))
            s.add(
                _make_override(
                    workspace_id="ws-1",
                    classe_auvp="acoes_br",
                    effective_from=date(2026, 1, 1),
                    retorno=Decimal("9.000"),
                    justificativa="perfil agressivo dogfood",
                )
            )
            s.commit()
            r = EconomicAssumptionsService(s).get_vigentes_em(
                date(2026, 6, 1), workspace_id="ws-1"
            )[0]
            assert r.fonte_origem == "workspace_override"
            assert r.retorno_real_esperado_pct_anual == Decimal("9.000")
            assert r.justificativa == "perfil agressivo dogfood"

    def test_workspace_override_does_not_leak_across_workspaces(self, sync_db):
        with sync_db() as s:
            _seed_class_global(s, "rf_pos", label="RF Pós", retorno=Decimal("3.500"))
            s.add(
                _make_override(
                    workspace_id="ws-A",
                    classe_auvp="rf_pos",
                    effective_from=date(2026, 1, 1),
                    retorno=Decimal("4.000"),
                )
            )
            s.commit()
            # ws-B não tem override → cai no global
            result = EconomicAssumptionsService(s).get_vigentes_em(
                date(2026, 6, 1), workspace_id="ws-B"
            )
            assert result[0].fonte_origem == "global"
            assert result[0].retorno_real_esperado_pct_anual == Decimal("3.500")

    def test_resolution_preserves_sort_order(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="rf_pos", label="RF Pós", sort_order=10))
            s.add(_make_class(code="acoes_br", label="Ações BR", sort_order=40))
            s.add(_make_class(code="caixa", label="Caixa", sort_order=5))
            s.add(_make_assumption(classe_auvp="rf_pos", effective_from=date(2026, 1, 1)))
            s.add(_make_assumption(classe_auvp="acoes_br", effective_from=date(2026, 1, 1)))
            s.add(_make_assumption(classe_auvp="caixa", effective_from=date(2026, 1, 1)))
            s.commit()
            result = EconomicAssumptionsService(s).get_vigentes_em(date(2026, 6, 1))
            assert [r.classe_auvp for r in result] == ["caixa", "rf_pos", "acoes_br"]

    def test_resolution_mixes_global_override_and_indisponivel(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="caixa", label="Caixa", sort_order=5))
            _seed_class_global(s, "rf_pos", label="RF Pós", order=10)
            s.add(_make_class(code="acoes_br", label="Ações BR", sort_order=40))
            s.add(
                _make_override(
                    workspace_id="ws-1", classe_auvp="acoes_br", effective_from=date(2026, 1, 1)
                )
            )
            s.commit()
            result = EconomicAssumptionsService(s).get_vigentes_em(
                date(2026, 6, 1), workspace_id="ws-1"
            )
            statuses = {r.classe_auvp: (r.status, r.fonte_origem) for r in result}
            assert statuses == {
                "caixa": ("indisponivel", None),
                "rf_pos": ("emitted", "global"),
                "acoes_br": ("emitted", "workspace_override"),
            }

    def test_list_active_class_codes_helper(self, sync_db):
        with sync_db() as s:
            s.add(_make_class(code="rf_pos", label="RF Pós", sort_order=10))
            s.add(_make_class(code="acoes_br", label="Ações BR", sort_order=40))
            s.add(_make_class(code="extinct", label="Extinto", sort_order=99, active=False))
            s.commit()
            codes = EconomicAssumptionsService(s).list_active_class_codes()
            assert codes == ["rf_pos", "acoes_br"]


# ---------------------------------------------------------------------------
# Seed baseline (idempotência + cobertura das 10 classes canônicas)
# ---------------------------------------------------------------------------


class TestSeedBaselineEconomicAssumptions:
    def test_seed_inserts_10_baseline_rows(self, sync_db):
        from backend.app.scripts.economic_asset_class_seed import (
            CANONICAL_ASSET_CLASSES as _INITIAL_ASSET_CLASSES,
        )
        from backend.app.scripts.seed_economic_assumptions import (
            seed_baseline_economic_assumptions,
        )

        with sync_db() as s:
            for row in _INITIAL_ASSET_CLASSES:
                s.add(
                    _make_class(code=row["code"], label=row["label"], sort_order=row["sort_order"])
                )
            s.commit()
            n = seed_baseline_economic_assumptions(s)
            assert n == 10
            rows = s.query(EconomicAssumption).filter_by(effective_from=date(2026, 1, 1)).all()
            assert {r.classe_auvp for r in rows} == {row["code"] for row in _INITIAL_ASSET_CLASSES}

    def test_seed_is_idempotent(self, sync_db):
        from backend.app.scripts.economic_asset_class_seed import (
            CANONICAL_ASSET_CLASSES as _INITIAL_ASSET_CLASSES,
        )
        from backend.app.scripts.seed_economic_assumptions import (
            seed_baseline_economic_assumptions,
        )

        with sync_db() as s:
            for row in _INITIAL_ASSET_CLASSES:
                s.add(
                    _make_class(code=row["code"], label=row["label"], sort_order=row["sort_order"])
                )
            s.commit()
            seed_baseline_economic_assumptions(s)
            n_rerun = seed_baseline_economic_assumptions(s)
            assert n_rerun == 0

    def test_seed_skips_classes_absent_from_lookup(self, sync_db):
        """Se a lookup foi modificada e classe baseline não está mais lá, seed ignora."""
        from backend.app.scripts.seed_economic_assumptions import (
            seed_baseline_economic_assumptions,
        )

        with sync_db() as s:
            # Só insere 2 das 10 classes — seed deve inserir só essas 2
            s.add(_make_class(code="caixa", label="Caixa", sort_order=5))
            s.add(_make_class(code="rf_pos", label="RF Pós", sort_order=10))
            s.commit()
            n = seed_baseline_economic_assumptions(s)
            assert n == 2

    def test_baseline_rows_are_decimals_not_floats(self, sync_db):
        """ADR-090: retorno + sigma são Decimal, não float."""
        from backend.app.scripts.seed_economic_assumptions import _BASELINE_2026

        for row in _BASELINE_2026:
            assert isinstance(row.retorno_real_esperado_pct_anual, Decimal)
            assert isinstance(row.sigma_anual_pct, Decimal)
            assert row.sigma_anual_pct >= Decimal("0")

    def test_baseline_covers_all_seeded_classes(self, sync_db):
        """Toda classe na lookup canônica tem baseline correspondente."""
        from backend.app.scripts.economic_asset_class_seed import (
            CANONICAL_ASSET_CLASSES,
        )
        from backend.app.scripts.seed_economic_assumptions import _BASELINE_2026

        seeded_codes = {row["code"] for row in CANONICAL_ASSET_CLASSES}
        baseline_codes = {row.classe_auvp for row in _BASELINE_2026}
        assert seeded_codes == baseline_codes
