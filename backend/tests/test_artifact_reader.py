"""DB-only reader de artefatos (ADR-212 PR3b — fallback disco removido)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.app.services.storage.artifact_reader import read_latest_artifact


def test_read_returns_db_payload_when_present(tmp_path: Path) -> None:
    """DB tem o artefato → retorna conteúdo do DB."""
    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.return_value = MagicMock(
        content_json={"patrimonio": {"bruto": 4_308_452.40}}
    )
    with patch(
        "backend.app.services.storage.artifact_reader.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = read_latest_artifact("ws-1", stage="E5", key="analise_financeira")
    assert result == {"patrimonio": {"bruto": 4_308_452.40}}
    fake_repo.get_latest_for_workspace.assert_called_once_with(
        "ws-1", stage="E5", artifact_key="analise_financeira"
    )


def _fake_legacy_e4_row(workspace_id, *, stage, artifact_key):
    """Side effect: simula DB com row em formato legado (`"E4"` only)."""
    if stage == "E4" and artifact_key == "despesas":
        return MagicMock(content_json={"dados": {"saude": [{"valor": 11400}]}})
    return None


def test_read_finds_legacy_row_when_caller_uses_descriptive() -> None:
    """ADR-093: caller passa nome descritivo, DB tem nome legado."""
    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.side_effect = _fake_legacy_e4_row
    with patch(
        "backend.app.services.storage.artifact_reader.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = read_latest_artifact("ws-1", stage="categorize_transactions", key="despesas")
    assert result == {"dados": {"saude": [{"valor": 11400}]}}
    calls = [c.kwargs["stage"] for c in fake_repo.get_latest_for_workspace.call_args_list]
    assert calls == ["categorize_transactions", "E4"]


def test_read_finds_descriptive_row_when_caller_uses_legacy() -> None:
    """ADR-093 (direção inversa): pós-F9.3 (Alembic re-key DB→descritivo),
    callers que ainda passam ``"E5"`` devem continuar achando o row.
    """
    artifact = MagicMock(content_json={"score": {"valor": 78}})

    def fake_lookup(workspace_id, *, stage, artifact_key):
        return artifact if stage == "analyze_finances" else None

    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.side_effect = fake_lookup
    with patch(
        "backend.app.services.storage.artifact_reader.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = read_latest_artifact("ws-1", stage="E5", key="analise_financeira")
    assert result == {"score": {"valor": 78}}


def test_read_returns_none_when_db_empty() -> None:
    """DB-only: sem row → None (ADR-212 PR3b — fallback disco removido)."""
    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.return_value = None
    with patch(
        "backend.app.services.storage.artifact_reader.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = read_latest_artifact("ws-1", stage="E5", key="analise_financeira")
    assert result is None


def test_tenant_root_deprecated_arg_warns(tmp_path: Path) -> None:
    """``tenant_root`` deprecated em ADR-212 PR3b; passar não-None gera warning.

    Mocka o logger direto para evitar interação flaky com caplog do pytest
    (logger reconfigurado por outros tests no full-suite quebra captura).
    """
    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.return_value = MagicMock(content_json={"x": 1})
    with (
        patch(
            "backend.app.services.storage.artifact_reader.PipelineArtifactRepository",
            return_value=fake_repo,
        ),
        patch("backend.app.services.storage.artifact_reader.logger") as mock_logger,
    ):
        result = read_latest_artifact(
            "ws-1", stage="E5", key="analise_financeira", tenant_root=tmp_path
        )
    assert result == {"x": 1}
    assert mock_logger.warning.called
    msg = mock_logger.warning.call_args[0][0]
    assert "tenant_root deprecated" in msg
