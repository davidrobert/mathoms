"""Seed sintético zero-PII para o restore drill (A21.l9 · ADR-174 / ADR-228 G2)."""

# Popula as tabelas-chave na ordem de FK (users → workspaces →
# workspace_members → pipeline_runs → pipeline_artifacts → password_vault)
# com dados fixos e obviamente falsos, incluindo 1 segredo cifrado via Fernet.
# `restore_drill.py` usa esse seed para provar que dump→restore preserva
# conteúdo, schema e o round-trip de decifragem do vault. Sem PII: email em
# `.invalid` (RFC 6761), sem CPF, sem valor monetário real.

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Sentinels compartilhados com restore_drill.py — o drill decifra o segredo
# restaurado e compara com este plaintext (round-trip Fernet).
DRILL_SECRET_LABEL = "drill-fernet-canary"
DRILL_SECRET_PLAINTEXT = "drill-restore-roundtrip-sentinel"  # noqa: S105 - sintético

# IDs fixos (UUID v4 determinístico) — manifesto estável entre execuções.
_USER_ID = "00000000-0000-4000-8000-000000000001"
_WS_ID = "00000000-0000-4000-8000-000000000002"
_MEMBER_ID = "00000000-0000-4000-8000-000000000003"
_RUN_ID = "00000000-0000-4000-8000-000000000004"
_FIXED_TS = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

# Hash bcrypt-shaped sintético — nunca verificado, só ocupa a coluna NOT NULL.
_FAKE_HASH = "$2b$12$drillseedplaceholderhashnotarealsecretxxxxxxxxxxxxxx"


def _user():
    from backend.app.models.user import User

    return User(
        id=_USER_ID,
        email="drill-seed@example.invalid",
        hashed_password=_FAKE_HASH,
        full_name="Drill Seed",
        created_at=_FIXED_TS,
    )


def _workspace():
    from backend.app.models.workspace import Workspace

    return Workspace(id=_WS_ID, name="Drill Workspace", owner_id=_USER_ID, created_at=_FIXED_TS)


def _member():
    from backend.app.models.workspace_member import WorkspaceMember

    return WorkspaceMember(
        id=_MEMBER_ID, workspace_id=_WS_ID, user_id=_USER_ID, role="owner", joined_at=_FIXED_TS
    )


def _run():
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus

    return PipelineRun(
        id=_RUN_ID,
        workspace_id=_WS_ID,
        status=PipelineRunStatus.completed,
        tier_at_run="free",
        started_at=_FIXED_TS,
    )


def _artifact():
    from backend.app.models.pipeline_artifact import PipelineArtifact

    return PipelineArtifact(
        workspace_id=_WS_ID,
        pipeline_run_id=_RUN_ID,
        stage="E5",
        artifact_key="analise_financeira",
        content_json={"drill": True, "patrimonio_liquido": "0.00"},
        created_at=_FIXED_TS,
    )


def _vault_row():
    from backend.app.models.password_vault import PasswordVault
    from backend.app.services.vault import get_vault

    return PasswordVault(
        workspace_id=_WS_ID,
        label=DRILL_SECRET_LABEL,
        encrypted_password=get_vault().encrypt(DRILL_SECRET_PLAINTEXT),
        created_at=_FIXED_TS,
    )


def seed(dsn: str | None = None) -> None:
    """Insere o seed sintético; ``dsn`` (opcional) sobrescreve MATHOMS_DATABASE_URL."""
    if dsn:
        os.environ["MATHOMS_DATABASE_URL"] = dsn
    import backend.app.models  # noqa: F401 - registra todos os mappers
    from backend.app.core.database import SyncSessionLocal

    rows = [_user(), _workspace(), _member(), _run(), _artifact(), _vault_row()]
    with SyncSessionLocal() as session:
        session.add_all(rows)
        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed sintético zero-PII p/ restore drill")
    parser.add_argument("--dsn", default=None, help="MATHOMS_DATABASE_URL override")
    args = parser.parse_args()
    seed(args.dsn)
    print("drill_seed: 6 linhas inseridas (users/workspaces/members/run/artifact/vault).")


if __name__ == "__main__":
    main()
