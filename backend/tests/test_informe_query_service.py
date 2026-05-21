"""A17 L1 P4 (ADR-238 D5) — InformeQuery service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.app.application.informes.informe_query import InformeQuery


def _make_payload(*, ano: int, tipo: str, cnpj: str = "16404287000167") -> dict:
    return {
        "ano_base": ano,
        "tipo_informe": tipo,
        "fonte_pagadora_cnpj": cnpj,
        "fonte_pagadora_nome": "BrasilPrev",
        "confidence": 0.95,
        "source_priority": 1,
        "prompt_version": "informe-prev-v1.0.0",
        "needs_review": False,
    }


def _fake_artifact(content: dict, art_id: str = "art-1") -> MagicMock:
    art = MagicMock()
    art.id = art_id
    art.content_json = content
    return art


def test_list_for_workspace_retorna_payloads_decriptados() -> None:
    """Retorna lista de dicts prontos para FiscalSource.from_informes."""
    fake_repo = MagicMock()
    fake_repo.list_latest_keys.side_effect = (
        lambda ws_id, *, stage: ["prev_brasilprev_2024"]
        if stage == "extract_informes_anuais"
        else []
    )
    fake_repo.get_latest_for_workspace.return_value = _fake_artifact(
        _make_payload(ano=2024, tipo="previdencia_privada")
    )
    with patch(
        "backend.app.application.informes.informe_query.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = InformeQuery(session=MagicMock()).list_for_workspace("ws-1")
    assert len(result) == 1
    assert result[0]["tipo_informe"] == "previdencia_privada"


def test_filtro_por_ano_base() -> None:
    """Filtra apenas informes do ano solicitado."""
    fake_repo = MagicMock()
    fake_repo.list_latest_keys.side_effect = (
        lambda ws_id, *, stage: ["a", "b"] if stage == "extract_informes_anuais" else []
    )
    fake_repo.get_latest_for_workspace.side_effect = [
        _fake_artifact(_make_payload(ano=2024, tipo="previdencia_privada"), art_id="x1"),
        _fake_artifact(_make_payload(ano=2023, tipo="previdencia_privada"), art_id="x2"),
    ]
    with patch(
        "backend.app.application.informes.informe_query.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = InformeQuery(session=MagicMock()).list_for_workspace("ws-1", ano_base=2024)
    assert len(result) == 1
    assert result[0]["ano_base"] == 2024


def test_filtro_por_tipo_informe() -> None:
    """Filtra apenas tipos solicitados — preparação L2-L4 com múltiplos tipos."""
    fake_repo = MagicMock()
    fake_repo.list_latest_keys.side_effect = (
        lambda ws_id, *, stage: ["a", "b"] if stage == "extract_informes_anuais" else []
    )
    fake_repo.get_latest_for_workspace.side_effect = [
        _fake_artifact(_make_payload(ano=2024, tipo="previdencia_privada"), art_id="x1"),
        # Hipotético tipo L3 (financeiro_pf) — não casa filtro
        _fake_artifact(_make_payload(ano=2024, tipo="financeiro_pf"), art_id="x2"),
    ]
    with patch(
        "backend.app.application.informes.informe_query.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = InformeQuery(session=MagicMock()).list_previdencia("ws-1", ano_base=2024)
    assert len(result) == 1
    assert result[0]["tipo_informe"] == "previdencia_privada"


def test_dedup_entre_stage_descritivo_e_legacy() -> None:
    """Tentativa em ambos os nomes não duplica o mesmo artifact_id."""
    art = _fake_artifact(_make_payload(ano=2024, tipo="previdencia_privada"), art_id="same-id")
    fake_repo = MagicMock()
    fake_repo.list_latest_keys.side_effect = lambda ws_id, *, stage: ["k"]
    fake_repo.get_latest_for_workspace.return_value = art  # mesmo ID nas duas chamadas
    with patch(
        "backend.app.application.informes.informe_query.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = InformeQuery(session=MagicMock()).list_for_workspace("ws-1")
    assert len(result) == 1  # dedupe por id


def test_workspace_sem_informes_retorna_lista_vazia() -> None:
    """Sem rows em pipeline_artifacts → []. Não levanta exceção."""
    fake_repo = MagicMock()
    fake_repo.list_latest_keys.return_value = []
    with patch(
        "backend.app.application.informes.informe_query.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        result = InformeQuery(session=MagicMock()).list_for_workspace("ws-1")
    assert result == []
