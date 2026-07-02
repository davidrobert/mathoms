"""Rotação Fernet via MultiFernet (ADR-171 · W3-T04).

Janela de duas keys: encrypt sempre na primária, decrypt em qualquer uma;
``rotate_fernet_secrets`` re-encripta colunas + sentinels ADR-231 por ``kid``.
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.services.vault as vault_mod
from backend.app.core.config import settings
from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models import User, Workspace
from backend.app.services.vault import VaultService

OLD_KEY = Fernet.generate_key().decode()
NEW_KEY = Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# VaultService — MultiFernet
# ---------------------------------------------------------------------------


def test_multifernet_decrypts_old_key_ciphertext() -> None:
    old_vault = VaultService(key=OLD_KEY)
    ciphertext = old_vault.encrypt("segredo-legado")

    rotating = VaultService(key=f"{NEW_KEY},{OLD_KEY}")
    assert rotating.decrypt(ciphertext) == "segredo-legado"


def test_multifernet_encrypts_with_primary_key() -> None:
    rotating = VaultService(key=f"{NEW_KEY},{OLD_KEY}")
    ciphertext = rotating.encrypt("segredo-novo")

    assert VaultService(key=NEW_KEY).decrypt(ciphertext) == "segredo-novo"
    assert VaultService(key=OLD_KEY).decrypt(ciphertext) is None


def test_needs_rotation_semantics() -> None:
    old_ct = VaultService(key=OLD_KEY).encrypt("s")
    rotating = VaultService(key=f"{NEW_KEY},{OLD_KEY}")

    assert rotating.needs_rotation(old_ct) is True
    assert rotating.needs_rotation(rotating.encrypt("s")) is False
    # Plaintext acidental / lixo não é candidato a rotação (nunca sobrescrever).
    assert rotating.needs_rotation("nao-e-token-fernet") is False


def test_single_key_behavior_unchanged() -> None:
    vault = VaultService(key=OLD_KEY)
    assert vault.decrypt(vault.encrypt("roundtrip")) == "roundtrip"
    assert vault.decrypt("garbage") is None


def test_resolve_keys_precedence(monkeypatch) -> None:
    monkeypatch.setattr(settings, "FERNET_KEY", OLD_KEY)
    monkeypatch.setattr(settings, "FERNET_KEYS", "")
    assert vault_mod.resolve_fernet_keys() == [OLD_KEY]
    assert vault_mod.primary_fernet_key() == OLD_KEY

    monkeypatch.setattr(settings, "FERNET_KEYS", f"{NEW_KEY}, {OLD_KEY}")
    assert vault_mod.resolve_fernet_keys() == [NEW_KEY, OLD_KEY]
    assert vault_mod.primary_fernet_key() == NEW_KEY


# ---------------------------------------------------------------------------
# rotate_fernet_secrets — colunas + artifacts
# ---------------------------------------------------------------------------


@pytest.fixture()
def rotation_env(monkeypatch):
    """Sqlite in-memory + vault singleton na janela [NEW, OLD]."""
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(settings, "FERNET_KEYS", f"{NEW_KEY},{OLD_KEY}")
    monkeypatch.setattr(vault_mod, "_singleton", None)
    yield factory
    monkeypatch.setattr(vault_mod, "_singleton", None)
    engine.dispose()


def _seed_member_with_old_cpf(factory) -> str:
    from backend.app.models import FamilyMember

    old_ct = VaultService(key=OLD_KEY).encrypt("12345678909")
    session = factory()
    try:
        user = User(email="rot@test.com", hashed_password=hash_password("p"), full_name="U")
        session.add(user)
        session.flush()
        ws = Workspace(name="WS", owner_id=user.id)
        session.add(ws)
        session.flush()
        member = FamilyMember(
            workspace_id=ws.id,
            key="titular",
            full_name="Titular",
            short_name="T",
            cpf_encrypted=old_ct,
        )
        session.add(member)
        session.commit()
        return member.id
    finally:
        session.close()


def test_rotate_column_reencrypts_old_key_rows(rotation_env) -> None:
    from backend.app.models import FamilyMember
    from backend.app.tasks.rotate_fernet_secrets import _rotate_column

    member_id = _seed_member_with_old_cpf(rotation_env)
    vault = VaultService(key=f"{NEW_KEY},{OLD_KEY}")

    session = rotation_env()
    try:
        counts = _rotate_column(session, vault, FamilyMember, "cpf_encrypted", dry_run=False)
        row = session.execute(
            select(FamilyMember).where(FamilyMember.id == member_id)
        ).scalar_one()
        rotated_ct = row.cpf_encrypted
    finally:
        session.close()

    assert counts == {"rotated": 1, "skipped": 0, "failed": 0}
    assert VaultService(key=NEW_KEY).decrypt(rotated_ct) == "12345678909"

    # Idempotência: segunda passada não reescreve nada.
    session = rotation_env()
    try:
        counts2 = _rotate_column(session, vault, FamilyMember, "cpf_encrypted", dry_run=False)
    finally:
        session.close()
    assert counts2 == {"rotated": 0, "skipped": 1, "failed": 0}


def test_rotate_column_dry_run_does_not_write(rotation_env) -> None:
    from backend.app.models import FamilyMember
    from backend.app.tasks.rotate_fernet_secrets import _rotate_column

    member_id = _seed_member_with_old_cpf(rotation_env)
    vault = VaultService(key=f"{NEW_KEY},{OLD_KEY}")

    session = rotation_env()
    try:
        counts = _rotate_column(session, vault, FamilyMember, "cpf_encrypted", dry_run=True)
        row = session.execute(
            select(FamilyMember).where(FamilyMember.id == member_id)
        ).scalar_one()
        assert VaultService(key=OLD_KEY).decrypt(row.cpf_encrypted) == "12345678909"
    finally:
        session.close()
    assert counts["rotated"] == 1


def test_rotate_artifacts_reencrypts_stale_kid(rotation_env, monkeypatch) -> None:
    import hashlib

    from backend.app.models import PipelineArtifact, PipelineRun
    from backend.app.services.crypto import _key_id, is_encrypted_payload
    from backend.app.tasks.rotate_fernet_secrets import _rotate_artifacts

    old_kid = hashlib.sha256(OLD_KEY.encode()).hexdigest()[:8]
    old_ct = VaultService(key=OLD_KEY).encrypt('{"resumo": "dado"}')
    stale_sentinel = {"_encrypted": True, "v": 1, "kid": old_kid, "ct": old_ct}

    session = rotation_env()
    try:
        user = User(email="art@test.com", hashed_password=hash_password("p"), full_name="U")
        session.add(user)
        session.flush()
        ws = Workspace(name="WS", owner_id=user.id)
        session.add(ws)
        session.flush()
        run = PipelineRun(workspace_id=ws.id)
        session.add(run)
        session.flush()
        artifact = PipelineArtifact(
            workspace_id=ws.id,
            pipeline_run_id=run.id,
            stage="E5",
            artifact_key="analise_financeira",
            content_json=stale_sentinel,
        )
        session.add(artifact)
        session.commit()
        artifact_id = artifact.id
    finally:
        session.close()

    session = rotation_env()
    try:
        counts = _rotate_artifacts(session, dry_run=False)
        row = session.execute(
            select(PipelineArtifact).where(PipelineArtifact.id == artifact_id)
        ).scalar_one()
        payload = row.content_json
    finally:
        session.close()

    assert counts == {"rotated": 1, "skipped": 0, "failed": 0}
    assert is_encrypted_payload(payload)
    assert payload["kid"] == _key_id() != old_kid
    assert VaultService(key=NEW_KEY).decrypt(payload["ct"]) == '{"resumo": "dado"}'
