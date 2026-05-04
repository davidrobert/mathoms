"""Tests — ``backend.app.services.db_artifact_store.DBArtifactStore`` (Fase 2.1).

Valida:
- Round-trip write/read preserva dados exatos.
- ``list_keys`` cross-run (distinct artifact_key por workspace+stage).
- ``write`` é upsert (mesma key mesma run → UPDATE, não INSERT).
- ``delete_stage`` remove apenas artefatos da run atual.
- Sessão é injetada (store não cria/fecha sessão).
- Satisfaz os protocolos ``ArtifactStore`` e ``ReadableArtifactStore``.
"""

from __future__ import annotations

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
from backend.app.services.db_artifact_store import DBArtifactStore
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

    raw = await db.connection()
    await raw.run_sync(_do)
    rows = (
        (
            await db.execute(
                select(PipelineArtifact).where(
                    PipelineArtifact.pipeline_run_id == run_id,
                    PipelineArtifact.stage == "E3",
                    PipelineArtifact.artifact_key == "k",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].content_json == {"v": 2}


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
    """E2/E3/E4/E5 não fazem fallback — cada run é dono dos próprios outputs."""
    ws_id, run_a = await _seed_ws_and_run(db, email="cross-run-b@test.com")

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            run_b_obj = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
            s.add(run_b_obj)
            s.flush()
            run_b = run_b_obj.id

            store_a = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_a)
            store_a.write("E2-extratos", "itau_202601", {"transacoes": [{"v": 1}]})
            store_a.write("E4", "patrimonio", {"big": "data"})
            store_a.write("E5", "analise_financeira", {"bruto": 999.0})
            s.commit()

            store_b = _store_on_sync_conn(s, workspace_id=ws_id, pipeline_run_id=run_b)
            return (
                store_b.read("E2-extratos", "itau_202601"),
                store_b.read("E4", "patrimonio"),
                store_b.read("E5", "analise_financeira"),
            )

    raw = await db.connection()
    e2_val, e4_val, e5_val = await raw.run_sync(_do)
    assert e2_val is None, "E2 é run-scoped, não pode vazar entre runs"
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
    ],
)
async def test_workspace_scoped_stages_fall_back_cross_run(db: AsyncSession, stage: str):
    """Cada stage workspace-scoped resolve cross-run por workspace.

    Regressão A8: ``extract_irpf_full`` (ADR-157) escreve/lê em forma descritiva
    e não estava na frozenset, então run novo sem reprocessar IRPF perdia IRPF
    da última run silenciosamente. Inclui descritivos legacy-equivalentes para
    proteger cutover parcial F9.2 → F9.6.
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
