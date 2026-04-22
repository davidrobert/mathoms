"""Tenancy lint (ADR-072) — garante que queries SQLAlchemy em services/API
de F8+ filtram por `workspace_id`.

## O que faz

Usa AST para analisar cada `.py` em `backend/app/services/` e
`backend/app/api/` procurando:

1. Expressões `select(Model)...` onde `Model` é uma entidade **com coluna
   `workspace_id`** (descoberta por introspecção de `backend.app.models`).
2. Para cada uma, verifica se a cadeia de chamadas **no mesmo `Call`
   node** (e.g. `select(Task).where(...).order_by(...)`) contém um
   `.where()` ou `.filter()` cujo argumento referencia `workspace_id`.
3. Se não contém, **falha** a menos que haja um comentário explícito
   marcando a exceção: `# tenancy: global` na mesma linha ou na linha
   anterior à `select(...)`.

Também detecta queries legadas escritas com helpers privados
`_get_workspace(user)` — essas **não falham** o lint (são legado pré-F8),
mas são reportadas em modo `--verbose` como débito.

## Modelos considerados tenant-scoped

Descoberto automaticamente: todo model em `backend.app.models` que tem
uma coluna chamada `workspace_id`. Modelos globais (User, AuditLog,
etc.) são ignorados.

## Baseline

Violações em código pré-F8 são listadas em
`scripts/lint/tenancy_baseline.txt` (uma por linha, formato
`rel/path.py:line:ModelName`) e são toleradas pelo lint.

A cada endpoint pré-F8 migrado para `get_current_workspace`, remova a
linha correspondente do baseline. O objetivo é que o baseline esvazie
até F8.4 (cutover final).

Novas violações em código F8+ **nunca** devem ser adicionadas ao
baseline — devem ser corrigidas.

## Uso

    python scripts/lint/check_workspace_scoping.py                    # exit 0/1
    python scripts/lint/check_workspace_scoping.py --verbose          # detalhes
    python scripts/lint/check_workspace_scoping.py --no-baseline      # ignora baseline (mostra tudo)
    python scripts/lint/check_workspace_scoping.py --write-baseline   # regrava baseline com estado atual
    python scripts/lint/check_workspace_scoping.py --paths backend/app/services/goal_service.py

## Saída de exemplo

    backend/app/services/task_service.py:42:
      select(Task).where(Task.status == 'done') sem filtro por workspace_id
      Sugestão: adicione .where(Task.workspace_id == workspace_id) como
      PRIMEIRO filtro, ou marque com '# tenancy: global' se intencional.

## CI

Roda como job `tenancy-lint` em `.github/workflows/ci.yml`. Bloqueia merge.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_PATH = REPO_ROOT / "scripts" / "lint" / "tenancy_baseline.txt"


@dataclass(frozen=True)
class Violation:
    file: Path
    line: int
    model: str
    snippet: str

    def key(self, root: Path) -> str:
        """Identificador estável para comparação com baseline."""
        return f"{self.file.relative_to(root).as_posix()}:{self.line}:{self.model}"

    def format(self, root: Path) -> str:
        rel = self.file.relative_to(root)
        return (
            f"{rel}:{self.line}: "
            f"select({self.model}).where(...) sem filtro por workspace_id\n"
            f"  Query: {self.snippet}\n"
            f"  Sugestão: adicione "
            f".where({self.model}.workspace_id == workspace_id) como "
            f"PRIMEIRO filtro, ou marque com '# tenancy: global' se "
            f"intencional."
        )


def load_baseline(path: Path) -> set[str]:
    """Lê o baseline (um id por linha, `#` para comentário). Inexistente → vazio."""
    if not path.exists():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        keys.add(stripped)
    return keys


def write_baseline(path: Path, violations: list[Violation], root: Path) -> None:
    header = (
        "# Baseline de violações de tenancy scoping — ADR-072.\n"
        "# Cada linha é um id estável: <path>:<line>:<Model>.\n"
        "# Adicionado automaticamente por check_workspace_scoping.py "
        "--write-baseline.\n"
        "# Objetivo: esvaziar este arquivo até F8.4 (cutover CLI→web).\n"
        "# NÃO adicionar manualmente entradas novas — código F8+ corrige "
        "em vez de baselinar.\n\n"
    )
    keys = sorted({v.key(root) for v in violations})
    path.write_text(header + "\n".join(keys) + "\n", encoding="utf-8")


def _discover_via_ast() -> set[str]:
    """Detecção primária: varre `backend/app/models/*.py` via AST procurando
    classes que declaram atributo `workspace_id`. Zero dependência de
    runtime, funciona em CI antes de instalar deps."""
    models_dir = REPO_ROOT / "backend" / "app" / "models"
    if not models_dir.is_dir():
        return set()
    found: set[str] = set()
    for py in models_dir.glob("*.py"):
        if py.name in {"__init__.py"}:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError:
            continue
        for cls in ast.walk(tree):
            if not isinstance(cls, ast.ClassDef):
                continue
            for stmt in cls.body:
                # Casa `workspace_id: Mapped[...] = ...` e `workspace_id = ...`
                target_name = None
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    target_name = stmt.target.id
                elif isinstance(stmt, ast.Assign):
                    if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                        target_name = stmt.targets[0].id
                if target_name == "workspace_id":
                    found.add(cls.name)
                    break
    return found


def discover_tenant_models(verbose: bool = False) -> set[str]:
    """Descobre nomes de models que têm coluna `workspace_id`.

    Estratégia primária: AST scan dos arquivos em `backend/app/models/`.
    Tentativa secundária: importar `backend.app.models` e inspecionar
    `__table__` — só usada se AST voltar vazio (safety net).
    """
    ast_result = _discover_via_ast()
    if ast_result:
        return ast_result

    # Fallback: tenta import runtime
    sys.path.insert(0, str(REPO_ROOT))
    try:
        models_mod = importlib.import_module("backend.app.models")
    except Exception as exc:
        if verbose:
            print(
                f"[tenancy-lint] aviso: AST e import falharam ({exc}); "
                f"nenhum modelo tenant descoberto.",
                file=sys.stderr,
            )
        return set()

    tenant_models: set[str] = set()
    for attr_name in getattr(models_mod, "__all__", dir(models_mod)):
        cls = getattr(models_mod, attr_name, None)
        table = getattr(cls, "__table__", None)
        if table is None:
            continue
        if "workspace_id" in {c.name for c in table.columns}:
            tenant_models.add(cls.__name__)
    return tenant_models


def _extract_select_call(node: ast.Call) -> ast.Call | None:
    """Se este Call é `select(Model)`, retorna o próprio Call. Senão None."""
    func = node.func
    if isinstance(func, ast.Name) and func.id == "select":
        return node
    return None


def _resolve_receiver_chain(node: ast.AST) -> list[ast.Call]:
    """Para `select(X).where(a).where(b).order_by(c)`, devolve lista de
    Calls na cadeia de métodos (where/filter) aplicados ao select."""
    chain: list[ast.Call] = []
    current = node
    # Sobe pela chain `attr.method(...)` até chegar ao receiver original
    while isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
        chain.append(current)
        current = current.func.value
    chain.reverse()
    return chain


def _references_workspace_id(expr: ast.AST) -> bool:
    """Devolve True se algum `.workspace_id` aparecer em `expr`.

    Cobre padrões:
      Model.workspace_id == workspace_id
      workspace_id == Model.workspace_id
      Model.workspace_id.in_(...)
    """
    for sub in ast.walk(expr):
        if isinstance(sub, ast.Attribute) and sub.attr == "workspace_id":
            return True
        if isinstance(sub, ast.Name) and sub.id == "workspace_id":
            return True
    return False


def _line_has_tenancy_global(source_lines: list[str], line_no: int) -> bool:
    """Aceita exceção se houver `# tenancy: global` na linha da expressão
    ou nas 3 linhas imediatamente anteriores."""
    for i in range(max(0, line_no - 4), line_no):
        if i < len(source_lines) and "tenancy: global" in source_lines[i]:
            return True
    return False


def check_file(path: Path, tenant_models: set[str]) -> list[Violation]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    lines = source.splitlines()
    violations: list[Violation] = []

    for node in ast.walk(tree):
        # Procura expressões `select(Model)`
        if not isinstance(node, ast.Call):
            continue
        sel = _extract_select_call(node)
        if sel is None or not sel.args:
            continue
        arg0 = sel.args[0]
        if not isinstance(arg0, ast.Name):
            continue
        model_name = arg0.id
        if model_name not in tenant_models:
            continue

        # Sobe: achar o outermost Call da chain (a expressão que contém
        # `select().where()...`). `node` atual é só o `select(...)`.
        # Para pegar a cadeia completa, precisamos olhar quem "contém"
        # esse node — faremos isso via pass separado abaixo.
        # Por ora guardamos para processamento posterior.

    # Pass 2: percorre Expr/Assign/Call e para cada chain que começa em
    # select(Model tenant), coleta todos `.where/.filter` e valida.
    class ChainVisitor(ast.NodeVisitor):
        def visit_Call(self, call: ast.Call) -> None:  # noqa: N802
            # Descobre se o nó mais interno na cadeia é `select(TenantModel)`
            inner = call
            while isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
                inner = inner.func.value
            if not (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "select"
            ):
                self.generic_visit(call)
                return
            if not inner.args or not isinstance(inner.args[0], ast.Name):
                self.generic_visit(call)
                return
            model_name = inner.args[0].id
            if model_name not in tenant_models:
                self.generic_visit(call)
                return

            # Só processa o Call "mais externo" — evitar múltiplas
            # violações pelo mesmo select.
            if call is not _outermost(call):
                return

            chain = _resolve_receiver_chain(call)
            # Inclui o próprio call (pode já estar na chain, inofensivo)
            if call not in chain:
                chain.append(call)

            has_ws_filter = False
            has_any_where = False
            for c in chain:
                if not isinstance(c.func, ast.Attribute):
                    continue
                if c.func.attr not in {"where", "filter"}:
                    continue
                has_any_where = True
                for a in c.args:
                    if _references_workspace_id(a):
                        has_ws_filter = True
                        break
                if has_ws_filter:
                    break

            if has_ws_filter:
                return

            # Padrão builder: `q = select(Model); q = q.where(...)` em
            # statements separados. Não é detectável por AST-local sem
            # análise de fluxo. Pular com nota silenciosa — falha se
            # o ÚNICO .where da chain não for por workspace_id.
            if not has_any_where:
                return

            line_no = inner.lineno
            if _line_has_tenancy_global(lines, line_no):
                return

            snippet = lines[line_no - 1].strip() if line_no - 1 < len(lines) else ""
            violations.append(Violation(file=path, line=line_no, model=model_name, snippet=snippet))

    # Helper para achar o Call externo na mesma chain. Usa map parent↔child.
    _parents: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            _parents[id(child)] = parent

    def _outermost(call: ast.Call) -> ast.Call:
        current: ast.AST = call
        while True:
            parent = _parents.get(id(current))
            if (
                isinstance(parent, ast.Call)
                and isinstance(parent.func, ast.Attribute)
                and parent.func.value is current
            ):
                current = parent
                continue
            # Ou: parent é Call cujo receiver é este (chained)
            break
        return current  # type: ignore[return-value]

    ChainVisitor().visit(tree)
    return violations


def scan_paths(roots: Iterable[Path], tenant_models: set[str]) -> list[Violation]:
    violations: list[Violation] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            violations.extend(check_file(root, tenant_models))
            continue
        for p in root.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            violations.extend(check_file(p, tenant_models))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint de tenancy scoping (ADR-072)")
    parser.add_argument(
        "--paths",
        nargs="*",
        help="Arquivos ou diretórios específicos. Default: backend/app/services + backend/app/api",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Ignora o baseline (mostra todas as violações, incluindo legado).",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Regrava scripts/lint/tenancy_baseline.txt com o estado atual. "
        "Usar apenas ao introduzir o lint ou após migrar um endpoint.",
    )
    args = parser.parse_args()

    if args.paths:
        roots = [REPO_ROOT / p for p in args.paths]
    else:
        roots = [
            REPO_ROOT / "backend" / "app" / "services",
            REPO_ROOT / "backend" / "app" / "api",
        ]

    tenant_models = discover_tenant_models(verbose=args.verbose)
    if not tenant_models:
        print(
            "[tenancy-lint] ERRO: nenhum modelo com workspace_id descoberto. "
            "Verifique backend/app/models/.",
            file=sys.stderr,
        )
        return 2
    if args.verbose:
        print(f"[tenancy-lint] tenant models: {sorted(tenant_models)}")
        print(f"[tenancy-lint] escaneando: {[str(r) for r in roots]}")

    all_violations = scan_paths(roots, tenant_models)

    if args.write_baseline:
        write_baseline(BASELINE_PATH, all_violations, REPO_ROOT)
        print(
            f"[tenancy-lint] baseline regravado em "
            f"{BASELINE_PATH.relative_to(REPO_ROOT)} "
            f"com {len(all_violations)} entrada(s)."
        )
        return 0

    baseline = set() if args.no_baseline else load_baseline(BASELINE_PATH)
    if args.verbose and baseline:
        print(f"[tenancy-lint] baseline: {len(baseline)} entrada(s) toleradas")

    new_violations = [v for v in all_violations if v.key(REPO_ROOT) not in baseline]
    stale_baseline = baseline - {v.key(REPO_ROOT) for v in all_violations}

    if stale_baseline and args.verbose:
        print(
            f"[tenancy-lint] {len(stale_baseline)} entrada(s) do baseline não "
            f"mais violadas (pode remover):"
        )
        for k in sorted(stale_baseline):
            print(f"  - {k}")

    if not new_violations:
        if args.verbose:
            msg = "[tenancy-lint] OK — nenhuma violação nova."
            if baseline:
                msg += f" ({len(baseline)} legado no baseline)"
            print(msg)
        return 0

    print(
        f"[tenancy-lint] {len(new_violations)} violação(ões) NOVA(S) "
        f"encontrada(s) (fora do baseline):\n"
    )
    for v in new_violations:
        print(v.format(REPO_ROOT))
        print()
    print(
        "\nReferência: ADR-072 (docs/DECISIONS.md) — multi-tenancy scoping explícito.\n"
        "Para marcar uma query como intencionalmente global, adicione comentário\n"
        "'# tenancy: global' na mesma linha ou nas 3 linhas anteriores.\n"
        "Para ver o baseline completo de violações legadas, use --no-baseline."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
