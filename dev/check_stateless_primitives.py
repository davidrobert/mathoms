#!/usr/bin/env python3
"""Bloqueia primitiva proibida pela ADR-111 §3 em app code; exit 1 = violação.

Origem (ADR-359): `STATELESS_AUDIT.md` §5 afirmou "`threading.Thread` — nenhum
resultado em app code" por 3,5 meses enquanto
`pipeline_service._start_fallback_thread` existia — o thread precedia o audit em
6 dias. Não houve drift; a afirmação nasceu falsa porque nada a verificava. O
gate empírico da ADR-111 (`test_multi_worker_concurrency.py`) testa
*comportamento* multi-worker, não *ausência* das primitivas, e nunca teve como
pegar isto.

Escopo deliberadamente estreito: conjunto **fechado** de primitivas nomeadas —
a metade tratável. A alternativa 2 da ADR-111 rejeitou lint para globais
mutáveis porque singleton legítimo é indistinguível de dict acumulador por AST;
essa razão segue valendo e §2 do audit segue manual.

**Fora do escopo, por decisão:** `threading.Lock` / `Semaphore` sobre objeto
local ao processo (concorrência intra-processo, categoria (b) do audit — ex.
`_pdf_semaphore`, o lock de progresso em `extract_with_llm`). A ADR-111 nunca
as proibiu; incluí-las trocaria zero falso-positivo por ruído.

Detecção é por **AST**, não texto: `category_cache.py` documenta na docstring
"sem ``@lru_cache`` em processo" — prosa que *afirma a ausência* e que um grep
acusaria como violação. Gate hard-fail não pode ter essa classe de falso
positivo. Só `ast` puro (stdlib) — roda no job Lint sem venv completo.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_AUDIT = _REPO_ROOT / "docs" / "reference" / "STATELESS_AUDIT.md"
_SCAN_GLOBS = ("backend/app/**/*.py", "pipeline/**/*.py")

_REASONS: dict[str, str] = {
    "Thread": (
        "executor sem dono de lifetime — não sobrevive a processo curto nem a "
        "reciclagem de worker; trabalho assíncrono vai pelo Celery (ADR-359)"
    ),
    "create_task": "task solta no event loop do worker — morre com ele, invisível a outro worker",
    "BackgroundTasks": (
        "executa no processo do request; não sobrevive a restart nem escala cross-worker"
    ),
    "flock": (
        "lock em disco não coordena workers em hosts distintos — use advisory "
        "lock Postgres ou SET NX no Redis"
    ),
    "lockf": "idem flock — lock em disco não é cross-host",
    "FileLock": "idem flock — lock em disco não é cross-host",
    "lru_cache": "cache in-memory por worker — hit/miss divergem entre workers; use Redis",
    "functools.cache": "idem lru_cache",
    "cached_property": (
        "estado mutável por instância que atravessa requests quando o objeto é reusado"
    ),
    "fcntl": "módulo de lock em disco — não coordena workers cross-host",
    "filelock": "módulo de lock em disco — não coordena workers cross-host",
    "portalocker": "módulo de lock em disco — não coordena workers cross-host",
}

#: Callee com nome dotted **exato**. Suffix-match é ambíguo aqui: o produto tem
#: um `create_task` de domínio (agregado Tarefas, chamado como
#: `task_service.create_task`) que nada tem a ver com `asyncio.create_task`.
_CALL_DOTTED = frozenset(
    {"threading.Thread", "asyncio.create_task", "fcntl.flock", "fcntl.lockf", "filelock.FileLock"}
)
#: Forma `from X import Y` — nome nu no call-site. Sem `create_task` aqui, pela
#: colisão acima; `asyncio.create_task` na prática nunca é importado nu.
_CALL_BARE = frozenset({"Thread", "FileLock"})
#: Decorators proibidos por último segmento (`@cache` bare fica fora — nome
#: genérico demais; só a forma dotted `@functools.cache` conta).
_DECORATOR_SUFFIXES = frozenset({"lru_cache", "cached_property"})
_DECORATOR_DOTTED = frozenset({"functools.cache"})
#: Referência a nome proibida em qualquer posição (inclusive annotation).
_BARE_NAMES = frozenset({"BackgroundTasks"})
_FORBIDDEN_MODULES = frozenset({"fcntl", "filelock", "portalocker"})

# (path relativo ao repo, símbolo) → justificativa. Cada path precisa estar
# mencionado em STATELESS_AUDIT.md (loop doc↔código, checado abaixo).
_ALLOWLIST: dict[tuple[str, str], str] = {}


def _dotted(node: ast.AST) -> str:
    """``a.b.c`` para cadeias Name/Attribute; string vazia para o resto."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _decorator_hit(node: ast.AST) -> str | None:
    target = node.func if isinstance(node, ast.Call) else node
    dotted = _dotted(target)
    if dotted in _DECORATOR_DOTTED:
        return dotted
    suffix = dotted.rsplit(".", 1)[-1]
    return suffix if suffix in _DECORATOR_SUFFIXES else None


def _import_hits(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return [a.name for a in node.names if a.name.split(".")[0] in _FORBIDDEN_MODULES]
    root = (node.module or "").split(".")[0]
    if root in _FORBIDDEN_MODULES:
        return [root]
    return [a.name for a in node.names if a.name in _DECORATOR_SUFFIXES | _BARE_NAMES]


class _Collector(ast.NodeVisitor):
    """Acumula ``(lineno, símbolo)`` de cada uso proibido no módulo."""

    def __init__(self) -> None:
        self.hits: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:
        dotted = _dotted(node.func)
        if dotted in _CALL_DOTTED or dotted in _CALL_BARE:
            self.hits.append((node.lineno, dotted.rsplit(".", 1)[-1]))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in _BARE_NAMES:
            self.hits.append((node.lineno, node.id))

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in _BARE_NAMES:
            self.hits.append((node.lineno, node.attr))
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        self.hits.extend((node.lineno, name) for name in _import_hits(node))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.hits.extend((node.lineno, name) for name in _import_hits(node))

    def _visit_decorated(self, node: ast.AST) -> None:
        for decorator in node.decorator_list:  # type: ignore[attr-defined]
            hit = _decorator_hit(decorator)
            if hit:
                self.hits.append((decorator.lineno, hit))
        self.generic_visit(node)

    visit_FunctionDef = _visit_decorated
    visit_AsyncFunctionDef = _visit_decorated
    visit_ClassDef = _visit_decorated


def _scan_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in _SCAN_GLOBS:
        files.update(p for p in _REPO_ROOT.glob(pattern) if p.is_file())
    return sorted(files)


def _violations_in(path: Path) -> list[tuple[str, int, str]]:
    rel = path.relative_to(_REPO_ROOT).as_posix()
    collector = _Collector()
    collector.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    return [
        (rel, lineno, symbol)
        for lineno, symbol in collector.hits
        if (rel, symbol) not in _ALLOWLIST
    ]


def _report_violations(rows: list[tuple[str, int, str]]) -> None:
    print("❌ Primitiva proibida pela ADR-111 §3 em app code:\n")
    for rel, lineno, symbol in sorted(set(rows)):
        print(f"   {rel}:{lineno} — {symbol}")
        print(f"      {_REASONS.get(symbol, 'ver ADR-111 §3')}")
    print(
        "\nSe o uso é legítimo, adicione entrada em `_ALLOWLIST` de "
        "dev/check_stateless_primitives.py COM justificativa e mencione o path "
        "em docs/reference/STATELESS_AUDIT.md. Se não é, resolva via Redis/DB/Celery."
    )


def _allowlist_drift() -> list[str]:
    """Entrada de allowlist cujo path não aparece no audit — doc mente por omissão."""
    if not _ALLOWLIST:
        return []
    audit = _AUDIT.read_text(encoding="utf-8")
    return [
        f"{path} ({symbol}) está na allowlist mas não é mencionado em {_AUDIT.name}"
        for (path, symbol) in sorted(_ALLOWLIST)
        if path not in audit
    ]


def main() -> int:
    rows = [row for path in _scan_files() for row in _violations_in(path)]
    drift = _allowlist_drift()
    if not rows and not drift:
        return 0
    if rows:
        _report_violations(rows)
    for message in drift:
        print(f"❌ {message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
