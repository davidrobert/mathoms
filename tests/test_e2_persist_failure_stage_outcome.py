"""E2 determinístico: write recusado em strict não conta como processado e derruba o stage (runbook schema_validation_strict_flip §8)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

import backend.app.models  # noqa: F401 — registra as tabelas no metadata
from backend.app.core.database import Base, attach_sqlite_pragmas
from backend.app.models import PipelineArtifact, PipelineRun, PipelineRunStatus, User, Workspace
from backend.app.services.storage.db_artifact_store import DBArtifactStore
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext
from pipeline.orchestrator import _run_stage
from pipeline.stage_failure_reason import StageFailureReason, reason_from_stage_detail

_REPO_CONFIG = Path(__file__).resolve().parents[1] / "config"
_VALIDO = "itau_extratoconta_202604-0_original.csv"
_FORA_DO_CONTRATO = "santander_extratoconta_202604-0_original.csv"
_ILEGIVEL = "bradesco_extratoconta_202604-0_original.csv"
_SEM_PARSER = "bancoficticio_extratoconta_202604-0_original.csv"


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


def _parser_que_quebra(file_path: Path, filename: str) -> dict:
    raise ValueError("layout sintético que o parser não reconhece")


# Arquivo fora do mapa não tem parser: vira stub de escalação (ADR-342).
_PARSERS = {
    _VALIDO: _parser_no_contrato,
    _FORA_DO_CONTRATO: _parser_fora_do_contrato,
    _ILEGIVEL: _parser_que_quebra,
}


class _StoreQueRecusaUmaKey(InMemoryArtifactStore):
    """`write` levanta para uma key — falha do store sem DB; o tipo do erro decide a classe."""

    def __init__(self, key: str, erro: Exception) -> None:
        super().__init__()
        self._key = key
        self._erro = erro

    def write(self, stage: str, key: str, data: dict, *, document_id: str | None = None) -> None:
        if key == self._key:
            raise self._erro
        super().write(stage, key, data, document_id=document_id)


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
    monkeypatch.setattr(ebd, "route_to_parser", _PARSERS.get)
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


def _rodar_extract_statements(tenant_root: Path, store, workspace_id: str | None = None):
    ctx = WorkspaceContext.for_tenant(tenant_root, artifact_store=store, workspace_id=workspace_id)
    return _run_stage(ctx, "extract_statements")


def _executar_com_db(stage_session, tenant_root: Path):
    session, ws_id, run_id = stage_session
    store = DBArtifactStore(session, workspace_id=ws_id, pipeline_run_id=run_id)
    result = _rodar_extract_statements(tenant_root, store, ws_id)
    gravadas = (
        session.query(PipelineArtifact.artifact_key)
        .filter_by(pipeline_run_id=run_id, stage="extract_statements")
        .all()
    )
    return result, sorted(key for (key,) in gravadas)


def test_unico_documento_recusado_em_strict_nao_sai_verde(stage_session, tenant_root):
    _documentos(tenant_root, _FORA_DO_CONTRATO)

    result, gravadas = _executar_com_db(stage_session, tenant_root)

    assert gravadas == []
    assert result.success is False
    # O que o §8.1 do runbook filtra: o veredito do decoder (ADR-447) e a mensagem do raise.
    assert reason_from_stage_detail(result.detail) is StageFailureReason.output_invalid
    assert (
        "extract_statements/santander_extratoconta_202604 viola e2_extract.schema.json"
        in result.error
    )


def test_recusa_em_strict_derruba_o_stage_mesmo_com_irmao_gravado(stage_session, tenant_root):
    _documentos(tenant_root, _VALIDO, _FORA_DO_CONTRATO)

    result, gravadas = _executar_com_db(stage_session, tenant_root)

    assert "santander_extratoconta_202604" not in gravadas
    assert result.success is False
    assert reason_from_stage_detail(result.detail) is StageFailureReason.output_invalid


def test_falha_de_parse_continua_sendo_do_documento(tenant_root):
    _documentos(tenant_root, _VALIDO, _ILEGIVEL)
    store = InMemoryArtifactStore()

    result = _rodar_extract_statements(tenant_root, store)

    assert result.success is True
    assert (result.detail["total"], result.detail["erros_validacao"]) == (1, 1)
    assert store.list_keys("extract_statements") == ["itau_extratoconta_202604"]


def test_erro_do_store_fora_do_schema_derruba_o_stage(tenant_root):
    _documentos(tenant_root, _VALIDO)
    erro = OperationalError("INSERT INTO pipeline_artifacts", {}, Exception("database is locked"))
    store = _StoreQueRecusaUmaKey("itau_extratoconta_202604", erro)

    result = _rodar_extract_statements(tenant_root, store)

    assert result.success is False
    assert reason_from_stage_detail(result.detail) is StageFailureReason.internal_error


def test_stub_de_escalacao_que_nao_grava_derruba_o_stage(tenant_root):
    _documentos(tenant_root, _VALIDO, _SEM_PARSER)
    erro = OperationalError("INSERT INTO pipeline_artifacts", {}, Exception("database is locked"))
    store = _StoreQueRecusaUmaKey("bancoficticio_extratoconta_202604", erro)

    result = _rodar_extract_statements(tenant_root, store)

    # Sem o stub, o parcial de run anterior ressuscita pelo fallback da ADR-241 —
    # e o irmão gravado não pode tornar isso progresso.
    assert result.success is False
    assert "bancoficticio_extratoconta_202604" not in store.list_keys("extract_statements")
