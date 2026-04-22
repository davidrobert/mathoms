"""Testes do lint de tenancy scoping (ADR-072).

Fixtures sintéticas em strings ao invés de arquivos reais — cobre casos
positivos e negativos sem precisar mexer em backend/app/**.

Rodar:
    python -m pytest scripts/lint/test_check_workspace_scoping.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Torna scripts/lint importável
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lint"))

from check_workspace_scoping import check_file  # noqa: E402

TENANT_MODELS = {"Task", "Goal", "FamilyMember"}


def _write(tmp_path: Path, source: str) -> Path:
    p = tmp_path / "sample.py"
    p.write_text(source, encoding="utf-8")
    return p


# ─── Casos que devem PASSAR (sem violações) ─────────────────────────────


def test_passes_when_workspace_id_in_first_where(tmp_path: Path) -> None:
    src = """
from sqlalchemy import select
from models import Task

async def list_tasks(workspace_id, db):
    stmt = select(Task).where(Task.workspace_id == workspace_id)
    return await db.execute(stmt)
"""
    assert check_file(_write(tmp_path, src), TENANT_MODELS) == []


def test_passes_when_workspace_id_combined_with_other_conditions(tmp_path: Path) -> None:
    src = """
from sqlalchemy import select
from models import Task

async def list_pending(workspace_id, db):
    stmt = select(Task).where(
        Task.workspace_id == workspace_id,
        Task.status == 'pending',
    ).order_by(Task.deadline_date)
    return await db.execute(stmt)
"""
    assert check_file(_write(tmp_path, src), TENANT_MODELS) == []


def test_passes_with_tenancy_global_comment(tmp_path: Path) -> None:
    src = """
from sqlalchemy import select
from models import Task

async def count_all_tasks(db):
    # tenancy: global — admin-only metric
    stmt = select(Task).where(Task.status == 'done')
    return await db.execute(stmt)
"""
    assert check_file(_write(tmp_path, src), TENANT_MODELS) == []


def test_passes_with_tenancy_global_on_same_line(tmp_path: Path) -> None:
    src = """
from sqlalchemy import select
from models import Task

async def count_all_tasks(db):
    stmt = select(Task).where(Task.status == 'done')  # tenancy: global
    return await db.execute(stmt)
"""
    assert check_file(_write(tmp_path, src), TENANT_MODELS) == []


def test_passes_when_model_not_tenant_scoped(tmp_path: Path) -> None:
    src = """
from sqlalchemy import select
from models import User

async def get_user(user_id, db):
    stmt = select(User).where(User.id == user_id)
    return await db.execute(stmt)
"""
    # User não está em TENANT_MODELS → não deve gerar violação
    assert check_file(_write(tmp_path, src), TENANT_MODELS) == []


def test_passes_with_builder_pattern_no_where(tmp_path: Path) -> None:
    """Quando `select(Model)` aparece sem `.where()` na mesma expressão,
    assume-se builder pattern (filtro aplicado via variável posterior)
    — não gera violação para evitar falso positivo."""
    src = """
from sqlalchemy import select
from models import Task

async def build_query(workspace_id, filters):
    q = select(Task)
    q = q.where(Task.workspace_id == workspace_id)
    for f in filters:
        q = q.where(f)
    return q
"""
    assert check_file(_write(tmp_path, src), TENANT_MODELS) == []


# ─── Casos que devem FALHAR (violação detectada) ─────────────────────────


def test_fails_when_where_without_workspace_id(tmp_path: Path) -> None:
    src = """
from sqlalchemy import select
from models import Task

async def list_by_status(status, db):
    stmt = select(Task).where(Task.status == status)
    return await db.execute(stmt)
"""
    violations = check_file(_write(tmp_path, src), TENANT_MODELS)
    assert len(violations) == 1
    assert violations[0].model == "Task"


def test_fails_with_multiple_wheres_none_scoped(tmp_path: Path) -> None:
    src = """
from sqlalchemy import select
from models import Goal

async def recent_goals(user_id, db):
    stmt = (
        select(Goal)
        .where(Goal.type == 'IF')
        .where(Goal.created_by == user_id)
    )
    return await db.execute(stmt)
"""
    violations = check_file(_write(tmp_path, src), TENANT_MODELS)
    assert len(violations) == 1
    assert violations[0].model == "Goal"


def test_reports_multiple_distinct_selects(tmp_path: Path) -> None:
    src = """
from sqlalchemy import select
from models import Task, Goal

async def bad(db):
    a = select(Task).where(Task.status == 'done')
    b = select(Goal).where(Goal.type == 'IF')
    return a, b
"""
    violations = check_file(_write(tmp_path, src), TENANT_MODELS)
    assert len(violations) == 2
    assert {v.model for v in violations} == {"Task", "Goal"}


def test_fails_when_where_uses_only_id_fk(tmp_path: Path) -> None:
    """Caso típico: `select(FamilyMember).where(FamilyMember.id == x)` —
    aceita o ID cru do cliente sem validar membership, vulnerável a
    IDOR se o x for previsível."""
    src = """
from sqlalchemy import select
from models import FamilyMember

async def get_member(member_id, db):
    stmt = select(FamilyMember).where(FamilyMember.id == member_id)
    return await db.execute(stmt)
"""
    violations = check_file(_write(tmp_path, src), TENANT_MODELS)
    assert len(violations) == 1


def test_tenancy_global_misspelled_does_not_exempt(tmp_path: Path) -> None:
    src = """
from sqlalchemy import select
from models import Task

async def bad(db):
    # tenancy-global  <- faltou os dois-pontos
    stmt = select(Task).where(Task.status == 'done')
    return await db.execute(stmt)
"""
    violations = check_file(_write(tmp_path, src), TENANT_MODELS)
    assert len(violations) == 1


# ─── Caso combinado: where com workspace_id + outras condições ─────────


def test_passes_when_workspace_id_is_not_first_but_present(tmp_path: Path) -> None:
    """O lint não exige que `workspace_id` seja LITERALMENTE o primeiro
    argumento — basta que apareça em algum `.where/.filter` da chain.
    A mensagem sugere "primeiro filtro" por convenção de leitura, mas a
    validação é por presença."""
    src = """
from sqlalchemy import select
from models import Task

async def list_recent(workspace_id, db):
    stmt = select(Task).where(
        Task.status == 'pending',
        Task.workspace_id == workspace_id,
    )
    return await db.execute(stmt)
"""
    assert check_file(_write(tmp_path, src), TENANT_MODELS) == []
