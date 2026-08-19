#!/usr/bin/env python3
"""A40.l69 (3b · [[ADR-394]] §Emenda (b) D8) — chave de membro não casa por substring.

`titular_key in nome` casa DENTRO de nome alheio: `"ana"` entra em `"mariana"`,
`"luis"` em `"luisa"`. Medido em 4 de 5 pares plausíveis. O casamento canônico é
`matches_member_key(chave, texto)`, por token normalizado.

**A distinção que decide o gate é o TIPO do lado direito**, não a sintaxe:

- `chave in <string>`  → defeito, é o que este gate recusa;
- `chave in <coleção>` → uso legítimo (`key not in keys_seen`, `papel not in
  ("titular", "conjuge")`) e passa.

Um gate por regex não separa os dois — casaria as 38 linhas do repo, das quais 3
são membership em coleção. Daí ser AST: o lado direito é classificado por forma
(literal de tupla/lista/set/dict, comprehension, `.keys()`, nome plural
declarado) antes de virar violação.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SCAN_DIRS = ("pipeline", "backend/app", "scripts")

# Nome que denota chave de membro — o lado ESQUERDO do `in`.
_KEY_SUFFIXES = ("titular_key", "conjuge_key")

# Lado direito que é comprovadamente coleção. Sufixo, não nome inteiro: o que
# importa é a forma declarada, e `keys_seen`/`member_keys`/`_by_key` são plurais
# de chave, nunca texto livre.
_COLLECTION_SUFFIXES = ("_seen", "_keys", "_set", "_map", "_index", "_by_key", "_ids")

# `(path, linha)` com motivo escrito. Entrada nova aqui é decisão consciente.
ALLOWLIST: dict[tuple[str, int], str] = {}


def _is_member_key(node: ast.expr) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr in _KEY_SUFFIXES
    if isinstance(node, ast.Name):
        return node.id.lower().lstrip("_") in _KEY_SUFFIXES
    return False


def _is_collection(node: ast.expr) -> bool:
    """Lado direito comprovadamente não-string, pela forma."""
    if isinstance(node, (ast.Tuple, ast.List, ast.Set, ast.Dict)):
        return True
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr in ("keys", "values", "items")
    if isinstance(node, ast.Name):
        return node.id.endswith(_COLLECTION_SUFFIXES)
    if isinstance(node, ast.Attribute):
        return node.attr.endswith(_COLLECTION_SUFFIXES)
    return False


def violations_in(path: Path) -> list[str]:
    rel = path.relative_to(REPO_ROOT).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        if not isinstance(node.ops[0], (ast.In, ast.NotIn)):
            continue
        if not _is_member_key(node.left) or _is_collection(node.comparators[0]):
            continue
        if (rel, node.lineno) in ALLOWLIST:
            continue
        out.append(f"{rel}:{node.lineno}: chave de membro casando por substring")
    return out


def main() -> int:
    files = [p for d in SCAN_DIRS for p in (REPO_ROOT / d).rglob("*.py")]
    violations = [v for p in sorted(files) for v in violations_in(p)]
    if not violations:
        return 0
    print("Chave de membro casando por substring (A40.l69 · ADR-394 D8):\n", file=sys.stderr)
    for v in violations:
        print(f"  - {v}", file=sys.stderr)
    print(
        "\nUse `matches_member_key(chave, texto)` "
        "(pipeline/domain/services/member_key_matcher.py).\n"
        "`chave in <coleção>` é legítimo e não cai aqui — se caiu, o lado direito "
        "não se declara como coleção; renomeie ou adicione à ALLOWLIST com motivo.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
