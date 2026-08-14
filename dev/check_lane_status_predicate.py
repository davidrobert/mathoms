#!/usr/bin/env python3
"""Deriva o predicado de `status` de lane de `depends_on` e falha nos dois sentidos."""
# O predicado é decisão do dono (2026-08-03, docs/sprint/A40/_README.md §Predicado
# do campo `status` de lane) e vinha sendo convenção manual. A sprint mediu TRÊS
# violações em dois dias, nos DOIS sentidos, e nenhuma foi pega por leitura da vault
# — só por varredura que cruzou frontmatter com commits de origin/main:
#
#   - `open` com dep pendente MENTE PARA CIMA: vira armadilha de pickup (quem segue
#     a ordem óbvia do SPRINT_CURRENT pega lane que não termina).
#   - `blocked` com todas as deps terminais MENTE PARA BAIXO: a lane some do
#     SPRINT_CURRENT justamente quando fica pegável (aconteceu com uma P0).
#
# O sentido "para baixo" já rodava como check *advisory* dentro da skill
# lane-closeout (check_stale_blocked); aqui ele vira gate e ganha o inverso.
#
# A 2ª cláusula do predicado ("ou a lane declara amarra explícita de entrega
# parcial") não é derivável de prosa — exige campo. É o `partial_delivery` do
# schema, e ele é declaração do autor, não inferência: precedentes A40.l20,
# A40.l27 e A40.l60 entregam parte e declaram por escrito o que fica de fora.

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"

# `shipped`/`cancelled` são os únicos estados que satisfazem uma dependência.
# `planned`/`open`/`in_progress`/`blocked` deixam a dep pendente.
TERMINAL_STATUS: frozenset[str] = frozenset({"shipped", "cancelled"})

# `[[Alvo]]`, `[[Alvo|apelido]]`, `[[Alvo#anchor]]` — captura só o alvo.
WIKILINK_TARGET_RE = re.compile(r"^\[\[([^\]|#]+)")


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return {}


def _dependency_ids(front: dict[str, Any]) -> list[str]:
    """Alvos de `depends_on`, sem os colchetes do wikilink."""
    out: list[str] = []
    for raw in front.get("depends_on") or []:
        match = WIKILINK_TARGET_RE.match(str(raw))
        if match:
            out.append(match.group(1).strip())
    return out


def _display_path(path: Path) -> str:
    """Caminho relativo ao repo quando aplicável — em vault sintética de teste,
    o absoluto. `relative_to` levanta fora do repo e derrubava os testes."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def collect_lanes(docs_root: Path) -> dict[str, dict[str, Any]]:
    """Mapa id → frontmatter de toda nota `type: lane` do vault."""
    lanes: dict[str, dict[str, Any]] = {}
    for path in sorted(docs_root.glob("sprint/*/lanes/*.md")):
        front = _frontmatter(path)
        if front.get("type") != "lane" or not front.get("id"):
            continue
        front["_path"] = _display_path(path)
        lanes[str(front["id"])] = front
    return lanes


def _pending_dependencies(front: dict[str, Any], lanes: dict[str, dict[str, Any]]) -> list[str]:
    """Deps que existem no vault e ainda não estão terminais. Dep inexistente é
    problema de `check_doc_graph_refs`, não deste gate — ignorar evita dois gates
    reclamando do mesmo defeito com mensagens diferentes."""
    pending: list[str] = []
    for dep_id in _dependency_ids(front):
        dep = lanes.get(dep_id)
        if dep is not None and dep.get("status") not in TERMINAL_STATUS:
            pending.append(f"{dep_id} ({dep.get('status')})")
    return pending


def _known_dependency_count(front: dict[str, Any], lanes: dict[str, dict[str, Any]]) -> int:
    return sum(1 for dep_id in _dependency_ids(front) if dep_id in lanes)


def _violation_open_with_pending(
    lane_id: str, front: dict[str, Any], lanes: dict[str, dict[str, Any]]
) -> str | None:
    """`open` exige toda dep terminal — salvo amarra de entrega parcial declarada."""
    if front.get("status") != "open":
        return None
    if front.get("partial_delivery") is True:
        return None
    pending = _pending_dependencies(front, lanes)
    if not pending:
        return None
    return (
        f"{front['_path']}: {lane_id} está `open` com dependência pendente "
        f"({', '.join(pending)}). Vire para `blocked`, OU declare "
        f"`partial_delivery: true` e escreva na lane o que fica de fora."
    )


def _violation_blocked_but_free(
    lane_id: str, front: dict[str, Any], lanes: dict[str, dict[str, Any]]
) -> str | None:
    """`blocked` cujas deps já shipparam some do SPRINT_CURRENT quando fica pegável."""
    if front.get("status") != "blocked":
        return None
    if _known_dependency_count(front, lanes) == 0:
        return None  # bloqueador externo (precedente F12.2-F12.8) — não derivável
    if _pending_dependencies(front, lanes):
        return None
    return (
        f"{front['_path']}: {lane_id} está `blocked` mas TODAS as dependências "
        f"declaradas já são terminais. Vire para `open` — hoje a lane está "
        f"invisível no SPRINT_CURRENT justamente por ter ficado pegável."
    )


_CHECKS = (_violation_open_with_pending, _violation_blocked_but_free)


def _lane_violations(
    lane_id: str, front: dict[str, Any], lanes: dict[str, dict[str, Any]]
) -> list[str]:
    """Erros do predicado para uma lane — os dois sentidos."""
    found = (check(lane_id, front, lanes) for check in _CHECKS)
    return [problem for problem in found if problem]


def find_violations(lanes: dict[str, dict[str, Any]]) -> list[str]:
    """Erros do predicado, nos dois sentidos, ordenados por id de lane."""
    violations: list[str] = []
    for lane_id, front in sorted(lanes.items()):
        violations.extend(_lane_violations(lane_id, front, lanes))
    return violations


def main() -> int:
    violations = find_violations(collect_lanes(DOCS))
    if not violations:
        return 0
    print("Predicado de `status` de lane violado:\n", file=sys.stderr)
    for violation in violations:
        print(f"  - {violation}", file=sys.stderr)
    print(
        "\nPredicado (docs/sprint/A40/_README.md §Predicado do campo `status` de lane):\n"
        "  open  ⇔ pegável E terminável agora — toda dep terminal, ou `partial_delivery: true`\n"
        "  blocked ⇔ liberada, retida por bloqueador declarado",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
