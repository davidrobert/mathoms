"""Fernet encrypt/decrypt helpers para pipeline_artifacts.content_json (ADR-231)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from backend.app.core.config import settings
from backend.app.services.vault import get_vault

logger = logging.getLogger("mathoms.crypto")

SENTINEL_KEY = "_encrypted"
SENTINEL_VERSION = 1


class ArtifactDecryptError(RuntimeError):
    """Falha de decrypt em sentinel — chave perdida ou rotação incompleta (P0)."""


def _key_id() -> str:
    key = (
        settings.FERNET_KEY.encode()
        if isinstance(settings.FERNET_KEY, str)
        else settings.FERNET_KEY
    )
    return hashlib.sha256(key).hexdigest()[:8]


def is_encrypted_payload(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get(SENTINEL_KEY) is True


def _wrap_sentinel(ciphertext: str) -> dict:
    return {SENTINEL_KEY: True, "v": SENTINEL_VERSION, "kid": _key_id(), "ct": ciphertext}


def encrypt_artifact_payload(payload: dict) -> dict:
    """Encripta ``payload`` e retorna sentinel dict. Idempotente em sentinel."""
    if is_encrypted_payload(payload):
        return payload
    try:
        ciphertext = get_vault().encrypt(json.dumps(payload, ensure_ascii=False, sort_keys=False))
    except Exception:
        logger.exception("mathoms.crypto.artifact_encrypt_failed")
        raise
    return _wrap_sentinel(ciphertext)


def _raise_decrypt_error(payload: dict, reason: str) -> None:
    kid = payload.get("kid", "<unknown>")
    logger.error(
        "mathoms.crypto.artifact_decrypt_failed",
        extra={"kid_stored": kid, "kid_current": _key_id()},
    )
    raise ArtifactDecryptError(f"{reason} (kid_stored={kid}, kid_current={_key_id()})")


def decrypt_artifact_payload(payload: dict) -> dict:
    """Decripta sentinel e retorna payload de domínio. Raise ``ArtifactDecryptError`` em falha."""
    if not is_encrypted_payload(payload):
        return payload
    ciphertext = payload.get("ct")
    if not isinstance(ciphertext, str):
        _raise_decrypt_error(
            payload, f"sentinel sem campo 'ct' string: keys={sorted(payload.keys())!r}"
        )
    plaintext = get_vault().decrypt(ciphertext)  # type: ignore[arg-type]
    if plaintext is None:
        _raise_decrypt_error(
            payload, f"Fernet decrypt retornou None para sentinel v={payload.get('v')}"
        )
    try:
        return json.loads(plaintext)
    except json.JSONDecodeError as exc:
        raise ArtifactDecryptError(f"plaintext decriptado não é JSON válido: {exc}") from exc


def should_encrypt_writes() -> bool:
    return bool(settings.ENCRYPT_PIPELINE_ARTIFACTS)
