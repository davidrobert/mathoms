"""Tests — ``dev/dedup_property_identity.py`` (ADR-225 §3).

Cobre os 3 passes idempotentes do backfill script: passe 0
(re-canonicalize NULL via cascade), passe 1 (strict dedup),
passe 3 (cross-codigo_rfb dedup com detecção de conflito).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import PropertyIdentity, User, Workspace
from dev.dedup_property_identity import _build_report


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "test_dedup.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_workspace(factory) -> Workspace:
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
        s.commit()
        s.refresh(ws)
        return ws


def _build_property(ws: Workspace, **kw) -> PropertyIdentity:
    return PropertyIdentity(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        titular_key=kw.get("titular_key", "titular"),
        codigo_rfb=kw.get("codigo_rfb", "12"),
        endereco_canonical=kw.get("endereco_canonical"),
        first_seen_year=2023,
        descricao_sample=kw.get("descricao", "X"),
        low_confidence=kw.get("low_confidence", False),
        created_at=datetime.now(timezone.utc),
    )


def _seed_property(factory, ws: Workspace, **kw) -> PropertyIdentity:
    with factory() as s:
        prop = _build_property(ws, **kw)
        s.add(prop)
        s.commit()
        s.refresh(prop)
        return prop


def _seed_5at5_scenario(factory, ws):
    """6 rows que reproduzem subset do problema 5@5.com."""
    for _ in range(3):
        _seed_property(
            factory,
            ws,
            codigo_rfb="12",
            endereco_canonical=None,
            low_confidence=True,
            descricao="CASA Leonardo da Vinci 2707, QUADRA 33 - Matrícula 20462",
        )
    for code in ("11", "11", "01"):
        _seed_property(factory, ws, codigo_rfb=code, endereco_canonical="alberto augusto alves 320")


class TestPasse0Recanonicalize:
    """Passe 0: re-canonicaliza rows NULL via cascata atual (ADR-225 §1)."""

    def test_recanonicalizes_matricula_only_description(self, sync_db):
        ws = _seed_workspace(sync_db)
        _seed_property(
            sync_db,
            ws,
            codigo_rfb="12",
            endereco_canonical=None,
            descricao=(
                "CASA - LEONARDO DA VINCI 2707, QUADRA 33 LOTE 27, "
                "JABAQUARA, SAO PAULO/SP - Matrícula 20462"
            ),
            low_confidence=True,
        )
        with sync_db() as session:
            report = _build_report(session, ws.id, dry_run=False)
            session.commit()
            assert len(report["pass_0_recanonicalized"]) == 1
            assert report["pass_0_recanonicalized"][0]["new_canonical"] == "mat:20462"

    def test_dry_run_does_not_modify(self, sync_db):
        ws = _seed_workspace(sync_db)
        row = _seed_property(
            sync_db,
            ws,
            endereco_canonical=None,
            descricao="Apartamento com Matrícula 98765 sem outras infos",
            low_confidence=True,
        )
        with sync_db() as session:
            report = _build_report(session, ws.id, dry_run=True)
            assert len(report["pass_0_recanonicalized"]) == 1
            # Verifica que a row não foi salva.
            session.expire_all()
            from backend.app.models import PropertyIdentity

            reloaded = session.get(PropertyIdentity, row.id)
            assert reloaded.endereco_canonical is None
            assert reloaded.low_confidence is True

    def test_skips_rows_without_extractable_signal(self, sync_db):
        ws = _seed_workspace(sync_db)
        _seed_property(
            sync_db,
            ws,
            endereco_canonical=None,
            descricao="Apartamento sem qualquer identificador útil",
            low_confidence=True,
        )
        with sync_db() as session:
            report = _build_report(session, ws.id, dry_run=False)
            assert report["pass_0_recanonicalized"] == []


class TestPasse1StrictDedup:
    """Passe 1 (legado): funde rows com mesmo (codigo_rfb, endereco_canonical)."""

    def test_merges_duplicates_with_same_strict_key(self, sync_db):
        ws = _seed_workspace(sync_db)
        _seed_property(sync_db, ws, codigo_rfb="12", endereco_canonical="paulista 1500")
        _seed_property(sync_db, ws, codigo_rfb="12", endereco_canonical="paulista 1500")
        _seed_property(sync_db, ws, codigo_rfb="12", endereco_canonical="paulista 1500")
        with sync_db() as session:
            report = _build_report(session, ws.id, dry_run=False)
            session.commit()
            assert len(report["pass_1_strict_merged"]) == 1
            assert len(report["pass_1_strict_merged"][0]["dupes_dropped"]) == 2

    def test_does_not_merge_different_canonical(self, sync_db):
        ws = _seed_workspace(sync_db)
        _seed_property(sync_db, ws, codigo_rfb="12", endereco_canonical="paulista 1500")
        _seed_property(sync_db, ws, codigo_rfb="12", endereco_canonical="ipiranga 200")
        with sync_db() as session:
            report = _build_report(session, ws.id, dry_run=False)
            assert report["pass_1_strict_merged"] == []


class TestPasse3CrossCodigoRFB:
    """Passe 3 (ADR-225 §3): funde cross-codigo_rfb com 1 lado genérico."""

    def test_merges_generic_01_into_specific_11(self, sync_db):
        ws = _seed_workspace(sync_db)
        _seed_property(sync_db, ws, codigo_rfb="11", endereco_canonical="joao dias 2192")
        _seed_property(sync_db, ws, codigo_rfb="01", endereco_canonical="joao dias 2192")
        with sync_db() as session:
            report = _build_report(session, ws.id, dry_run=False)
            session.commit()
            assert len(report["pass_3_cross_codigo_merged"]) == 1
            entry = report["pass_3_cross_codigo_merged"][0]
            assert sorted(entry["codigos_fundidos"]) == ["01", "11"]
            assert len(entry["dupes_dropped"]) == 1

    def test_does_not_merge_two_specific_codigos(self, sync_db):
        """11 (Apto) + 12 (Casa) no mesmo endereço: lote com casa + apto? Não funde."""
        ws = _seed_workspace(sync_db)
        _seed_property(sync_db, ws, codigo_rfb="11", endereco_canonical="lote 33")
        _seed_property(sync_db, ws, codigo_rfb="12", endereco_canonical="lote 33")
        with sync_db() as session:
            report = _build_report(session, ws.id, dry_run=False)
            assert report["pass_3_cross_codigo_merged"] == []
            assert len(report["pass_3_conflicts_need_human"]) == 1
            conflict = report["pass_3_conflicts_need_human"][0]
            assert sorted(conflict["codigos_specificos_divergentes"]) == ["11", "12"]

    def test_idempotent_rerun(self, sync_db):
        """Rerun após apply produz reporte vazio."""
        ws = _seed_workspace(sync_db)
        _seed_property(sync_db, ws, codigo_rfb="11", endereco_canonical="paulista 1500")
        _seed_property(sync_db, ws, codigo_rfb="01", endereco_canonical="paulista 1500")
        with sync_db() as session:
            _build_report(session, ws.id, dry_run=False)
            session.commit()
        with sync_db() as session:
            report2 = _build_report(session, ws.id, dry_run=False)
            assert report2["pass_3_cross_codigo_merged"] == []
            assert report2["pass_1_strict_merged"] == []


class TestEnd2End5at5LikeScenario:
    """Reproduz subset do cenário 5@5.com: 14 rows → ~3-4 esperadas após dedup."""

    def test_merges_typical_5at5_pattern(self, sync_db):
        from sqlalchemy import func, select

        ws = _seed_workspace(sync_db)
        _seed_5at5_scenario(sync_db, ws)
        with sync_db() as session:
            report = _build_report(session, ws.id, dry_run=False)
            session.commit()
            assert len(report["pass_0_recanonicalized"]) == 3
            assert len(report["pass_1_strict_merged"]) == 2
            assert len(report["pass_3_cross_codigo_merged"]) == 1
            assert report["pass_3_conflicts_need_human"] == []
        with sync_db() as session:
            count = session.execute(
                select(func.count())
                .select_from(PropertyIdentity)
                .where(PropertyIdentity.workspace_id == ws.id)
            ).scalar()
            assert count == 2
