"""Golden de execução E5: tenant mínimo + E3→E4→E5 → assert + schema."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.pipeline_golden_asserts import assert_qa_log_md

_REPO = Path(__file__).resolve().parents[1]
_E3_FIXTURE = _REPO / "tests" / "fixtures" / "pipeline_golden" / "e3" / "minimal-conta-3_reconciled.json"
_E3_MIXED = _REPO / "tests" / "fixtures" / "pipeline_golden" / "e3" / "minimal-conta-com-despesa-3_reconciled.json"
_BASELINE_MIN = _REPO / "tests" / "fixtures" / "pipeline_golden" / "e2" / "minimal-baseline-1.5_consolidated.json"

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


@pytest.fixture
def e5_tenant_minimal(tmp_path: Path) -> Path:
    """Workspace com configs E4+E5 e um reconciliado E3; E4 gera E4_unified, E5 lê."""
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
    shutil.copy(_REPO / "config" / "parametros_fiscais.json", cfg / "parametros_fiscais.json")
    shutil.copy(_REPO / "config" / "taxas.json", cfg / "taxas.json")

    e3_dir = tmp_path / "processed" / "E3_reconciled"
    e3_dir.mkdir(parents=True)
    shutil.copy(_E3_FIXTURE, e3_dir / "golden-minimal-3_reconciled.json")

    return tmp_path


@pytest.fixture
def e5_tenant_mixed_cashflow(tmp_path: Path) -> Path:
    """Como e5_tenant_minimal, mas E3 com receita + despesa categorizada."""
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
    shutil.copy(_REPO / "config" / "parametros_fiscais.json", cfg / "parametros_fiscais.json")
    shutil.copy(_REPO / "config" / "taxas.json", cfg / "taxas.json")

    e3_dir = tmp_path / "processed" / "E3_reconciled"
    e3_dir.mkdir(parents=True)
    shutil.copy(_E3_MIXED, e3_dir / "golden-mixed-3_reconciled.json")

    return tmp_path


@pytest.fixture
def e5_tenant_with_baseline(tmp_path: Path) -> Path:
    """Como e5_tenant_minimal + baseline patrimonial em E2_extracts."""
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
    shutil.copy(_REPO / "config" / "parametros_fiscais.json", cfg / "parametros_fiscais.json")
    shutil.copy(_REPO / "config" / "taxas.json", cfg / "taxas.json")

    e2_dir = tmp_path / "processed" / "E2_extracts"
    e2_dir.mkdir(parents=True)
    shutil.copy(_BASELINE_MIN, e2_dir / "baseline_patrimonial-1.5_consolidated.json")

    e3_dir = tmp_path / "processed" / "E3_reconciled"
    e3_dir.mkdir(parents=True)
    shutil.copy(_E3_FIXTURE, e3_dir / "golden-minimal-3_reconciled.json")

    return tmp_path


def test_e5_execution_produces_analysis_json(e5_tenant_minimal: Path):
    """Roda E4 e E5 em tenant isolado; restaura globals dos scripts."""
    from scripts.e4_categorize import _DEFAULT_BASE_DIR as E4_DEFAULT, _init_config as e4_init, main as e4_main
    from scripts.e5_analyze import _DEFAULT_BASE_DIR as E5_DEFAULT, _init_config as e5_init, main as e5_main
    from scripts.pipeline_common import _init_config as pc_init

    try:
        pc_init(e5_tenant_minimal)
        e4_main(root_dir=e5_tenant_minimal)
        pc_init(_REPO)
        e5_main(root_dir=e5_tenant_minimal)
    except SystemExit as exc:
        pytest.fail(f"Pipeline main exited with {exc.code}")
    finally:
        pc_init(_REPO)
        e4_init(E4_DEFAULT)
        e5_init(E5_DEFAULT)

    out = e5_tenant_minimal / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    assert out.is_file(), f"missing {out}"

    payload = json.loads(out.read_text(encoding="utf-8"))
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

    from scripts.pipeline_common import validate_artifact

    assert validate_artifact(out, "e5_analysis.schema.json") is True

    assert_qa_log_md(e5_tenant_minimal)


def test_e5_execution_mixed_receita_despesa(e5_tenant_mixed_cashflow: Path):
    """E5 com receitas e despesas não nulas no E4 (golden expandido)."""
    from scripts.e4_categorize import _DEFAULT_BASE_DIR as E4_DEFAULT, _init_config as e4_init, main as e4_main
    from scripts.e5_analyze import _DEFAULT_BASE_DIR as E5_DEFAULT, _init_config as e5_init, main as e5_main
    from scripts.pipeline_common import _init_config as pc_init

    try:
        pc_init(e5_tenant_mixed_cashflow)
        e4_main(root_dir=e5_tenant_mixed_cashflow)
        pc_init(_REPO)
        e5_main(root_dir=e5_tenant_mixed_cashflow)
    except SystemExit as exc:
        pytest.fail(f"Pipeline main exited with {exc.code}")
    finally:
        pc_init(_REPO)
        e4_init(E4_DEFAULT)
        e5_init(E5_DEFAULT)

    out = e5_tenant_mixed_cashflow / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
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
    from scripts.e4_categorize import _DEFAULT_BASE_DIR as E4_DEFAULT, _init_config as e4_init, main as e4_main
    from scripts.e5_analyze import _DEFAULT_BASE_DIR as E5_DEFAULT, _init_config as e5_init, main as e5_main
    from scripts.pipeline_common import _init_config as pc_init

    try:
        pc_init(e5_tenant_with_baseline)
        e4_main(root_dir=e5_tenant_with_baseline)
        pc_init(_REPO)
        e5_main(root_dir=e5_tenant_with_baseline)
    except SystemExit as exc:
        pytest.fail(f"Pipeline main exited with {exc.code}")
    finally:
        pc_init(_REPO)
        e4_init(E4_DEFAULT)
        e5_init(E5_DEFAULT)

    out = e5_tenant_with_baseline / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["patrimonio"]["bruto"] == 500_000.0
    assert payload["patrimonio"]["liquido"] == 400_000.0
    assert payload["patrimonio"]["dividas"] == 100_000.0

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (_REPO / "config" / "schemas" / "e5_analysis.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(payload, schema)

    assert_qa_log_md(e5_tenant_with_baseline)
