"""Golden de execução E4: tenant mínimo + E3 fixture → E4 → assert + schema.

ADR-212 PR3b: E3/baseline são seeded no ``InMemoryArtifactStore`` (não em
disco). E4 lê via ``store.read``/``list_keys``.
"""

from __future__ import annotations

import json
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


def _write_e4_config(tmp_path: Path, *, expense_keywords: dict | None = None) -> None:
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
    (cfg / "family_members.json").write_text("{}", encoding="utf-8")
    (cfg / "pipeline.json").write_text("{}", encoding="utf-8")


def _load_fixture_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def e4_tenant_minimal(tmp_path: Path) -> Path:
    """Workspace com config mínima. E3 será seeded no store pelo teste."""
    _write_e4_config(tmp_path)
    return tmp_path


@pytest.fixture
def e4_tenant_mixed_cashflow(tmp_path: Path) -> Path:
    """E3 misto + keywords. E3 será seeded no store pelo teste."""
    _write_e4_config(tmp_path, expense_keywords={"lazer": ["CINEMA"]})
    return tmp_path


@pytest.fixture
def e4_tenant_with_baseline(tmp_path: Path) -> Path:
    """E3 + baseline E1.5. Ambos serão seeded no store pelo teste."""
    _write_e4_config(tmp_path)
    return tmp_path


def _new_e4_ctx(root: Path, *, e3_fixture: Path, baseline: Path | None = None):
    """ADR-212 PR3b: ``WorkspaceContext`` requer ``artifact_store`` explícito.

    Seed E3 (e baseline opcional E1.5c) no ``InMemoryArtifactStore`` antes
    do ``main_with_store``. E4 lê E3/baseline via ``store.read``; escreve
    E4 via store.
    """
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.context import WorkspaceContext

    store = InMemoryArtifactStore()
    # E3 sob ``"E3"`` (legacy) — adapter consome via store.list_keys("E3").
    e3_key = e3_fixture.stem.replace("-3_reconciled", "")
    store.seed("E3", e3_key, _load_fixture_json(e3_fixture))
    if baseline is not None:
        store.seed("E1.5c", "baseline_patrimonial", _load_fixture_json(baseline))
    return WorkspaceContext(root=root, artifact_store=store)


def test_e4_execution_produces_unified_json(e4_tenant_minimal: Path):
    """Roda categorize_transactions.main em tenant isolado; restaura globals."""
    from scripts.categorize_transactions import main_with_store

    ctx = _new_e4_ctx(e4_tenant_minimal, e3_fixture=_E3_FIXTURE)
    main_with_store(ctx)
    store = ctx.artifact_store

    receitas = store.read("E4", "receitas")
    assert receitas is not None
    assert receitas["total_geral"] == 100.0
    assert "renda" in receitas["categorias"]

    despesas = store.read("E4", "despesas")
    assert despesas is not None
    assert despesas["total_geral"] == 0.0

    fluxo = store.read("E4", "fluxo_mensal_detalhado")
    assert fluxo is not None
    assert isinstance(fluxo.get("meses_ordenados"), list)
    assert len(fluxo["meses_ordenados"]) >= 1

    for key in ("investimentos", "seguros", "pontos_milhas"):
        assert store.exists("E4", key), f"missing E4/{key}"

    # ADR-132: sem baseline E1.5c, ``patrimonio`` é omitido — antes era
    # escrito como ``{"dados": []}`` e sobrescrevia o artefato bom de runs
    # anteriores em re-runs.
    assert not store.exists("E4", "patrimonio")

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (_REPO / "config" / "schemas" / "e4_unified.schema.json").read_text(encoding="utf-8")
    )
    from scripts.pipeline_common import validate_dict

    for key in store.list_keys("E4"):
        payload = store.read("E4", key)
        jsonschema.validate(payload, schema)
        assert validate_dict(payload, "e4_unified.schema.json", source=f"E4/{key}") is True

    assert_qa_log_md(e4_tenant_minimal)


def test_e4_execution_mixed_receita_despesa(e4_tenant_mixed_cashflow: Path):
    """Cenário com despesa categorizada (golden expandido)."""
    from scripts.categorize_transactions import main_with_store

    ctx = _new_e4_ctx(e4_tenant_mixed_cashflow, e3_fixture=_E3_MIXED)
    main_with_store(ctx)
    store = ctx.artifact_store

    receitas = store.read("E4", "receitas")
    despesas = store.read("E4", "despesas")
    assert receitas["total_geral"] == 100.0
    assert despesas["total_geral"] == 30.0
    assert "lazer" in despesas["categorias"]

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (_REPO / "config" / "schemas" / "e4_unified.schema.json").read_text(encoding="utf-8")
    )
    for key in store.list_keys("E4"):
        jsonschema.validate(store.read("E4", key), schema)

    assert_qa_log_md(e4_tenant_mixed_cashflow)


def test_e4_execution_with_baseline_patrimonial(e4_tenant_with_baseline: Path):
    """E4 com baseline: patrimonio espelha o consolidado (schema baseline, não e4_unified)."""
    from scripts.categorize_transactions import main_with_store

    ctx = _new_e4_ctx(e4_tenant_with_baseline, e3_fixture=_E3_FIXTURE, baseline=_BASELINE_MIN)
    main_with_store(ctx)
    store = ctx.artifact_store

    pat = store.read("E4", "patrimonio")
    assert pat is not None
    assert pat["pipeline_stage"] == "E1.5_Baseline_Patrimonial"
    assert pat["patrimonio_por_ano"]["2024"]["total_bens"] == 500000.0

    jsonschema = pytest.importorskip("jsonschema")
    baseline_schema = json.loads(
        (_REPO / "config" / "schemas" / "baseline_patrimonial.schema.json").read_text(
            encoding="utf-8"
        )
    )
    e4_schema = json.loads(
        (_REPO / "config" / "schemas" / "e4_unified.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(pat, baseline_schema)
    for key in store.list_keys("E4"):
        if key == "patrimonio":
            continue
        jsonschema.validate(store.read("E4", key), e4_schema)

    assert_qa_log_md(e4_tenant_with_baseline)
