"""Golden de execução E4: tenant mínimo + E3 fixture → E4 → assert + schema."""

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


@pytest.fixture
def e4_tenant_minimal(tmp_path: Path) -> Path:
    """Workspace com config mínima e um reconciliado E3 compatível com E4."""
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    cat = {
        "expense_keywords": {},
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

    e3_dir = tmp_path / "processed" / "E3_reconciled"
    e3_dir.mkdir(parents=True)
    shutil.copy(
        _E3_FIXTURE,
        e3_dir / "golden-minimal-3_reconciled.json",
    )

    return tmp_path


@pytest.fixture
def e4_tenant_mixed_cashflow(tmp_path: Path) -> Path:
    """E3 com receita + despesa (débito) e keywords para ambas as categorias."""
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    cat = {
        "expense_keywords": {"lazer": ["CINEMA"]},
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

    e3_dir = tmp_path / "processed" / "E3_reconciled"
    e3_dir.mkdir(parents=True)
    shutil.copy(_E3_MIXED, e3_dir / "golden-mixed-3_reconciled.json")

    return tmp_path


@pytest.fixture
def e4_tenant_with_baseline(tmp_path: Path) -> Path:
    """Inclui baseline E1.5 em E2_extracts (mesmo E3 mínimo que o golden base)."""
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    cat = {
        "expense_keywords": {},
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

    e2_dir = tmp_path / "processed" / "E2_extracts"
    e2_dir.mkdir(parents=True)
    shutil.copy(_BASELINE_MIN, e2_dir / "baseline_patrimonial-1.5_consolidated.json")

    e3_dir = tmp_path / "processed" / "E3_reconciled"
    e3_dir.mkdir(parents=True)
    shutil.copy(_E3_FIXTURE, e3_dir / "golden-minimal-3_reconciled.json")

    return tmp_path


def test_e4_execution_produces_unified_json(e4_tenant_minimal: Path):
    """Roda e4_categorize.main em tenant isolado; restaura globals."""
    from pipeline.context import WorkspaceContext
    from scripts.e4_categorize import main_with_store

    ctx = WorkspaceContext(root=e4_tenant_minimal)
    main_with_store(ctx)

    out = e4_tenant_minimal / "processed" / "E4_unified"
    assert out.is_dir()

    receitas_path = out / "receitas-4_unified.json"
    assert receitas_path.is_file()
    receitas = json.loads(receitas_path.read_text(encoding="utf-8"))
    assert receitas["total_geral"] == 100.0
    assert "renda" in receitas["categorias"]

    despesas = json.loads((out / "despesas-4_unified.json").read_text(encoding="utf-8"))
    assert despesas["total_geral"] == 0.0

    fluxo = json.loads((out / "fluxo_mensal_detalhado-4_unified.json").read_text(encoding="utf-8"))
    assert isinstance(fluxo.get("meses_ordenados"), list)
    assert len(fluxo["meses_ordenados"]) >= 1

    for name in (
        "patrimonio-4_unified.json",
        "investimentos-4_unified.json",
        "seguros-4_unified.json",
        "pontos_milhas-4_unified.json",
    ):
        p = out / name
        assert p.is_file(), f"missing {name}"

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (_REPO / "config" / "schemas" / "e4_unified.schema.json").read_text(encoding="utf-8")
    )
    for p in sorted(out.glob("*.json")):
        payload = json.loads(p.read_text(encoding="utf-8"))
        jsonschema.validate(payload, schema)

    from scripts.pipeline_common import validate_artifact

    for p in sorted(out.glob("*.json")):
        assert validate_artifact(p, "e4_unified.schema.json") is True

    assert_qa_log_md(e4_tenant_minimal)


def test_e4_execution_mixed_receita_despesa(e4_tenant_mixed_cashflow: Path):
    """Cenário com despesa categorizada (golden expandido)."""
    from pipeline.context import WorkspaceContext
    from scripts.e4_categorize import main_with_store

    ctx = WorkspaceContext(root=e4_tenant_mixed_cashflow)
    main_with_store(ctx)

    out = e4_tenant_mixed_cashflow / "processed" / "E4_unified"
    receitas = json.loads((out / "receitas-4_unified.json").read_text(encoding="utf-8"))
    despesas = json.loads((out / "despesas-4_unified.json").read_text(encoding="utf-8"))
    assert receitas["total_geral"] == 100.0
    assert despesas["total_geral"] == 30.0
    assert "lazer" in despesas["categorias"]

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (_REPO / "config" / "schemas" / "e4_unified.schema.json").read_text(encoding="utf-8")
    )
    for p in sorted(out.glob("*.json")):
        jsonschema.validate(json.loads(p.read_text(encoding="utf-8")), schema)

    assert_qa_log_md(e4_tenant_mixed_cashflow)


def test_e4_execution_with_baseline_patrimonial(e4_tenant_with_baseline: Path):
    """E4 com baseline: patrimonio-4_unified espelha o consolidado (schema baseline, não e4_unified)."""
    from pipeline.context import WorkspaceContext
    from scripts.e4_categorize import main_with_store

    ctx = WorkspaceContext(root=e4_tenant_with_baseline)
    main_with_store(ctx)

    out = e4_tenant_with_baseline / "processed" / "E4_unified"
    pat_path = out / "patrimonio-4_unified.json"
    pat = json.loads(pat_path.read_text(encoding="utf-8"))
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
    for p in sorted(out.glob("*.json")):
        payload = json.loads(p.read_text(encoding="utf-8"))
        if p.name == "patrimonio-4_unified.json":
            continue
        jsonschema.validate(payload, e4_schema)

    assert_qa_log_md(e4_tenant_with_baseline)
