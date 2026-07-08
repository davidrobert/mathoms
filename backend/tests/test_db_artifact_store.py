"""Tests — ``backend.app.services.storage.db_artifact_store.DBArtifactStore`` (Fase 2.1).

Valida:
- Round-trip write/read preserva dados exatos.
- ``list_keys`` cross-run (distinct artifact_key por workspace+stage).
- ``write`` é upsert (mesma key mesma run → UPDATE, não INSERT).
- ``delete_stage`` remove apenas artefatos da run atual.
- Sessão é injetada (store não cria/fecha sessão).
- Satisfaz os protocolos ``ArtifactStore`` e ``ReadableArtifactStore``.
"""

from __future__ import annotations

import logging

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models import (
    PipelineArtifact,
    PipelineRun,
    PipelineRunStatus,
    User,
    Workspace,
)
from backend.app.services.storage.db_artifact_store import DBArtifactStore
from pipeline.artifact_store import ArtifactStore, ReadableArtifactStore


async def _seed_ws_and_run(db: AsyncSession, *, email: str = "st@test.com"):
    user = User(email=email, hashed_password=hash_password("p"), full_name="U")
    db.add(user)
    await db.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    db.add(ws)
    await db.flush()
    run = PipelineRun(workspace_id=ws.id, status=PipelineRunStatus.running)
    db.add(run)
    await db.flush()
    return ws.id, run.id


def _store_on_sync_conn(sync_session, *, workspace_id, pipeline_run_id):
    """Retorna ``DBArtifactStore`` para uso em run_sync."""
    return DBArtifactStore(
        sync_session,
        workspace_id=workspace_id,
        pipeline_run_id=pipeline_run_id,
    )


@pytest.mark.asyncio
async def test_write_then_read(db: AsyncSession):
    ws_id, run_id = await _seed_ws_and_run(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E2-extratos", "itau_202601", {"tx": [{"v": 1}]})
            s.commit()
            s2 = Session(sync_conn)
            store2 = _store_on_sync_conn(s2, workspace_id=ws_id, pipeline_run_id=run_id)
            return store2.read("E2-extratos", "itau_202601")

    raw = await db.connection()
    got = await raw.run_sync(_do)
    assert got == {"tx": [{"v": 1}]}


@pytest.mark.asyncio
async def test_write_is_upsert(db: AsyncSession):
    ws_id, run_id = await _seed_ws_and_run(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E3", "k", {"v": 1})
            store.write("E3", "k", {"v": 2})
            s.commit()
            return store.read("E3", "k")

    raw = await db.connection()
    via_read = await raw.run_sync(_do)
    assert via_read == {"v": 2}


@pytest.mark.asyncio
async def test_list_keys_and_exists(db: AsyncSession):
    ws_id, run_id = await _seed_ws_and_run(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E4", "receitas", {})
            store.write("E4", "despesas", {})
            store.write("E5", "analise", {})
            s.commit()
            return store.list_keys("E4"), store.exists("E4", "despesas"), store.exists("E4", "nope")

    raw = await db.connection()
    keys, exists_yes, exists_no = await raw.run_sync(_do)
    assert keys == ["despesas", "receitas"]
    assert exists_yes is True
    assert exists_no is False


@pytest.mark.asyncio
async def test_delete_and_delete_stage(db: AsyncSession):
    ws_id, run_id = await _seed_ws_and_run(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E3", "a", {})
            store.write("E3", "b", {})
            store.write("E4", "c", {})
            s.commit()
            store.delete("E3", "a")
            s.commit()
            remaining_e3 = store.list_keys("E3")
            removed = store.delete_stage("E3")
            s.commit()
            return remaining_e3, removed, store.list_keys("E3"), store.list_keys("E4")

    raw = await db.connection()
    remaining, removed, after_stage_del, e4 = await raw.run_sync(_do)
    assert remaining == ["b"]
    assert removed == 1
    assert after_stage_del == []
    assert e4 == ["c"]


@pytest.mark.asyncio
async def test_delete_stage_scoped_to_current_run(db: AsyncSession):
    """``delete_stage`` não apaga artefatos de outras runs."""
    ws_id, run_id = await _seed_ws_and_run(db, email="multi@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            other_run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed)
            s.add(other_run)
            s.flush()
            other_id = other_run.id

            store1 = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store2 = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=other_id)
            store1.write("E3", "x", {"run": 1})
            store2.write("E3", "x", {"run": 2})
            s.commit()
            removed = store1.delete_stage("E3")
            s.commit()
            # run atual limpo; outra run intocada
            return removed, store1.list_keys("E3"), store2.read("E3", "x")

    raw = await db.connection()
    removed, after, other_run_value = await raw.run_sync(_do)
    # list_keys retorna distinct no workspace — a outra run ainda tem "x"
    assert removed == 1
    assert after == ["x"]
    assert other_run_value == {"run": 2}


@pytest.mark.asyncio
async def test_satisfies_artifact_store_protocol(db: AsyncSession):
    ws_id, run_id = await _seed_ws_and_run(db, email="proto@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            return isinstance(store, ArtifactStore), isinstance(store, ReadableArtifactStore)

    raw = await db.connection()
    is_full, is_read = await raw.run_sync(_do)
    assert is_full
    assert is_read


@pytest.mark.asyncio
async def test_read_after_write_without_commit_sees_pending(db: AsyncSession):
    """Autoflush garante que ``read`` após ``write`` na mesma sessão sem
    commit enxerga os dados pendentes (upsert semantics preservada ao
    remover flush explícito por-write)."""
    ws_id, run_id = await _seed_ws_and_run(db, email="autoflush@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E2", "k1", {"v": 1})
            first = store.read("E2", "k1")
            # Re-escreve (UPDATE path) e relê antes de commit
            store.write("E2", "k1", {"v": 2})
            second = store.read("E2", "k1")
            s.commit()
            return first, second

    raw = await db.connection()
    first, second = await raw.run_sync(_do)
    assert first == {"v": 1}
    assert second == {"v": 2}


@pytest.mark.asyncio
async def test_bulk_writes_single_commit(db: AsyncSession):
    """N writes em série com um único commit no fim — semântica preservada
    sem flush por-write (mitigação de lock contention em E2 com milhares
    de transações)."""
    ws_id, run_id = await _seed_ws_and_run(db, email="bulk@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            for i in range(50):
                store.write("E2", f"tx_{i:04d}", {"idx": i})
            s.commit()
            return store.list_keys("E2")

    raw = await db.connection()
    keys = await raw.run_sync(_do)
    assert len(keys) == 50
    assert keys[0] == "tx_0000"
    assert keys[-1] == "tx_0049"


@pytest.mark.asyncio
async def test_store_does_not_close_session(db: AsyncSession):
    """Sessão injetada permanece utilizável pelo chamador após o store agir."""
    ws_id, run_id = await _seed_ws_and_run(db, email="noclose@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        s = Session(sync_conn)
        try:
            store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
            store.write("E5", "analise", {"a": 1})
            s.commit()
            # A sessão ainda deve ser usável
            count = s.query(PipelineArtifact).filter_by(pipeline_run_id=run_id, stage="E5").count()
            return count
        finally:
            s.close()

    raw = await db.connection()
    n = await raw.run_sync(_do)
    assert n == 1


# =============================================================================
# T1 — Cross-run fallback para stages workspace-scoped (ADR-132)
# =============================================================================
#
# Bug observado: rodar pipeline sem reprocessar IRPF deixava E1.5c (baseline)
# de runs anteriores invisível ao run atual; E4 lia None, escrevia placeholder
# vazio sobre o E4-patrimônio bom, E5 zerava composição patrimonial.
# Fix: read() cai para o artefato mais recente do workspace quando o stage
# está em _WORKSPACE_SCOPED_STAGES e o run atual não tem o key.


@pytest.mark.asyncio
async def test_workspace_scoped_stage_falls_back_across_runs(db: AsyncSession):
    """E1.5c escrito no run A é visível ao read() de um store no run B."""
    ws_id, run_a = await _seed_ws_and_run(db, email="cross-run-a@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add(run_b_obj)
            s.flush()
            run_b = run_b_obj.id

            store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
            store_a.write(
                "E1.5c",
                "baseline_patrimonial",
                {
                    "itens": [{"valor_brl": 1000.0}],
                    "patrimonio_por_ano": {"2024": {"total_bens": 1000.0}},
                },
            )
            s.commit()

            store_b = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_b)
            return store_b.read("E1.5c", "baseline_patrimonial")

    raw = await db.connection()
    payload = await raw.run_sync(_do)
    assert payload is not None, "fallback workspace-wide deveria devolver baseline do run anterior"
    assert payload["patrimonio_por_ano"]["2024"]["total_bens"] == 1000.0


@pytest.mark.asyncio
async def test_run_scoped_stage_does_not_fall_back(db: AsyncSession):
    """E3/E4/E5 não fazem fallback — cada run é dono dos próprios outputs.

    ADR-241: E2 foi **promovido** a workspace-scoped (per-doc idempotente).
    E3/E4/E5 mantêm semântica run-scoped (invariantes cross-account).
    """
    ws_id, run_a = await _seed_ws_and_run(db, email="cross-run-b@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add(run_b_obj)
            s.flush()
            run_b = run_b_obj.id

            store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
            store_a.write("E3", "itau_202601_reconciled", {"transacoes": [{"v": 1}]})
            store_a.write("E4", "patrimonio", {"big": "data"})
            store_a.write("E5", "analise_financeira", {"bruto": 999.0})
            s.commit()

            store_b = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_b)
            return (
                store_b.read("E3", "itau_202601_reconciled"),
                store_b.read("E4", "patrimonio"),
                store_b.read("E5", "analise_financeira"),
            )

    raw = await db.connection()
    e3_val, e4_val, e5_val = await raw.run_sync(_do)
    assert e3_val is None, "E3 é run-scoped (invariantes cross-account, ADR-241)"
    assert e4_val is None, "E4 é run-scoped"
    assert e5_val is None, "E5 é run-scoped"


@pytest.mark.asyncio
async def test_workspace_fallback_returns_most_recent(db: AsyncSession):
    """Quando 2 runs anteriores escreveram o mesmo (stage, key) workspace-scoped,
    o fallback resolve para o mais recente por created_at."""
    ws_id, run_a = await _seed_ws_and_run(db, email="cross-run-c@test.com")

    def _do(sync_conn):
        import time

        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed)
            s.add(run_b_obj)
            s.flush()
            run_b = run_b_obj.id
            run_c_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add(run_c_obj)
            s.flush()
            run_c = run_c_obj.id

            store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
            store_a.write("E1.5c", "baseline_patrimonial", {"version": "old"})
            s.commit()
            time.sleep(0.01)  # garante created_at distinto em sqlite (resolução ms)

            store_b = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_b)
            store_b.write("E1.5c", "baseline_patrimonial", {"version": "new"})
            s.commit()

            store_c = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_c)
            return store_c.read("E1.5c", "baseline_patrimonial")

    raw = await db.connection()
    payload = await raw.run_sync(_do)
    assert payload is not None
    assert payload["version"] == "new", "fallback deve pegar a entrada mais recente"


def _add_completed_and_running_runs(s, ws_id: str) -> tuple[str, str]:
    runs = [
        PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed),
        PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running),
    ]
    s.add_all(runs)
    s.flush()
    return runs[0].id, runs[1].id


def _insert_baselines_with_tied_created_at(s, ws_id: str, entries) -> None:
    """Insere E1.5c com created_at idêntico — reproduz empate de microssegundo."""
    from datetime import datetime, timezone

    tied = datetime.now(timezone.utc)
    for run_id, version in entries:
        s.add(
            PipelineArtifact(
                workspace_id=ws_id,
                pipeline_run_id=run_id,
                stage="E1.5c",
                artifact_key="baseline_patrimonial",
                content_json={"version": version},
                created_at=tied,
            )
        )
    s.commit()


@pytest.mark.asyncio
async def test_workspace_fallback_deterministic_on_created_at_tie(db: AsyncSession):
    """created_at empatado entre runs → fallback resolve pelo maior id, sem flake."""
    ws_id, run_a = await _seed_ws_and_run(db, email="tiebreak@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            run_b, run_c = _add_completed_and_running_runs(s, ws_id)
            _insert_baselines_with_tied_created_at(s, ws_id, [(run_a, "old"), (run_b, "new")])
            store_c = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_c)
            return store_c.read("E1.5c", "baseline_patrimonial")

    raw = await db.connection()
    payload = await raw.run_sync(_do)
    assert payload == {"version": "new"}, "empate em created_at deve resolver pelo maior id"


@pytest.mark.asyncio
async def test_workspace_fallback_isolated_by_workspace(db: AsyncSession):
    """Fallback NUNCA cruza workspaces — outro workspace não enxerga baseline alheio."""
    ws_a_id, run_a = await _seed_ws_and_run(db, email="cross-ws-a@test.com")
    ws_b_id, run_b = await _seed_ws_and_run(db, email="cross-ws-b@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store_a = _store_on_sync_conn(s, workspace_id=ws_a_id, pipeline_run_id=run_a)
            store_a.write("E1.5c", "baseline_patrimonial", {"secret": "ws_a_only"})
            s.commit()

            store_b = _store_on_sync_conn(s, workspace_id=ws_b_id, pipeline_run_id=run_b)
            return store_b.read("E1.5c", "baseline_patrimonial")

    raw = await db.connection()
    payload = await raw.run_sync(_do)
    assert payload is None, "workspace fallback não pode vazar entre workspaces"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stage",
    [
        # Legacy names (escritos hoje por extract_members/extract_baseline/etc)
        "E1",
        "E1.5",
        "E1.5a",
        "E1.5c",
        # Descritivos equivalentes (compat F9.2 → F9.6)
        "extract_members",
        "extract_baseline",
        "consolidate_baseline",
        # ADR-157 — IRPF só existe em forma descritiva
        "extract_irpf_full",
        # ADR-216 + ADR-238 — informes de imobiliária e anuais
        "extract_informe_aluguel",
        "extract_informes_anuais",
        # ADR-241 — E2 (extratos / faturas / LLM fallback): per-doc idempotente.
        # Sem fallback, incremental ficaria cego aos E2 das runs anteriores.
        "E2-extratos",
        "E2-faturas",
        "E2-llm",
        "extract_statements",
        "extract_invoices",
        "extract_with_llm",
    ],
)
async def test_workspace_scoped_stages_fall_back_cross_run(db: AsyncSession, stage: str):
    """Cada stage workspace-scoped resolve cross-run por workspace.

    Regressão A8 (ADR-157): ``extract_irpf_full`` em forma descritiva ficou
    fora da frozenset → runs sem IRPF perdia IRPF da última run silenciosamente.

    Regressão A17 (ADR-241): E2-* (extratos/faturas/LLM) eram run-scoped →
    incremental que extraía só docs novos perdia os ~80 E2 das runs anteriores
    no momento do E3, derrubando ``statements_loaded`` para ~2 e produzindo
    relatório com fluxo de caixa subdimensionado em 95%+.
    """
    ws_id, run_a = await _seed_ws_and_run(db, email=f"ws-scope-{stage.replace('.', '-')}@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add(run_b_obj)
            s.flush()
            run_b = run_b_obj.id

            store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
            store_a.write(stage, "ref_key", {"v": "ws_scoped"})
            s.commit()

            store_b = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_b)
            return store_b.read(stage, "ref_key")

    raw = await db.connection()
    payload = await raw.run_sync(_do)
    assert payload is not None, f"stage {stage} deveria fazer fallback workspace-wide"
    assert payload["v"] == "ws_scoped"


@pytest.mark.asyncio
async def test_current_run_takes_precedence_over_workspace_fallback(db: AsyncSession):
    """Quando o run atual tem o artefato, fallback NÃO é consultado."""
    ws_id, run_a = await _seed_ws_and_run(db, email="precedence@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add(run_b_obj)
            s.flush()
            run_b = run_b_obj.id

            store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
            store_a.write("E1.5c", "baseline_patrimonial", {"version": "older_other_run"})
            s.commit()

            store_b = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_b)
            store_b.write("E1.5c", "baseline_patrimonial", {"version": "current_run"})
            s.commit()

            return store_b.read("E1.5c", "baseline_patrimonial")

    raw = await db.connection()
    payload = await raw.run_sync(_do)
    assert (
        payload["version"] == "current_run"
    ), "read() do run atual com artefato deve devolver o do run, não o fallback"


# =============================================================================
# T2 — Telemetria de fallback (ADR-241)
# =============================================================================


class _RecordCapture(logging.Handler):
    """Captura LogRecords de um logger nominado, bypassando caplog/root.

    `setup_logging()` global em `backend/app/core/logging.py` reconfigura
    root + nível depois que caplog instalou; sob `pytest-xdist`/CI
    caplog pode perder os records emitidos antes do reconfig. Este
    handler anexa direto ao logger por nome — independente do root.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.mark.asyncio
async def test_workspace_fallback_emits_telemetry(db: AsyncSession):
    """ADR-241: fallback workspace-wide emite log estruturado por chamada."""
    import logging as _logging

    ws_id, run_a = await _seed_ws_and_run(db, email="fallback-telemetry@test.com")

    logger = _logging.getLogger("mathoms.pipeline.artifact")
    handler = _RecordCapture()
    original_level = logger.level
    original_disabled = logger.disabled
    logger.addHandler(handler)
    logger.setLevel(_logging.INFO)
    logger.disabled = False  # `logging.config.fileConfig` (Alembic) pode ter desativado.
    try:

        def _do(sync_conn):
            from sqlalchemy.orm import Session

            with Session(sync_conn) as s:
                run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
                s.add(run_b_obj)
                s.flush()
                run_b = run_b_obj.id

                store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
                store_a.write("E2-extratos", "itau_202601", {"transacoes": []})
                s.commit()

                store_b = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_b)
                return store_b.read("E2-extratos", "itau_202601"), run_a, run_b

        raw = await db.connection()
        payload, run_a_id, run_b_id = await raw.run_sync(_do)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)
        logger.disabled = original_disabled

    assert payload is not None
    records = [
        r for r in handler.records if r.msg == "mathoms.pipeline.artifact.workspace_fallback"
    ]
    assert len(records) == 1
    rec = records[0]
    assert getattr(rec, "stage", None) == "E2-extratos"
    assert getattr(rec, "artifact_key", None) == "itau_202601"
    assert getattr(rec, "current_run_id", None) == run_b_id
    assert getattr(rec, "source_run_id", None) == run_a_id


@pytest.mark.asyncio
async def test_incremental_run_sees_e2_from_previous_runs(db: AsyncSession):
    """ADR-241 — integração: run incremental enxerga E2 das runs anteriores.

    Cenário: workspace tem 5 E2 do run A (full). Usuário envia 2 docs
    novos → run B (incremental) extrai só esses 2. Quando E3 do run B
    iterar ``list_keys("E2-extratos")``, deve enxergar os 7 keys e
    ``read`` deve devolver payload válido para cada um.

    Sem ADR-241, ``read`` retornava None para os 5 docs antigos
    (filtrados por ``pipeline_run_id=run_b``) e o pipeline ficava cego.
    """
    ws_id, run_a = await _seed_ws_and_run(db, email="incremental-e2@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
            # Run A: 5 docs extraídos.
            for i in range(5):
                store_a.write(
                    "E2-extratos",
                    f"itau_extratoconta_BRL_2025{i + 1:02d}_2025{i + 1:02d}",
                    {"transacoes": [{"data": f"2025-{i + 1:02d}-15", "valor": 100 + i}]},
                )
            s.commit()

            # Run B: incremental — extrai só 2 docs novos.
            run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add(run_b_obj)
            s.flush()
            run_b = run_b_obj.id

            store_b = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_b)
            for i in range(5, 7):
                store_b.write(
                    "E2-extratos",
                    f"itau_extratoconta_BRL_2025{i + 1:02d}_2025{i + 1:02d}",
                    {"transacoes": [{"data": f"2025-{i + 1:02d}-15", "valor": 100 + i}]},
                )
            s.commit()

            # Simula o que E3 faz: itera list_keys → read cada um.
            keys = store_b.list_keys("E2-extratos")
            payloads = {k: store_b.read("E2-extratos", k) for k in keys}
            return keys, payloads

    raw = await db.connection()
    keys, payloads = await raw.run_sync(_do)
    assert len(keys) == 7, f"esperado 7 keys workspace-wide, veio {len(keys)}"
    assert all(
        payloads[k] is not None for k in keys
    ), "todos os reads devem retornar payload — 5 via fallback workspace, 2 do run atual"
    valores = sorted(p["transacoes"][0]["valor"] for p in payloads.values())
    assert valores == [
        100,
        101,
        102,
        103,
        104,
        105,
        106,
    ], "cumulative correctness: pipeline incremental deve enxergar transações de todas as runs"


@pytest.mark.asyncio
async def test_run_scoped_read_does_not_emit_fallback_log(db: AsyncSession):
    """Read do run atual NÃO emite log de fallback (sem ruído no caminho quente)."""
    import logging as _logging

    ws_id, run_a = await _seed_ws_and_run(db, email="no-fallback-log@test.com")
    logger = _logging.getLogger("mathoms.pipeline.artifact")
    handler = _RecordCapture()
    original_level = logger.level
    original_disabled = logger.disabled
    logger.addHandler(handler)
    logger.setLevel(_logging.INFO)
    logger.disabled = False
    try:

        def _do(sync_conn):
            from sqlalchemy.orm import Session

            with Session(sync_conn) as s:
                store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
                store.write("E2-extratos", "itau_202601", {"transacoes": []})
                s.commit()
                return store.read("E2-extratos", "itau_202601")

        raw = await db.connection()
        payload = await raw.run_sync(_do)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)
        logger.disabled = original_disabled

    assert payload is not None
    records = [
        r for r in handler.records if r.msg == "mathoms.pipeline.artifact.workspace_fallback"
    ]
    assert records == []


# =============================================================================
# ADR-291 — Fallback pinado em base_run para runs com from_stage
# =============================================================================
#
# Bug observado (dogfood A25.l2): from_stage="E4" cria run novo; E3 é
# run-scoped → read() retornava None para todas as keys que list_keys via,
# E4/E5 saíam vazios e o relatório zerava silenciosamente. Fix: store recebe
# base_run_id + base_run_fallback_stages e lê os stages upstream não
# reagendados de UM run coerente (pin exato, não latest-per-key).


@pytest.mark.asyncio
async def test_base_run_fallback_reads_pinned_run_not_latest(db: AsyncSession):
    """Fallback lê do run PINADO mesmo existindo run mais recente com a key."""
    ws_id, run_a = await _seed_ws_and_run(db, email="base-run-pin@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed)
            run_c_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add_all([run_b_obj, run_c_obj])
            s.flush()
            run_b, run_c = run_b_obj.id, run_c_obj.id

            store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
            store_a.write("E3", "itau_202601", {"transacoes": [{"origem": "run_a"}]})
            store_b = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_b)
            store_b.write("E3", "itau_202601", {"transacoes": [{"origem": "run_b"}]})
            s.commit()

            store_c = DBArtifactStore(
                s,
                workspace_id=ws_id,
                pipeline_run_id=run_c,
                base_run_id=run_a,
                base_run_fallback_stages=frozenset({"E3", "reconcile_transactions"}),
            )
            return store_c.read("E3", "itau_202601")

    raw = await db.connection()
    payload = await raw.run_sync(_do)
    assert payload == {
        "transacoes": [{"origem": "run_a"}]
    }, "fallback deve ler do base_run pinado, nunca latest-per-key (ADR-291)"


@pytest.mark.asyncio
async def test_base_run_fallback_does_not_apply_to_stage_outside_set(db: AsyncSession):
    """Stage fora de base_run_fallback_stages permanece run-scoped estrito (ADR-291)."""
    # Protege contra conta-fantasma: stage recomputado no run atual nunca
    # pode ressuscitar keys antigas via fallback.
    ws_id, run_a = await _seed_ws_and_run(db, email="base-run-outside@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add(run_b_obj)
            s.flush()
            run_b = run_b_obj.id

            store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
            store_a.write("E3", "conta_removida", {"transacoes": [{"v": 1}]})
            store_a.write("E4", "despesas", {"total_transacoes": 10})
            s.commit()

            store_b = DBArtifactStore(
                s,
                workspace_id=ws_id,
                pipeline_run_id=run_b,
                base_run_id=run_a,
                base_run_fallback_stages=frozenset({"E4", "categorize_transactions"}),
            )
            return store_b.read("E3", "conta_removida"), store_b.read("E4", "despesas")

    raw = await db.connection()
    e3_val, e4_val = await raw.run_sync(_do)
    assert e3_val is None, "E3 fora do set de fallback deve continuar run-scoped"
    assert e4_val == {"total_transacoes": 10}


@pytest.mark.asyncio
async def test_base_run_fallback_prefers_current_run_row(db: AsyncSession):
    """Row do run atual vence o fallback — stage que regrava no run (E5.N) lê o próprio output."""
    ws_id, run_a = await _seed_ws_and_run(db, email="base-run-current@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add(run_b_obj)
            s.flush()
            run_b = run_b_obj.id

            store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
            store_a.write("E5", "analise_financeira", {"versao": "base"})
            s.commit()

            store_b = DBArtifactStore(
                s,
                workspace_id=ws_id,
                pipeline_run_id=run_b,
                base_run_id=run_a,
                base_run_fallback_stages=frozenset({"E5", "analyze_finances"}),
            )
            before = store_b.read("E5", "analise_financeira")
            store_b.write("E5", "analise_financeira", {"versao": "merged_no_run_atual"})
            s.commit()
            after = store_b.read("E5", "analise_financeira")
            return before, after

    raw = await db.connection()
    before, after = await raw.run_sync(_do)
    assert before == {"versao": "base"}
    assert after == {"versao": "merged_no_run_atual"}


@pytest.mark.asyncio
async def test_e4_adapter_reads_e3_from_base_run_or_fails_loud(db: AsyncSession):
    """Reprodução do bug do dogfood A25.l2 na costura real store↔adapter (ADR-291)."""
    # Run novo (from_stage=E4) com pin lê E3 do run base; sem pin, o guard do
    # adapter aborta alto — nunca E4 vazio silencioso.
    import pytest as _pytest

    from pipeline.domain.services.e4_categorizer_adapter import E4CategorizerAdapter

    ws_id, run_a = await _seed_ws_and_run(db, email="e4-base-run@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add(run_b_obj)
            s.flush()
            run_b = run_b_obj.id

            store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
            store_a.write(
                "E3",
                "itau_extratoconta_BRL_202601_202604",
                {"transacoes": [{"data": "2026-01-05", "valor": "-12.34"}]},
            )
            s.commit()

            adapter = E4CategorizerAdapter.from_configs()

            pinned = DBArtifactStore(
                s,
                workspace_id=ws_id,
                pipeline_run_id=run_b,
                base_run_id=run_a,
                base_run_fallback_stages=frozenset({"E3", "reconcile_transactions"}),
            )
            accounts = adapter.load_reconciled_accounts(pinned)

            unpinned = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_b)
            with _pytest.raises(RuntimeError, match="0 payloads"):
                adapter.load_reconciled_accounts(unpinned)

            return accounts

    raw = await db.connection()
    accounts = await raw.run_sync(_do)
    assert len(accounts) == 1
    assert accounts[0]["transacoes"], "E3 do run base deve chegar ao E4 com transações"


def _write_versions_and_read_columns(s, ws_id, run_id) -> dict:
    store = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_id)
    store.write("E2-llm", "k1", {"banco": "x", "prompt_version": "1.3.0"})
    store.write("E2-llm", "k2", {"banco": "x"})
    s.commit()
    store.write("E2-llm", "k1", {"banco": "x", "prompt_version": "1.4.0"})
    s.commit()
    rows = (
        s.query(PipelineArtifact.artifact_key, PipelineArtifact.prompt_version)
        .filter(PipelineArtifact.pipeline_run_id == run_id)
        .all()
    )
    return {r[0]: r[1] for r in rows}


@pytest.mark.asyncio
async def test_write_lifts_prompt_version_from_payload(db: AsyncSession):
    """ADR-311 — `prompt_version` do payload vira coluna consultável; overwrite espelha o payload atual; payload sem o campo → NULL (≡ versão 0)."""
    ws_id, run_id = await _seed_ws_and_run(db, email="pv@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            return _write_versions_and_read_columns(s, ws_id, run_id)

    raw = await db.connection()
    versions = await raw.run_sync(_do)
    assert versions == {"k1": "1.4.0", "k2": None}
