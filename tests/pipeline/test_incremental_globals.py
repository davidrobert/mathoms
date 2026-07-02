"""Tests para extensão do modo incremental aos stages globais E1 (ADR-169)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.context import WorkspaceContext  # noqa: E402
from pipeline.incremental import (  # noqa: E402
    allowed_stems,
    filter_to_incremental,
    has_incremental_overlap,
    normalize_stem,
)
from tests._llm_stage_fixtures import make_llm_ctx  # noqa: E402
from tests.fakes.llm import FakeStructuredLLMClient  # noqa: E402

# =============================================================================
# Unit — helpers em pipeline/incremental.py
# =============================================================================


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("foo.pdf", "foo"),
        ("foo-0_original.pdf", "foo"),
        ("a/b/c-0_original.pdf", "c"),
        ("data/income_tax_br/decl_2024-0_original.pdf", "decl_2024"),
        ("decl_2024", "decl_2024"),
        ("file-0_original-extra", "file"),
    ],
)
def test_normalize_stem(raw: str, expected: str) -> None:
    assert normalize_stem(raw) == expected


def test_allowed_stems_none_when_full(tmp_path: Path) -> None:
    ctx = WorkspaceContext(root=tmp_path)
    assert allowed_stems(ctx) is None


def test_allowed_stems_none_when_incremental_but_empty(tmp_path: Path) -> None:
    ctx = WorkspaceContext(root=tmp_path, incremental=True, incremental_doc_paths=[])
    assert allowed_stems(ctx) is None


def test_allowed_stems_normalized_set(tmp_path: Path) -> None:
    ctx = WorkspaceContext(
        root=tmp_path,
        incremental=True,
        incremental_doc_paths=[
            "data/income_tax_br/decl_2024-0_original.pdf",
            "data/financial_statements/itau_extrato_202601-0_original.pdf",
        ],
    )
    assert allowed_stems(ctx) == {"decl_2024", "itau_extrato_202601"}


def test_filter_to_incremental_passthrough_full_mode(tmp_path: Path) -> None:
    ctx = WorkspaceContext(root=tmp_path)
    candidates = [Path("a-0_original.pdf"), Path("b-0_original.pdf")]
    assert filter_to_incremental(ctx, candidates) == candidates


def test_filter_to_incremental_filters_incremental(tmp_path: Path) -> None:
    ctx = WorkspaceContext(
        root=tmp_path,
        incremental=True,
        incremental_doc_paths=["data/x/a-0_original.pdf"],
    )
    candidates = [Path("a-0_original.pdf"), Path("b-0_original.pdf")]
    assert filter_to_incremental(ctx, candidates) == [Path("a-0_original.pdf")]


def test_has_incremental_overlap_full_mode_always_true(tmp_path: Path) -> None:
    ctx = WorkspaceContext(root=tmp_path)
    assert has_incremental_overlap(ctx, []) is True
    assert has_incremental_overlap(ctx, [Path("anything.pdf")]) is True


def test_has_incremental_overlap_true_with_match(tmp_path: Path) -> None:
    ctx = WorkspaceContext(
        root=tmp_path,
        incremental=True,
        incremental_doc_paths=["data/x/a-0_original.pdf"],
    )
    assert has_incremental_overlap(ctx, [Path("a-0_original.pdf"), Path("z.pdf")]) is True


def test_has_incremental_overlap_false_when_no_match(tmp_path: Path) -> None:
    ctx = WorkspaceContext(
        root=tmp_path,
        incremental=True,
        incremental_doc_paths=["data/x/a-0_original.pdf"],
    )
    assert has_incremental_overlap(ctx, [Path("y-0_original.pdf"), Path("z.pdf")]) is False


# =============================================================================
# Stage — extract_irpf_full (filtro per-doc)
# =============================================================================


def _seed_irpf_pdf(root: Path, name: str) -> Path:
    irpf_dir = root / "data" / "income_tax_br"
    irpf_dir.mkdir(parents=True, exist_ok=True)
    p = irpf_dir / name
    p.write_text("conteudo ficticio do PDF de IRPF")
    return p


def _make_irpf_fake() -> FakeStructuredLLMClient:
    from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput

    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "llm_golden"
        / "e16_irpf_full_completo.json"
    )
    fixture = json.loads(fixture_path.read_text())
    return FakeStructuredLLMClient(output=IRPFFullOutput.model_validate(fixture))


def _setup_three_irpfs_with_allowlist_for_2024(tmp_path: Path):
    ctx = make_llm_ctx(tmp_path)
    for year in (2022, 2023, 2024):
        _seed_irpf_pdf(tmp_path, f"irpfdeclaracao_{year}-0_original.pdf")
    ctx.incremental = True
    ctx.incremental_doc_paths = ["data/income_tax_br/irpfdeclaracao_2024-0_original.pdf"]
    return ctx


@patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract", return_value="fake")
@patch("pipeline.llm.litellm_client.LLMService._ensure_client")
def test_irpf_full_incremental_filters_per_doc(_mock_ensure, _mock_extract, tmp_path: Path) -> None:
    """3 IRPFs no disco; allowlist tem 1 — processa só esse 1."""
    ctx = _setup_three_irpfs_with_allowlist_for_2024(tmp_path)
    fake = _make_irpf_fake()
    with patch("pipeline.llm.litellm_client.LLMService.call", side_effect=fake.call):
        from pipeline.stages.extract_irpf_full import run

        result = run(ctx)

    assert result["declarations_extracted"] == 1
    assert fake.calls == 1
    store = ctx.get_artifact_store()
    assert store.read("extract_irpf_full", "irpfdeclaracao_2024") is not None
    assert store.read("extract_irpf_full", "irpfdeclaracao_2023") is None
    assert store.read("extract_irpf_full", "irpfdeclaracao_2022") is None


def test_irpf_full_incremental_skips_when_no_overlap(tmp_path: Path) -> None:
    ctx = make_llm_ctx(tmp_path)
    _seed_irpf_pdf(tmp_path, "irpfdeclaracao_2022-0_original.pdf")
    ctx.incremental = True
    ctx.incremental_doc_paths = ["data/financial_statements/itau_202601-0_original.pdf"]

    from pipeline.stages.extract_irpf_full import run

    result = run(ctx)

    assert result["skipped"] is True
    assert "incremental" in result["reason"]


# =============================================================================
# Stage — extract_baseline (filter per-doc + agregação read-from-store)
# =============================================================================


def test_baseline_incremental_skips_when_no_new_irpf(tmp_path: Path) -> None:
    ctx = make_llm_ctx(tmp_path)
    irpf_dir = tmp_path / "data" / "income_tax_br"
    irpf_dir.mkdir(parents=True)
    (irpf_dir / "irpfdeclaracao_2022-0_original.pdf").write_text("dummy")
    ctx.incremental = True
    ctx.incremental_doc_paths = ["data/financial_statements/itau_202601-0_original.pdf"]

    from pipeline.stages.extract_baseline import run

    result = run(ctx)

    assert result["skipped"] is True
    assert "incremental" in result["reason"]


def _e15a_item(descricao: str, value: float, ano: int) -> dict:
    return {
        "codigo": "01",
        "descricao": descricao,
        "categoria": "imovel",
        "valor_brl": value,
        "membro": "david",
        "ano": ano,
    }


def _e15a_resumo(value: float, ano: int) -> dict:
    return {
        "total_ativos": value,
        "total_passivos": 0.0,
        "patrimonio_liquido": value,
        "ano_referencia": ano,
        "membros": ["david"],
    }


def _seed_existing_e15a(store, *, key: str, descricao: str, value: float, ano: int) -> None:
    payload = {
        "itens": [_e15a_item(descricao, value, ano)],
        "resumo": _e15a_resumo(value, ano),
        "_meta": {"source": "E1.5-llm", "confidence": 0.9, "notes": None},
    }
    store.write("E1.5a", key, payload)


def _patrimonial_item(descricao: str, value: float, ano: int):
    from pipeline.llm.schemas.e15_baseline import PatrimonialItem

    return PatrimonialItem(
        code="41",
        description=descricao,
        category="poupanca",
        institution="itau",
        value_brl=value,
        member_key="david",
        year=ano,
    )


def _make_baseline_output(*, descricao: str, value: float, ano: int):
    from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput

    return BaselinePatrimonialOutput(
        items=[_patrimonial_item(descricao, value, ano)],
        total_assets_brl=value,
        total_liabilities_brl=0.0,
        net_worth_brl=value,
        reference_year=ano,
        members_found=["david"],
        confidence=0.95,
        notes=None,
    )


def _setup_baseline_aggregate_scenario(tmp_path: Path):
    ctx = make_llm_ctx(tmp_path)
    irpf_dir = tmp_path / "data" / "income_tax_br"
    irpf_dir.mkdir(parents=True)
    (irpf_dir / "irpfdeclaracao_2024-0_original.pdf").write_text("doc novo")
    (irpf_dir / "irpfdeclaracao_2023-0_original.pdf").write_text("doc antigo")
    _seed_existing_e15a(
        ctx.get_artifact_store(),
        key="irpfdeclaracao_2023",
        descricao="Imovel antigo",
        value=200000.0,
        ano=2023,
    )
    ctx.incremental = True
    ctx.incremental_doc_paths = ["data/income_tax_br/irpfdeclaracao_2024-0_original.pdf"]
    return ctx


@patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract", return_value="fake")
@patch("pipeline.llm.litellm_client.LLMService._ensure_client")
def test_baseline_incremental_aggregate_combines_store_existing_and_new(
    _mock_ensure, _mock_extract, tmp_path: Path
) -> None:
    """E1.5a antigo (no store) + IRPF novo (filtered) → E1.5 agregado contém ambos."""
    ctx = _setup_baseline_aggregate_scenario(tmp_path)
    fake = FakeStructuredLLMClient(
        output=_make_baseline_output(descricao="Poupanca novo", value=50000.0, ano=2024)
    )

    with patch("pipeline.llm.litellm_client.LLMService.call", side_effect=fake.call):
        from pipeline.stages.extract_baseline import run

        result = run(ctx)

    assert fake.calls == 1
    assert result["files_processed"] == 1
    aggregated = ctx.get_artifact_store().read("E1.5", "baseline_patrimonial")
    descricoes = sorted(item["descricao"] for item in aggregated["itens"])
    assert descricoes == ["Imovel antigo", "Poupanca novo"]
    assert aggregated["resumo"]["total_ativos"] == "250000.00"  # v1 float + v2 → str (A20.l11)


# =============================================================================
# Stage — extract_members (skip-if-no-overlap)
# =============================================================================


def test_members_incremental_skips_when_no_new_personal(tmp_path: Path) -> None:
    ctx = make_llm_ctx(tmp_path)
    irpf_dir = tmp_path / "data" / "income_tax_br"
    irpf_dir.mkdir(parents=True)
    # Doc personal antigo no disco — usuário fez upload anteriormente.
    (irpf_dir / "irpfdeclaracao_2022-0_original.pdf").write_text("antigo")
    ctx.incremental = True
    # Allowlist apenas com bank statement novo (não-personal).
    ctx.incremental_doc_paths = ["data/financial_statements/itau_202601-0_original.pdf"]

    from pipeline.stages.extract_members import run

    result = run(ctx)

    assert result["skipped"] is True
    assert "incremental" in result["reason"]


def _setup_members_run_scenario(tmp_path: Path):
    ctx = make_llm_ctx(tmp_path)
    _seed_irpf_pdf(tmp_path, "irpfdeclaracao_2024-0_original.pdf")
    ctx.incremental = True
    ctx.incremental_doc_paths = ["data/income_tax_br/irpfdeclaracao_2024-0_original.pdf"]
    return ctx


@patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract", return_value="fake")
@patch("pipeline.llm.litellm_client.LLMService._ensure_client")
def test_members_incremental_runs_when_new_personal_doc(
    _mock_ensure, _mock_extract, tmp_path: Path
) -> None:
    """Pelo menos 1 personal doc novo → roda full sobre todos personal docs (paridade)."""
    from tests._llm_stage_fixtures import make_e1_output

    ctx = _setup_members_run_scenario(tmp_path)
    fake = FakeStructuredLLMClient(output=make_e1_output())
    with patch("pipeline.llm.litellm_client.LLMService.call", side_effect=fake.call):
        from pipeline.stages.extract_members import run

        result = run(ctx)

    assert result["success"] is True
    assert fake.calls == 1
