"""A26.l10 — cobertura estrutural do export LGPD (Art.18, finding r2-new-2).

Todo model SQLAlchemy com FK direta ou transitiva para ``workspaces`` guarda
dado do titular (ou deriva dele) e é apagado pelo erasure em cascata
(ADR-275). Cada um deve estar no export (``EXPORTED_TABLES``) ou na allowlist
de exclusão com rationale (``EXPORT_EXCLUDED_TABLES``). Model novo fora das
duas listas → vermelho: decida export ou allowlist ao criar a tabela.
"""

from __future__ import annotations

import json
import tarfile
from datetime import date
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.models  # noqa: F401 — registra todos os models no metadata
from backend.app.core.database import Base
from backend.app.core.security import create_access_token
from backend.app.models import (
    Debt,
    PropertyIdentity,
    Protection,
    Risk,
    TransactionOverride,
    User,
    Vehicle,
)
from backend.app.services.lgpd_export_service import (
    EXPORT_EXCLUDED_TABLES,
    EXPORTED_TABLES,
)
from backend.tests.factories import make_user, make_workspace


def _tables_reaching_workspaces() -> set[str]:
    """Fecho transitivo: tabelas com caminho de FK (saindo) até ``workspaces``."""
    graph = {
        table.name: {fk.column.table.name for fk in table.foreign_keys}
        for table in Base.metadata.tables.values()
    }
    reaching = {"workspaces"}
    frontier = reaching
    while frontier:
        frontier = {
            name for name, targets in graph.items() if name not in reaching and targets & reaching
        }
        reaching |= frontier
    return reaching


def test_every_workspace_reachable_table_is_exported_or_allowlisted() -> None:
    reaching = _tables_reaching_workspaces()
    unaccounted = sorted(reaching - EXPORTED_TABLES - set(EXPORT_EXCLUDED_TABLES))
    assert not unaccounted, (
        f"tabelas com dado do titular fora do export LGPD e sem rationale de "
        f"exclusão: {unaccounted}. Adicione a _WORKSPACE_TABLES/_CHILD_TABLES "
        f"(export) ou a EXPORT_EXCLUDED_TABLES (allowlist com rationale) em "
        f"lgpd_export_service.py"
    )


def test_export_and_allowlist_are_disjoint() -> None:
    overlap = sorted(EXPORTED_TABLES & set(EXPORT_EXCLUDED_TABLES))
    assert not overlap, f"tabelas em ambas as listas (decisão ambígua): {overlap}"


def test_allowlist_entries_are_live_tables_with_rationale() -> None:
    stale = sorted(set(EXPORT_EXCLUDED_TABLES) - set(Base.metadata.tables))
    assert not stale, f"allowlist referencia tabelas inexistentes: {stale}"
    missing_rationale = sorted(
        name for name, rationale in EXPORT_EXCLUDED_TABLES.items() if not rationale.strip()
    )
    assert not missing_rationale, f"exclusões sem rationale: {missing_rationale}"


def test_exported_tables_are_live_tables() -> None:
    stale = sorted(EXPORTED_TABLES - set(Base.metadata.tables))
    assert not stale, f"export referencia tabelas inexistentes: {stale}"


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=user.id, token_version=user.token_version)
    return {"Authorization": f"Bearer {token}"}


def _seed_titular_aggregates(db: AsyncSession, workspace_id: str) -> None:
    db.add_all(
        [
            Debt(
                workspace_id=workspace_id,
                tipo="cdc",
                descricao="CDC veículo LGPD",
                saldo_devedor_cents=1_234_500,
                source="user_declared",
            ),
            PropertyIdentity(
                workspace_id=workspace_id,
                titular_key="titular",
                codigo_rfb="11",
                endereco_canonical="Rua Exemplo, 123",
                first_seen_year=2024,
            ),
            Vehicle(
                workspace_id=workspace_id,
                placa="ABC1D23",
                renavam="123456789",
                marca="Marca LGPD",
                modelo="Modelo LGPD",
                ano_modelo=2024,
                ano_fabricacao=2023,
            ),
            Protection(
                workspace_id=workspace_id,
                category="vida",
                insurer="Seguradora LGPD",
                coverage_brl_cents=50_000_000,
                starts_at=date(2026, 1, 1),
            ),
            Risk(
                workspace_id=workspace_id,
                code="renda_unica",
                name="Renda concentrada",
                rationale="Uma única fonte de renda",
                impact_level="alto",
            ),
            TransactionOverride(
                workspace_id=workspace_id,
                transaction_hash="a" * 64,
                original_category="outros",
                new_category="alimentacao",
            ),
        ]
    )


_EXPECTED_CONTENT = {
    "debt.ndjson": "CDC veículo LGPD",
    "property_identity.ndjson": "Rua Exemplo, 123",
    "vehicles.ndjson": "ABC1D23",
    "protections.ndjson": "Seguradora LGPD",
    "risks.ndjson": "Renda concentrada",
    "transaction_overrides.ndjson": "alimentacao",
}


def _assert_family_present(tar: tarfile.TarFile, filename: str, needle: str) -> None:
    member = tar.extractfile(filename)
    assert member is not None, filename
    rows = [json.loads(line) for line in member.read().splitlines()]
    assert rows, filename
    assert any(needle in json.dumps(r, ensure_ascii=False) for r in rows), filename


@pytest.mark.asyncio
async def test_data_export_includes_titular_aggregates(
    client: AsyncClient, db: AsyncSession, tmp_path: Path, monkeypatch
) -> None:
    """A26.l10 — as 6 famílias do finding r2-new-2 (Debt, PropertyIdentity,
    Vehicle, Protection, Risk, TransactionOverride) entram no export Art.18."""
    monkeypatch.setattr(
        "backend.app.services.lgpd_export_service.export_storage_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr("backend.app.api.me._enqueue_export", lambda _request_id: None)
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    _seed_titular_aggregates(db, ws.id)
    await db.commit()

    resp = await client.post("/api/v1/me/data-export", headers=_auth_headers(user))
    request_id = resp.json()["request_id"]

    from backend.app.tasks.lgpd_export import process_data_export

    result = process_data_export.run(request_id)
    assert result["status"] == "ready"

    with tarfile.open(tmp_path / f"{request_id}.tar.gz", "r:gz") as tar:
        names = set(tar.getnames())
        assert set(_EXPECTED_CONTENT) <= names, sorted(names)
        for filename, needle in _EXPECTED_CONTENT.items():
            _assert_family_present(tar, filename, needle)

        manifest_member = tar.extractfile("manifest.json")
        assert manifest_member is not None
        manifest_tables = {f["table"] for f in json.loads(manifest_member.read())["files"]}
        assert {n.removesuffix(".ndjson") for n in _EXPECTED_CONTENT} <= manifest_tables

        # ADR-090: valores monetários saem como int cents, nunca float.
        debt_member = tar.extractfile("debt.ndjson")
        assert debt_member is not None
        debt_row = json.loads(debt_member.read().splitlines()[0])
        assert debt_row["saldo_devedor_cents"] == 1_234_500
        assert isinstance(debt_row["saldo_devedor_cents"], int)
