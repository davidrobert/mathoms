"""Golden de paridade — E5.N e E7 Caminho B (Sessão A5e).

Cobre:
- E5.N: ``main(root_dir)`` vs ``main_with_store(ctx)`` em mesmo workspace;
  compara o E5 enriquecido (chave ``narrativas``).
- E7 crossval: executa `main_with_store(ctx, mode="crossval")` e valida que
  o template é gravado em `processed/E7_review/e7_review_template.json`
  (paridade com legado).
- E7 apply: `main_with_store(ctx, mode="apply", review_path=...)` aplica
  review e escreve E5 atualizado via store.
- Critério estrutural: wrappers `e5n.py` e `e7.py` não importam `stage_runner_compat`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

_E3_FIXTURE = (
    _REPO / "tests" / "fixtures" / "pipeline_golden" / "e3" / "minimal-conta-com-despesa-3_reconciled.json"
)
_BASELINE_MIN = (
    _REPO / "tests" / "fixtures" / "pipeline_golden" / "e2" / "minimal-baseline-1.5_consolidated.json"
)

_GOALS_MIN = {
    "independencia_financeira": {
        "if_meta": 1_000_000.0,
        "trs_pct": 4.0,
    }
}

_FAMILY = {
    "titular": "david",
    "membros": {
        "david": {
            "nome_curto": "David",
            "data_nascimento": "1985-06-15",
        }
    },
}

_CATEGORIZATION = {
    "expense_keywords": {"mercado": ["mercado"]},
    "income_keywords": {"receita_clt": ["salario"]},
    "internal_transfer_patterns": [],
    "pj_source_mapping": {},
    "clt_source_mapping": {"empresa": "Empresa X"},
}


def _build_workspace(root: Path) -> None:
    cfg = root / "config"
    cfg.mkdir(parents=True)
    (cfg / "categorization.json").write_text(json.dumps(_CATEGORIZATION), encoding="utf-8")
    (cfg / "family_members.json").write_text(json.dumps(_FAMILY), encoding="utf-8")
    (cfg / "pipeline.json").write_text("{}", encoding="utf-8")
    (cfg / "goals.json").write_text(json.dumps(_GOALS_MIN), encoding="utf-8")

    e3_dir = root / "processed" / "E3_reconciled"
    e3_dir.mkdir(parents=True)
    (e3_dir / "minimal-conta-com-despesa-3_reconciled.json").write_text(
        _E3_FIXTURE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    e2_dir = root / "processed" / "E2_extracts"
    e2_dir.mkdir(parents=True)
    (e2_dir / "baseline_patrimonial-1.5_consolidated.json").write_text(
        _BASELINE_MIN.read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def _read_e5(root: Path) -> dict:
    path = root / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    return json.loads(path.read_text(encoding="utf-8"))


# =============================================================================
# Setup runners (E4 + E5 + E5.N)
# =============================================================================


def _run_legacy_through_e5n(workspace: Path) -> None:
    from scripts import pipeline_common as _pc
    from scripts.e4_categorize import (
        _DEFAULT_BASE_DIR as E4_DEFAULT,
        _init_config as e4_init,
        main as e4_main,
    )
    from scripts.e5_analyze import (
        _DEFAULT_BASE_DIR as E5_DEFAULT,
        _init_config as e5_init,
        main as e5_main,
    )
    from scripts.e5n_narrativas import (
        _DEFAULT_BASE_DIR as E5N_DEFAULT,
        _init_config as e5n_init,
        main as e5n_main,
    )

    original_pc = _pc.PROJECT_DIR
    try:
        _pc._init_config(workspace)
        e4_main(root_dir=workspace)
        e5_main(root_dir=workspace)
        e5n_main(root_dir=workspace)
    except SystemExit as exc:
        if exc.code not in (0, None):
            pytest.fail(f"Pipeline legado saiu com {exc.code}")
    finally:
        _pc._init_config(original_pc)
        e4_init(E4_DEFAULT)
        e5_init(E5_DEFAULT)
        e5n_init(E5N_DEFAULT)


def _run_new_through_e5n(workspace: Path) -> None:
    from pipeline.context import WorkspaceContext
    from scripts.e4_categorize import main_with_store as e4_mws
    from scripts.e5_analyze import main_with_store as e5_mws
    from scripts.e5n_narrativas import main_with_store as e5n_mws

    ctx = WorkspaceContext(root=workspace)
    e4_mws(ctx)
    e5_mws(ctx)
    e5n_mws(ctx)


# =============================================================================
# Golden paridade E5.N
# =============================================================================


def test_e5n_main_with_store_parity_against_legacy(tmp_path: Path):
    legacy_root = tmp_path / "legacy"
    new_root = tmp_path / "new"

    _build_workspace(legacy_root)
    _build_workspace(new_root)

    _run_legacy_through_e5n(legacy_root)
    _run_new_through_e5n(new_root)

    legacy_e5 = _read_e5(legacy_root)
    new_e5 = _read_e5(new_root)

    # Presença de narrativas.
    assert "narrativas" in legacy_e5
    assert "narrativas" in new_e5

    legacy_narr = legacy_e5["narrativas"]
    new_narr = new_e5["narrativas"]

    # Mesmas chaves top-level.
    assert set(legacy_narr.keys()) == set(new_narr.keys())

    # Mesma quantidade de summaries e charts.
    assert len(legacy_narr.get("summaries", {})) == len(new_narr.get("summaries", {}))
    assert len(legacy_narr.get("charts", {})) == len(new_narr.get("charts", {}))

    # Texto de narrativas deve ser idêntico (funções puras sem clock).
    assert legacy_narr == new_narr


# =============================================================================
# E7 crossval + apply — integração funcional
# =============================================================================


def test_e7_crossval_via_main_with_store_writes_template(tmp_path: Path):
    """E7 crossval grava template em disco (paridade com legado)."""
    ws = tmp_path / "ws"
    _build_workspace(ws)
    _run_new_through_e5n(ws)

    # Precisa de methodology.md para extração de persona — stub mínimo.
    (ws / "config" / "methodology.md").write_text(
        "## PERSONA E ABORDAGEM\nPersona fictícia.\n",
        encoding="utf-8",
    )

    from pipeline.context import WorkspaceContext
    from scripts.e7_review import main_with_store

    result = main_with_store(WorkspaceContext(root=ws), mode="crossval")

    assert result["success"] is True
    assert result["mode"] == "crossval"
    assert result["checks_total"] >= 1

    template_path = ws / "processed" / "E7_review" / "e7_review_template.json"
    assert template_path.exists(), "template não foi escrito"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    assert "cross_validation_results" in template or "cv_results" in template or len(template) > 0


def test_e7_apply_skips_without_review_path(tmp_path: Path):
    """Modo apply sem review_path retorna skip gracioso."""
    ws = tmp_path / "ws"
    _build_workspace(ws)
    _run_new_through_e5n(ws)

    from pipeline.context import WorkspaceContext
    from scripts.e7_review import main_with_store

    result = main_with_store(WorkspaceContext(root=ws), mode="apply")

    assert result["success"] is True
    assert result.get("skipped") is True


def test_e7_apply_validates_review(tmp_path: Path):
    """Modo apply rejeita review com shape inválido."""
    ws = tmp_path / "ws"
    _build_workspace(ws)
    _run_new_through_e5n(ws)

    # Review inválido (sem campos obrigatórios).
    invalid_review = ws / "review.json"
    invalid_review.write_text(json.dumps({"not_valid": True}), encoding="utf-8")

    from pipeline.context import WorkspaceContext
    from scripts.e7_review import main_with_store

    result = main_with_store(
        WorkspaceContext(root=ws),
        mode="apply",
        review_path=str(invalid_review),
    )

    # Invalid review → falha.
    assert result["success"] is False


# =============================================================================
# Critérios estruturais
# =============================================================================


def test_pipeline_stages_e5n_does_not_import_stage_runner_compat():
    src = (_REPO / "pipeline" / "stages" / "e5n.py").read_text(encoding="utf-8")
    assert "stage_runner_compat" not in src, (
        "pipeline/stages/e5n.py ainda referencia stage_runner_compat — "
        "A5e deveria ter migrado para main_with_store direto."
    )
    assert "main_with_store" in src


def test_pipeline_stages_e7_does_not_import_stage_runner_compat():
    src = (_REPO / "pipeline" / "stages" / "e7.py").read_text(encoding="utf-8")
    assert "stage_runner_compat" not in src, (
        "pipeline/stages/e7.py ainda referencia stage_runner_compat — "
        "A5e deveria ter migrado para main_with_store direto."
    )
    assert "main_with_store" in src
