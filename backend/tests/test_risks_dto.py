"""DTO validation + seed templates do Risk aggregate (ADR-178 · Sprint A10.4).

Tests síncronos puros sobre Pydantic + dataclass. Domínio em
``test_risk_aggregate.py``; HTTP em ``test_risks_api.py``.
"""

from __future__ import annotations

import pytest

from backend.app.schemas.dto.risk import (
    RiskCreateCommand,
    RiskUpdateCommand,
)
from backend.app.scripts.seed_workspace_risks import DEFAULT_RISK_TEMPLATES


def test_create_command_rejects_invalid_probability():
    with pytest.raises(ValueError, match="probability inválida"):
        RiskCreateCommand(
            code="morte",
            name="Morte",
            rationale="rationale fictício",
            impact_level="alto",
            probability="muito_alta",
        )


def test_create_command_rejects_invalid_impact_level():
    with pytest.raises(ValueError, match="impact_level inválido"):
        RiskCreateCommand(
            code="morte",
            name="Morte",
            rationale="rationale fictício",
            impact_level="catastrofico",
        )


def test_create_command_rejects_invalid_status():
    with pytest.raises(ValueError, match="status inválido"):
        RiskCreateCommand(
            code="morte",
            name="Morte",
            rationale="rationale fictício",
            impact_level="alto",
            status="EmAnalise",
        )


def test_create_command_rejects_short_rationale():
    with pytest.raises(ValueError):
        RiskCreateCommand(
            code="morte",
            name="Morte",
            rationale="curto",  # < 10 chars
            impact_level="alto",
        )


def test_update_command_accepts_partial_patch():
    cmd = RiskUpdateCommand(probability="alta")
    assert cmd.probability == "alta"
    assert cmd.impact_level is None


def test_update_command_rejects_invalid_status():
    with pytest.raises(ValueError, match="status inválido"):
        RiskUpdateCommand(status="Resolvido")


def test_seed_templates_have_canonical_codes_and_count():
    codes = {t.code for t in DEFAULT_RISK_TEMPLATES}
    assert codes == {"morte", "invalidez", "doenca_grave", "desemprego", "longevidade"}
    assert len(DEFAULT_RISK_TEMPLATES) == 5


def test_seed_templates_have_canonical_impact_levels():
    by_code = {t.code: t for t in DEFAULT_RISK_TEMPLATES}
    assert by_code["morte"].impact_level == "crítico"
    assert by_code["invalidez"].impact_level == "alto"
    assert by_code["doenca_grave"].impact_level == "alto"
    assert by_code["desemprego"].impact_level == "médio"
    assert by_code["longevidade"].impact_level == "alto"


def test_seed_templates_have_rationale_min_length():
    for template in DEFAULT_RISK_TEMPLATES:
        assert len(template.rationale) >= 10
