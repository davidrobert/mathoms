"""DB-first + fallback disco para artefatos do pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.app.services.artifact_reader import read_latest_artifact


def test_read_returns_db_payload_when_present(tmp_path: Path) -> None:
    """DB tem o artefato → retorna conteúdo do DB sem tocar no disco."""
    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.return_value = MagicMock(
        content_json={"patrimonio": {"bruto": 4_308_452.40}}
    )
    with patch(
        "backend.app.services.artifact_reader.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = read_latest_artifact(
            "ws-1", stage="E5", key="analise_financeira", tenant_root=tmp_path
        )
    assert result == {"patrimonio": {"bruto": 4_308_452.40}}
    fake_repo.get_latest_for_workspace.assert_called_once_with(
        "ws-1", stage="E5", artifact_key="analise_financeira"
    )


def _fake_legacy_e4_row(workspace_id, *, stage, artifact_key):
    """Side effect: simula DB com row em formato legado (`"E4"` only)."""
    if stage == "E4" and artifact_key == "despesas":
        return MagicMock(content_json={"dados": {"saude": [{"valor": 11400}]}})
    return None


def test_read_finds_legacy_row_when_caller_uses_descriptive(tmp_path: Path) -> None:
    """ADR-093: caller passa nome descritivo, DB tem nome legado."""
    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.side_effect = _fake_legacy_e4_row
    with patch(
        "backend.app.services.artifact_reader.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = read_latest_artifact(
            "ws-1", stage="categorize_transactions", key="despesas", tenant_root=tmp_path
        )
    assert result == {"dados": {"saude": [{"valor": 11400}]}}
    calls = [c.kwargs["stage"] for c in fake_repo.get_latest_for_workspace.call_args_list]
    assert calls == ["categorize_transactions", "E4"]


def test_read_finds_descriptive_row_when_caller_uses_legacy(tmp_path: Path) -> None:
    """ADR-093 (direção inversa): pós-F9.3 (Alembic re-key DB→descritivo),
    callers que ainda passam ``"E5"`` devem continuar achando o row.
    """
    artifact = MagicMock(content_json={"score": {"valor": 78}})

    def fake_lookup(workspace_id, *, stage, artifact_key):
        return artifact if stage == "analyze_finances" else None

    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.side_effect = fake_lookup
    with patch(
        "backend.app.services.artifact_reader.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = read_latest_artifact(
            "ws-1", stage="E5", key="analise_financeira", tenant_root=tmp_path
        )
    assert result == {"score": {"valor": 78}}


def test_read_falls_back_to_disk_when_db_empty(tmp_path: Path) -> None:
    """DB vazio + disco presente → lê disco (back-compat DiskArtifactStore)."""
    disk_dir = tmp_path / "processed" / "E5_analysis"
    disk_dir.mkdir(parents=True)
    (disk_dir / "analise_financeira-5_analysis.json").write_text(
        json.dumps({"patrimonio": {"bruto": 940_278.13}})
    )

    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.return_value = None
    with patch(
        "backend.app.services.artifact_reader.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = read_latest_artifact(
            "ws-1", stage="E5", key="analise_financeira", tenant_root=tmp_path
        )
    assert result == {"patrimonio": {"bruto": 940_278.13}}


def test_read_returns_none_when_neither_db_nor_disk(tmp_path: Path) -> None:
    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.return_value = None
    with patch(
        "backend.app.services.artifact_reader.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = read_latest_artifact(
            "ws-1", stage="E5", key="analise_financeira", tenant_root=tmp_path
        )
    assert result is None


def test_read_prefers_db_over_disk_when_both_exist(tmp_path: Path) -> None:
    """Regressão: se disco tem dado velho e DB tem novo, DB vence."""
    disk_dir = tmp_path / "processed" / "E5_analysis"
    disk_dir.mkdir(parents=True)
    (disk_dir / "analise_financeira-5_analysis.json").write_text(json.dumps({"stale": True}))

    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.return_value = MagicMock(content_json={"fresh": True})
    with patch(
        "backend.app.services.artifact_reader.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = read_latest_artifact(
            "ws-1", stage="E5", key="analise_financeira", tenant_root=tmp_path
        )
    assert result == {"fresh": True}
