#!/usr/bin/env python3
"""Isolamento da superfície de diagnóstico (ADR-395; uso:
``python3 dev/check_diagnostic_session_isolation.py [-v]``; exit 1 = violação).
O run `140ac8d7` morreu em 12/18 porque a row de `review_reasons` compartilhava
transação — e domínio de falha — com o `run.status = needs_review`.

Dois checks, porque um só deixaria metade da classe aberta:

1. **Boundary** — só ``backend/app/services/diagnostics/`` constrói o model
   ``ReviewReason``, e a API pública de lá não aceita ``Session``. Compartilhar
   transação deixa de ser proibido e passa a ser impossível. É o check forte:
   decidível, independente de arquivo, e não fica vacuamente verde.
2. **Sessão mista** — nenhum bloco ``with SyncSessionLocal()`` transiciona o run
   E escreve tabela de diagnóstico. Mais fraco (só vê o que está no mesmo
   módulo), mas é a ÚNICA cobertura das outras tabelas de diagnóstico, que ainda
   não têm sink próprio. Ponto cego declarado: sessão passada por parâmetro
   através de módulos — exatamente o que o check 1 fecha para `review_reasons`."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# Tabelas cuja row EXPLICA a execução. Ausência degrada a observabilidade e não
# muda o que o sistema faz — logo, nunca pode custar a execução.
#
# `StageReview` está FORA de propósito: `resume_run` exige zero reviews `pending`
# para liberar a retomada, então status sem review deixa o humano retomar sem
# revisar. É contrato de pausa, não diagnóstico. `AuditLog`/`InternalOpsAudit`
# também estão fora — trilha de compliance tem de ser durável.
DIAGNOSTIC_MODELS = frozenset(
    {
        "ReviewReason",  # ADR-272 — projeção consultável da razão de needs_review
        "LLMCallLog",  # telemetria de chamada (RV6-11 é desta família)
        "LLMDriftCheck",  # telemetria de drift
        "PipelineRunCost",  # telemetria de custo (ADR-173)
        "ArtifactLineageEdge",  # índice reverso, derivável do run (ADR-279)
    }
)

# Factories de sessão síncrona/assíncrona: o escopo transacional que o gate mede.
SESSION_FACTORIES = frozenset({"SyncSessionLocal", "AsyncSessionLocal"})

# Atributos exclusivos de `PipelineRun` — transição de estado do run.
RUN_ONLY_ATTRS = frozenset({"paused_at_stage", "failed_at_stage"})
# `status` existe em vários models; só conta com `PipelineRunStatus` no RHS.
RUN_STATUS_MARKER = "PipelineRunStatus"

_REPO_ROOT = Path(__file__).resolve().parents[1]
# `pipeline/` entra pelo check de boundary: lá `ReviewReason` é a dataclass do
# domínio (desambiguada pelo import), e um dia alguém importa a do backend.
_SCAN_ROOTS = (_REPO_ROOT / "backend" / "app", _REPO_ROOT / "pipeline")


def _names_in(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _callee_names(node: ast.AST) -> set[str]:
    out: set[str] = set()
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        out.add(func.id if isinstance(func, ast.Name) else getattr(func, "attr", ""))
    return out - {""}


def _writes_diagnostic_directly(node: ast.AST) -> bool:
    """Construção de model de diagnóstico no escopo — o `db.add` sempre a segue."""
    return bool(_callee_names(node) & DIAGNOSTIC_MODELS)


def _assigns_run_state(sub: ast.AST) -> bool:
    if not isinstance(sub, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
        return False
    targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
    attrs = {t.attr for t in targets if isinstance(t, ast.Attribute)}
    if attrs & RUN_ONLY_ATTRS:
        return True
    status_rhs = "status" in attrs and sub.value is not None
    return bool(status_rhs and RUN_STATUS_MARKER in _names_in(sub.value))


def _transitions_run_directly(node: ast.AST) -> bool:
    return any(_assigns_run_state(sub) for sub in ast.walk(node))


def _module_functions(tree: ast.Module) -> dict[str, ast.AST]:
    """Funções do módulo por nome (inclui métodos — colisão é conservadora)."""
    out: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, node)
    return out


def _closure(funcs: dict[str, ast.AST], seed) -> set[str]:
    """Fecho transitivo: função que CHAMA quem faz X também faz X. Sem isso o
    gate fecha sintaxe, não classe — extrair a escrita para um helper o cegaria."""
    marked = {name for name, node in funcs.items() if seed(node)}
    while True:
        grown = {n for n, node in funcs.items() if n not in marked and _callee_names(node) & marked}
        if not grown:
            return marked
        marked |= grown


def _scope_does(node: ast.AST, direct, marked: set[str]) -> bool:
    return direct(node) or bool(_callee_names(node) & marked)


def _with_opens_session(node: ast.With | ast.AsyncWith) -> bool:
    return any(
        isinstance(item.context_expr, ast.Call)
        and isinstance(item.context_expr.func, ast.Name)
        and item.context_expr.func.id in SESSION_FACTORIES
        for item in node.items
    )


def _assigns_session(sub: ast.AST) -> bool:
    if not (isinstance(sub, ast.Assign) and isinstance(sub.value, ast.Call)):
        return False
    func = sub.value.func
    return isinstance(func, ast.Name) and func.id in SESSION_FACTORIES


def _function_opens_session(node: ast.AST) -> bool:
    """`session = SyncSessionLocal()` — escopo transacional é o corpo da função."""
    return any(_assigns_session(sub) for sub in ast.walk(node))


def _session_scopes(tree: ast.Module, funcs: dict[str, ast.AST]) -> list[tuple[int, ast.AST]]:
    scopes = [
        (n.lineno, n)
        for n in ast.walk(tree)
        if isinstance(n, (ast.With, ast.AsyncWith)) and _with_opens_session(n)
    ]
    scopes += [
        (n.lineno, n)
        for n in funcs.values()
        if _function_opens_session(n) and not any(s is n for _, s in scopes)
    ]
    return scopes


def violations_in_source(src: str, path: str) -> list[str]:
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError as exc:
        return [f"{path}: parse error: {exc}"]
    funcs = _module_functions(tree)
    writers = _closure(funcs, _writes_diagnostic_directly)
    transitioners = _closure(funcs, _transitions_run_directly)
    out: list[str] = []
    for lineno, scope in _session_scopes(tree, funcs):
        if not _scope_does(scope, _transitions_run_directly, transitioners):
            continue
        if not _scope_does(scope, _writes_diagnostic_directly, writers):
            continue
        out.append(
            f"{path}:{lineno}: sessão transiciona PipelineRun E escreve tabela de "
            f"diagnóstico ({', '.join(sorted(DIAGNOSTIC_MODELS))}) — separe a sessão "
            "e proteja o diagnóstico com try/except (ADR-395)"
        )
    return out


def _violations_in_file(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    rel = str(path.relative_to(_REPO_ROOT))
    return violations_in_source(src, rel) + boundary_violations(src, rel)


def _python_files(root: Path):
    return (p for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts)


def collect_violations(roots: tuple[Path, ...] = _SCAN_ROOTS) -> list[str]:
    missing = [f"{r} not found" for r in roots if not r.is_dir()]
    if missing:
        return missing
    return [v for root in roots for p in _python_files(root) for v in _violations_in_file(p)]


# Único dono da escrita de diagnóstico. Tabela nova ganha sink aqui — incluí-la
# em DIAGNOSTIC_MODELS sem mover o writer é ato deliberado, e o gate cobra.
_SINK_PACKAGE = "backend/app/services/diagnostics"
# Model de diagnóstico com sink próprio hoje. `LLMCallLog` fica de fora até o
# writer sair de `pipeline/llm/` e do repositório (RV6-11, lane própria).
OWNED_BY_SINK = frozenset({"ReviewReason"})
_SESSION_PARAM_NAMES = frozenset({"db", "session", "sync_db"})


def _binds_db_model(tree: ast.Module, name: str) -> bool:
    """`ReviewReason` é model do backend E dataclass do domínio (`pipeline`).
    Só o primeiro tem coluna — desambigua pelo import do módulo."""
    return any(
        isinstance(n, ast.ImportFrom)
        and (n.module or "").startswith("backend.app.models")
        and any(a.name == name for a in n.names)
        for n in ast.walk(tree)
    )


def _accepts_session(node: ast.AST) -> bool:
    args = node.args
    params = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    return any(
        a.arg in _SESSION_PARAM_NAMES or "Session" in ast.dump(a.annotation or ast.Pass())
        for a in params
    )


def _logs_traceback(node: ast.Call) -> bool:
    """`logger.exception(...)` ou `exc_info=True`."""
    if getattr(node.func, "attr", "") == "exception":
        return True
    return any(
        kw.arg == "exc_info"
        and not (isinstance(kw.value, ast.Constant) and kw.value.value is False)
        for kw in node.keywords
    )


def _traceback_violations(tree: ast.Module, path: str) -> list[str]:
    """Traceback de `StatementError` carrega os bound parameters, e `artifact_key`
    é stem de filename: `redact_pii` (CPF + BRL) e o `_redact` por chave do
    formatter não alcançam nome próprio ali. Campos tipados, nunca traceback."""
    return [
        f"{path}:{n.lineno}: log com traceback em {_SINK_PACKAGE} — o traceback do "
        "driver carrega os bound parameters (PII). Use exc_info=False + campos "
        "tipados por shape (ADR-395)"
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and _logs_traceback(n)
    ]


def _public_session_params(tree: ast.Module, path: str) -> list[str]:
    """API pública do sink que aceita `Session` — o chamador voltaria a compartilhar."""
    return [
        f"{path}:{n.lineno}: `{n.name}` é público em {_SINK_PACKAGE} e aceita "
        "Session — o sink abre a sessão dele, senão o chamador volta a "
        "compartilhar a transação (ADR-395)"
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not n.name.startswith("_")
        and _accepts_session(n)
    ]


def _constructions_outside_sink(tree: ast.Module, path: str) -> list[str]:
    """Model de diagnóstico construído fora do sink."""
    owned = [n for n in sorted(OWNED_BY_SINK) if _binds_db_model(tree, n)]
    return [
        f"{path}:{n.lineno}: `{n.func.id}(...)` construído fora de {_SINK_PACKAGE} — "
        "escrita de diagnóstico tem um dono só (ADR-395)"
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in owned
    ]


def boundary_violations(src: str, path: str) -> list[str]:
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError as exc:
        return [f"{path}: parse error: {exc}"]
    if path.startswith(_SINK_PACKAGE):
        return _traceback_violations(tree, path) + _public_session_params(tree, path)
    return _constructions_outside_sink(tree, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    errors = collect_violations()
    for line in errors:
        print(line, file=sys.stderr)
    if args.verbose and not errors:
        print("OK: diagnóstico isolado da transição de run (ADR-395)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
