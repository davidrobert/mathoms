"""Golden de execução E5.N: E3→E4→E5→E5.N — narrativas fundidas no JSON de análise."""

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
# A7.5: ``parametros_fiscais.json`` + ``taxas.json`` saíram de ``config/``.
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

# ADR-176: chave universal `cenarios_conjuge` no bloco de narrativas — fixture
# mantida para verificar que workspace com cônjuge produz a mesma chave estável
# que workspace minimal (regressão da chave dinâmica `<membro>_cenarios`).
_FAMILY_E5_CONJUGE = {
    "titular": "david",
    "membros": {
        "david": {
            "nome_curto": "David",
            "data_nascimento": "1985-06-15",
        },
        "ana": {
            "nome_curto": "Ana",
            "data_nascimento": "1987-03-20",
            "papel": "conjuge",
        },
    },
}


def _build_e5_workspace(tmp_path: Path, family: dict) -> Path:
    """Tenant mínimo (configs only). ADR-212 PR3b: E3 é seeded no store
    pelo teste, não escrito em disco.
    """
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
        json.dumps(family, ensure_ascii=False, indent=2),
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
    return tmp_path


def _new_e5n_ctx(root: Path):
    """WorkspaceContext + InMemoryArtifactStore seeded com E3 fixture."""
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.context import WorkspaceContext

    store = InMemoryArtifactStore()
    store.seed("E3", "golden-minimal", json.loads(_E3_FIXTURE.read_text(encoding="utf-8")))
    return WorkspaceContext(root=root, artifact_store=store)


@pytest.fixture
def e5_tenant_minimal(tmp_path: Path) -> Path:
    """Mesmo workspace mínimo que `tests/test_e5_golden_execution.py` (E3→E4→E5)."""
    return _build_e5_workspace(tmp_path, _FAMILY_E5)


@pytest.fixture
def e5n_tenant_with_conjuge(tmp_path: Path) -> Path:
    """Como o mínimo, com membro `papel: conjuge` — chave de chart fixa
    `cenarios_conjuge` desde ADR-176 (era `ana_cenarios` antes)."""
    return _build_e5_workspace(tmp_path, _FAMILY_E5_CONJUGE)


def test_e5n_execution_injects_narrativas(e5_tenant_minimal: Path):
    """Após E5, `e5n_narrativas.main` injeta `narrativas` válidas (spec E5.N)."""
    from scripts.e4_categorize import main_with_store as e4_mws
    from scripts.e5_analyze import main_with_store as e5_mws
    from scripts.e5n_narrativas import _init_config as e5n_init
    from scripts.e5n_narrativas import main_with_store as e5n_mws
    from scripts.e5n_narrativas import validate_narrativas

    ctx = _new_e5n_ctx(e5_tenant_minimal)
    e4_mws(ctx)
    e5_mws(ctx)
    # validate_narrativas usa globals do e5n; init para o tenant antes de chamar.
    e5n_init(e5_tenant_minimal)
    e5n_mws(ctx)

    payload = ctx.artifact_store.read("E5", "analise_financeira")
    assert payload is not None
    narr = payload.get("narrativas")
    narr_ok, val_errors = validate_narrativas(narr or {})

    assert narr is not None
    assert set(narr.keys()) >= {"perfil_familia", "summaries", "charts"}
    assert narr_ok, val_errors

    assert_qa_log_md(e5_tenant_minimal)


def test_e5n_execution_narrativas_with_conjuge_chart(e5n_tenant_with_conjuge: Path):
    """ADR-176: workspace com cônjuge produz chart obrigatório ``cenarios_conjuge`` (chave universal, não mais ``<membro>_cenarios``)."""
    from scripts.e4_categorize import main_with_store as e4_mws
    from scripts.e5_analyze import main_with_store as e5_mws
    from scripts.e5n_narrativas import _init_config as e5n_init
    from scripts.e5n_narrativas import main_with_store as e5n_mws
    from scripts.e5n_narrativas import validate_narrativas

    ctx = _new_e5n_ctx(e5n_tenant_with_conjuge)
    e4_mws(ctx)
    e5_mws(ctx)
    e5n_init(e5n_tenant_with_conjuge)
    e5n_mws(ctx)

    payload = ctx.artifact_store.read("E5", "analise_financeira")
    assert payload is not None
    narr = payload.get("narrativas")
    narr_ok, val_errors = validate_narrativas(narr or {})

    assert narr is not None
    assert narr_ok, val_errors
    charts = narr.get("charts", {})
    assert "cenarios_conjuge" in charts
    # Garantia explícita: nenhuma chave derivada de membro permanece.
    assert "ana_cenarios" not in charts

    assert_qa_log_md(e5n_tenant_with_conjuge)
