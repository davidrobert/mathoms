"""Canned LLM outputs + `WorkspaceContext` helpers shared by
`test_llm_stages*.py`.

Underscore prefix keeps pytest from collecting this as a test module.
Helpers return fresh instances on every call — tests mutate outputs
freely.
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.context import WorkspaceContext
from pipeline.llm.schemas.e1_members import (
    ExtractedAccount,
    ExtractedMember,
    MembersExtractOutput,
)
from pipeline.llm.schemas.e15_baseline import (
    BaselinePatrimonialOutput,
    PatrimonialItem,
)
from pipeline.llm.schemas.e2_llm_extract import (
    ExtractedInvestment,
    ExtractedTransaction,
    LLMExtractOutput,
)
from pipeline.llm.schemas.e7_review import (
    E7ReviewOutput,
    NarrativeSection,
    ReviewInsight,
    ScoreAdjustment,
)
from pipeline.llm.service import LLMCallResult


def make_llm_ctx(tmp_path: Path) -> WorkspaceContext:
    """WorkspaceContext with llm_config.json in config/."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    llm_config = {
        "provider": "anthropic",
        "api_key": "sk-test-fake",
        "model_name": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "temperature": 0.1,
    }
    (config_dir / "llm_config.json").write_text(json.dumps(llm_config))
    return WorkspaceContext(root=tmp_path)


def make_llm_ctx_no_llm(tmp_path: Path) -> WorkspaceContext:
    """WorkspaceContext without llm_config.json (free tier simulation)."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    return WorkspaceContext(root=tmp_path)


def make_e1_output() -> MembersExtractOutput:
    return MembersExtractOutput(
        members=[
            ExtractedMember(
                key="david",
                full_name="David Ferreira Campos",
                short_name="David",
                cpf="12345678901",
                birth_date="1985-03-15",
                role="titular",
                accounts=[
                    ExtractedAccount(
                        institution_code="itau",
                        account_type="extratoconta",
                        agency="1234",
                        account_number="56789",
                    ),
                ],
            ),
            ExtractedMember(
                key="mariana",
                full_name="Mariana Ferreira Campos",
                short_name="Mariana",
                role="conjuge",
                accounts=[],
            ),
        ],
        titular_key="david",
        confidence=0.95,
        notes="Clear extraction from IRPF declaration",
    )


def make_e15_output() -> BaselinePatrimonialOutput:
    return BaselinePatrimonialOutput(
        items=[
            PatrimonialItem(
                code="01",
                description="Apartamento São Paulo",
                category="imovel",
                institution=None,
                value_brl=500000.00,
                member_key="david",
                year=2024,
            ),
            PatrimonialItem(
                code="41",
                description="Poupança Itaú",
                category="poupanca",
                institution="itau",
                value_brl=50000.00,
                member_key="david",
                year=2024,
            ),
        ],
        total_assets_brl=550000.00,
        total_liabilities_brl=0.0,
        net_worth_brl=550000.00,
        reference_year=2024,
        members_found=["david"],
        confidence=0.90,
        notes=None,
    )


def make_e2_llm_output() -> LLMExtractOutput:
    return LLMExtractOutput(
        source_file="btg_informe_2024.pdf",
        institution="btgpactual",
        document_type="investment_report",
        period="202412",
        member_key="david",
        currency="BRL",
        transactions=[
            ExtractedTransaction(
                date="2024-12-01",
                description="Resgate CDB",
                amount=10000.00,
            ),
        ],
        investments=[
            ExtractedInvestment(
                type="cdb",
                institution="btgpactual",
                description="CDB DI 100% CDI",
                value_brl=25000.00,
                applied_date="2024-06-15",
                maturity_date="2025-06-15",
                rate="100% CDI",
                member_key="david",
            ),
        ],
        confidence=0.88,
        notes="Investment report PDF",
    )


def make_e7_review_output() -> E7ReviewOutput:
    return E7ReviewOutput(
        insights=[
            ReviewInsight(
                category="patrimonio",
                severity="info",
                title="Patrimônio concentrado",
                description="72% em imóvel.",
                recommendation="Diversificar.",
            ),
        ],
        recommendations=["Diversificar investimentos"],
        score_adjustments=[
            ScoreAdjustment(
                factor="diversificacao",
                original_value=70.0,
                adjustment=-10.0,
                reason="100% renda fixa",
            ),
        ],
        narrative_sections=[
            NarrativeSection(
                section_key="resumo_executivo",
                title="Resumo Executivo",
                content="Situação financeira estável.",
            ),
        ],
        overall_assessment="Saúde financeira moderada.",
        risk_level="moderate",
        confidence=0.85,
    )


def make_llm_call_result(output) -> LLMCallResult:
    return LLMCallResult(
        output=output,
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        tokens_in=1500,
        tokens_out=800,
        total_tokens=2300,
        cost_estimate_usd=0.0165,
        duration_ms=2500,
        retries_used=0,
    )
