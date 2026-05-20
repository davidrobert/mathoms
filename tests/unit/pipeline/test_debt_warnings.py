"""Warning tipado DebtVsIrpfDeclaracaoConflict (ADR-097 D1 · ADR-227 §D6)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.debt_warnings import DebtVsIrpfDeclaracaoConflict


def test_format_renders_amounts_and_ratio_excess():
    w = DebtVsIrpfDeclaracaoConflict(
        member_key="david",
        soma_debt_brl=Decimal("120000.00"),
        total_dividas_irpf_brl=Decimal("100000.00"),
        ratio=Decimal("1.20"),
    )
    msg = w.format()
    assert "david" in msg
    assert "R$ 120000.00" in msg
    assert "R$ 100000.00" in msg
    assert "20%" in msg
    assert "Per-property prevalece" in msg


def test_warning_is_frozen():
    """Dataclass frozen impede mutação (ADR-097 D1)."""
    import dataclasses

    w = DebtVsIrpfDeclaracaoConflict(
        member_key="m",
        soma_debt_brl=Decimal("0"),
        total_dividas_irpf_brl=Decimal("0"),
        ratio=Decimal("0"),
    )
    assert dataclasses.is_dataclass(w)
    try:
        w.member_key = "outro"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("dataclass deveria ser frozen")
