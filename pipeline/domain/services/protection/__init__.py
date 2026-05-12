"""4 calculators determinísticos puros (ADR-192 §D3, S9-T03) emitindo ``RiskInferred`` whitelisted; boundary ADR-101 R5: stdlib + ``pipeline.domain.*``; disclaimer fiduciário canônico em todo ``rationale``."""

from __future__ import annotations

from pipeline.domain.services.protection.compliance_us_person import (
    ComplianceFlag,
    USExposureInputs,
    USPersonThresholds,
    compliance_risk_us_person,
)
from pipeline.domain.services.protection.disability_coverage import (
    CoverageGap,
    DisabilityInputs,
    disability_coverage_gap,
)
from pipeline.domain.services.protection.itcmd_estimator import (
    ITCMDEstimate,
    ITCMDInputs,
    itcmd_estimated,
)
from pipeline.domain.services.protection.life_insurance_coverage import (
    CoverageRecommendation,
    LifeInsuranceInputs,
    life_insurance_coverage_ideal,
)
from pipeline.domain.services.protection.risk_inferred import (
    SOURCE_CALCULATORS_WHITELIST,
    build_risk_inferred,
)

__all__ = [
    "ComplianceFlag",
    "CoverageGap",
    "CoverageRecommendation",
    "DisabilityInputs",
    "ITCMDEstimate",
    "ITCMDInputs",
    "LifeInsuranceInputs",
    "SOURCE_CALCULATORS_WHITELIST",
    "USExposureInputs",
    "USPersonThresholds",
    "build_risk_inferred",
    "compliance_risk_us_person",
    "disability_coverage_gap",
    "itcmd_estimated",
    "life_insurance_coverage_ideal",
]
