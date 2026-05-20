"""W2-T05 · ADR-233 — incremental + prompt_version em ``extract_with_llm``."""

# Cobre os 4 cenários da lane: modo full processa todos; incremental+allowlist
# com 1 doc processa só esse; incremental sem overlap skipa; payload contém
# prompt_version (ADR-233).

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests._llm_stage_fixtures import make_e2_llm_output, make_llm_ctx  # noqa: E402
from tests.fakes.llm import FakeStructuredLLMClient  # noqa: E402


def _seed_unprocessed_doc(root: Path, name: str) -> Path:
    """Seed dummy PDF em data/financial_statements/ (entra na fila do E2-llm)."""
    fs_dir = root / "data" / "financial_statements"
    fs_dir.mkdir(parents=True, exist_ok=True)
    p = fs_dir / name
    p.write_text("conteudo ficticio do informe de investimentos")
    return p


@patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract", return_value="fake-content")
@patch("pipeline.llm.text_extractor.DocumentTextExtractor.is_image", return_value=False)
@patch("pipeline.llm.litellm_client.LLMService._ensure_client")
def test_extract_with_llm_full_mode_processes_all(
    _mock_ensure, _mock_is_image, _mock_extract, tmp_path: Path
) -> None:
    """Modo full (default): processa todos os docs sem artifact E2."""
    ctx = make_llm_ctx(tmp_path)
    _seed_unprocessed_doc(tmp_path, "btg_informe_202412-0_original.pdf")
    _seed_unprocessed_doc(tmp_path, "btg_informe_202411-0_original.pdf")

    fake = FakeStructuredLLMClient(output=make_e2_llm_output())
    with patch("pipeline.llm.litellm_client.LLMService.call", side_effect=fake.call):
        from pipeline.stages.extract_with_llm import run

        result = run(ctx)

    assert result.get("skipped") is not True
    assert result["total_processed"] == 2
    assert fake.calls == 2


@patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract", return_value="fake-content")
@patch("pipeline.llm.text_extractor.DocumentTextExtractor.is_image", return_value=False)
@patch("pipeline.llm.litellm_client.LLMService._ensure_client")
def test_extract_with_llm_incremental_filters_to_allowlist(
    _mock_ensure, _mock_is_image, _mock_extract, tmp_path: Path
) -> None:
    """Modo incremental: 2 docs no disco, allowlist tem 1 — processa só esse."""
    ctx = make_llm_ctx(tmp_path)
    _seed_unprocessed_doc(tmp_path, "btg_informe_202412-0_original.pdf")
    _seed_unprocessed_doc(tmp_path, "btg_informe_202411-0_original.pdf")

    ctx.incremental = True
    ctx.incremental_doc_paths = [
        "data/financial_statements/btg_informe_202412-0_original.pdf",
    ]

    fake = FakeStructuredLLMClient(output=make_e2_llm_output())
    with patch("pipeline.llm.litellm_client.LLMService.call", side_effect=fake.call):
        from pipeline.stages.extract_with_llm import run

        result = run(ctx)

    assert result.get("skipped") is not True
    assert result["total_processed"] == 1
    assert fake.calls == 1


def test_extract_with_llm_incremental_skips_when_no_overlap(tmp_path: Path) -> None:
    """Modo incremental + allowlist sem overlap → skipped, sem chamar LLM."""
    ctx = make_llm_ctx(tmp_path)
    _seed_unprocessed_doc(tmp_path, "btg_informe_202412-0_original.pdf")

    ctx.incremental = True
    ctx.incremental_doc_paths = [
        # allowlist aponta para um doc que não está em data/financial_statements/
        "data/income_tax_br/irpfdeclaracao_2024-0_original.pdf",
    ]

    from pipeline.stages.extract_with_llm import run

    result = run(ctx)

    assert result["skipped"] is True
    assert "incremental" in result["reason"]


@patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract", return_value="fake-content")
@patch("pipeline.llm.text_extractor.DocumentTextExtractor.is_image", return_value=False)
@patch("pipeline.llm.litellm_client.LLMService._ensure_client")
def test_extract_with_llm_payload_carries_prompt_version(
    _mock_ensure, _mock_is_image, _mock_extract, tmp_path: Path
) -> None:
    """E2-llm payload escrito no store contém prompt_version (ADR-233)."""
    from pipeline.llm.prompts.e2_llm import PROMPT_VERSION

    ctx = make_llm_ctx(tmp_path)
    doc = _seed_unprocessed_doc(tmp_path, "btg_informe_202412-0_original.pdf")

    fake = FakeStructuredLLMClient(output=make_e2_llm_output())
    with patch("pipeline.llm.litellm_client.LLMService.call", side_effect=fake.call):
        from pipeline.stages.extract_with_llm import run

        run(ctx)

    store = ctx.get_artifact_store()
    keys = store.list_keys("E2-llm")
    assert keys, "stage não gravou artifact E2-llm"
    payload = store.read("E2-llm", keys[0])
    assert payload is not None
    assert payload.get("prompt_version") == PROMPT_VERSION
    # E o doc físico do disco realmente foi consumido (sanity).
    assert doc.exists()


@pytest.mark.parametrize("stage", ["extract_members", "extract_baseline"])
def test_other_llm_stages_propagate_prompt_version(stage: str) -> None:
    """Sanity: módulos do prompt expõem PROMPT_VERSION para os stages consumirem."""
    if stage == "extract_members":
        from pipeline.llm.prompts.e1_members import PROMPT_VERSION
    else:
        from pipeline.llm.prompts.e15_baseline import PROMPT_VERSION

    assert isinstance(PROMPT_VERSION, str)
    # Formato canônico (ADR-233): semver puro.
    import re

    assert re.match(
        r"^\d+\.\d+\.\d+$", PROMPT_VERSION
    ), f"prompt {stage} PROMPT_VERSION={PROMPT_VERSION!r} não é semver puro"
