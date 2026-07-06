"""``family_member_pii_service`` — CPF fora do boundary LLM (ADR-259 §3 · A20.l15).

Backfill lê o documento ORIGINAL (nunca o output do LLM), associa CPF a
membro por proximidade de nome e cifra via Fernet. Purge remove CPF cru de
artifacts E1 legados preservando o sinal ``cpf_present``.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models import FamilyMember, PipelineArtifact, PipelineRun, User, Workspace
from backend.app.services.family_member_pii_service import (
    backfill_member_cpfs,
    cpf_near_name,
    mask_cpf_last_digits,
    purge_cpf_from_e1_artifacts,
)
from backend.app.services.vault import get_vault

# Placeholder LGPD-safe (allowlist do lint_no_real_pii).
_CPF = "123.456.789-09"
_CPF_DIGITS = "12345678909"


@pytest.fixture()
def db_factory(tmp_path):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


def _seed_member(factory, *, full_name: str = "Ricardo Alves Pereira") -> tuple[str, str]:
    session = factory()
    try:
        user = User(email="pii@test.com", hashed_password=hash_password("p"), full_name="U")
        session.add(user)
        session.flush()
        ws = Workspace(name="WS", owner_id=user.id)
        session.add(ws)
        session.flush()
        member = FamilyMember(
            workspace_id=ws.id, key="ricardo", full_name=full_name, short_name="Ricardo"
        )
        session.add(member)
        session.commit()
        return ws.id, member.id
    finally:
        session.close()


def _write_irpf_doc(tenant_root, text: str) -> None:
    d = tenant_root / "data" / "income_tax_br"
    d.mkdir(parents=True)
    (d / "irpfdeclaracao_2024.txt").write_text(text)


# ---------------------------------------------------------------------------
# mask_cpf_last_digits (ADR-259 §4)
# ---------------------------------------------------------------------------


def test_mask_cpf_last_digits_canonical_format() -> None:
    assert mask_cpf_last_digits(_CPF) == "***.***.789-09"


def test_mask_cpf_last_digits_accepts_plain_digits() -> None:
    assert mask_cpf_last_digits(_CPF_DIGITS) == "***.***.789-09"


def test_mask_cpf_last_digits_rejects_wrong_length() -> None:
    with pytest.raises(ValueError):
        mask_cpf_last_digits("123.456.789")


# ---------------------------------------------------------------------------
# cpf_near_name
# ---------------------------------------------------------------------------


def test_cpf_near_name_janela_e_acentos() -> None:
    text = f"DECLARAÇÃO IRPF\nNome: RICARDO ALVES PEREIRA\nCPF: {_CPF}\nAno-base 2024"
    assert cpf_near_name(text, "Ricardo Alves Pereira") == _CPF_DIGITS


def test_cpf_near_name_ambiguidade_degrada() -> None:
    text = f"RICARDO ALVES PEREIRA CPF {_CPF} conjuge CPF 000.000.000-00"
    assert cpf_near_name(text, "Ricardo Alves Pereira") is None


def test_cpf_near_name_nome_ausente() -> None:
    assert cpf_near_name(f"CPF {_CPF}", "Outro Nome") is None


# ---------------------------------------------------------------------------
# backfill
# ---------------------------------------------------------------------------


def test_backfill_preenche_cpf_encrypted(db_factory, tmp_path, monkeypatch) -> None:
    ws_id, member_id = _seed_member(db_factory)
    _write_irpf_doc(tmp_path, f"Contribuinte RICARDO ALVES PEREIRA\nCPF: {_CPF}")

    session = db_factory()
    try:
        counts = backfill_member_cpfs(
            session, workspace_id=ws_id, tenant_root=tmp_path, dry_run=False
        )
        row = session.execute(select(FamilyMember).where(FamilyMember.id == member_id)).scalar_one()
        assert counts["filled"] == 1
        assert row.cpf_encrypted is not None
        assert get_vault().decrypt(row.cpf_encrypted) == _CPF_DIGITS
    finally:
        session.close()


def test_backfill_dry_run_nao_escreve(db_factory, tmp_path) -> None:
    ws_id, member_id = _seed_member(db_factory)
    _write_irpf_doc(tmp_path, f"RICARDO ALVES PEREIRA CPF {_CPF}")

    session = db_factory()
    try:
        counts = backfill_member_cpfs(
            session, workspace_id=ws_id, tenant_root=tmp_path, dry_run=True
        )
        row = session.execute(select(FamilyMember).where(FamilyMember.id == member_id)).scalar_one()
        assert counts["filled"] == 1
        assert row.cpf_encrypted is None
    finally:
        session.close()


def test_backfill_nunca_sobrescreve_cpf_existente(db_factory, tmp_path) -> None:
    ws_id, member_id = _seed_member(db_factory)
    _write_irpf_doc(tmp_path, f"RICARDO ALVES PEREIRA CPF {_CPF}")
    existing = get_vault().encrypt("00000000000")
    session = db_factory()
    try:
        session.execute(
            select(FamilyMember).where(FamilyMember.id == member_id)
        ).scalar_one().cpf_encrypted = existing
        session.commit()

        counts = backfill_member_cpfs(
            session, workspace_id=ws_id, tenant_root=tmp_path, dry_run=False
        )
        assert counts == {"dry_run": False, "candidates": 0, "filled": 0, "unmatched": 0}
    finally:
        session.close()


def test_backfill_sem_docs_conta_unmatched(db_factory, tmp_path) -> None:
    ws_id, _ = _seed_member(db_factory)
    session = db_factory()
    try:
        counts = backfill_member_cpfs(
            session, workspace_id=ws_id, tenant_root=tmp_path, dry_run=False
        )
        assert counts["unmatched"] == 1 and counts["filled"] == 0
    finally:
        session.close()


# ---------------------------------------------------------------------------
# purge de artifacts E1 legados
# ---------------------------------------------------------------------------


def _seed_e1_artifact(session, ws_id: str, *, stage: str, membros: dict) -> None:
    run = PipelineRun(workspace_id=ws_id)
    session.add(run)
    session.flush()
    session.add(
        PipelineArtifact(
            workspace_id=ws_id,
            pipeline_run_id=run.id,
            stage=stage,
            artifact_key="members",
            content_json={"membros": membros},
        )
    )
    session.commit()


_MEMBROS_COM_CPF = {
    "ricardo": {"nome_completo": "Ricardo", "cpf": _CPF_DIGITS},
    "claudia": {"nome_completo": "Claudia"},
}


def test_purge_remove_cpf_e_preserva_sinal(db_factory) -> None:
    ws_id, _ = _seed_member(db_factory)
    session = db_factory()
    try:
        _seed_e1_artifact(session, ws_id, stage="E1", membros=_MEMBROS_COM_CPF)
        counts = purge_cpf_from_e1_artifacts(session, workspace_id=ws_id, dry_run=False)
        payload = session.execute(select(PipelineArtifact.content_json)).scalar_one()
    finally:
        session.close()

    assert counts["purged"] == 1
    ricardo = payload["membros"]["ricardo"]
    assert "cpf" not in ricardo and ricardo["cpf_present"] is True
    assert "cpf_present" not in payload["membros"]["claudia"]


def test_purge_dry_run_nao_escreve(db_factory) -> None:
    ws_id, _ = _seed_member(db_factory)
    session = db_factory()
    try:
        _seed_e1_artifact(
            session, ws_id, stage="extract_members", membros={"r": {"cpf": _CPF_DIGITS}}
        )
        counts = purge_cpf_from_e1_artifacts(session, workspace_id=ws_id, dry_run=True)
        payload = session.execute(select(PipelineArtifact.content_json)).scalar_one()
    finally:
        session.close()

    assert counts["purged"] == 1
    assert payload["membros"]["r"]["cpf"] == _CPF_DIGITS
