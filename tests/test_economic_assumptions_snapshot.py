"""Snapshot serializer das premissas econômicas no E5 (ADR-219 wave 2)."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft7Validator

from pipeline.domain.services.economic_assumptions_snapshot import (
    build_premissas_economicas_snapshot,
)
from pipeline.domain.types.economic_assumption import ResolvedAssumption

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "schemas" / "e5_analysis.schema.json"
)
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


class _StubResolver:
    def __init__(self, rows: tuple[ResolvedAssumption, ...]) -> None:
        self._rows = rows

    def get_vigentes_em(self, as_of, workspace_id=None):
        return self._rows


def _emitted(
    code: str, *, retorno: str = "4.500", fonte_origem: str = "global"
) -> ResolvedAssumption:
    return ResolvedAssumption(
        classe_auvp=code,
        status="emitted",
        retorno_real_esperado_pct_anual=Decimal(retorno),
        sigma_anual_pct=Decimal("3.000"),
        fonte="test",
        fonte_origem=fonte_origem,
        effective_from=date(2026, 1, 1),
    )


def _indisponivel(code: str) -> ResolvedAssumption:
    return ResolvedAssumption(
        classe_auvp=code,
        status="indisponivel",
        razao_indisponivel=f"Sem premissa em {code}",
    )


def test_snapshot_returns_none_when_resolver_is_none():
    snapshot = build_premissas_economicas_snapshot(None, as_of=date(2026, 6, 1))
    assert snapshot is None


def test_snapshot_returns_none_when_resolver_returns_empty():
    snapshot = build_premissas_economicas_snapshot(_StubResolver(()), as_of=date(2026, 6, 1))
    assert snapshot is None


def test_snapshot_status_completo_when_all_emitted():
    rows = (_emitted("rf_pos"), _emitted("acoes_br", retorno="7.000"))
    snapshot = build_premissas_economicas_snapshot(_StubResolver(rows), as_of=date(2026, 6, 1))
    assert snapshot is not None
    assert snapshot["status"] == "completo"
    assert len(snapshot["classes"]) == 2


def test_snapshot_status_parcial_when_any_indisponivel():
    rows = (_emitted("rf_pos"), _indisponivel("cripto"))
    snapshot = build_premissas_economicas_snapshot(_StubResolver(rows), as_of=date(2026, 6, 1))
    assert snapshot is not None
    assert snapshot["status"] == "parcial"


def test_snapshot_serializes_decimals_as_strings():
    """ADR-090: dinheiro/percentual no wire é string Decimal, não float."""
    rows = (_emitted("rf_pos", retorno="3.500"),)
    snapshot = build_premissas_economicas_snapshot(_StubResolver(rows), as_of=date(2026, 6, 1))
    cls = snapshot["classes"][0]
    assert cls["retorno_real_esperado_pct_anual"] == "3.500"
    assert cls["sigma_anual_pct"] == "3.000"
    assert isinstance(cls["retorno_real_esperado_pct_anual"], str)


def test_snapshot_serializes_indisponivel_with_null_fields():
    rows = (_indisponivel("cripto"),)
    snapshot = build_premissas_economicas_snapshot(_StubResolver(rows), as_of=date(2026, 6, 1))
    cls = snapshot["classes"][0]
    assert cls["status"] == "indisponivel"
    assert cls["retorno_real_esperado_pct_anual"] is None
    assert cls["sigma_anual_pct"] is None
    assert cls["razao_indisponivel"] == "Sem premissa em cripto"


def test_snapshot_payload_validates_against_e5_schema():
    """Snapshot completo é um sub-objeto válido do schema E5 ``premissas_economicas``."""
    rows = (
        _emitted("rf_pos"),
        _emitted("acoes_br", retorno="7.000", fonte_origem="workspace_override"),
        _indisponivel("cripto"),
    )
    snapshot = build_premissas_economicas_snapshot(_StubResolver(rows), as_of=date(2026, 6, 1))
    sub_schema = _SCHEMA["properties"]["premissas_economicas"]
    Draft7Validator.check_schema(sub_schema)
    Draft7Validator(sub_schema).validate(snapshot)


def test_snapshot_preserves_workspace_override_origem():
    rows = (_emitted("acoes_br", fonte_origem="workspace_override"),)
    snapshot = build_premissas_economicas_snapshot(_StubResolver(rows), as_of=date(2026, 6, 1))
    assert snapshot["classes"][0]["fonte_origem"] == "workspace_override"
