"""Sink de audit em tabela ``internal_ops_audit`` (ADR-309) — redaction, ordem, atomicidade."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.models.internal_ops_audit import InternalOpsAudit
from backend.app.services.internal_ops.audit import (
    AuditRecord,
    append_audit,
    append_audit_autonomous,
    read_audit,
)


@pytest.mark.asyncio
async def test_append_writes_row(db) -> None:
    append_audit(AuditRecord(action="user.test", actor="ops1", target_id="u1"), db)
    entries = await read_audit(db)
    assert len(entries) == 1
    assert entries[0]["action"] == "user.test"
    assert entries[0]["actor"] == "ops1"
    assert entries[0]["target_id"] == "u1"


@pytest.mark.asyncio
async def test_append_redacts_forbidden_keys(db) -> None:
    append_audit(
        AuditRecord(
            action="user.reset_password",
            actor="ops1",
            details={"email": "a@b.c", "password": "leak", "token": "secret"},
        ),
        db,
    )
    entries = await read_audit(db)
    assert entries[0]["details"] == {"email": "a@b.c"}


@pytest.mark.asyncio
async def test_read_limit_most_recent_last(db) -> None:
    for i in range(5):
        append_audit(AuditRecord(action=f"a{i}", actor="ops"), db)
    entries = await read_audit(db, limit=2)
    assert [e["action"] for e in entries] == ["a3", "a4"]


@pytest.mark.asyncio
async def test_empty_table_returns_empty_list(db) -> None:
    assert await read_audit(db) == []


@pytest.mark.asyncio
async def test_rollback_da_operacao_leva_audit_junto(db) -> None:
    """ADR-309 D2 — prova executável: "audit existe ⟺ ação aconteceu"."""
    append_audit(AuditRecord(action="user.hard_delete", actor="ops1"), db)
    await db.rollback()
    assert await read_audit(db) == []


@pytest.mark.asyncio
async def test_autonomous_commits_immediately(db) -> None:
    append_audit_autonomous(AuditRecord(action="ops.login_failed", actor="ops:x", result="fail"))
    entries = await read_audit(db)
    assert entries[-1]["action"] == "ops.login_failed"


def test_autonomous_hard_fail_emits_critical(monkeypatch, caplog) -> None:
    import backend.app.core.database as database_mod

    class _BrokenSession:
        def __enter__(self):
            raise OSError("db indisponível")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(database_mod, "SyncSessionLocal", lambda: _BrokenSession())
    with caplog.at_level("CRITICAL", logger="mathoms.internal_ops.audit"):
        with pytest.raises(OSError):
            append_audit_autonomous(AuditRecord(action="ops.login", actor="ops:x"))
    assert any("audit sink failure" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_purge_job_do_produto_nao_toca_internal_ops_audit(db) -> None:
    """ADR-309 D5 — retenção indefinida; o purge de leitura (ADR-275) filtra AuditLog."""
    import inspect

    from backend.app.tasks import periodic_tasks

    src = inspect.getsource(periodic_tasks)
    assert "InternalOpsAudit" not in src
    assert "internal_ops_audit" not in src


def test_contrato_sem_update_delete_no_modulo() -> None:
    """ADR-309 D4 — o módulo de audit só expõe append/read (imutabilidade)."""
    import inspect

    from backend.app.services.internal_ops import audit as audit_mod

    src = inspect.getsource(audit_mod)
    assert ".delete(" not in src
    assert "update(" not in src


_EXPECTED_MUTATION_AUDIT_ACTIONS = {
    "backfill_override_identity.py": "override.backfill_natural_key",
    "anonymize_user.py": "user.anonymize",
    "hard_delete_user.py": "user.hard_delete",
    "reset_password.py": "user.reset_password",
    "set_developer_flag.py": "user.set_developer_flag",
    "update_user_email.py": "user.email_changed",
    "update_user_profile.py": "user.update_profile",
    "delete_document.py": "document.delete",
    "purge_documents.py": "document.purge",
    "purge_reports.py": "report.purge",
    "pipeline_reset.py": "pipeline.reset_from_stage",
    "suggestion_backfill.py": "suggestions.backfill_supersede",
    "update_workspace_business_profile.py": "workspace.update_business_profile",
    "update_workspace_llm_budget.py": "workspace.update_llm_budget",
}

_EXPECTED_AUTONOMOUS_ACTIONS = {"ops.login", "ops.login_failed", "ops.logout"}


def test_paridade_services_passam_pelo_sink_transacional() -> None:
    """KR1 A31 — gate anti-Goodhart: service novo com append_audit sem constar
    no mapa, ou enumerado que pare de auditar, quebra este teste."""
    from pathlib import Path

    services_dir = Path("backend/app/services/internal_ops")
    writers = {
        f.name
        for f in services_dir.glob("*.py")
        if "append_audit(" in f.read_text() and f.name != "audit.py"
    }
    assert writers == set(_EXPECTED_MUTATION_AUDIT_ACTIONS)
    for name in sorted(writers):
        src = (services_dir / name).read_text()
        assert _EXPECTED_MUTATION_AUDIT_ACTIONS[name] in src, name
        assert "append_audit_autonomous" not in src, name


def test_paridade_login_usa_escrita_autonoma() -> None:
    """KR1 A31 — eventos session-less (ADR-309 D3) só no path autônomo."""
    from pathlib import Path

    login_src = Path("backend/app/api/admin/login.py").read_text()
    for action in _EXPECTED_AUTONOMOUS_ACTIONS:
        assert f'"{action}"' in login_src
    assert "append_audit(" not in login_src.replace("append_audit_autonomous(", "")


@pytest.mark.asyncio
async def test_created_at_persistido(db) -> None:
    append_audit(AuditRecord(action="x", actor="ops"), db)
    await db.flush()
    row = (await db.execute(select(InternalOpsAudit))).scalar_one()
    assert row.created_at is not None
