"""ADR-211 lane 1 — wire-up de ``llm_config.json`` em ``build_config_overrides_from_db``."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.llm_config import LLMConfig
from backend.app.services.config_materializer import (
    _vault,
    prepare_pipeline_config_dir,
    serialize_llm_config,
)
from backend.app.services.pipeline.pipeline_adapter import build_config_overrides_from_db


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "test_pa_llm.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


WS = "ws-llm-adr211"


def _seed_llm_config(session_factory, **kw) -> None:
    """Seed LLMConfig row com Fernet vault encrypt."""
    now = datetime.now(timezone.utc)
    row = LLMConfig(
        id=str(uuid.uuid4()),
        workspace_id=kw.get("workspace_id", WS),
        provider=kw.get("provider", "anthropic"),
        api_key_encrypted=_vault.encrypt(kw.get("api_key", "sk-ant-fixture-test-key")),
        model_name=kw.get("model_name", "claude-sonnet-4-20250514"),
        max_tokens=kw.get("max_tokens", 8192),
        temperature=kw.get("temperature", 0.2),
        created_at=now,
        updated_at=now,
    )
    with session_factory() as s:
        s.add(row)
        s.commit()


def test_build_overrides_includes_llm_config_when_row_exists(sync_db):
    """Positive: row no DB → key presente em overrides com payload decifrado."""
    _seed_llm_config(sync_db)
    with sync_db() as s:
        overrides = build_config_overrides_from_db(WS, db=s)
    assert "llm_config.json" in overrides
    payload = overrides["llm_config.json"]
    assert payload["provider"] == "anthropic"
    assert payload["api_key"] == "sk-ant-fixture-test-key"
    assert payload["model_name"] == "claude-sonnet-4-20250514"
    assert payload["max_tokens"] == 8192
    assert payload["temperature"] == 0.2


def test_build_overrides_omits_llm_config_without_row(sync_db):
    """Negative: workspace sem LLMConfig → key ausente (não None)."""
    with sync_db() as s:
        overrides = build_config_overrides_from_db(WS, db=s)
    assert "llm_config.json" not in overrides


def _read_via_disk(sync_db, tmp_path) -> dict:
    tenant_root = tmp_path / "tenant_parity"
    tenant_root.mkdir()
    with sync_db() as s:
        config_dir = prepare_pipeline_config_dir(WS, tenant_root, db=s)
    return json.loads((config_dir / "llm_config.json").read_text(encoding="utf-8"))


def test_overrides_payload_matches_disk_write_parity(sync_db, tmp_path):
    """Cutover dual-write — overrides payload é idêntico ao escrito em disco."""
    _seed_llm_config(sync_db, api_key="sk-parity-test", model_name="claude-haiku-4-5")
    with sync_db() as s:
        overrides_payload = build_config_overrides_from_db(WS, db=s)["llm_config.json"]
        serializer_payload = serialize_llm_config(WS, db=s)
    disk_payload = _read_via_disk(sync_db, tmp_path)
    assert overrides_payload == serializer_payload
    assert overrides_payload == disk_payload
    assert overrides_payload["api_key"] == "sk-parity-test"


def test_overrides_decrypt_uses_vault(sync_db):
    """api_key chega decifrada (Fernet → plaintext) — não passa o ciphertext."""
    _seed_llm_config(sync_db, api_key="sk-decrypt-test")
    with sync_db() as s:
        payload = build_config_overrides_from_db(WS, db=s)["llm_config.json"]
    assert payload["api_key"] == "sk-decrypt-test"
    # Sanity: não é o ciphertext (Fernet começa com "gAAAA...").
    assert not payload["api_key"].startswith("gAAAA")
