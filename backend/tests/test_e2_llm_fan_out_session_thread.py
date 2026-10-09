"""E2-llm: o fan-out em threads não toca a Session do stage (ADR-256)."""

# `extract_with_llm` paraleliza as chamadas LLM num ThreadPoolExecutor, mas a
# Session que o orchestrator injeta por stage não é thread-safe: autoflush,
# identity map e unit of work das threads se intercalam na mesma conexão. DB real
# em arquivo com o pool que produção usa para SQLite em arquivo (QueuePool, nunca
# StaticPool); o único fake é a fronteira LLM. O SAWarning vira erro porque é o
# próprio SQLAlchemy avisando "Session.add() durante o flush de outra thread".

from __future__ import annotations

import threading
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.database import Base, attach_sqlite_pragmas
from backend.app.models import PipelineArtifact, PipelineRun, PipelineRunStatus, User, Workspace
from backend.app.services.storage.db_artifact_store import DBArtifactStore
from pipeline.context import WorkspaceContext
from pipeline.llm.schemas.e2_llm_extract import ExtractedTransaction, LLMExtractOutput
from pipeline.llm.service_config import LLMCallResult

pytestmark = pytest.mark.filterwarnings("error::sqlalchemy.exc.SAWarning")

_WORKERS = 8
# Múltiplo de _WORKERS: toda rodada da barreira fecha com o pool cheio.
_DOCUMENTOS = 3 * _WORKERS
_LLM_CONFIG = {"provider": "anthropic", "api_key": "sk-test-fake", "max_tokens": 4096}


class _LLMQueSoltaAsThreadsJuntas:
    """Fronteira LLM fake: extração própria por documento, pool liberado de uma vez."""

    def __init__(self, *, moeda_por_documento: dict[str, str] | None = None) -> None:
        # Só passa com _WORKERS chamadas simultâneas: serializar o LLM quebra a barreira.
        self._barreira = threading.Barrier(_WORKERS, timeout=10)
        self._moeda = moeda_por_documento or {}
        self.threads: set[int] = set()

    def call(self, **kwargs) -> LLMCallResult:
        self.threads.add(threading.get_ident())
        self._barreira.wait()
        nome = kwargs["stage"].removeprefix("E2-llm:")
        saida = _extracao_do(nome, self._moeda.get(nome, "BRL"))
        return LLMCallResult(output=saida, provider="fake", model="fake-llm")


def _numero(nome: str) -> int:
    return int(nome.removeprefix("extrato_").split("-")[0])


def _extracao_do(nome: str, moeda: str) -> LLMExtractOutput:
    n = _numero(nome)
    transacao = ExtractedTransaction(
        date="2024-01-02", description=f"compra {n}", amount=Decimal(f"-{n + 1}.50")
    )
    return LLMExtractOutput(
        source_file=nome,
        institution="itau",
        document_type="extratoconta",
        period="202401",
        currency=moeda,
        transactions=[transacao],
        confidence=0.9,
    )


def _semeia_workspace_e_run(fabrica: sessionmaker) -> tuple[str, str]:
    with fabrica() as db:
        user = User(
            id=str(uuid.uuid4()), email="e2llm@test.com", hashed_password="x", full_name="T"
        )
        db.add(user)
        db.flush()
        ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="WS")
        db.add(ws)
        db.flush()
        run = PipelineRun(
            id=str(uuid.uuid4()), workspace_id=ws.id, status=PipelineRunStatus.running
        )
        db.add(run)
        db.commit()
        return ws.id, run.id


@pytest.fixture
def banco_do_stage(tmp_path: Path):
    """Engine em arquivo + workspace e run reais (pais da FK, ADR-371)."""
    engine = create_engine(f"sqlite:///{tmp_path / 'e2_llm_fan_out.db'}")
    attach_sqlite_pragmas(engine)
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, expire_on_commit=False)
    yield (fabrica, *_semeia_workspace_e_run(fabrica))
    engine.dispose()


@pytest.fixture(autouse=True)
def _pool_cheio_e_config_do_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pool com _WORKERS threads; validação de schema lendo o config/ real do repo."""
    import scripts.pipeline_common as pc

    monkeypatch.setenv("MATHOMS_E2_LLM_CONCURRENCY", str(_WORKERS))
    # Teste vizinho (`route_documents._init_config`) reponta CONFIG_DIR para um
    # layout sem `schema_validation` e não desfaz: o write em strict virava no-op.
    monkeypatch.setattr(pc, "CONFIG_DIR", Path(__file__).resolve().parents[2] / "config")
    monkeypatch.setattr(pc, "_schema_registry", None)
    monkeypatch.delitem(pc._config_cache, "pipeline.json", raising=False)


def _semeia_documentos(raiz: Path) -> list[Path]:
    pasta = raiz / "workspace" / "data" / "financial_statements"
    pasta.mkdir(parents=True)
    docs = [pasta / f"extrato_{n:02d}-0_original.csv" for n in range(_DOCUMENTOS)]
    for n, doc in enumerate(docs):
        doc.write_text(f"data;descricao;valor\n2024-01-02;compra {n};-{n + 1},50\n", "utf-8")
    return docs


def _threads_que_tocam(sessao: Session) -> set[int]:
    """Threads que usaram a Session: toda query, add e flush do unit of work."""
    threads: set[int] = set()

    def _registra(*_args) -> None:
        threads.add(threading.get_ident())

    for nome in ("do_orm_execute", "before_flush", "transient_to_pending"):
        event.listen(sessao, nome, _registra)
    return threads


def _roda_stage(raiz: Path, store: DBArtifactStore, llm: _LLMQueSoltaAsThreadsJuntas) -> dict:
    from pipeline.stages.extract_with_llm import run

    ctx = WorkspaceContext(
        root=raiz / "workspace",
        artifact_store=store,
        config_overrides={"llm_config.json": dict(_LLM_CONFIG)},
    )
    with patch("pipeline.llm.litellm_client.LLMService.call", side_effect=llm.call):
        return run(ctx)


def _roda_numa_session(banco, raiz: Path, llm) -> tuple[dict, set[int]]:
    """Uma Session por stage, commit no fim — o ciclo do orchestrator (ADR-256)."""
    fabrica, ws_id, run_id = banco
    with fabrica() as sessao:
        store = DBArtifactStore(sessao, workspace_id=ws_id, pipeline_run_id=run_id)
        threads = _threads_que_tocam(sessao)
        resultado = _roda_stage(raiz, store, llm)
        sessao.commit()
    return resultado, threads


def _artefatos_persistidos(banco) -> dict[str, dict]:
    fabrica, ws_id, run_id = banco
    with fabrica() as leitura:
        rows = leitura.scalars(
            select(PipelineArtifact).where(PipelineArtifact.pipeline_run_id == run_id)
        ).all()
        assert {r.stage for r in rows} <= {"extract_with_llm"}
        keys = [r.artifact_key for r in rows]
        assert len(keys) == len(set(keys)), f"artifact_key duplicada: {sorted(keys)}"
        leitor = DBArtifactStore(leitura, workspace_id=ws_id, pipeline_run_id=run_id)
        return {k: leitor.read("extract_with_llm", k) for k in keys}


def test_o_pool_chama_o_llm_e_so_a_thread_do_stage_toca_a_session(banco_do_stage, tmp_path):
    """LLM em _WORKERS threads; query, add e flush só na thread que roda o stage."""
    _semeia_documentos(tmp_path)
    llm = _LLMQueSoltaAsThreadsJuntas()

    _, threads_da_session = _roda_numa_session(banco_do_stage, tmp_path, llm)

    assert len(llm.threads) == _WORKERS
    assert threading.get_ident() not in llm.threads
    assert threads_da_session == {threading.get_ident()}


def test_um_artefato_integro_por_documento_sob_o_pool_cheio(banco_do_stage, tmp_path):
    """N documentos → N rows, cada payload do próprio documento, balanço fechado."""
    docs = _semeia_documentos(tmp_path)

    resultado, _ = _roda_numa_session(banco_do_stage, tmp_path, _LLMQueSoltaAsThreadsJuntas())

    assert resultado["errors"] == []
    assert (resultado["total_processed"], resultado["balanco"]["fecha"]) == (_DOCUMENTOS, True)
    artefatos = _artefatos_persistidos(banco_do_stage)
    assert sorted(artefatos) == sorted(d.name.removesuffix("-0_original.csv") for d in docs)
    for key, payload in artefatos.items():
        n = _numero(key)
        assert payload["arquivo_origem"] == f"{key}-0_original.csv"
        assert [(t["descricao"], t["valor"]) for t in payload["transacoes"]] == [
            (f"compra {n}", -(n + 1.5))
        ]


def test_write_que_falha_vira_erro_do_documento_e_os_outros_persistem(
    banco_do_stage, tmp_path, monkeypatch
):
    """Payload fora do contrato em strict: só aquele doc vira `errors` (ADR-393 D1)."""
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    rejeitado = _semeia_documentos(tmp_path)[5].name
    llm = _LLMQueSoltaAsThreadsJuntas(moeda_por_documento={rejeitado: "GBP"})

    resultado, _ = _roda_numa_session(banco_do_stage, tmp_path, llm)

    assert [e["file"] for e in resultado["errors"]] == [rejeitado]
    assert (resultado["total_processed"], resultado["balanco"]["fecha"]) == (_DOCUMENTOS - 1, True)
    assert rejeitado.removesuffix("-0_original.csv") not in _artefatos_persistidos(banco_do_stage)
    assert len(_artefatos_persistidos(banco_do_stage)) == _DOCUMENTOS - 1
