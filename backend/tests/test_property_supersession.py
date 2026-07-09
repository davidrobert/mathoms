"""Tests — ``DBPropertySupersessionWriter`` + inércia de superseded nos read-paths (ADR-324)."""

from __future__ import annotations

import tarfile
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import (
    AuditLog,
    PropertyIdentity,
    User,
    Workspace,
    WorkspaceMember,
    WorkspacePropertyOverride,
)
from backend.app.models.property_identity import (
    CLASSIFICATION_LOCADO,
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    CLASSIFICATION_USO_PESSOAL,
    OVERRIDE_SOURCE_FUZZY_MATCH_ACCEPTED,
    OVERRIDE_SOURCE_USER_MANUAL,
)
from backend.app.repositories.property_repository import (
    PropertyRepository,
    live_property_identities_stmt,
)
from backend.app.services.apolice_reconciliation_runner import _query_property_identities
from backend.app.services.db_property_supersession_writer import (
    DBPropertySupersessionWriter,
)
from backend.app.services.lgpd_export_service import export_user_data
from backend.app.services.real_estate_e5_integration import _load_identities


@pytest.fixture
def db_file(tmp_path):
    return tmp_path / "test_supersession.db"


@pytest.fixture
def sync_db(db_file):
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_workspace(factory) -> tuple[str, str]:
    with factory() as s:
        user = User(
            id=str(uuid.uuid4()),
            email=f"u-{uuid.uuid4().hex[:8]}@test.com",
            hashed_password="x",
            full_name="Test",
        )
        s.add(user)
        s.flush()
        ws = Workspace(id=str(uuid.uuid4()), name="Test WS", owner_id=user.id)
        s.add(ws)
        s.flush()
        s.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner"))
        s.commit()
        return ws.id, user.id


def _add_identity(session, ws_id: str, *, endereco: str = "rua exemplo 100") -> str:
    row = PropertyIdentity(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        titular_key="titular",
        codigo_rfb="12",
        endereco_canonical=endereco,
        first_seen_year=2023,
        descricao_sample=f"CASA - {endereco.upper()}",
        created_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()
    return row.id


def _add_override(session, ws_id: str, pid: str, classification: str, source: str) -> str:
    row = WorkspacePropertyOverride(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        property_id=pid,
        classification=classification,
        override_source=source,
    )
    session.add(row)
    session.flush()
    return row.id


def _get(session, pid: str) -> PropertyIdentity:
    return session.execute(select(PropertyIdentity).where(PropertyIdentity.id == pid)).scalar_one()


def _single_override(session, ws_id: str) -> WorkspacePropertyOverride:
    return session.execute(
        select(WorkspacePropertyOverride).where(WorkspacePropertyOverride.workspace_id == ws_id)
    ).scalar_one()


class TestReconcile:
    def test_marks_losers_and_keeps_lineage(self, sync_db):
        ws_id, _ = _seed_workspace(sync_db)
        with sync_db() as s:
            winner = _add_identity(s, ws_id)
            loser = _add_identity(s, ws_id, endereco="rua exemplo 100 v2")
            s.commit()
            outcome = DBPropertySupersessionWriter(s).reconcile_supersession(
                ws_id, {loser: winner, winner: winner}
            )
            assert outcome.superseded == 1 and outcome.cleared == 0
            row = _get(s, loser)
            assert row.superseded_at is not None
            assert row.superseded_by_id == winner
            assert _get(s, winner).superseded_at is None

    def test_flip_reactivates_ex_loser(self, sync_db):
        ws_id, _ = _seed_workspace(sync_db)
        with sync_db() as s:
            a = _add_identity(s, ws_id)
            b = _add_identity(s, ws_id, endereco="rua exemplo 100 b")
            s.commit()
            writer = DBPropertySupersessionWriter(s)
            writer.reconcile_supersession(ws_id, {b: a, a: a})
            outcome = writer.reconcile_supersession(ws_id, {a: b, b: b})
            assert outcome.superseded == 1 and outcome.cleared == 1
            assert _get(s, b).superseded_at is None
            assert _get(s, a).superseded_by_id == b

    def test_idempotent_second_run_is_noop(self, sync_db):
        ws_id, _ = _seed_workspace(sync_db)
        with sync_db() as s:
            winner = _add_identity(s, ws_id)
            loser = _add_identity(s, ws_id, endereco="rua exemplo 100 v2")
            s.commit()
            writer = DBPropertySupersessionWriter(s)
            first = writer.reconcile_supersession(ws_id, {loser: winner})
            second = writer.reconcile_supersession(ws_id, {loser: winner})
            assert first.changed and not second.changed

    def test_unknown_pids_are_ignored(self, sync_db):
        ws_id, _ = _seed_workspace(sync_db)
        with sync_db() as s:
            winner = _add_identity(s, ws_id)
            s.commit()
            outcome = DBPropertySupersessionWriter(s).reconcile_supersession(
                ws_id, {"nao-existe": winner, winner: "tambem-nao"}
            )
            assert not outcome.changed


class TestOverrideRepoint:
    def test_repoints_when_winner_has_none(self, sync_db):
        ws_id, _ = _seed_workspace(sync_db)
        with sync_db() as s:
            winner = _add_identity(s, ws_id)
            loser = _add_identity(s, ws_id, endereco="v2")
            _add_override(s, ws_id, loser, CLASSIFICATION_LOCADO, OVERRIDE_SOURCE_USER_MANUAL)
            s.commit()
            outcome = DBPropertySupersessionWriter(s).reconcile_supersession(ws_id, {loser: winner})
            assert outcome.overrides_repointed == 1
            ov = _single_override(s, ws_id)
            assert ov.property_id == winner
            assert ov.classification == CLASSIFICATION_LOCADO

    def test_merge_same_classification_drops_loser_without_audit(self, sync_db):
        ws_id, _ = _seed_workspace(sync_db)
        with sync_db() as s:
            winner = _add_identity(s, ws_id)
            loser = _add_identity(s, ws_id, endereco="v2")
            _add_override(s, ws_id, winner, CLASSIFICATION_LOCADO, OVERRIDE_SOURCE_USER_MANUAL)
            _add_override(s, ws_id, loser, CLASSIFICATION_LOCADO, OVERRIDE_SOURCE_USER_MANUAL)
            s.commit()
            outcome = DBPropertySupersessionWriter(s).reconcile_supersession(ws_id, {loser: winner})
            assert outcome.overrides_merged == 1
            assert _single_override(s, ws_id).property_id == winner
            assert s.execute(select(AuditLog)).scalars().all() == []

    def test_merge_conflict_higher_trust_loser_wins_with_audit(self, sync_db):
        ws_id, _ = _seed_workspace(sync_db)
        with sync_db() as s:
            winner = _add_identity(s, ws_id)
            loser = _add_identity(s, ws_id, endereco="v2")
            _add_override(
                s, ws_id, winner, CLASSIFICATION_USO_PESSOAL, OVERRIDE_SOURCE_FUZZY_MATCH_ACCEPTED
            )
            _add_override(s, ws_id, loser, CLASSIFICATION_LOCADO, OVERRIDE_SOURCE_USER_MANUAL)
            s.commit()
            DBPropertySupersessionWriter(s).reconcile_supersession(ws_id, {loser: winner})
            ov = _single_override(s, ws_id)
            assert ov.property_id == winner
            assert ov.classification == CLASSIFICATION_LOCADO
            assert ov.override_source == OVERRIDE_SOURCE_USER_MANUAL
            audit = s.execute(select(AuditLog)).scalar_one()
            assert audit.action == "property_override.supersession_merge"
            assert audit.details["kept"] == CLASSIFICATION_LOCADO

    def test_merge_conflict_tie_winner_prevails_with_audit(self, sync_db):
        ws_id, _ = _seed_workspace(sync_db)
        with sync_db() as s:
            winner = _add_identity(s, ws_id)
            loser = _add_identity(s, ws_id, endereco="v2")
            _add_override(s, ws_id, winner, CLASSIFICATION_USO_PESSOAL, OVERRIDE_SOURCE_USER_MANUAL)
            _add_override(s, ws_id, loser, CLASSIFICATION_LOCADO, OVERRIDE_SOURCE_USER_MANUAL)
            s.commit()
            DBPropertySupersessionWriter(s).reconcile_supersession(ws_id, {loser: winner})
            ov = _single_override(s, ws_id)
            assert ov.classification == CLASSIFICATION_USO_PESSOAL
            audit = s.execute(select(AuditLog)).scalar_one()
            assert audit.details["kept"] == CLASSIFICATION_USO_PESSOAL

    def test_residencia_principal_merge_respects_partial_unique(self, sync_db):
        ws_id, _ = _seed_workspace(sync_db)
        with sync_db() as s:
            winner = _add_identity(s, ws_id)
            loser = _add_identity(s, ws_id, endereco="v2")
            _add_override(
                s, ws_id, winner, CLASSIFICATION_USO_PESSOAL, OVERRIDE_SOURCE_FUZZY_MATCH_ACCEPTED
            )
            _add_override(
                s, ws_id, loser, CLASSIFICATION_RESIDENCIA_PRINCIPAL, OVERRIDE_SOURCE_USER_MANUAL
            )
            s.commit()
            DBPropertySupersessionWriter(s).reconcile_supersession(ws_id, {loser: winner})
            ov = _single_override(s, ws_id)
            assert ov.property_id == winner
            assert ov.classification == CLASSIFICATION_RESIDENCIA_PRINCIPAL


class TestSupersededInertia:
    """Row superseded é INERTE em todo read-path de negócio (espelha A26.l4)."""

    def _seed_superseded(self, sync_db):
        ws_id, user_id = _seed_workspace(sync_db)
        with sync_db() as s:
            winner = _add_identity(s, ws_id)
            loser = _add_identity(s, ws_id, endereco="v2")
            s.commit()
            DBPropertySupersessionWriter(s).reconcile_supersession(ws_id, {loser: winner})
        return ws_id, user_id, winner, loser

    def test_stmt_helper_excludes_superseded(self, sync_db):
        ws_id, _, winner, loser = self._seed_superseded(sync_db)
        with sync_db() as s:
            ids = {r.id for r in s.execute(live_property_identities_stmt(ws_id)).scalars()}
        assert ids == {winner}

    def test_real_estate_load_identities_excludes_superseded(self, sync_db):
        ws_id, _, winner, loser = self._seed_superseded(sync_db)
        with sync_db() as s:
            ids = {r.id for r in _load_identities(s, ws_id)}
        assert ids == {winner}

    def test_apolice_runner_excludes_superseded(self, sync_db):
        ws_id, _, winner, loser = self._seed_superseded(sync_db)
        with sync_db() as s:
            ids = {p["id"] for p in _query_property_identities(ws_id, db=s)}
        assert ids == {winner}

    @pytest.mark.asyncio
    async def test_async_repository_excludes_superseded(self, sync_db, db_file):
        ws_id, _, winner, loser = self._seed_superseded(sync_db)
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
        try:
            async with AsyncSession(engine) as db:
                repo = PropertyRepository(db)
                ids = {r.id for r in await repo.list_identities(ws_id)}
                assert ids == {winner}
                assert await repo.get_identity(ws_id, loser) is None
                assert (await repo.get_identity(ws_id, winner)) is not None
        finally:
            await engine.dispose()

    def test_lgpd_export_includes_superseded(self, sync_db, tmp_path):
        ws_id, user_id, winner, loser = self._seed_superseded(sync_db)
        out = tmp_path / "export.tar.gz"
        with sync_db() as s:
            export_user_data(s, user_id=user_id, output_path=out)
        contents = b""
        with tarfile.open(out, "r:gz") as tar:
            for member in tar.getmembers():
                extracted = tar.extractfile(member)
                if extracted is not None:
                    contents += extracted.read()
        assert loser.encode() in contents
