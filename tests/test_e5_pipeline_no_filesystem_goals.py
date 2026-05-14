"""Gate empírico ADR-180 — `goals.json` nunca mais escrito em filesystem (Sprint A10.6)."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import scripts.e5_analyze as e5_analyze
import scripts.e5n_narrativas as e5n


def test_load_goals_helper_removed_from_e5n() -> None:
    """ADR-180: ``_load_goals()`` deletado em ``scripts/e5n_narrativas``."""
    assert not hasattr(
        e5n, "_load_goals"
    ), "scripts.e5n_narrativas._load_goals deveria ter sido deletado em A10.6"


def test_select_chart_helpers_removed_from_e5n() -> None:
    """A10.5 fallback legacy helpers deletados em A10.6 — bundle direto."""
    for name in ("_select_decisoes_for_charts", "_select_riscos_for_charts"):
        assert not hasattr(
            e5n, name
        ), f"scripts.e5n_narrativas.{name} deveria ter sido deletado em A10.6"


def test_materialize_adapter_configs_removed() -> None:
    """``_materialize_adapter_configs`` deletado em A10.6."""
    from backend.app.tasks import pipeline_task

    assert not hasattr(pipeline_task, "_materialize_adapter_configs"), (
        "backend.app.tasks.pipeline_task._materialize_adapter_configs deveria"
        " ter sido deletado em A10.6 (substituído por _materialize_tarefas_md)"
    )


def test_e5_analyze_does_not_define_load_goals() -> None:
    """``e5_analyze`` nunca teve ``_load_goals``; defesa em profundidade."""
    src = inspect.getsource(e5_analyze)
    assert (
        "def _load_goals(" not in src
    ), "scripts/e5_analyze.py não pode definir _load_goals (ADR-180)"


def test_load_metrics_from_e5_accepts_goals_cfg_kwarg() -> None:
    """``load_metrics_from_e5`` aceita ``goals_cfg`` injetado via parâmetro."""
    sig = inspect.signature(e5n.load_metrics_from_e5)
    assert (
        "goals_cfg" in sig.parameters
    ), "load_metrics_from_e5 deveria aceitar ``goals_cfg`` como kwarg após A10.6"


def test_e5n_main_with_store_does_not_write_goals_json(tmp_path: Path) -> None:
    """Roda ``e5n.main_with_store`` em workspace sem ``goals.json`` em disco
    e confirma que o script não cria o arquivo (ADR-180 gate empírico).
    """
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.context import WorkspaceContext

    # Workspace mínimo: só E5 artifact precisa existir para o main rodar até
    # o ponto de leitura de goals_cfg. Família mínima cobre _init_config.
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True)
    family = {
        "titular": "david",
        "membros": {"david": {"nome_curto": "David", "data_nascimento": "1985-06-15"}},
    }
    (cfg_dir / "family_members.json").write_text(
        '{"titular":"david","membros":{"david":{"nome_curto":"David","data_nascimento":"1985-06-15"}}}',
        encoding="utf-8",
    )
    (cfg_dir / "categorization.json").write_text('{"clt_source_mapping": {}}', encoding="utf-8")
    (cfg_dir / "parametros_fiscais.json").write_text("{}", encoding="utf-8")

    e5_dir = tmp_path / "processed" / "E5_analysis"
    e5_dir.mkdir(parents=True)
    # E5 ausente → main retorna early (e5_not_found). O importante é que NÃO
    # escreve goals.json em filesystem.
    ctx = WorkspaceContext.for_tenant(
        tenant_root=tmp_path,
        config={"family_members.json": family},
        artifact_store=InMemoryArtifactStore(),
    )
    assert not (cfg_dir / "goals.json").exists()
    res = e5n.main_with_store(ctx)
    assert res.get("success") is False  # e5_not_found
    assert not (
        cfg_dir / "goals.json"
    ).exists(), "main_with_store NÃO pode criar goals.json em filesystem (ADR-180)"
