"""AST enforcement: sem `Any` em DTO boundary (CLAUDE.md §Code style · A6g.6).

Pydantic DTOs em ``backend/app/schemas/`` são o contrato HTTP↔domínio.
``dict[str, Any]`` aqui faz o tipo virar opaco — violates "TypeScript
sem `any`" em espírito, e frustra codegen.

**Gate white-glove:** lista ``CLEAN_FILES`` contém arquivos já sem
``Any``. Teste falha se qualquer um deles ganhar ``Any`` em futuro
commit. Legado fora da lista (11 arquivos em 2026-04-22) passa livre —
conforme cada arquivo é migrado (sweep A6e.3c, A6g.6b), move-se para
``CLEAN_FILES``.

Baseline 2026-04-22: 35+ ocorrências legadas em 11 arquivos. Catalogadas
em ``LEGACY_FILES`` com track previsto.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "schemas"

# Arquivos que NÃO podem introduzir ``Any`` — gate bloqueante permanente.
# Cada PR que limpa um arquivo legado o move de LEGACY_FILES para cá.
CLEAN_FILES: set[str] = {
    # Arquivos já clean em 2026-04-22 (qualquer schema não listado em
    # LEGACY_FILES abaixo). Lista gerada abaixo dinamicamente.
}

# Legado pré-A6g.6 — `dict[str, Any]` aceito por enquanto. Cada entrada
# documenta o track onde sai. Nunca adicionar novas entries sem ADR.
LEGACY_FILES: dict[str, str] = {
    # Opaque blobs intencionais (config dinâmico por workspace) — manter
    # Any é correto; arquivos ficam em allowlist forever.
    "dto/config_blob/command.py": "OPAQUE: config blob por workspace (ADR-081)",
    "dto/config_blob/mapper.py": "OPAQUE: config blob mapper",
    "dto/config_blob/response.py": "OPAQUE: config blob response",
    "config.py": "OPAQUE: MaterializedConfig blobs",
    # Legado que SAI com migração prevista — gate progressivo via audit.
    "events.py": "A6e.events: payload tipado",
    "dashboard.py": "A6g.6b: dashboard response",
    "report.py": "A6g.6b: report response schemas",
    "dto/document/response.py": "OPAQUE: debug endpoint extract-json",
}


class _AnyFinder(ast.NodeVisitor):
    """Coleta ocorrências de ``Any`` em annotations de boundary."""

    def __init__(self) -> None:
        self.hits: list[tuple[int, str]] = []

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == "Any":
            self.hits.append((node.lineno, "Any"))
        self.generic_visit(node)


def _count_any(path: Path) -> int:
    """Conta ocorrências de ``Any`` como tipo anotado no arquivo."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    finder = _AnyFinder()
    # Visit apenas annotations (não docstrings/strings).
    for node in ast.walk(tree):
        if isinstance(node, (ast.AnnAssign, ast.FunctionDef, ast.AsyncFunctionDef)):
            if isinstance(node, ast.AnnAssign) and node.annotation is not None:
                finder.visit(node.annotation)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.returns is not None:
                    finder.visit(node.returns)
                for arg in node.args.args + node.args.kwonlyargs:
                    if arg.annotation is not None:
                        finder.visit(arg.annotation)
    return len(finder.hits)


def _all_schema_files() -> list[Path]:
    return sorted(p for p in SCHEMAS_DIR.rglob("*.py") if p.name != "__init__.py")


def _relpath(p: Path) -> str:
    return str(p.relative_to(SCHEMAS_DIR))


# Popula CLEAN_FILES dinamicamente: qualquer arquivo não em LEGACY_FILES
# é tratado como clean e gated.
def _clean_files() -> set[str]:
    all_files = {_relpath(p) for p in _all_schema_files()}
    return all_files - set(LEGACY_FILES)


@pytest.mark.parametrize("rel_path", sorted(_clean_files()))
def test_clean_file_has_no_any(rel_path: str) -> None:
    """Arquivos não-legados em schemas/ não podem ter ``Any``."""
    abs_path = SCHEMAS_DIR / rel_path
    count = _count_any(abs_path)
    assert count == 0, (
        f"Regressão: {rel_path} ganhou {count} ocorrência(s) de `Any` em "
        "annotation de boundary. DTOs devem ter tipos concretos "
        "(CLAUDE.md §Code style › Tipos)."
    )


def test_legacy_files_still_legacy_or_migrated() -> None:
    """LEGACY_FILES consistente: arquivo ou (a) ainda tem Any OU (b) foi
    migrado — nesse caso remover da LEGACY_FILES para promover o gate."""
    still_legacy: list[str] = []
    migrated: list[str] = []
    for rel in LEGACY_FILES:
        abs_path = SCHEMAS_DIR / rel
        if not abs_path.exists():
            migrated.append(f"{rel} (arquivo removido)")
            continue
        if _count_any(abs_path) == 0:
            migrated.append(rel)
        else:
            still_legacy.append(rel)
    assert not migrated, (
        f"Arquivos migrados detectados — remova de LEGACY_FILES em "
        f"test_no_any_in_boundary.py para ativar o gate: {migrated}"
    )


def test_allowlist_files_exist() -> None:
    """LEGACY_FILES deve apontar para arquivos reais."""
    missing = [rel for rel in LEGACY_FILES if not (SCHEMAS_DIR / rel).exists()]
    assert not missing, f"LEGACY_FILES tem entradas órfãs: {missing}"
