#!/usr/bin/env python3
"""Stage runner tests for E1.6 (`extract_irpf_full`) — ADR-157."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._llm_stage_fixtures import make_llm_ctx, make_llm_ctx_no_llm
from tests.fakes.llm import FakeStructuredLLMClient

GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "llm_golden"

_STRUCTURAL_FIELDS = (
    "contribuinte",
    "rendimentos_pj",
    "rendimentos_pf",
    "rendimentos_exterior",
    "rendimentos_isentos",
    "rendimentos_tributacao_exclusiva",
    "pagamentos_efetuados",
    "dividas_onus",
    "imposto_apurado",
    "dependentes",
    "bens_direitos",
)


def _load_fixture(name: str) -> dict:
    return json.loads((GOLDEN_DIR / f"e16_irpf_full_{name}.json").read_text())


def _seed_irpf_pdf(tmp_path: Path, doc_name: str) -> None:
    irpf_dir = tmp_path / "data" / "income_tax_br"
    irpf_dir.mkdir(parents=True, exist_ok=True)
    (irpf_dir / doc_name).write_text("conteudo ficticio do PDF de IRPF")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("irpfdeclaracao_2024.pdf", "irpfdeclaracao_2024.pdf"),
        (
            "irpfdeclaracao_jose_silva_99988877766.pdf",
            "irpfdeclaracao_jose_silva_<cpf-redacted>.pdf",
        ),
        (
            "decl_123.456.789-00.pdf",
            "decl_<cpf-redacted>.pdf",
        ),
        ("ano_2024_doc.pdf", "ano_2024_doc.pdf"),  # 4 dígitos isolados não casam
    ],
)
def test_redact_filename_pii(raw: str, expected: str) -> None:
    from pipeline.stages.extract_irpf_full import _redact_filename_pii

    assert _redact_filename_pii(raw) == expected


def _build_setup(tmp_path: Path, fixture_name: str, doc_name: str):
    from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput

    ctx = make_llm_ctx(tmp_path)
    _seed_irpf_pdf(tmp_path, doc_name)
    fixture = _load_fixture(fixture_name)
    fake = FakeStructuredLLMClient(output=IRPFFullOutput.model_validate(fixture))
    return ctx, fixture, fake


def _run_with_fake(ctx, fake):
    with patch("pipeline.llm.litellm_client.LLMService.call", side_effect=fake.call):
        from pipeline.stages.extract_irpf_full import run

        return run(ctx)


def _assert_models_equal(persisted: dict, fixture: dict) -> None:
    """Paridade semântica via roundtrip pelo schema (neutraliza None vs missing)."""
    from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput

    pm = IRPFFullOutput.model_validate(persisted)
    fm = IRPFFullOutput.model_validate(fixture)
    for f in _STRUCTURAL_FIELDS:
        assert getattr(pm, f) == getattr(fm, f), f"{f}: fixture vs persisted divergem"


class TestExtractIrpfFullSkips:
    def test_skips_without_llm_config(self, tmp_path):
        ctx = make_llm_ctx_no_llm(tmp_path)
        from pipeline.stages.extract_irpf_full import run

        result = run(ctx)
        assert result["skipped"] is True
        assert "free tier" in result["reason"]

    def test_skips_without_irpf_declarations(self, tmp_path):
        ctx = make_llm_ctx(tmp_path)
        from pipeline.stages.extract_irpf_full import run

        result = run(ctx)
        assert result["skipped"] is True
        assert "No IRPF declarations" in result["reason"]

    def test_skips_recibo_only(self, tmp_path):
        """Recibo de entrega não conta — só `irpfdeclaracao*` entra na fila."""
        ctx = make_llm_ctx(tmp_path)
        irpf_dir = tmp_path / "data" / "income_tax_br"
        irpf_dir.mkdir(parents=True)
        (irpf_dir / "receitafederal_irpfrecibo_2024.pdf").write_text("recibo dummy")
        from pipeline.stages.extract_irpf_full import run

        result = run(ctx)
        assert result["skipped"] is True


class TestExtractIrpfFullRun:
    @patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract")
    @patch("pipeline.llm.litellm_client.LLMService._ensure_client")
    def test_completo_persists_byte_byte_against_fixture(
        self, _mock_ensure, mock_extract, tmp_path
    ):
        ctx, fixture, fake = _build_setup(tmp_path, "completo", "irpfdeclaracaodavid2024.pdf")
        mock_extract.return_value = "IRPF declaracao 2024 (texto fake)"

        result = _run_with_fake(ctx, fake)

        assert result["success"] is True
        assert result["declarations_extracted"] == 1
        assert result["anos_base"] == [2024]
        assert result["validation"]["valid"] is True
        assert fake.calls == 1

        persisted = ctx.get_artifact_store().read("extract_irpf_full", "irpfdeclaracaodavid2024")
        _assert_models_equal(persisted, fixture)
        assert persisted["prompt_version"] == "e16-v1.0.0"
        assert persisted["confidence"] == fixture["confidence"]

    @patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract")
    @patch("pipeline.llm.litellm_client.LLMService._ensure_client")
    def test_simplificado_validates_clean(self, _mock_ensure, mock_extract, tmp_path):
        ctx, _fixture, fake = _build_setup(
            tmp_path, "simplificado", "irpfdeclaracaosimples2024.pdf"
        )
        mock_extract.return_value = "IRPF simplificado (fake)"

        result = _run_with_fake(ctx, fake)

        assert result["success"] is True
        assert result["validation"]["valid"] is True
        # Sem PGBL no simplificado: nenhum warning de "PGBL".
        assert not any("PGBL" in w for w in result["validation"]["warnings"])

    @patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract")
    @patch("pipeline.llm.litellm_client.LLMService._ensure_client")
    def test_edge_cases_preserves_low_confidence(self, _mock_ensure, mock_extract, tmp_path):
        ctx, _fixture, fake = _build_setup(tmp_path, "edge_cases", "irpfdeclaracaoedge2024.pdf")
        mock_extract.return_value = "IRPF edge cases (fake)"

        result = _run_with_fake(ctx, fake)

        assert result["success"] is True
        persisted = ctx.get_artifact_store().read("extract_irpf_full", "irpfdeclaracaoedge2024")
        # Reconcilia OK → confidence preservado em 0.82; exterior multi-moeda; dívida estagnada.
        assert persisted["confidence"] == 0.82
        assert len(persisted["rendimentos_exterior"]) == 2
        assert persisted["dividas_onus"][0]["valor_inicial_brl"] == "45000.00"
        assert persisted["dividas_onus"][0]["valor_final_brl"] == "45000.00"

    @patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract")
    @patch("pipeline.llm.litellm_client.LLMService._ensure_client")
    def test_artifact_key_strips_zero_original_suffix(self, _mock_ensure, mock_extract, tmp_path):
        """E1.6 stem strip paridade com E1.5a (`_artifact_key_for`)."""
        ctx, _fixture, fake = _build_setup(
            tmp_path, "completo", "irpfdeclaracaodavid2024-0_original.pdf"
        )
        mock_extract.return_value = "fake"

        result = _run_with_fake(ctx, fake)

        assert result["success"] is True
        store = ctx.get_artifact_store()
        assert store.read("extract_irpf_full", "irpfdeclaracaodavid2024") is not None


class TestExtractIrpfFullReconcileFailure:
    """Reconcile divergente → confidence cap em 0.7 + needs_review (ADR-157)."""

    def _build_diverging_fixture(self) -> dict:
        # Mutamos `ir_pago` p/ valor não conciliável; ajustamos XOR a_restituir/a_pagar.
        fixture = _load_fixture("completo")
        fixture["imposto_apurado"]["ir_pago_brl"] = "99999.00"
        fixture["imposto_apurado"]["ir_a_pagar_brl"] = None
        fixture["imposto_apurado"]["ir_a_restituir_brl"] = "54999.00"
        fixture["confidence"] = 0.95
        return fixture

    def _setup_diverging(self, tmp_path: Path):
        from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput

        ctx = make_llm_ctx(tmp_path)
        _seed_irpf_pdf(tmp_path, "irpfdeclaracaobad2024.pdf")
        fixture = self._build_diverging_fixture()
        fake = FakeStructuredLLMClient(output=IRPFFullOutput.model_validate(fixture))
        return ctx, fake

    @patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract")
    @patch("pipeline.llm.litellm_client.LLMService._ensure_client")
    def test_confidence_capped_when_reconcile_diverges(self, _mock_ensure, mock_extract, tmp_path):
        ctx, fake = self._setup_diverging(tmp_path)
        mock_extract.return_value = "fake"

        result = _run_with_fake(ctx, fake)

        assert result["success"] is True
        assert any("divergente" in w for w in result["validation"]["warnings"])
        persisted = ctx.get_artifact_store().read("extract_irpf_full", "irpfdeclaracaobad2024")
        assert persisted["confidence"] == pytest.approx(0.7)
        assert persisted["needs_review"] is True
