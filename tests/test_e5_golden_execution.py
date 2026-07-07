"""Golden de execução E5: tenant mínimo + E3→E4→E5 → assert + schema.

ADR-212 PR3b: E3/baseline são seeded no ``InMemoryArtifactStore`` (não em
disco). E4/E5 lêem/escrevem via store API.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.pipeline_golden_asserts import assert_qa_log_md

_REPO = Path(__file__).resolve().parents[1]
_E3_FIXTURE = (
    _REPO / "tests" / "fixtures" / "pipeline_golden" / "e3" / "minimal-conta-3_reconciled.json"
)
_E3_MIXED = (
    _REPO
    / "tests"
    / "fixtures"
    / "pipeline_golden"
    / "e3"
    / "minimal-conta-com-despesa-3_reconciled.json"
)
_BASELINE_MIN = (
    _REPO
    / "tests"
    / "fixtures"
    / "pipeline_golden"
    / "e2"
    / "minimal-baseline-1.5_consolidated.json"
)
# ADR-274: itens em ano-base (2024) mas patrimonio_por_ano chaveado em
# exercício (2025) — reproduz o off-by-one que zerava imóveis no relatório.
_BASELINE_DIVERGENT = (
    _REPO
    / "tests"
    / "fixtures"
    / "pipeline_golden"
    / "e2"
    / "minimal-baseline-divergent-1.5_consolidated.json"
)
# A7.5: ``parametros_fiscais.json`` + ``taxas.json`` saíram de ``config/`` —
# fixtures locais cobrem tests legacy que precisam dos JSONs em disco.
_LEGACY_CONFIGS = _REPO / "tests" / "fixtures" / "legacy_configs"
_LEGACY_FISCAL = _LEGACY_CONFIGS / "parametros_fiscais.json"
_LEGACY_TAXAS = _LEGACY_CONFIGS / "taxas.json"

_GOALS_MIN = {
    "independencia_financeira": {
        "if_meta": 1_000_000.0,
        "trs_pct": 4.0,
    }
}

_FAMILY_E5 = {
    "titular": "david",
    "membros": {
        "david": {
            "nome_curto": "David",
            "data_nascimento": "1985-06-15",
        }
    },
}


def _write_e5_config(tmp_path: Path, *, expense_keywords: dict | None = None) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    cat = {
        "expense_keywords": expense_keywords or {},
        "income_keywords": {"renda": ["PIX"]},
        "internal_transfer_patterns": [],
        "pj_source_mapping": {},
        "clt_source_mapping": {},
    }
    (cfg / "categorization.json").write_text(
        json.dumps(cat, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (cfg / "family_members.json").write_text(
        json.dumps(_FAMILY_E5, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (cfg / "pipeline.json").write_text("{}", encoding="utf-8")
    (cfg / "goals.json").write_text(
        json.dumps(_GOALS_MIN, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    shutil.copy(_REPO / "config" / "scoring.json", cfg / "scoring.json")
    shutil.copy(_LEGACY_FISCAL, cfg / "parametros_fiscais.json")
    shutil.copy(_LEGACY_TAXAS, cfg / "taxas.json")


def _load_fixture_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _new_e5_ctx(root: Path, *, e3_fixture: Path, baseline: Path | None = None):
    """Cria WorkspaceContext com InMemoryArtifactStore seeded com E3 + baseline."""
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.context import WorkspaceContext

    store = InMemoryArtifactStore()
    e3_key = e3_fixture.stem.replace("-3_reconciled", "")
    store.seed("E3", e3_key, _load_fixture_json(e3_fixture))
    if baseline is not None:
        store.seed("E1.5c", "baseline_patrimonial", _load_fixture_json(baseline))
    return WorkspaceContext(root=root, artifact_store=store)


@pytest.fixture
def e5_tenant_minimal(tmp_path: Path) -> Path:
    _write_e5_config(tmp_path)
    return tmp_path


@pytest.fixture
def e5_tenant_mixed_cashflow(tmp_path: Path) -> Path:
    _write_e5_config(tmp_path, expense_keywords={"lazer": ["CINEMA"]})
    return tmp_path


@pytest.fixture
def e5_tenant_with_baseline(tmp_path: Path) -> Path:
    _write_e5_config(tmp_path)
    return tmp_path


def test_e5_execution_produces_analysis_json(e5_tenant_minimal: Path):
    """Roda E4 e E5 em tenant isolado; restaura globals dos scripts."""
    from scripts.categorize_transactions import main_with_store as e4_mws
    from scripts.e5_analyze import main_with_store as e5_mws

    ctx = _new_e5_ctx(e5_tenant_minimal, e3_fixture=_E3_FIXTURE)
    e4_mws(ctx)
    e5_mws(ctx)
    store = ctx.artifact_store

    payload = store.read("E5", "analise_financeira")
    assert payload is not None
    assert payload["score"]["valor"] >= 0
    assert payload["score"]["valor"] <= 10
    assert isinstance(payload["score"]["classificacao"], str)
    assert "bruto" in payload["patrimonio"] and "liquido" in payload["patrimonio"]
    assert "fluxo_caixa" in payload
    assert payload["goals"]["if_meta"] == 1_000_000.0

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (_REPO / "config" / "schemas" / "e5_analysis.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(payload, schema)

    from scripts.pipeline_common import validate_dict

    assert validate_dict(payload, "e5_analysis.schema.json") is True

    assert_qa_log_md(e5_tenant_minimal)


def test_e5_execution_mixed_receita_despesa(e5_tenant_mixed_cashflow: Path):
    """E5 com receitas e despesas não nulas no E4 (golden expandido)."""
    from scripts.categorize_transactions import main_with_store as e4_mws
    from scripts.e5_analyze import main_with_store as e5_mws

    ctx = _new_e5_ctx(e5_tenant_mixed_cashflow, e3_fixture=_E3_MIXED)
    e4_mws(ctx)
    e5_mws(ctx)
    store = ctx.artifact_store

    payload = store.read("E5", "analise_financeira")
    fc = payload["fluxo_caixa"]
    assert fc.get("receita_total", 0) > 0
    assert fc.get("despesa_total", 0) > 0

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (_REPO / "config" / "schemas" / "e5_analysis.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(payload, schema)

    assert_qa_log_md(e5_tenant_mixed_cashflow)


def test_e5_execution_with_baseline_patrimonial(e5_tenant_with_baseline: Path):
    """E5 lê baseline consolidado: patrimônio bruto/líquido refletem totais do IRPF sintético."""
    from scripts.categorize_transactions import main_with_store as e4_mws
    from scripts.e5_analyze import main_with_store as e5_mws

    ctx = _new_e5_ctx(e5_tenant_with_baseline, e3_fixture=_E3_FIXTURE, baseline=_BASELINE_MIN)
    e4_mws(ctx)
    e5_mws(ctx)
    store = ctx.artifact_store

    payload = store.read("E5", "analise_financeira")
    assert payload["patrimonio"]["bruto"] == 500_000.0
    assert payload["patrimonio"]["liquido"] == 400_000.0
    assert payload["patrimonio"]["dividas"] == 100_000.0

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (_REPO / "config" / "schemas" / "e5_analysis.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(payload, schema)

    assert_qa_log_md(e5_tenant_with_baseline)


def test_e5_divergent_baseline_imoveis_not_zeroed(e5_tenant_with_baseline: Path):
    """ADR-274 end-to-end: baseline com itens em ano-base (2024) e resumo
    chaveado em exercício (2025) não pode zerar imóveis. Antes do fix, o
    resolver buscava ``valores_31_12['2025']`` (miss) → ``valor_31_12_ano_base``
    = 0 → classe 'Imóveis Investimento' = 0 (sintoma do relatório)."""
    from scripts.categorize_transactions import main_with_store as e4_mws
    from scripts.e5_analyze import main_with_store as e5_mws

    ctx = _new_e5_ctx(e5_tenant_with_baseline, e3_fixture=_E3_FIXTURE, baseline=_BASELINE_DIVERGENT)
    e4_mws(ctx)
    e5_mws(ctx)
    payload = ctx.artifact_store.read("E5", "analise_financeira")

    classes = {c["categoria"]: c["valor"] for c in payload["investimentos"]["tabela_classes"]}
    assert classes.get("Imóveis Investimento", 0) == 350_000.0
    assert payload["patrimonio"]["bruto"] == 350_000.0
