"""Tenancy isolation — fuzz cross-tenant + AST scan + smoke positivo."""

# Complementa test_multi_tenant_isolation.py (per-domain). Aqui:
#   1. Fuzz: GETs em /api/v1/workspaces/{workspace_id}/... como user A
#      tentando ws_b nunca devolvem 200.
#   2. AST: rota com path-param workspace_id precisa Depends(get_current_workspace).
#   3. Smoke: user A acessa o próprio ws → 200, garante o gate não dá 403 pra tudo.

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_access_token
from backend.app.main import app
from backend.app.models.user import User
from backend.tests.factories import make_user, make_workspace


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=user.id, token_version=user.token_version)
    return {"Authorization": f"Bearer {token}"}


def _workspace_get_routes() -> list[tuple[str, set[str]]]:
    """Lista (path_template, methods) para rotas que aceitam {workspace_id} no path."""
    out: list[tuple[str, set[str]]] = []
    for route in app.routes:
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue
        path = route.path
        if "{workspace_id}" not in path:
            continue
        if not path.startswith("/api/v1/"):
            continue
        out.append((path, set(route.methods or set())))
    return out


def _instantiate_path(path: str, *, workspace_id: str) -> str | None:
    """Substitui placeholders por valores fictícios. Retorna None se a
    rota tem path-param que não conseguimos preencher (FK específica)."""
    out = path.replace("{workspace_id}", workspace_id)
    # Substitui demais path-params com sentinelas que provavelmente não
    # existem no DB. Endpoint deve ainda passar pela dependency
    # `get_current_workspace` ANTES de bater no repositório.
    placeholders = re.findall(r"\{(\w+)\}", out)
    for ph in placeholders:
        out = out.replace("{" + ph + "}", "00000000-0000-0000-0000-00000000aaaa")
    return out


@pytest.mark.asyncio
async def test_workspace_get_endpoints_block_cross_tenant_access(
    client: AsyncClient, db: AsyncSession
) -> None:
    user_a = await make_user(db, email="iso_a@test.com")
    user_b = await make_user(db, email="iso_b@test.com")
    ws_a = await make_workspace(db, owner=user_a, name="WS A")
    ws_b = await make_workspace(db, owner=user_b, name="WS B")
    await db.commit()

    headers_a = _auth_headers(user_a)
    leaks: list[tuple[str, str, int]] = []
    skipped: list[str] = []

    for path, methods in _workspace_get_routes():
        if "GET" not in methods:
            continue
        url = _instantiate_path(path, workspace_id=ws_b.id)
        if url is None:
            skipped.append(path)
            continue
        # alguns endpoints precisam de query params obrigatórios — não
        # passamos. FastAPI retorna 422 antes da dependency rodar; isso
        # NÃO é vazamento, então tratamos 422 como "skipped pelo fuzz".
        resp = await client.get(url, headers=headers_a)
        if resp.status_code == 422:
            skipped.append(path)
            continue
        if resp.status_code == 200:
            leaks.append((path, "GET", resp.status_code))
            continue
        # 403 (membership negado), 404 (path-id não existe), 410 (sunset
        # endpoints retornam 410), 409 (conflicting state) — todos OK.
        if resp.status_code not in (400, 403, 404, 405, 410, 409):
            leaks.append((path, "GET", resp.status_code))

    assert leaks == [], f"Cross-tenant leak detected on {len(leaks)} endpoint(s):\n" + "\n".join(
        f"  {p} [{m}] -> {s}" for p, m, s in leaks
    )
    # Se o fuzz pula > 80% dos endpoints, perdemos cobertura — logue mas
    # não quebra (alguns endpoints exigem body POST, fora do escopo
    # deste fuzz).
    total = sum(1 for _, methods in _workspace_get_routes() if "GET" in methods)
    assert total > 0, "No /api/v1/workspaces/{workspace_id}/... GET routes registered"
    # Smoke: ws_a (próprio) precisa ser acessível para confirmar que não
    # estamos só dando 403 pra tudo.
    own_path = _instantiate_path(
        "/api/v1/workspaces/{workspace_id}/audit",
        workspace_id=ws_a.id,
    )
    own_resp = await client.get(own_path, headers=headers_a)
    assert (
        own_resp.status_code == 200
    ), f"User A não consegue acessar próprio workspace audit: {own_resp.status_code}"


@pytest.mark.asyncio
async def test_workspace_path_param_endpoints_have_tenancy_dependency() -> None:
    """AST scan: toda função de endpoint que aceita `workspace_id` em
    path/query precisa ter `get_current_workspace` (ou helper derivado)
    em sua árvore de Depends. Falha lista os arquivos ofensores."""
    api_dir = Path("backend/app/api")
    offenders: list[str] = []
    inspected = 0

    for py_file in sorted(api_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            if not _is_route_handler(node):
                continue
            takes_ws = _takes_workspace_id(node)
            if not takes_ws:
                continue
            inspected += 1
            qualname = f"{py_file.name}::{node.name}"
            if qualname in _TENANCY_EXEMPTIONS:
                continue
            if not _has_tenancy_dependency(node):
                offenders.append(qualname)

    assert inspected > 0, "AST walker não encontrou endpoint algum — bug no scan"
    assert offenders == [], (
        f"{len(offenders)} endpoint(s) com `workspace_id` mas sem "
        f"`get_current_workspace`/`require_*role`:\n" + "\n".join(f"  - {o}" for o in offenders)
    )


def _is_route_handler(node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    for dec in node.decorator_list:
        # @router.get("/..."), @router.post("/...") etc.
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
            if dec.func.attr in {"get", "post", "put", "patch", "delete"}:
                return True
    return False


def _takes_workspace_id(node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    for arg in node.args.args + node.args.kwonlyargs:
        if arg.arg == "workspace_id":
            return True
    return False


_TENANCY_NAMES = {
    "get_current_workspace",
    "require_write_role",
    "require_member_admin_role",
    "require_role",
}

# Endpoints sunset (ADR-154 / ADR-129) sempre retornam 410 sem tocar DB,
# então não precisam (e não podem) passar por get_current_workspace.
# Listar aqui mantém o gate honesto — se alguém adicionar lógica real,
# precisa tirar daqui ou somar a dependency.
_TENANCY_EXEMPTIONS: frozenset[str] = frozenset(
    {
        "reports_collab.py::get_notes_gone",
        "reports_collab.py::put_notes_gone",
        "reports_collab.py::list_kanban_gone",
        "reports_collab.py::create_kanban_gone",
        "reports_collab.py::update_kanban_gone",
        "reports_collab.py::delete_kanban_gone",
    }
)


def _has_tenancy_dependency(node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    for arg in node.args.args + node.args.kwonlyargs:
        default = _default_for_arg(node, arg)
        if default is None:
            continue
        if _depends_targets_match(default, _TENANCY_NAMES):
            return True
    return False


def _default_for_arg(
    node: ast.AsyncFunctionDef | ast.FunctionDef, target_arg: ast.arg
) -> ast.expr | None:
    """Resolve o default literal de `target_arg`. Retorna None se não tem default."""
    args_obj = node.args
    positional = args_obj.args
    pos_defaults = args_obj.defaults
    pos_offset = len(positional) - len(pos_defaults)
    for idx, a in enumerate(positional):
        if a is target_arg:
            d_idx = idx - pos_offset
            if d_idx >= 0:
                return pos_defaults[d_idx]
            return None
    for idx, a in enumerate(args_obj.kwonlyargs):
        if a is target_arg:
            return args_obj.kw_defaults[idx]
    return None


def _depends_targets_match(default: ast.expr, names: set[str]) -> bool:
    """`Depends(foo)` onde foo está em `names`."""
    if not isinstance(default, ast.Call):
        return False
    if not (isinstance(default.func, ast.Name) and default.func.id == "Depends"):
        return False
    if not default.args:
        return False
    target = default.args[0]
    if isinstance(target, ast.Name):
        return target.id in names
    if isinstance(target, ast.Attribute):
        return target.attr in names
    if isinstance(target, ast.Call):
        # Depends(require_role(WRITE_ROLES)) → match `require_role`
        inner = target.func
        if isinstance(inner, ast.Name):
            return inner.id in names
        if isinstance(inner, ast.Attribute):
            return inner.attr in names
    return False


@pytest.mark.asyncio
async def test_path_id_endpoints_404_on_cross_tenant_resource(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Endpoint com `/{resource_id}` no path: tentar acessar resource de
    User B autenticado como User A deve retornar 403/404 — nunca 200."""
    from backend.tests.factories import make_document

    user_a = await make_user(db, email="path_a@test.com")
    user_b = await make_user(db, email="path_b@test.com")
    ws_a = await make_workspace(db, owner=user_a)
    ws_b = await make_workspace(db, owner=user_b)
    doc_b = await make_document(db, workspace=ws_b, original_name="b_secret.pdf")
    await db.commit()

    headers_a = _auth_headers(user_a)

    # User A tries to access doc_b's extract-json via WS_A's path —
    # endpoint exists, queries by document_id scoped to workspace_id.
    # Doc não existe em ws_a → 403/404 (nunca 200 com payload de B).
    resp1 = await client.get(
        f"/api/v1/workspaces/{ws_a.id}/documents/{doc_b.id}/extract-json",
        headers=headers_a,
    )
    assert resp1.status_code in (
        403,
        404,
    ), f"Cross-tenant doc leak via own ws path: {resp1.status_code} {resp1.text[:200]}"

    # User A tries to access doc_b via WS_B's path — must be 403 (not a member).
    resp2 = await client.get(
        f"/api/v1/workspaces/{ws_b.id}/documents/{doc_b.id}/extract-json",
        headers=headers_a,
    )
    assert (
        resp2.status_code == 403
    ), f"Cross-tenant doc reachable via foreign ws path: {resp2.status_code} {resp2.text[:200]}"
