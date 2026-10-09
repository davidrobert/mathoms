"""E2 determinístico: write recusado em strict não conta como processado e derruba o stage (runbook schema_validation_strict_flip §8)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import backend.app.models  # noqa: F401 — registra as tabelas no metadata
from backend.app.core.database import Base, attach_sqlite_pragmas
from backend.app.models import PipelineArtifact, PipelineRun, PipelineRunStatus, User, Workspace
from backend.app.services.storage.db_artifact_store import DBArtifactStore
from pipeline.context import WorkspaceContext
from pipeline.orchestrator import _run_stage

_REPO_CONFIG = Path(__file__).resolve().parents[1] / "config"
_VALIDO = "itau_extratoconta_202604-0_original.csv"
_FORA_DO_CONTRATO = "santander_extratoconta_202604-0_original.csv"


def _extrato_sintetico() -> dict:
    return {
        "pipeline_stage": "E2",
        "banco": "itau",
        "tipo": "extratoconta",
        "moeda": "BRL",
        "periodo": {"inicio": "2026-04-01", "fim": "2026-04-30"},
        "transacoes": [{"data": "2026-04-05", "descricao": "Mercado Sintetico", "valor": -250.5}],
    }


def _parser_no_contrato(file_path: Path, filename: str) -> dict:
    return _extrato_sintetico()


def _parser_fora_do_contrato(file_path: Path, filename: str) -> dict:
    payload = _extrato_sintetico()
    # Writer que ganhou campo sem declará-lo em `$defs/transacao`
    # (additionalProperties: false) — o drift que o strict existe para barrar.
    payload["transacoes"][0]["campo_nao_declarado"] = "x"
    return payload


_PARSERS = {_VALIDO: _parser_no_contrato, _FORA_DO_CONTRATO: _parser_fora_do_contrato}


@pytest.fixture(autouse=True)
def _e2_extract_strict(monkeypatch):
    """Strict só para `e2_extract` via `mode_overrides`, como no flip per-schema (ADR-284)."""
    import scripts.pipeline_common as pc

    monkeypatch.delenv("MATHOMS_PIPELINE_SCHEMA_MODE", raising=False)
    monkeypatch.setattr(pc, "CONFIG_DIR", _REPO_CONFIG)
    monkeypatch.setattr(pc, "_schema_registry", None)
    monkeypatch.setitem(
        pc._config_cache,
        "pipeline.json",
        {
            "schema_validation": {
                "enabled": True,
                "mode": "warn",
                "mode_overrides": {"e2_extract.schema.json": "strict"},
            }
        },
    )


@pytest.fixture
def tenant_root(tmp_path, monkeypatch):
    """Tenant com a pasta de extratos; restaura `scripts.e2.common`, que o stage re-inicializa."""
    import scripts.e2.common as e2_common
    import scripts.extract_bank_documents as ebd

    data_dir = tmp_path / "tenant" / "data" / "financial_statements"
    data_dir.mkdir(parents=True)
    # `find_all_files` lê o DATA_DIR vinculado no import do módulo, não o que o
    # `_init_config(ctx.root)` do stage regrava: pinar isola da ordem de import.
    monkeypatch.setattr(ebd, "DATA_DIR", data_dir)
    monkeypatch.setattr(ebd, "route_to_parser", lambda filename: _PARSERS[filename])
    raiz_anterior = e2_common.BASE_DIR
    yield tmp_path / "tenant"
    e2_common._init_config(raiz_anterior)


@pytest.fixture
def stage_session(tmp_path):
    """Sessão do stage sobre SQLite em arquivo, com os pais da FK materializados (ADR-371)."""
    engine = create_engine(f"sqlite:///{tmp_path / 'e2.db'}")
    attach_sqlite_pragmas(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = User(email="e2@test.local", hashed_password="x", full_name="E2 Fixture")
        session.add(owner)
        session.flush()
        workspace = Workspace(name="WS E2", owner_id=owner.id)
        session.add(workspace)
        session.flush()
        run = PipelineRun(workspace_id=workspace.id, status=PipelineRunStatus.running)
        session.add(run)
        session.flush()
        yield session, workspace.id, run.id
    engine.dispose()


def _documentos(tenant_root: Path, *nomes: str) -> None:
    for nome in nomes:
        (tenant_root / "data" / "financial_statements" / nome).write_text("data;valor\n")


def _executar_extract_statements(stage_session, tenant_root: Path):
    session, ws_id, run_id = stage_session
    store = DBArtifactStore(session, workspace_id=ws_id, pipeline_run_id=run_id)
    ctx = WorkspaceContext.for_tenant(tenant_root, artifact_store=store, workspace_id=ws_id)
    result = _run_stage(ctx, "extract_statements")
    gravadas = (
        session.query(PipelineArtifact.artifact_key)
        .filter_by(pipeline_run_id=run_id, stage="extract_statements")
        .all()
    )
    return result, sorted(key for (key,) in gravadas)


def test_unico_documento_recusado_em_strict_nao_sai_verde(stage_session, tenant_root):
    _documentos(tenant_root, _FORA_DO_CONTRATO)

    result, gravadas = _executar_extract_statements(stage_session, tenant_root)

    assert gravadas == []
    assert result.success is False


def test_recusa_em_strict_derruba_o_stage_mesmo_com_irmao_gravado(stage_session, tenant_root):
    _documentos(tenant_root, _VALIDO, _FORA_DO_CONTRATO)

    result, gravadas = _executar_extract_statements(stage_session, tenant_root)

    assert "santander_extratoconta_202604" not in gravadas
    assert result.success is False
