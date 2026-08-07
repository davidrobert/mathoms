"""A sombra do colapso está de fato ligada em produção (ADR-364 · A40.l2 PR3a).

O ramo que decide a sombra exige ``isinstance(store, DBArtifactStore)`` — então nenhum
teste do pipeline (que injeta ``InMemoryArtifactStore``) o alcança, e o PR3a shipou com o
caminho de produção **coberto só por leitura de código**. A flag pode estar em ``DEFAULTS``,
``shadow_counts`` pode estar correto, e a sombra ainda assim ficar inerte porque o predicado
do store rejeita silenciosamente. Este arquivo é o único lugar onde esse elo é exercitado.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.models import PipelineRun, PipelineRunStatus, User, Workspace
from backend.app.services.feature_flags_service import DEFAULTS, OPERATOR_ONLY
from backend.app.services.storage.db_artifact_store import DBArtifactStore

_FLAG = "cross_document_collapse_measure_enabled"


class _Ctx:
    """Substituto mínimo de ``WorkspaceContext`` — só o que o predicado consulta."""

    def __init__(self, workspace_id):
        # `str(None)` daria `"None"`, que passa pelo guard `is None` do stage e fazia este
        # próprio teste reprovar por defeito do fake, não do código.
        self.workspace_id = None if workspace_id is None else str(workspace_id)


async def _seed(db: AsyncSession):
    user = User(email="shadow@wiring.test", hashed_password=hash_password("p"), full_name="U")
    db.add(user)
    await db.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    db.add(ws)
    await db.flush()
    run = PipelineRun(workspace_id=ws.id, status=PipelineRunStatus.running)
    db.add(run)
    await db.flush()
    return ws.id, run.id


async def _com_store(db: AsyncSession, callback):
    raw = await db.connection()
    return await raw.run_sync(callback)


def test_flag_da_sombra_esta_registrada_e_protegida():
    """Flag fora de ``DEFAULTS`` faz ``is_enabled_sync`` devolver False em silêncio."""
    assert DEFAULTS.get(_FLAG) is True
    assert _FLAG in OPERATOR_ONLY, "sem isto a própria família desliga a medição e cega o gate"


@pytest.mark.asyncio
async def test_com_db_artifact_store_a_sombra_e_construida(db: AsyncSession):
    """O elo que nenhum teste do pipeline alcança: predicado do store + flag + injeção."""
    from scripts.reconcile_transactions import _e3_build_collapser

    ws_id, run_id = await _seed(db)

    def _build(sync_conn):
        with Session(sync_conn) as s:
            store = DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id)
            return _e3_build_collapser(_Ctx(ws_id), store)

    collapser = await _com_store(db, _build)

    assert collapser is not None, "sombra INERTE em produção — o predicado rejeitou o store"
    assert hasattr(collapser, "measure")


@pytest.mark.asyncio
async def test_sem_workspace_a_sombra_fica_inerte(db: AsyncSession):
    """CLI/golden sem workspace não paga o custo da medição."""
    from scripts.reconcile_transactions import _e3_build_collapser

    ws_id, run_id = await _seed(db)

    def _build(sync_conn):
        with Session(sync_conn) as s:
            store = DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id)
            return _e3_build_collapser(_Ctx(None), store)

    assert await _com_store(db, _build) is None


@pytest.mark.parametrize("store", [None, object()])
def test_store_que_nao_e_db_fica_inerte(store):
    """Golden/CLI injeta o colapsador direto; o stage não mede por conta própria."""
    from scripts.reconcile_transactions import _e3_build_collapser

    assert _e3_build_collapser(_Ctx("ws-qualquer"), store) is None


# ─── PR3b: o gate de pré-condição por run (ADR-364 §5) ──────────────────────────────────
#
# Mesmo elo, um andar acima: o gate exige `DBArtifactStore` pelas MESMAS duas razões (sessão
# real + workspace), então nenhum teste do pipeline o alcança. Sem os testes abaixo o PR3b
# poderia shipar com o gate escrito, testado em unidade, e **nunca chamado em produção** — o
# defeito que esta sprint já pagou em outra lane (diff verde, runtime morto).


class _Medicao:
    def __init__(self, candidates=(), corpus=frozenset()):
        self.candidates = candidates
        self.corpus_gate_digests = corpus


class _Resultado:
    def __init__(self, medicao):
        self.collapse_measurement = medicao


def _gate_com_store(ws_id, run_id, medicao):
    """Roda o gate sobre um ``DBArtifactStore`` real, como o stage faz."""
    from scripts.reconcile_transactions import _e3_collapse_precondition

    def _rodar(sync_conn):
        with Session(sync_conn) as s:
            store = DBArtifactStore(s, workspace_id=ws_id, pipeline_run_id=run_id)
            return _e3_collapse_precondition(_Ctx(ws_id), store, _Resultado(medicao))

    return _rodar


# Sem override no workspace não há o que órfãnar; o que este teste trava é que o gate *rodou*
# em produção e emitiu as cláusulas — não o veredito.
@pytest.mark.asyncio
async def test_gate_roda_com_db_artifact_store_e_devolve_relatorio(db: AsyncSession):
    """O elo de produção do gate: store real + workspace real ⇒ relatório PII-free."""
    ws_id, run_id = await _seed(db)

    relatorio = await _com_store(
        db, _gate_com_store(ws_id, run_id, _Medicao(corpus={"digest-qualquer"}))
    )

    assert relatorio is not None, "gate INERTE em produção — o composition root não o alcança"
    assert relatorio["medido"] is True
    assert relatorio["corpus_observado"] == 1
    assert "clausulas_reprovadas" in relatorio


@pytest.mark.asyncio
async def test_sem_medicao_o_gate_nao_emite_relatorio(db: AsyncSession):
    """Corpus vazio = flag off. Ausência é o sinal honesto; relatório vazio mentiria."""
    ws_id, run_id = await _seed(db)

    assert await _com_store(db, _gate_com_store(ws_id, run_id, _Medicao())) is None


@pytest.mark.parametrize("store", [None, object()])
def test_gate_nao_roda_sem_store_de_db(store):
    """`InMemoryArtifactStore` não tem `.session` — o golden não pode estourar aqui."""
    from scripts.reconcile_transactions import _e3_collapse_precondition

    resultado = _Resultado(_Medicao(corpus={"digest-qualquer"}))

    assert _e3_collapse_precondition(_Ctx("ws-qualquer"), store, resultado) is None


def test_main_with_store_chama_o_gate_e_anexa_ao_detail():
    """AST: o composition root chama o gate E o resultado entra no dict que vira
    ``output_summary``. Asserção sobre o service provaria o gate, não a fiação."""
    import ast
    from pathlib import Path

    fonte = Path(__file__).resolve().parents[2] / "scripts" / "reconcile_transactions.py"
    corpo = next(
        n
        for n in ast.walk(ast.parse(fonte.read_text(encoding="utf-8")))
        if isinstance(n, ast.FunctionDef) and n.name == "main_with_store"
    )
    trecho = ast.dump(corpo)

    assert "_e3_collapse_precondition" in trecho, "gate removido do composition root"
    assert "collapse_precondition" in trecho, "relatório não chega ao detail/output_summary"
