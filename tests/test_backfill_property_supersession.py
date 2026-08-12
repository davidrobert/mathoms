"""Tests — ``dev/backfill_property_supersession.py`` (ADR-324).

Fixtures 100% sintéticas: endereço fictício, sem CPF, sem valor real.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import PropertyIdentity, User, Workspace
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun
from dev.backfill_property_supersession import (
    BaselineUnreadableError,
    _process,
    _synthetic_entries,
)

_TEST_FERNET_KEY = "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA="
_DESCRICAO = "Rua Exemplo, 100"


@pytest.fixture(autouse=True)
def fernet_key(monkeypatch):
    """Key sintética + vault zerado: o backfill não pode mais injetar key falsa sozinho."""
    from backend.app.core.config import settings
    from backend.app.services.security import vault

    monkeypatch.setattr(settings, "FERNET_KEY", _TEST_FERNET_KEY)
    monkeypatch.setattr(settings, "FERNET_KEYS", "")
    monkeypatch.setattr(vault, "_singleton", None)


@pytest.fixture
def db_file(tmp_path, monkeypatch):
    path = tmp_path / "test_backfill_supersession.db"
    engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(engine)
    engine.dispose()
    monkeypatch.setenv("MATHOMS_DATABASE_URL_SYNC", f"sqlite:///{path}")
    return path


def _session_factory(db_file):
    return sessionmaker(bind=create_engine(f"sqlite:///{db_file}", future=True), future=True)


def _add_pair(s, ws_id: str) -> tuple[str, str]:
    specific, generic = str(uuid.uuid4()), str(uuid.uuid4())
    for pid, codigo in ((specific, "12"), (generic, "01")):
        s.add(
            PropertyIdentity(
                id=pid,
                workspace_id=ws_id,
                titular_key="titular",
                codigo_rfb=codigo,
                endereco_canonical="exemplo 100",
                first_seen_year=2023,
                descricao_sample=_DESCRICAO,
                created_at=datetime.now(timezone.utc),
            )
        )
    return specific, generic


def _seed(db_file) -> tuple[str, str, str]:
    """Workspace com par cross-código (ADR-246): '12' específico vence '01' genérico."""
    factory = _session_factory(db_file)
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
        specific, generic = _add_pair(s, ws.id)
        s.commit()
        return ws.id, specific, generic


def _baseline_payload(pids: list[str]) -> dict:
    return {
        "imoveis_consolidados": [
            {"property_id": pid, "valores_31_12": {"2024": 1000.0}} for pid in pids
        ]
    }


def _seed_baseline(db_file, ws_id: str, payload: dict, *, encrypted: bool = True) -> None:
    from backend.app.services.security.crypto import encrypt_artifact_payload

    factory = _session_factory(db_file)
    with factory() as s:
        run = PipelineRun(id=str(uuid.uuid4()), workspace_id=ws_id)
        s.add(run)
        s.flush()
        s.add(
            PipelineArtifact(
                workspace_id=ws_id,
                pipeline_run_id=run.id,
                stage="consolidate_baseline",
                artifact_key="baseline_patrimonial",
                content_json=encrypt_artifact_payload(payload) if encrypted else payload,
            )
        )
        s.commit()


def test_encrypted_baseline_is_decrypted_and_anchors_the_winner(db_file):
    ws_id, specific, generic = _seed(db_file)
    _seed_baseline(db_file, ws_id, _baseline_payload([specific]))
    report = _process(ws_id, dry_run=True)
    assert report["baseline_found"] is True
    assert report["to_supersede"] == [generic]
    assert report["losers"] == {generic: specific}
    assert report["aborted_groups"] == []


def test_row_report_exposes_recomputed_canonical(db_file):
    ws_id, specific, _ = _seed(db_file)
    _seed_baseline(db_file, ws_id, _baseline_payload([specific]))
    rows = _process(ws_id, dry_run=True)["identities"]
    assert {r["canonical_recomputed"] for r in rows} == {"exemplo 100"}
    assert [r["in_baseline"] for r in rows if r["pid"] == specific[:8]] == [True]


def test_hard_fail_when_decrypted_payload_lacks_imoveis_consolidados(db_file):
    ws_id, _, _ = _seed(db_file)
    _seed_baseline(db_file, ws_id, {"outra_chave": []})
    with pytest.raises(BaselineUnreadableError) as exc:
        _process(ws_id, dry_run=True)
    assert "imoveis_consolidados" in str(exc.value)
    assert "outra_chave" in str(exc.value)


def test_hard_fail_when_baseline_is_an_undecryptable_envelope(db_file):
    """Sem `_encrypted: True` o envelope passa cru — é o shape que o bug B1 produzia."""
    ws_id, _, _ = _seed(db_file)
    _seed_baseline(db_file, ws_id, {"v": 1, "kid": "abc12345", "ct": "x"}, encrypted=False)
    with pytest.raises(BaselineUnreadableError):
        _process(ws_id, dry_run=True)


@pytest.mark.parametrize("anchors", ["none", "both"])
def test_group_aborts_without_exactly_one_baseline_anchor(db_file, anchors):
    ws_id, specific, generic = _seed(db_file)
    pids = [] if anchors == "none" else [specific, generic]
    _seed_baseline(db_file, ws_id, _baseline_payload(pids))
    report = _process(ws_id, dry_run=True)
    assert report["to_supersede"] == []
    assert len(report["aborted_groups"]) == 1
    expected = "0" if anchors == "none" else "2"
    assert report["aborted_groups"][0]["reason"].endswith(expected)


def test_missing_baseline_warns_and_elects_nobody(db_file):
    ws_id, _, _ = _seed(db_file)
    report = _process(ws_id, dry_run=True)
    assert report["baseline_found"] is False
    assert report["to_supersede"] == []
    assert len(report["aborted_groups"]) == 1


def test_dry_run_does_not_write(db_file):
    ws_id, specific, _ = _seed(db_file)
    _seed_baseline(db_file, ws_id, _baseline_payload([specific]))
    _process(ws_id, dry_run=True)
    factory = _session_factory(db_file)
    with factory() as s:
        rows = s.execute(select(PropertyIdentity)).scalars().all()
        assert all(r.superseded_at is None for r in rows)


def test_apply_is_idempotent(db_file):
    ws_id, specific, generic = _seed(db_file)
    _seed_baseline(db_file, ws_id, _baseline_payload([specific]))
    first = _process(ws_id, dry_run=False)
    assert first["applied"]["superseded"] == 1
    second = _process(ws_id, dry_run=False)
    assert second["applied"]["superseded"] == 0
    assert second["to_supersede"] == []
    factory = _session_factory(db_file)
    with factory() as s:
        row = s.execute(select(PropertyIdentity).where(PropertyIdentity.id == generic)).scalar_one()
        assert row.superseded_at is not None
        assert row.superseded_by_id == specific


def test_synthetic_entries_map_baseline_values():
    class _Ident:
        def __init__(self, pid):
            self.id = pid
            self.codigo_rfb = "12"
            self.endereco_canonical = "exemplo 100"
            self.descricao_sample = _DESCRICAO

    baseline = _baseline_payload(["a"])
    entries = _synthetic_entries([_Ident("a"), _Ident("b")], baseline)
    assert entries[0]["valores_31_12"] == {"2024": 1000.0}
    assert entries[1]["valores_31_12"] == {}


# A coluna guarda a forma da era em que a row nasceu; agrupar por ela deixaria
# cada era num grupo isolado e o sweep não colapsaria nada (ADR-385 §Tabela de eras).
_DESCRICAO_COM_MATRICULA = "CASA - VIA EXEMPLO 100, BAIRRO EXEMPLO - Matricula 99999"


def _seed_workspace_vazio(session) -> str:
    user = User(
        id=str(uuid.uuid4()),
        email=f"u-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="x",
        full_name="Test",
    )
    session.add(user)
    session.flush()
    ws = Workspace(id=str(uuid.uuid4()), name="Test WS", owner_id=user.id)
    session.add(ws)
    session.flush()
    return ws.id


def _seed_cluster_de_eras(db_file, formas: tuple) -> list:
    with _session_factory(db_file)() as s:
        ws_id = _seed_workspace_vazio(s)
        for stored in formas:
            s.add(
                PropertyIdentity(
                    id=str(uuid.uuid4()),
                    workspace_id=ws_id,
                    titular_key="titular",
                    codigo_rfb="12",
                    endereco_canonical=stored,
                    first_seen_year=2023,
                    descricao_sample=_DESCRICAO_COM_MATRICULA,
                    created_at=datetime.now(timezone.utc),
                )
            )
        s.commit()
        return list(s.query(PropertyIdentity).filter_by(workspace_id=ws_id).all())


def test_cluster_de_eras_agrupa_pela_chave_recomputada(db_file):
    from dev.backfill_property_supersession import _synthetic_entries

    identities = _seed_cluster_de_eras(db_file, ("8 0", None, "mat:99999"))
    entries = _synthetic_entries(identities, None)
    assert {e["endereco_canonical"] for e in entries} == {"mat:99999"}
