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
