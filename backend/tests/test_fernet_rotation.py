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

import backend.app.services.security.vault as vault_mod
from backend.app.core.config import settings
from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models import User, Workspace
from backend.app.services.security.vault import VaultService

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


def _seed_user_ws(session) -> str:
    user = User(email="rot@test.com", hashed_password=hash_password("p"), full_name="U")
    session.add(user)
    session.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    session.add(ws)
    session.flush()
    return ws.id


def _seed_member_with_old_cpf(factory) -> str:
    from backend.app.models import FamilyMember

    old_ct = VaultService(key=OLD_KEY).encrypt("12345678909")
    session = factory()
    try:
        ws_id = _seed_user_ws(session)
        member = FamilyMember(
            workspace_id=ws_id,
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


def _run_cpf_rotation(factory, *, dry_run: bool) -> dict:
    from backend.app.models import FamilyMember
    from backend.app.tasks.rotate_fernet_secrets import _rotate_column

    vault = VaultService(key=f"{NEW_KEY},{OLD_KEY}")
    session = factory()
    try:
        return _rotate_column(session, vault, FamilyMember, "cpf_encrypted", dry_run=dry_run)
    finally:
        session.close()


def _load_member_ct(factory, member_id: str) -> str:
    from backend.app.models import FamilyMember

    session = factory()
    try:
        row = session.execute(select(FamilyMember).where(FamilyMember.id == member_id)).scalar_one()
        return row.cpf_encrypted
    finally:
        session.close()


def test_rotate_column_reencrypts_old_key_rows(rotation_env) -> None:
    member_id = _seed_member_with_old_cpf(rotation_env)

    counts = _run_cpf_rotation(rotation_env, dry_run=False)

    assert counts == {"rotated": 1, "skipped": 0, "failed": 0}
    rotated_ct = _load_member_ct(rotation_env, member_id)
    assert VaultService(key=NEW_KEY).decrypt(rotated_ct) == "12345678909"


def test_rotate_column_second_pass_is_idempotent(rotation_env) -> None:
    _seed_member_with_old_cpf(rotation_env)
    _run_cpf_rotation(rotation_env, dry_run=False)

    counts = _run_cpf_rotation(rotation_env, dry_run=False)

    assert counts == {"rotated": 0, "skipped": 1, "failed": 0}


def test_rotate_column_dry_run_does_not_write(rotation_env) -> None:
    member_id = _seed_member_with_old_cpf(rotation_env)

    counts = _run_cpf_rotation(rotation_env, dry_run=True)

    assert counts["rotated"] == 1
    ct = _load_member_ct(rotation_env, member_id)
    assert VaultService(key=OLD_KEY).decrypt(ct) == "12345678909"


def _stale_kid() -> str:
    import hashlib

    return hashlib.sha256(OLD_KEY.encode()).hexdigest()[:8]


def _stale_artifact_row(ws_id: str, run_id: str):
    from backend.app.models import PipelineArtifact

    old_ct = VaultService(key=OLD_KEY).encrypt('{"resumo": "dado"}')
    sentinel = {"_encrypted": True, "v": 1, "kid": _stale_kid(), "ct": old_ct}
    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="E5",
        artifact_key="analise_financeira",
        content_json=sentinel,
    )


def _seed_stale_artifact(factory) -> int:
    """Run + artifact com sentinel cifrado na key ANTIGA (kid defasado)."""
    from backend.app.models import PipelineRun

    session = factory()
    try:
        ws_id = _seed_user_ws(session)
        run = PipelineRun(workspace_id=ws_id)
        session.add(run)
        session.flush()
        artifact = _stale_artifact_row(ws_id, run.id)
        session.add(artifact)
        session.commit()
        return artifact.id
    finally:
        session.close()


def _rotate_and_load_artifact(factory, artifact_id: int) -> tuple[dict, dict]:
    from backend.app.models import PipelineArtifact
    from backend.app.tasks.rotate_fernet_secrets import _rotate_artifacts

    session = factory()
    try:
        counts = _rotate_artifacts(session, dry_run=False)
        row = session.execute(
            select(PipelineArtifact).where(PipelineArtifact.id == artifact_id)
        ).scalar_one()
        return counts, row.content_json
    finally:
        session.close()


def test_rotate_artifacts_reencrypts_stale_kid(rotation_env) -> None:
    from backend.app.services.security.crypto import _key_id, is_encrypted_payload

    artifact_id = _seed_stale_artifact(rotation_env)

    counts, payload = _rotate_and_load_artifact(rotation_env, artifact_id)

    assert counts == {"rotated": 1, "skipped": 0, "failed": 0}
    assert is_encrypted_payload(payload)
    assert payload["kid"] == _key_id() != _stale_kid()
    assert VaultService(key=NEW_KEY).decrypt(payload["ct"]) == '{"resumo": "dado"}'
