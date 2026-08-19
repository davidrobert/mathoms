"""A40.l73 · ADR-395: contraprova documental retém o gap em vez de zerá-lo."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app.models.family_member import FamilyMember
from backend.app.services.protection_bundle_adapter import (
    _bundle_to_response,
    _gap_analysis_to_response,
)
from backend.app.services.protection_bundle_inputs import ProtectionComputationInputs
from backend.app.services.protection_bundle_populator import populate_protection_bundle
from pipeline.domain.protection_bundle import DocumentaryCoverage

_TODAY = date(2026, 8, 19)


def _members() -> list[FamilyMember]:
    return [
        FamilyMember(
            workspace_id="workspace-sintetico",
            key="titular",
            full_name="Pessoa Titular",
            short_name="titular",
            role="titular",
            birth_date=date(1985, 3, 10),
        ),
        FamilyMember(
            workspace_id="workspace-sintetico",
            key="filho",
            full_name="Pessoa Filho",
            short_name="filho",
            role="filho",
            birth_date=date(2016, 5, 2),
        ),
    ]


def _computable_inputs() -> ProtectionComputationInputs:
    return ProtectionComputationInputs(
        annual_active_income_brl_cents=240_000_00,
        outstanding_debts_brl_cents=100_000_00,
    )


def _documentary(**overrides) -> DocumentaryCoverage:
    base: DocumentaryCoverage = {
        "active_policies_count": 2,
        "insurers": ["Seguradora Alfa"],
        "earliest_coverage_end": "2027-03-31",
        "unconfirmed_categories": ["vida"],
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def _bundle(documentary: DocumentaryCoverage | None):
    return populate_protection_bundle(
        items=[],
        members=_members(),
        workspace=None,
        today=_TODAY,
        adapter_version=3,
        computation_inputs=_computable_inputs(),
        documentary_coverage=documentary,
    )


def test_sem_documento_o_gap_de_vida_continua_computando():
    """Regressão: o caminho apurado não pode virar falso-negativo."""
    bundle = _bundle(None)
    assert bundle["calculation_status"]["vida"]["status"] == "computed"
    assert "vida" in bundle["gap_analysis"]
    assert any(rec["category"] == "vida" for rec in bundle["recommendations"])


def test_contraprova_documental_retem_a_categoria():
    bundle = _bundle(_documentary())
    status = bundle["calculation_status"]["vida"]
    assert status["status"] == "missing_data"
    assert status["missing_inputs"] == ["policy_inventory_confirmation"]


def test_categoria_retida_nao_publica_gap_nem_prescricao():
    bundle = _bundle(_documentary())
    assert "vida" not in bundle["gap_analysis"]
    assert [rec for rec in bundle["recommendations"] if rec["category"] == "vida"] == []
    assert [r for r in bundle["auto_inferred_risks"] if r["category"] == "vida"] == []


def test_fonte_documental_sem_categoria_do_bundle_nao_retem_gap():
    """Apólice de auto/residencial não pode silenciar o gap de vida."""
    bundle = _bundle(_documentary(unconfirmed_categories=[]))
    assert bundle["calculation_status"]["vida"]["status"] == "computed"
    assert "vida" in bundle["gap_analysis"]


def test_bundle_carrega_a_fonte_documental_para_o_render():
    bundle = _bundle(_documentary())
    assert bundle["documentary_coverage"] == _documentary()
    response = _bundle_to_response(bundle)
    assert response.documentary_coverage is not None
    assert response.documentary_coverage.active_policies_count == 2
    assert response.documentary_coverage.unconfirmed_categories == ["vida"]


def test_sem_fonte_documental_o_bundle_nao_inventa_o_bloco():
    response = _bundle_to_response(_bundle(None))
    assert response.documentary_coverage is None


def test_actual_nulo_nao_vira_zero_no_dto():
    """Retenção é ausência de entry; `actual` nulo jamais é `0,00` fabricado."""
    resposta = _gap_analysis_to_response({"gap_analysis": {"vida": {"actual_brl_cents": None}}})
    assert resposta["vida"].actual_brl is None


def test_actual_observado_continua_convertendo():
    resposta = _gap_analysis_to_response({"gap_analysis": {"vida": {"actual_brl_cents": 0}}})
    assert resposta["vida"].actual_brl == Decimal("0.00")
