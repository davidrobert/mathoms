"""Tests — backend.app.services.crypto (ADR-231)."""

from __future__ import annotations

import json

import pytest
from cryptography.fernet import Fernet

from backend.app.core.config import settings
from backend.app.services import crypto


def test_encrypt_decrypt_roundtrip():
    payload = {"cpf": "000.000.000-00", "nome": "Foo Bar", "saldo": "1234.56"}
    sentinel = crypto.encrypt_artifact_payload(payload)

    assert sentinel["_encrypted"] is True
    assert sentinel["v"] == 1
    assert isinstance(sentinel["kid"], str) and len(sentinel["kid"]) == 8
    assert isinstance(sentinel["ct"], str) and len(sentinel["ct"]) > 0

    restored = crypto.decrypt_artifact_payload(sentinel)
    assert restored == payload


def test_is_encrypted_payload_detects_sentinel():
    assert crypto.is_encrypted_payload({"_encrypted": True, "v": 1, "kid": "a", "ct": "b"})
    assert not crypto.is_encrypted_payload({"foo": "bar"})
    assert not crypto.is_encrypted_payload({"_encrypted": False})
    assert not crypto.is_encrypted_payload([])
    assert not crypto.is_encrypted_payload(None)


def test_encrypt_idempotent_skips_sentinel():
    payload = {"foo": "bar"}
    once = crypto.encrypt_artifact_payload(payload)
    twice = crypto.encrypt_artifact_payload(once)
    assert twice == once


def test_decrypt_plaintext_passthrough():
    payload = {"foo": "bar"}
    assert crypto.decrypt_artifact_payload(payload) == payload


def test_kid_is_stable_for_same_key():
    payload = {"x": 1}
    a = crypto.encrypt_artifact_payload(payload)
    b = crypto.encrypt_artifact_payload(payload)
    assert a["kid"] == b["kid"]


def test_kid_changes_when_key_changes(monkeypatch):
    original_kid = crypto._key_id()
    new_key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "FERNET_KEY", new_key)
    assert crypto._key_id() != original_kid


def test_decrypt_raises_when_ciphertext_wrong_key(monkeypatch):
    payload = {"secret": "abc"}
    sentinel = crypto.encrypt_artifact_payload(payload)

    new_key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "FERNET_KEY", new_key)
    import backend.app.services.vault as vault_mod

    monkeypatch.setattr(vault_mod, "_singleton", None)

    with pytest.raises(crypto.ArtifactDecryptError):
        crypto.decrypt_artifact_payload(sentinel)


def test_decrypt_invalid_sentinel_shape():
    with pytest.raises(crypto.ArtifactDecryptError):
        crypto.decrypt_artifact_payload({"_encrypted": True, "v": 1})


def test_should_encrypt_writes_reads_setting(monkeypatch):
    monkeypatch.setattr(settings, "ENCRYPT_PIPELINE_ARTIFACTS", True)
    assert crypto.should_encrypt_writes() is True
    monkeypatch.setattr(settings, "ENCRYPT_PIPELINE_ARTIFACTS", False)
    assert crypto.should_encrypt_writes() is False


def test_encrypt_preserves_unicode_brl_chars():
    payload = {"descricao": "Pagamento de aluguel R$ 1.234,56 — pendência"}
    sentinel = crypto.encrypt_artifact_payload(payload)
    assert crypto.decrypt_artifact_payload(sentinel) == payload


def test_ciphertext_is_decodable_as_string():
    payload = {"foo": ["bar", 1, None, True]}
    sentinel = crypto.encrypt_artifact_payload(payload)
    # ct should be valid JSON-serializable string
    json.dumps(sentinel)
