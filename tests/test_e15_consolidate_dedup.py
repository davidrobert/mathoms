"""Integration: E1.5c deduplica imóveis co-declarados cross-IRPF (ADR-246)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext

_DESC_LIVING_WISH = (
    "APARTAMENTO LIVING WISH - AV JOAO DIAS 2192 TORRE 2 APT 163, SANTO AMARO SAO PAULO/SP"
)


def _make_item(*, codigo: str, descricao: str, valor_brl, membro: str, ano: int = 2024) -> dict:
    return {
        "codigo": codigo,
        "descricao": descricao,
        "categoria": "imovel",
        "valor_brl": valor_brl,
        "membro": membro,
        "ano": ano,
    }


def _make_baseline(itens: list[dict]) -> dict:
    total = sum(it["valor_brl"] for it in itens)
    return {
        "itens": itens,
        "resumo": {
            "total_ativos": total,
            "total_passivos": 0.0,
            "patrimonio_liquido": total,
            "ano_referencia": 2024,
        },
    }


def _make_ctx(
    tmp_path: Path, baseline: dict
) -> tuple[WorkspaceContext, InMemoryPropertyIdentityResolver]:
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "pipeline.json").write_text("{}")
    (tmp_path / "config" / "family_members.json").write_text("{}")
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", baseline)
    resolver = InMemoryPropertyIdentityResolver()
    ctx = WorkspaceContext(
        root=tmp_path,
        artifact_store=store,
        workspace_id="test-ws-dedup",
        property_identity_resolver=resolver,
    )
    return ctx, resolver


def _run_consolidate(ctx: WorkspaceContext) -> list[dict]:
    from scripts.e15_consolidate import main_with_store

    result = main_with_store(ctx)
    assert result["success"] is True
    consolidated = ctx.get_artifact_store().read("E1.5c", "baseline_patrimonial")
    return consolidated["imoveis_consolidados"]


@pytest.fixture
def co_declared_living_wish(tmp_path: Path) -> list[dict]:
    """Cenário real: David R$ 477.436,58 vs Mariana R$ 530.000 (LIVING WISH)."""
    baseline = _make_baseline(
        [
            _make_item(
                codigo="11", descricao=_DESC_LIVING_WISH, valor_brl=477436.58, membro="david_robert"
            ),
            _make_item(
                codigo="11", descricao=_DESC_LIVING_WISH, valor_brl=530000.00, membro="mariana_xxx"
            ),
        ]
    )
    ctx, _ = _make_ctx(tmp_path, baseline)
    return _run_consolidate(ctx)


@pytest.fixture
def distinct_imoveis(tmp_path: Path) -> list[dict]:
    baseline = _make_baseline(
        [
            _make_item(
                codigo="11",
                descricao="APT AV PAULISTA 1500",
                valor_brl=800000.0,
                membro="david_robert",
            ),
            _make_item(
                codigo="12",
                descricao="CASA RUA AUGUSTA 100",
                valor_brl=1200000.0,
                membro="david_robert",
            ),
        ]
    )
    ctx, _ = _make_ctx(tmp_path, baseline)
    return _run_consolidate(ctx)


@pytest.fixture
def single_declarant(tmp_path: Path) -> list[dict]:
    baseline = _make_baseline(
        [
            _make_item(
                codigo="11",
                descricao="APT RUA PINHEIROS 500",
                valor_brl=800000.0,
                membro="david_robert",
            )
        ]
    )
    ctx, _ = _make_ctx(tmp_path, baseline)
    return _run_consolidate(ctx)


@pytest.fixture
def high_divergence_co_declared(tmp_path: Path) -> list[dict]:
    desc = "APT RUA DA PAZ 100"
    baseline = _make_baseline(
        [
            _make_item(codigo="11", descricao=desc, valor_brl=400000.0, membro="david_robert"),
            _make_item(codigo="11", descricao=desc, valor_brl=600000.0, membro="mariana_xxx"),
        ]
    )
    ctx, _ = _make_ctx(tmp_path, baseline)
    return _run_consolidate(ctx)


def test_co_declared_collapses_to_single_entry(co_declared_living_wish):
    assert len(co_declared_living_wish) == 1


def test_co_declared_uses_maior_valor(co_declared_living_wish):
    assert co_declared_living_wish[0]["valores_31_12"]["2024"] == 530000.0


def test_co_declared_marks_casal(co_declared_living_wish):
    merged = co_declared_living_wish[0]
    assert merged["proprietario"] == "casal"
    assert set(merged["proprietarios"]) == {"david_robert", "mariana_xxx"}


def test_co_declared_preserves_property_id(co_declared_living_wish):
    assert co_declared_living_wish[0]["property_id"] is not None


def test_co_declared_below_10pct_no_warning(co_declared_living_wish):
    # 477.436,58 vs 530.000 ≈ 9.92% — abaixo do limiar
    assert "_dedup_warning" not in co_declared_living_wish[0]


def test_distinct_imoveis_preserved(distinct_imoveis):
    assert len(distinct_imoveis) == 2
    assert {e["proprietario"] for e in distinct_imoveis} == {"david_robert"}


def test_single_declarant_not_marked_casal(single_declarant):
    assert len(single_declarant) == 1
    assert single_declarant[0]["proprietario"] == "david_robert"
    assert "proprietarios" not in single_declarant[0]


def test_high_divergence_marks_warning(high_divergence_co_declared):
    merged = high_divergence_co_declared[0]
    assert merged["valores_31_12"]["2024"] == 600000.0
    assert merged["_dedup_warning"]["type"] == "valor_divergente"
    assert merged["_dedup_warning"]["diff_pct"] > 10.0
