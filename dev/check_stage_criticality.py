#!/usr/bin/env python3
"""Criticidade de stage: a cabeça do pipeline é `required`, e a cauda decide explicitamente."""

# Contexto (A40.l18 · ADR-357 §1). `StageSpec.criticality` governa o raio de
# explosão da não-entrega de um stage. O default é fail-closed (`required`), o
# que protege a cabeça do pipeline mas cria um buraco na cauda: um add-on
# advisory novo inserido depois de `analyze_finances` herdaria `required` em
# silêncio e voltaria a destruir o entregável — o incidente de origem (run
# 2ded7aab: E5 completo em `pipeline_artifacts`, relatório nunca derivado).
#
# **Duas regras, não uma — e a segunda não é a recíproca da primeira.**
#
# 1. Todo stage até `analyze_finances` (inclusive) é `required`. Metade provada:
#    é o invariante que a ADR-357 §1 declara ("`analyze_finances` é o último
#    stage `required`").
#
# 2. Todo stage APÓS `analyze_finances` declara `criticality=` explicitamente —
#    com qualquer valor. NÃO exigimos que seja `degradable`.
#
# A regra 2 existe porque o §Delta do co-design (2026-08-06, item 3) recusou a
# recíproca — *"todo stage após `analyze_finances` é `degradable`"* — por forçar
# `validate_cross` para dentro da classe por CI e transformar questão semântica
# em invariante de pipeline. Mas o §Critério de aceite da mesma lane pede o gate
# nas duas direções, com a justificativa *"falha se alguém inserir stage no meio
# sem decidir"*. As duas seções se contradizem.
#
# Exigir DECLARAÇÃO em vez de VALOR entrega o que o §Critério de aceite quer
# (stage novo na cauda não passa sem decisão) sem o que o §Delta recusa (o CI
# não escolhe o valor). Ver a nota de reconciliação na lane.
#
# **Por que AST e não import.** O default do dataclass é indistinguível do valor
# explícito em runtime: `spec.criticality == "required"` é o mesmo objeto tenha
# o autor decidido ou esquecido. A declaração só existe no texto do código.

from __future__ import annotations

import ast
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_STAGE_SPEC = _REPO_ROOT / "pipeline" / "stage_spec.py"

_LAST_REQUIRED_STAGE = "analyze_finances"
_VALID = ("required", "degradable")


def _module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _assigned_value(tree: ast.Module, name: str) -> ast.expr | None:
    """Valor da atribuição top-level `name = ...` (aceita anotada)."""
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == name:
            return node.value
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == name for t in node.targets
        ):
            return node.value
    return None


def _full_order(tree: ast.Module) -> list[str]:
    node = _assigned_value(tree, "FULL_ORDER")
    if not isinstance(node, ast.List):
        raise SystemExit("check_stage_criticality: FULL_ORDER não é literal de lista")
    return [e.value for e in node.elts if isinstance(e, ast.Constant)]


def _kwarg(call: ast.Call, name: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _registry_calls(tree: ast.Module) -> dict[str, ast.Call]:
    """`{stage: nó da chamada StageSpec(...)}` a partir do literal de STAGE_REGISTRY."""
    node = _assigned_value(tree, "STAGE_REGISTRY")
    if not isinstance(node, ast.Dict):
        raise SystemExit("check_stage_criticality: STAGE_REGISTRY não é literal de dict")
    calls: dict[str, ast.Call] = {}
    for key, value in zip(node.keys, node.values):
        if isinstance(key, ast.Constant) and isinstance(value, ast.Call):
            calls[key.value] = value
    return calls


def _declared_criticality(call: ast.Call) -> str | None:
    """Valor literal de `criticality=`; `None` quando o autor não declarou."""
    node = _kwarg(call, "criticality")
    return node.value if isinstance(node, ast.Constant) else None


def _check_head(stage: str, declared: str | None) -> list[str]:
    effective = declared or "required"
    if effective != "required":
        return [
            f"{stage}: está em FULL_ORDER até {_LAST_REQUIRED_STAGE} e declara "
            f"criticality={effective!r}. A ADR-357 §1 declara {_LAST_REQUIRED_STAGE} como o "
            f"último stage required — degradar a cabeça entrega relatório sem os dados dele."
        ]
    return []


def _check_tail(stage: str, declared: str | None) -> list[str]:
    if declared is None:
        return [
            f"{stage}: vem depois de {_LAST_REQUIRED_STAGE} e NÃO declara criticality=. "
            f"O default é 'required' (fail-closed), então a não-entrega deste stage vai "
            f"destruir o relatório — reintroduzindo o incidente que a ADR-357 fechou. "
            f"Decida: criticality='degradable' (add-on advisory) ou criticality='required' "
            f"(explicitamente crítico, e justifique no registry)."
        ]
    return []


def _check_commit_flag(stage: str, declared: str | None, call: ast.Call) -> list[str]:
    node = _kwarg(call, "commit_artifacts_on_degrade")
    if node is None or (declared or "required") == "degradable":
        return []
    return [
        f"{stage}: declara commit_artifacts_on_degrade mas é required — a flag só é lida "
        f"em degradação, então é config morta. Remova, ou marque o stage degradable."
    ]


def _check_stage(stage: str, call: ast.Call | None, *, in_head: bool) -> list[str]:
    if call is None:
        return [f"{stage}: está em FULL_ORDER mas não tem StageSpec em STAGE_REGISTRY"]
    declared = _declared_criticality(call)
    if declared is not None and declared not in _VALID:
        return [f"{stage}: criticality={declared!r} inválido — use um de {_VALID}"]
    checked = _check_head(stage, declared) if in_head else _check_tail(stage, declared)
    return checked + _check_commit_flag(stage, declared, call)


def _collect_errors(tree: ast.Module) -> tuple[list[str], int, int]:
    """`(erros, índice de corte, total de stages)`."""
    order = _full_order(tree)
    calls = _registry_calls(tree)
    if _LAST_REQUIRED_STAGE not in order:
        raise SystemExit(f"check_stage_criticality: {_LAST_REQUIRED_STAGE} ausente de FULL_ORDER")
    cutoff = order.index(_LAST_REQUIRED_STAGE)
    errors: list[str] = []
    for idx, stage in enumerate(order):
        errors += _check_stage(stage, calls.get(stage), in_head=idx <= cutoff)
    return errors, cutoff, len(order)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    errors, cutoff, total = _collect_errors(_module(Path(args[0]) if args else _STAGE_SPEC))
    if errors:
        print("Criticidade de stage inconsistente (ADR-357 §1):\n")
        for e in errors:
            print(f"  - {e}\n")
        return 1
    print(
        f"criticality OK: {cutoff + 1} stages required até {_LAST_REQUIRED_STAGE}, "
        f"{total - cutoff - 1} na cauda"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
