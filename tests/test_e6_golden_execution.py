"""Golden de execução E6: tenant mínimo + E4→E5→E6 (HTML standalone)."""

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

_GOALS_MIN = {
    "independencia_financeira": {
        "if_meta": 1_000_000.0,
        "trs_pct": 4.0,
    }
}

_FAMILY_E6 = {
    "titular": "david",
    "familia": {"sobrenome": "Golden"},
    "membros": {
        "david": {
            "nome_curto": "David",
            "data_nascimento": "1985-06-15",
        }
    },
}


@pytest.fixture
def e6_tenant_minimal(tmp_path: Path) -> Path:
    """Configs E4/E5/E6: E3 mínimo + artefatos de render (template, layout, instituições)."""
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
        json.dumps(_FAMILY_E6, ensure_ascii=False, indent=2),
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
    shutil.copy(_REPO / "config" / "cenarios.json", cfg / "cenarios.json")
    shutil.copy(_REPO / "config" / "institutions.json", cfg / "institutions.json")
    shutil.copy(_REPO / "config" / "report_layout.yaml", cfg / "report_layout.yaml")

    tpl_dir = cfg / "templates"
    tpl_dir.mkdir(parents=True)
    shutil.copy(
        _REPO / "config" / "templates" / "report_template.html",
        tpl_dir / "report_template.html",
    )

    e3_dir = tmp_path / "processed" / "E3_reconciled"
    e3_dir.mkdir(parents=True)
    shutil.copy(_E3_FIXTURE, e3_dir / "golden-minimal-3_reconciled.json")

    return tmp_path


def test_e6_execution_produces_html(e6_tenant_minimal: Path):
    """Roda E4, E5 e `render_report` isoladamente; restaura globals."""
    from scripts.e4_categorize import _DEFAULT_BASE_DIR as E4_DEFAULT
    from scripts.e4_categorize import _init_config as e4_init
    from scripts.e4_categorize import main as e4_main
    from scripts.e5_analyze import _DEFAULT_BASE_DIR as E5_DEFAULT
    from scripts.e5_analyze import _init_config as e5_init
    from scripts.e5_analyze import main as e5_main
    from scripts.e6_render import _DEFAULT_BASE_DIR as E6_DEFAULT
    from scripts.e6_render import _init_config as e6_init
    from scripts.e6_render import render_report
    from scripts.pipeline_common import _init_config as pc_init

    try:
        pc_init(e6_tenant_minimal)
        e4_main(root_dir=e6_tenant_minimal)
        pc_init(_REPO)
        e5_main(root_dir=e6_tenant_minimal)
        pc_init(_REPO)
        out_path = render_report(root_dir=e6_tenant_minimal)
    except SystemExit as exc:
        pytest.fail(f"Pipeline exited with {exc.code}")
    except Exception as exc:
        pytest.fail(f"E6 render failed: {exc}")
    finally:
        pc_init(_REPO)
        e4_init(E4_DEFAULT)
        e5_init(E5_DEFAULT)
        e6_init(E6_DEFAULT)

    assert out_path is not None
    assert out_path.is_file()

    assert_qa_log_md(e6_tenant_minimal)

    html = out_path.read_text(encoding="utf-8")
    assert len(html) > 5000
    assert "<!DOCTYPE html>" in html or "<html" in html.lower()
    assert "Família Golden" in html or "Golden" in html
