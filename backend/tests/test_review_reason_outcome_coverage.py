"""A40.l81 / ADR-411 — a razão sai do artefato em TODO desfecho, não só na pausa.

O gate conta a razão **onde quer que ela esteja** no detail (topo + aninhada) e
compara por Σ `occurrence_count`, não por contagem de rows: a consolidação da
ADR-272 é 1 row por `(run, code, locator)`, então `count(rows) == 4` reprovaria o
comportamento correto.

Forma medida no run `d0f6260a`: 4 ocorrências, 2 códigos, 2 posições — 2 em
`validation.review_reasons` e 2 em `imoveis_consolidados[].review_reasons`.
Antes desta lane a tabela ficava com 0 delas, porque o stage entregou.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from typing import Any

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
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.tasks.pipeline_task import _record_stage_result
from pipeline.domain.review_reason_harvest import harvest_review_reasons
from pipeline.stage_outcome import resolve_stage_outcome

_STAGE = "consolidate_baseline"


@dataclass
class _FakeStageResult:
    success: bool
    detail: Any
    error: str | None = None


@pytest_asyncio.fixture
async def sync_db(db):
    """Mesmo padrão de `test_review_reason_adapter`: o `db` async cria o schema
    no arquivo SQLite, e o código sob teste abre `SyncSessionLocal` por dentro."""
    with SyncSessionLocal() as session:
        yield session


@pytest.fixture
def silence_publish(monkeypatch):
    """Pub/sub não é o objeto do teste; sem isto o terminal fala com Redis."""
    for name in ("publish_stage_completed", "publish_stage_failed"):
        monkeypatch.setattr(f"backend.app.tasks.pipeline_task.{name}", lambda *a, **kw: None)


@pytest.fixture
def seeded(sync_db) -> tuple[str, str, str]:
    """`(workspace_id, run_id, log_id)` reais — as FKs são enforçadas (ADR-371)."""
    ws_id, run_id, log_id = (str(uuid.uuid4()) for _ in range(3))
    user = User(
        id=str(uuid.uuid4()),
        email=f"outcome-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="x",
        full_name="Outcome Coverage Fixture",
    )
    sync_db.add(user)
    sync_db.flush()
    sync_db.add(Workspace(id=ws_id, name="WS outcome", owner_id=user.id))
    sync_db.add(PipelineRun(id=run_id, workspace_id=ws_id, status=PipelineRunStatus.running))
    sync_db.add(
        PipelineStageLog(
            id=log_id,
            pipeline_run_id=run_id,
            stage=_STAGE,
            status=PipelineStageStatus.running,
        )
    )
    sync_db.commit()
    return ws_id, run_id, log_id


def _reason(code: str, *, occ: int = 1) -> dict:
    return {
        "code": code,
        "stage": _STAGE,
        "artifact_key": "baseline_patrimonial",
        "document_id": None,
        "offending_value": "endereco_canonical=None",
        "expected": "canonical or unique",
        "message": "identity not minted",
        "occurrence_count": occ,
    }


def _detail_do_run_medido() -> dict:
    """A forma exata do `d0f6260a`: 2 razões no topo, 2 aninhadas por item."""
    return {
        "success": True,
        "imoveis": 2,
        # SEM `valid`: o stage entrega (WARN-first, ADR-357) — é justamente o
        # desfecho em que o sink não era chamado.
        "validation": {"review_reasons": [_reason("domain.baseline_divergence") for _ in range(2)]},
        "imoveis_consolidados": [
            {"review_reasons": [_reason("domain.property_identity_uncanonical")]},
            {"review_reasons": [_reason("domain.property_identity_uncanonical")]},
        ],
    }


def _terminar(run_id: str, log_id: str, detail: dict, *, delivered: bool = True) -> None:
    """O terminal REAL do desfecho — não uma cópia à mão do que ele faz."""
    _record_stage_result(
        run_id,
        _STAGE,
        log_id,
        _FakeStageResult(success=delivered, detail=detail),
        100,
        50,
        resolve_stage_outcome(_STAGE, delivered=delivered),
    )


def _rows(db, run_id: str) -> list[ReviewReason]:
    db.expire_all()
    return list(
        db.execute(select(ReviewReason).where(ReviewReason.pipeline_run_id == run_id))
        .scalars()
        .all()
    )


def _occ_por_code(rows: list[ReviewReason]) -> dict[str, int]:
    out: Counter[str] = Counter()
    for row in rows:
        out[row.code] += row.occurrence_count
    return dict(out)


def _occ_do_artefato(detail: dict) -> dict[str, int]:
    """Σ occurrence_count por code, colhida com a MESMA função que o sink usa."""
    out: Counter[str] = Counter()
    for reason in harvest_review_reasons(detail):
        out[reason["code"]] += int(reason.get("occurrence_count", 1) or 1)
    return dict(out)


@pytest.mark.asyncio
async def test_stage_que_entrega_tambem_persiste_a_razao(sync_db, seeded, silence_publish) -> None:
    """O caso da lane: o stage ENTREGOU, logo não passou pelo ramo de pausa."""
    _, run_id, log_id = seeded
    _terminar(run_id, log_id, _detail_do_run_medido())
    assert _rows(sync_db, run_id), "razão do desfecho entregue não pode sumir"


@pytest.mark.asyncio
async def test_cobertura_e_total_em_qualquer_posicao(sync_db, seeded, silence_publish) -> None:
    # Conta a razão ONDE QUER QUE ELA ESTEJA: um gate que lesse só
    # `validation.review_reasons` passaria verde sobre 2 de 4.
    """O predicado que o r9 mede: Σ occurrence_count colhida == Σ persistida."""
    _, run_id, log_id = seeded
    detail = _detail_do_run_medido()
    _terminar(run_id, log_id, detail)

    esperado = _occ_do_artefato(detail)
    assert esperado == {"domain.baseline_divergence": 2, "domain.property_identity_uncanonical": 2}
    assert _occ_por_code(_rows(sync_db, run_id)) == esperado


@pytest.mark.asyncio
async def test_razao_aninhada_sozinha_nao_e_perdida(sync_db, seeded, silence_publish) -> None:
    """Mutação que mata: sink que leia o caminho de topo devolve 0 aqui."""
    _, run_id, log_id = seeded
    detail = {
        "success": True,
        "imoveis_consolidados": [
            {"review_reasons": [_reason("domain.property_identity_uncanonical", occ=3)]}
        ],
    }
    _terminar(run_id, log_id, detail)
    assert _occ_por_code(_rows(sync_db, run_id)) == {"domain.property_identity_uncanonical": 3}


@pytest.mark.asyncio
async def test_locator_separa_a_mesma_razao_em_posicoes_distintas(
    sync_db, seeded, silence_publish
) -> None:
    """Sem o locator as duas colapsariam numa row cujo ponteiro não reencontra
    a evidência — o defeito de RV8-19 (ADR-411 D3)."""
    _, run_id, log_id = seeded
    code = "domain.property_identity_uncanonical"
    detail = {
        "success": True,
        "validation": {"review_reasons": [_reason(code)]},
        "imoveis_consolidados": [{"review_reasons": [_reason(code)]}],
    }
    _terminar(run_id, log_id, detail)

    rows = _rows(sync_db, run_id)
    assert {r.locator for r in rows} == {
        "validation.review_reasons",
        "imoveis_consolidados[].review_reasons",
    }
    assert _occ_por_code(rows) == {code: 2}


@pytest.mark.asyncio
async def test_desfecho_falho_tambem_registra(sync_db, seeded, silence_publish) -> None:
    """ "Todo desfecho" inclui o que não entregou: é onde o diagnóstico mais vale."""
    _, run_id, log_id = seeded
    _terminar(run_id, log_id, _detail_do_run_medido(), delivered=False)
    assert _occ_por_code(_rows(sync_db, run_id))["domain.baseline_divergence"] == 2


@pytest.mark.asyncio
async def test_detail_sem_razao_nao_escreve_row(sync_db, seeded, silence_publish) -> None:
    """Fail-open não é fail-noisy: stage limpo não polui a tabela."""
    _, run_id, log_id = seeded
    _terminar(run_id, log_id, {"success": True, "imoveis": 2})
    assert _rows(sync_db, run_id) == []
