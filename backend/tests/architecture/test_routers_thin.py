"""AST enforcement: routers finos (ADR-101 R15/R16 · A6e.4).

Cada endpoint em ``backend/app/api/*.py`` deve delegar a um use case
em ``backend/app/application/<aggregate>/`` ou a um service — nunca
executar lógica de negócio, query SQL ou `session.commit()` no handler.

Este teste é o **gate permanente** da lane A6e.4. Enquanto os 17 routers
são refatorados incrementalmente, ``THIN_ROUTERS`` lista os já finos
(enforcement ativo). Conforme cada router é convertido, seu nome é
adicionado ao set; regressões então falham o CI.

Rules checked em cada router no allowlist:
  1. Nenhum endpoint (``async def`` decorada com ``@router.<method>``) tem
     > 15 statements no corpo.
  2. Nenhum ``from sqlalchemy import select`` ou ``from sqlalchemy import
     delete as ...`` diretamente no módulo (repositórios/use cases podem).
  3. Nenhuma string ``session.commit`` / ``.execute(select`` no source
     (sinal de query ad-hoc em handler).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "api"

# Routers já refatorados para o padrão thin. Adicione entradas conforme
# cada slice A6e.4 merge em main. Routers NÃO listados aqui ficam fora
# do enforcement (ainda pendentes de refactor).
THIN_ROUTERS = frozenset(
    {
        "audit.py",
        "auth.py",
        "categories.py",
        "dashboard.py",
        "family_members.py",
        "feature_flags.py",
        "goals.py",
        "vault.py",
    }
)

MAX_STATEMENTS_PER_ENDPOINT = 15


def _router_endpoint_names(tree: ast.AST) -> list[ast.AsyncFunctionDef | ast.FunctionDef]:
    """Encontra funções decoradas com ``@router.<method>(...)``."""
    out: list[ast.AsyncFunctionDef | ast.FunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            if _has_router_decorator(node):
                out.append(node)
    return out


def _has_router_decorator(node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    for d in node.decorator_list:
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute):
            value = d.func.value
            if isinstance(value, ast.Name) and value.id in {
                "router",
                "tenant_router",
            }:
                return True
    return False


def _imports_sqlalchemy_query_helpers(tree: ast.AST) -> list[str]:
    """Lista imports de ``sqlalchemy.select``/``delete``/``update`` etc.

    ``sqlalchemy.ext.asyncio.AsyncSession`` é permitido — é apenas o type
    alias do parâmetro ``db: AsyncSession = Depends(get_db)``.
    """
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "sqlalchemy":
            for alias in node.names:
                if alias.name in {"select", "delete", "update", "insert", "func"}:
                    bad.append(alias.name)
    return bad


@pytest.mark.parametrize(
    "router_file", sorted(THIN_ROUTERS), ids=lambda p: p
)
def test_thin_router_has_no_fat_endpoints(router_file: str) -> None:
    path = API_DIR / router_file
    assert path.exists(), f"router {router_file} listed in THIN_ROUTERS not found"
    src = path.read_text()
    tree = ast.parse(src)
    offenders = [
        (n.name, len(n.body))
        for n in _router_endpoint_names(tree)
        if len(n.body) > MAX_STATEMENTS_PER_ENDPOINT
    ]
    assert not offenders, (
        f"{router_file}: endpoints com > {MAX_STATEMENTS_PER_ENDPOINT} "
        f"statements ({offenders}). Mova lógica para use case em "
        f"backend/app/application/<aggregate>/."
    )


@pytest.mark.parametrize(
    "router_file", sorted(THIN_ROUTERS), ids=lambda p: p
)
def test_thin_router_has_no_sqlalchemy_queries(router_file: str) -> None:
    path = API_DIR / router_file
    src = path.read_text()
    tree = ast.parse(src)
    imports = _imports_sqlalchemy_query_helpers(tree)
    assert not imports, (
        f"{router_file}: imports proibidos de sqlalchemy ({imports}). "
        f"Queries vivem em repositórios ou use cases, não no router."
    )
    # Detecta construção de query inline por string (defesa extra).
    for marker in ("session.commit(", ".execute(select", ".execute(delete"):
        assert marker not in src, (
            f"{router_file}: contém `{marker}` — router deve delegar a "
            f"repositório/use case e commitar via ``await db.commit()`` "
            f"no final do handler."
        )
