"""CTO-6 · ADR-404 — a superfície de diagnóstico nunca aborta a execução que
documenta. DB real (SQLite via `SyncSessionLocal`, FKs ON — ADR-371), nunca mock:
produtor emite payload venenoso → o run PAUSA e a row de `review_reasons` degrada.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.models.review_reason import ReviewReason
from backend.app.models.stage_review import StageReview, StageReviewStatus
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.diagnostics.review_reason_boundary import CLIPPED_COLUMNS
from backend.app.tasks.pipeline_task import _record_stage_needs_review

_STAGE = "reconcile_transactions"


@pytest_asyncio.fixture
async def sync_db(db):
    # Mesma factory que produção abre internamente — ver nota em
    # test_review_reason_adapter.py sobre o drift do `_sync_test_engine`.
    with SyncSessionLocal() as session:
        yield session


@dataclass
class _FakeStageResult:
    detail: dict[str, Any] | None


def _seed(db) -> tuple[str, str, str]:
    """`(workspace_id, run_id, log_id)` materializados — FK exige os pais (ADR-371)."""
    ws_id, run_id, log_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    user = User(
        id=str(uuid.uuid4()),
        email=f"cto6-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="x",
        full_name="Diagnostic Isolation Fixture",
    )
    db.add(user)
    db.flush()
    db.add(Workspace(id=ws_id, name="WS cto6", owner_id=user.id))
    db.add(PipelineRun(id=run_id, workspace_id=ws_id, status=PipelineRunStatus.running))
    db.add(
        PipelineStageLog(
            id=log_id,
            pipeline_run_id=run_id,
            stage=_STAGE,
            status=PipelineStageStatus.running,
        )
    )
    db.commit()
    return ws_id, run_id, log_id


def _reason(**over) -> dict:
    base = {
        "code": "domain.balance_gap",
        "stage": _STAGE,
        "artifact_key": "abc123def456_itau_extratoconta_202601",
        "document_id": None,
        "offending_value": "index=0",
        "expected": "gap=0",
        "message": "saldo declarado nao fecha",
        "occurrence_count": 1,
    }
    base.update(over)
    return base


def _detail(*reasons: Any) -> dict:
    return {
        "validation": {
            "valid": False,
            "errors": ["revisao manual"],
            "review_reasons": list(reasons),
        }
    }


def _record(run_id: str, log_id: str, detail: dict) -> None:
    with patch("backend.app.tasks.pipeline_task.publish_needs_review"):
        _record_stage_needs_review(run_id, _STAGE, log_id, _FakeStageResult(detail), 5)


def _run(db, run_id: str) -> PipelineRun:
    db.expire_all()
    return db.execute(select(PipelineRun).where(PipelineRun.id == run_id)).scalar_one()


def _rows(db, run_id: str) -> list[ReviewReason]:
    db.expire_all()
    return list(
        db.execute(select(ReviewReason).where(ReviewReason.pipeline_run_id == run_id))
        .scalars()
        .all()
    )


def _review(db, run_id: str) -> StageReview:
    db.expire_all()
    return db.execute(select(StageReview).where(StageReview.pipeline_run_id == run_id)).scalar_one()


def _assert_paused(db, run_id: str) -> None:
    run = _run(db, run_id)
    assert run.status == PipelineRunStatus.needs_review, "o run tem de pausar, não morrer"
    assert run.paused_at_stage == _STAGE
    assert run.current_stage is None
    assert _review(db, run_id).status == StageReviewStatus.pending, "pausa sem review libera resume"


# Munição que o SQLite REALMENTE rejeita — cada uma matava o run inteiro antes do
# fix (run 140ac8d7 morreu em 12/18 pela irmã dessa família, RV7-01 · #1535).
_POISON_SQLITE = [
    pytest.param(
        _reason(offending_value={"esperado": 100, "obtido": 90}),
        id="dict-em-coluna-Text",  # sqlite3.ProgrammingError no bind
    ),
    pytest.param(
        "extrato sem banco determinavel",
        id="entrada-str-em-vez-de-objeto",  # AttributeError: 'str' has no 'get'
    ),
    pytest.param(
        _reason(occurrence_count="muitas"),
        id="occurrence_count-nao-numerico",  # ValueError no int()
    ),
]


@pytest.mark.parametrize("poison", _POISON_SQLITE)
@pytest.mark.asyncio
async def test_payload_venenoso_pausa_o_run_em_vez_de_mata_lo(sync_db, poison) -> None:
    """O teste-mãe: cada munição derrubava a execução inteira antes do fix."""
    _, run_id, log_id = _seed(sync_db)
    _record(run_id, log_id, _detail(poison))
    _assert_paused(sync_db, run_id)


@pytest.mark.asyncio
async def test_artifact_key_acima_da_coluna_trunca_preservando_a_cabeca(sync_db) -> None:
    """SQLite ignora `VARCHAR(n)`; o Postgres levanta `22001` (classe do RV6-11).
    A prova aqui é a LARGURA da row publicada contra o limite do model — e a
    cabeça sobrevive porque `content_hash[:12]` (ADR-084) resolve a identidade."""
    limit = ReviewReason.__table__.c.artifact_key.type.length
    _, run_id, log_id = _seed(sync_db)
    key = "abc123def456_" + "k" * 400
    _record(run_id, log_id, _detail(_reason(artifact_key=key)))
    _assert_paused(sync_db, run_id)
    rows = _rows(sync_db, run_id)
    assert len(rows) == 1, "valor largo trunca, não apaga a evidência"
    assert len(rows[0].artifact_key) <= limit
    assert rows[0].artifact_key.startswith("abc123def456_")


@pytest.mark.asyncio
async def test_code_fora_do_vocabulario_e_descartado(sync_db) -> None:
    """`(run, code)` é a chave de consolidação: code fabricado a envenena.
    O sinal vai para o log — a tabela não tem consumidor de UI hoje."""
    _, run_id, log_id = _seed(sync_db)
    _record(run_id, log_id, _detail(_reason(code="domain." + "x" * 200)))
    _assert_paused(sync_db, run_id)
    assert _rows(sync_db, run_id) == []


@pytest.mark.asyncio
async def test_stage_do_produtor_e_ignorado(sync_db) -> None:
    """`stage` é do orquestrador. Deixar o produtor escolher reabriria a munição
    de largura num campo que nunca foi dele."""
    _, run_id, log_id = _seed(sync_db)
    _record(run_id, log_id, _detail(_reason(stage="s" * 200)))
    assert _rows(sync_db, run_id)[0].stage == _STAGE


@pytest.mark.asyncio
async def test_toda_coluna_estreita_passa_pelo_fit(sync_db) -> None:
    """Dialect-independent e cobre coluna que ainda não existe: `String(n)` nova
    em `review_reasons` sem `_fit` reprova aqui, não num Postgres distante."""
    narrow = {
        c.name
        for c in ReviewReason.__table__.columns
        if getattr(c.type, "length", None) is not None
    }
    # `id`/`workspace_id`/`pipeline_run_id` são UUID nosso; `document_id` é
    # nulificado no boundary; `stage` vem do orquestrador. Sobra o que o
    # produtor escreve, e tudo isso tem de estar em CLIPPED_COLUMNS.
    ours = {"id", "workspace_id", "pipeline_run_id", "stage", "document_id"}
    assert narrow - ours == set(CLIPPED_COLUMNS)


@pytest.mark.asyncio
async def test_dict_em_coluna_de_texto_vira_texto_e_a_row_sobrevive(sync_db) -> None:
    """Degradar não é sumir: a row existe com o valor coagido."""
    _, run_id, log_id = _seed(sync_db)
    _record(run_id, log_id, _detail(_reason(offending_value={"esperado": 100, "obtido": 90})))
    rows = _rows(sync_db, run_id)
    assert len(rows) == 1
    assert isinstance(rows[0].offending_value, str)
    assert "esperado" in rows[0].offending_value


@pytest.mark.asyncio
async def test_entrada_insalvavel_e_descartada_sem_derrubar_as_irmas(sync_db) -> None:
    _, run_id, log_id = _seed(sync_db)
    _record(run_id, log_id, _detail("texto solto", _reason(code="domain.temporal_gap")))
    _assert_paused(sync_db, run_id)
    assert [r.code for r in _rows(sync_db, run_id)] == ["domain.temporal_gap"]


@pytest.mark.asyncio
async def test_payload_saudavel_persiste_intacto(sync_db) -> None:
    """A guarda não pode cegar o caminho feliz — senão o fix apaga o diagnóstico."""
    _, run_id, log_id = _seed(sync_db)
    _record(run_id, log_id, _detail(_reason(occurrence_count=7)))
    row = _rows(sync_db, run_id)[0]
    assert row.code == "domain.balance_gap"
    assert row.occurrence_count == 7
    assert row.artifact_key == "abc123def456_itau_extratoconta_202601"
    assert row.offending_value == "index=0"


@pytest.mark.asyncio
async def test_falha_desconhecida_no_diagnostico_nao_aborta(sync_db) -> None:
    """Fecha a CLASSE, não a munição: o DTO conhece as colunas de hoje, o
    try/except cobre o que o produtor de amanhã inventar."""
    _, run_id, log_id = _seed(sync_db)
    with patch(
        "backend.app.services.diagnostics.review_reason_sink._materialize_review_reasons",
        side_effect=RuntimeError("munição futura"),
    ):
        _record(run_id, log_id, _detail(_reason()))
    _assert_paused(sync_db, run_id)
    assert _rows(sync_db, run_id) == [], "o diagnóstico se perdeu — o run, não"


@pytest.mark.asyncio
async def test_projecao_de_issues_falha_open_sem_perder_a_pausa(sync_db) -> None:
    """`validation_issues` é nullable e a UI cai para `validation_errors`."""
    _, run_id, log_id = _seed(sync_db)
    with patch(
        "backend.app.tasks.pipeline_task._issues_from_reasons",
        side_effect=RuntimeError("projeção quebrada"),
    ):
        _record(run_id, log_id, _detail(_reason()))
    _assert_paused(sync_db, run_id)
    review = _review(sync_db, run_id)
    assert review.validation_issues is None
    assert review.validation_errors == "revisao manual"


@pytest.mark.asyncio
async def test_falha_na_transicao_de_estado_continua_alta(sync_db) -> None:
    """Polaridade: o fail-open é do diagnóstico. Perder a transição é perder o
    estado do run — tem de estourar, não virar log."""
    _, run_id, _ = _seed(sync_db)
    with pytest.raises(Exception):  # noqa: B017 — qualquer propagação serve
        _record(run_id, str(uuid.uuid4()), _detail(_reason()))
    assert _run(sync_db, run_id).status == PipelineRunStatus.running


@pytest.mark.asyncio
async def test_errors_heterogeneo_nao_derruba_a_pausa(sync_db) -> None:
    """`"\\n".join` sobre lista mista levantava ANTES de abrir a sessão."""
    _, run_id, log_id = _seed(sync_db)
    detail = {"validation": {"valid": False, "errors": ["ok", {"code": "x"}], "review_reasons": []}}
    _record(run_id, log_id, detail)
    _assert_paused(sync_db, run_id)
