#!/usr/bin/env python3
"""Toda FK para ``pipeline_runs``/``pipeline_artifacts`` é classificada (ADR-371).

Contexto: o expurgo de 2026-05-15 apagou a subárvore de ``pipeline_runs``
enumerando as tabelas-filhas **à mão** em ``purge_documents``, porque o
``PRAGMA foreign_keys`` estava OFF. A lista esqueceu ``reports``,
``planner_review_metadata`` e ``pipeline_run_costs``, e o DB de dogfood
ficou com 48 rows penduradas. Consertar as três tabelas fecharia a
*instância*; este gate fecha a *classe* — a próxima tabela-filha nova
não pode entrar sem classificação.

**Por que AST e não ``Base.metadata``.** Importar os models puxa config,
Fernet e env do backend dentro de um hook de pre-commit. Pior: o lado
"declarado" e o lado "verificado" viriam do mesmo objeto Python, e o
gate ficaria auto-referente — verde durante todo o drift. As duas
metades aqui são independentes: os ``ForeignKey(...)`` dos models e o
registry ``REFERENCING_COLUMNS`` de ``artifact_references.py``.

Regras:

- **R1** — coluna com FK para ``pipeline_artifacts.id`` tem que estar em
  ``REFERENCING_COLUMNS``. É o conjunto que toda rotina de deleção
  consulta antes de apagar; ficar de fora significa ser destruída em
  silêncio (``SET NULL``/``CASCADE``) ou abortar o batch (``RESTRICT``).
- **R2** — FK para ``pipeline_runs.id`` ou ``pipeline_artifacts.id`` tem
  que declarar ``ondelete=``. Sem ele o grafo não sabe o que fazer e
  alguém volta a enumerar filhas na mão.
- **R3** — coluna cujo nome referencia run/artifact sem FK precisa de
  justificativa explícita no allowlist abaixo.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODELS_DIR = _REPO_ROOT / "backend" / "app" / "models"
_REGISTRY = _REPO_ROOT / "backend" / "app" / "services" / "storage" / "artifact_references.py"

_ARTIFACT_TARGET = "pipeline_artifacts.id"
_RUN_TARGET = "pipeline_runs.id"

# Colunas que nomeiam run/artifact e legitimamente NÃO têm FK (R3).
# Cada entrada carrega o porquê — allowlist sem justificativa é dívida.
_SOFT_REFERENCE_ALLOWLIST = {
    # Telemetria de custo (ADR-260) sobrevive de propósito ao run: FinOps
    # agrega gasto por período, não por run vivo. Cascatear apagaria o
    # histórico de custo junto com o expurgo do run.
    ("llm_call_log.py", "pipeline_run_id"),
}

_SUSPICIOUS_NAMES = ("pipeline_run_id", "analysis_artifact_id", "artifact_id", "e5_artifact_id")


def _foreign_key_call(node: ast.AST) -> ast.Call | None:
    if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "ForeignKey":
        return node
    return None


def _fk_target(call: ast.Call) -> str | None:
    if call.args and isinstance(call.args[0], ast.Constant):
        return str(call.args[0].value)
    return None


def _ondelete(call: ast.Call) -> str | None:
    for kw in call.keywords:
        if kw.arg == "ondelete" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return None


def _assignments(tree: ast.Module) -> list[ast.AnnAssign | ast.Assign]:
    return [n for n in ast.walk(tree) if isinstance(n, (ast.AnnAssign, ast.Assign))]


def _target_name(node: ast.AnnAssign | ast.Assign) -> str | None:
    target = node.target if isinstance(node, ast.AnnAssign) else (node.targets or [None])[0]
    return target.id if isinstance(target, ast.Name) else None


def _class_of(tree: ast.Module, node: ast.AST) -> str | None:
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        if any(child is node for child in ast.walk(cls)):
            return cls.name
    return None


def _declared_registry() -> set[tuple[str, str]]:
    """`{(Classe, coluna)}` de `REFERENCING_COLUMNS` em artifact_references.py."""
    tree = ast.parse(_REGISTRY.read_text(encoding="utf-8"))
    for node in _assignments(tree):
        if _target_name(node) != "REFERENCING_COLUMNS":
            continue
        value = node.value if isinstance(node, ast.Assign) else node.value
        if not isinstance(value, ast.Tuple):
            continue
        return {
            (e.value.id, e.attr)
            for e in value.elts
            if isinstance(e, ast.Attribute) and isinstance(e.value, ast.Name)
        }
    return set()


def _collect_violations(registry: set[tuple[str, str]]) -> list[str]:
    problems: list[str] = []
    for path in sorted(_MODELS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in _assignments(tree):
            problems.extend(_check_column(path, tree, node, registry))
    return problems


def _check_column(path: Path, tree: ast.Module, node, registry: set[tuple[str, str]]) -> list[str]:
    column = _target_name(node)
    if column is None:
        return []
    call = next((c for c in ast.walk(node) if _foreign_key_call(c)), None)
    if call is None:
        return _check_soft_reference(path, column, node)
    target = _fk_target(call)
    if target not in (_ARTIFACT_TARGET, _RUN_TARGET):
        return []
    cls = _class_of(tree, node) or "?"
    out: list[str] = []
    if _ondelete(call) is None:
        out.append(f"{path.name}:{cls}.{column} — FK para {target} sem ondelete= (R2)")
    if target == _ARTIFACT_TARGET and (cls, column) not in registry:
        out.append(
            f"{path.name}:{cls}.{column} — FK para pipeline_artifacts fora de "
            f"REFERENCING_COLUMNS em artifact_references.py (R1)"
        )
    return out


def _check_soft_reference(path: Path, column: str, node) -> list[str]:
    if column not in _SUSPICIOUS_NAMES:
        return []
    if (path.name, column) in _SOFT_REFERENCE_ALLOWLIST:
        return []
    if not any(isinstance(n, ast.Call) for n in ast.walk(node)):
        return []
    return [
        f"{path.name}:{column} — nomeia run/artifact mas não declara ForeignKey; "
        f"adicione a FK ou justifique em _SOFT_REFERENCE_ALLOWLIST (R3)"
    ]


def main() -> int:
    registry = _declared_registry()
    if not registry:
        print("ERRO: REFERENCING_COLUMNS não encontrado em artifact_references.py", file=sys.stderr)
        return 1
    problems = _collect_violations(registry)
    if problems:
        print("FK para pipeline_runs/pipeline_artifacts sem classificação (ADR-371):\n")
        for p in problems:
            print(f"  - {p}")
        print("\nVer docstring de dev/check_run_artifact_fk_coverage.py para as regras.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
