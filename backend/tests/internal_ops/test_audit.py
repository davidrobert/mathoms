"""Testes do sink de audit (append-only JSONL + redaction)."""

from __future__ import annotations

from pathlib import Path

from backend.app.services.internal_ops.audit import (
    AuditRecord,
    append_audit,
    read_audit,
)


def test_append_writes_json_line(audit_path: Path) -> None:
    append_audit(AuditRecord(action="user.test", actor="ops1", target_id="u1"))
    entries = read_audit(path=audit_path)
    assert len(entries) == 1
    assert entries[0]["action"] == "user.test"
    assert entries[0]["actor"] == "ops1"
    assert entries[0]["target_id"] == "u1"


def test_append_redacts_forbidden_keys(audit_path: Path) -> None:
    append_audit(
        AuditRecord(
            action="user.reset_password",
            actor="ops1",
            details={"email": "a@b.c", "password": "leak", "token": "secret"},
        )
    )
    entries = read_audit(path=audit_path)
    assert entries[0]["details"] == {"email": "a@b.c"}


def test_read_limit(audit_path: Path) -> None:
    for i in range(5):
        append_audit(AuditRecord(action=f"a{i}", actor="ops"))
    entries = read_audit(path=audit_path, limit=2)
    assert [e["action"] for e in entries] == ["a3", "a4"]


def test_empty_log_returns_empty_list(tmp_path: Path) -> None:
    assert read_audit(path=tmp_path / "missing.log") == []
