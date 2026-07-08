"""Hidratação canônica do WorkspaceContext (run_context_factory).

Gate de paridade dos três executores (Celery/HTTP/CLI): o contexto sai com
config_store, os 3 resolvers DB, imoveis_no_if e llm_call_hooks não-None —
o gap que a ADR-303 §Escopo deferido registrou e este módulo fecha.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401 — registra tabelas no metadata
from backend.app.core.database import Base
from backend.app.services.pipeline.run_context_factory import build_hydrated_context


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


def _build(tmp_path, session_factory, **kwargs):
    return build_hydrated_context(
        ws_id="ws-factory",
        tenant_root=tmp_path,
        run_id="run-factory",
        session_factory=lambda: session_factory(),
        **kwargs,
    )


def test_context_fully_hydrated(tmp_path, session_factory):
    hydrated = _build(tmp_path, session_factory)
    ctx = hydrated.ctx
    try:
        assert ctx.config_store is not None
        assert ctx.property_identity_resolver is not None
        assert ctx.economic_assumptions_resolver is not None
        assert ctx.property_overrides_resolver is not None
        assert ctx.institution_catalog_provider is not None
        assert ctx.llm_call_hooks is not None
        assert ctx.imoveis_no_if is True, "default ADR-222 quando workspace ausente"
        assert ctx.workspace_id == "ws-factory"
        assert ctx.pipeline_run_id == "run-factory"
        assert isinstance(ctx.config_overrides, dict)
    finally:
        hydrated.close()


def test_imoveis_no_if_read_from_workspace_row(tmp_path, session_factory):
    from backend.app.models.workspace import Workspace

    session = session_factory()
    session.add(Workspace(id="ws-factory", name="F", owner_id="u-1", imoveis_no_if=False))
    session.commit()
    session.close()

    hydrated = _build(tmp_path, session_factory)
    try:
        assert hydrated.ctx.imoveis_no_if is False
    finally:
        hydrated.close()


def test_incremental_flags_and_config_dir_precedence(tmp_path, session_factory):
    explicit_cfg = tmp_path / "cfg-explicito"
    explicit_cfg.mkdir()
    hydrated = _build(
        tmp_path,
        session_factory,
        config_dir=explicit_cfg,
        incremental=True,
        incremental_doc_paths=["inbox/doc.pdf"],
    )
    try:
        assert hydrated.ctx.config_dir == explicit_cfg, "config_dir explícito vence"
        assert hydrated.ctx.incremental is True
        assert hydrated.ctx.incremental_doc_paths == ["inbox/doc.pdf"]
    finally:
        hydrated.close()


def test_close_is_idempotent_and_never_raises(tmp_path, session_factory):
    hydrated = _build(tmp_path, session_factory)
    hydrated.close()
    hydrated.close()
