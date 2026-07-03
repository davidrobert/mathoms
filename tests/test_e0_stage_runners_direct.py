"""Cobertura direta dos stage runners E0 (`route_documents` + `unlock_documents`).

Roda os runners `run(ctx)` sobre workspace tmp com 1 CSV sintético (PII-zero)
cujo conteúdo classifica por **regex de conteúdo** com confidence 1.0 — o LLM
nunca é chamado (e o teste remove ANTHROPIC_API_KEY por defesa). Trava:
roteamento p/ `data/financial_statements/` + cópia de auditoria em
`inbox_processed/`, e idempotência da segunda execução.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.context import WorkspaceContext
from pipeline.stages import route_documents, unlock_documents

_SYNTHETIC_CSV = (
    "EXTRATO DA CONTA CORRENTE\n"
    "ITAU UNIBANCO S.A.\n"
    "Periodo: 01/01/2026 a 31/01/2026\n"
    "Agencia: 0001 Conta: 12345-6\n"
    "SALDO ANTERIOR;0,00\n"
    "PAGAMENTO ASSINATURA STREAMING;-10,00\n"
)


@pytest.fixture()
def e0_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> WorkspaceContext:
    """Workspace tmp com configs mínimos + 1 CSV sintético no inbox, sem LLM."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = tmp_path / "config"
    cfg.mkdir()
    for name in ("pipeline.json", "institutions.json", "family_members.json"):
        (cfg / name).write_text("{}")
    (cfg / "passwords.txt").write_text("senha-fake-teste\n")
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "documento.csv").write_text(_SYNTHETIC_CSV)
    return WorkspaceContext(root=tmp_path, artifact_store=None)


def _routed_files(ctx: WorkspaceContext) -> list[str]:
    dest = ctx.root / "data" / "financial_statements"
    return sorted(p.name for p in dest.glob("*")) if dest.exists() else []


def test_route_documents_routes_csv_by_content_regex(e0_workspace: WorkspaceContext) -> None:
    """CSV sintético é classificado (itau/extratoconta) e movido do inbox p/ data/."""
    result = route_documents.run(e0_workspace)
    assert result == {"success": True}
    routed = _routed_files(e0_workspace)
    assert len(routed) == 1
    assert "itau_extratoconta_202601" in routed[0]
    assert routed[0].endswith("-0_original.csv")
    assert list((e0_workspace.root / "inbox").iterdir()) == []


def test_route_documents_keeps_audit_copy(e0_workspace: WorkspaceContext) -> None:
    """Roteamento preserva cópia de auditoria em inbox_processed/<data>/."""
    route_documents.run(e0_workspace)
    audit = list((e0_workspace.root / "inbox_processed").rglob("documento.csv"))
    assert len(audit) == 1


def test_route_documents_second_run_is_idempotent(e0_workspace: WorkspaceContext) -> None:
    """Segunda execução com inbox vazio é no-op: não duplica nada em data/."""
    route_documents.run(e0_workspace)
    first = _routed_files(e0_workspace)
    result = route_documents.run(e0_workspace)
    assert result == {"success": True}
    assert _routed_files(e0_workspace) == first


def test_unlock_documents_noop_without_pdfs_or_zips(e0_workspace: WorkspaceContext) -> None:
    """Inbox só com CSV → unlock é no-op idempotente e não toca o arquivo."""
    assert unlock_documents.run(e0_workspace) == {"success": True}
    assert unlock_documents.run(e0_workspace) == {"success": True}
    assert (e0_workspace.root / "inbox" / "documento.csv").exists()
