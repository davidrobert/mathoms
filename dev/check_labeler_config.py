#!/usr/bin/env python3
"""Proíbe glob negativo sob chave `any-glob-to-*` em .github/labeler.yml — em actions/labeler@v5 o negativo é avaliado como padrão próprio, então qualquer arquivo que NÃO seja o excluído satisfaz o "any" e a label casa sempre."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / ".github" / "labeler.yml"
ANY_KEY_PREFIX = "any-glob-to-"

REMEDIATION = """\
Correção — exclusão vive em `all-globs-to-all-files` (idiom da doc da v5,
onde o negativo precisa valer para TODOS os arquivos do PR):

  'area:x':
    - changed-files:
        - any-glob-to-any-file: ['src/**']
        - all-globs-to-all-files: ['!src/docs/**']

Se o path excluído já é coberto intencionalmente pelo glob positivo,
prefira remover o negativo — é mais barato que a semântica composta."""


@dataclass(frozen=True)
class NegativeGlobUnderAny:
    """Glob negativo numa chave `any-*`, que torna o matcher sempre verdadeiro."""

    label: str
    key: str
    glob: str

    def format(self) -> str:
        return f"[ANY-NEGATIVE] {self.label}: `{self.key}` contém `{self.glob}`"


def _as_glob_list(value: object) -> list[str]:
    """Normaliza o valor de um matcher — a v5 aceita string única ou lista."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _scan_matcher(label: str, matcher: dict[str, object]) -> list[NegativeGlobUnderAny]:
    """Coleta violações de um dict de matcher (`{any-glob-to-any-file: [...]}`)."""
    found: list[NegativeGlobUnderAny] = []
    for key, value in matcher.items():
        if not key.startswith(ANY_KEY_PREFIX):
            continue
        found += [
            NegativeGlobUnderAny(label, key, glob)
            for glob in _as_glob_list(value)
            if glob.startswith("!")
        ]
    return found


def _scan_node(label: str, node: object) -> list[NegativeGlobUnderAny]:
    """Desce recursivamente por `changed-files`, `all:` e `any:` até os matchers."""
    if isinstance(node, list):
        return [v for item in node for v in _scan_node(label, item)]
    if not isinstance(node, dict):
        return []
    found = _scan_matcher(label, node)
    for key, value in node.items():
        if not key.startswith(ANY_KEY_PREFIX):
            found += _scan_node(label, value)
    return found


def scan_config(config: dict[str, object]) -> list[NegativeGlobUnderAny]:
    """Varre todas as labels do arquivo de config do labeler."""
    return [v for label, node in config.items() for v in _scan_node(str(label), node)]


def _report(violations: list[NegativeGlobUnderAny], name: str) -> None:
    """Imprime as violações e como corrigir."""
    print(f"✗ {name}: {len(violations)} glob(s) negativo(s) sob `any-*`\n")
    for violation in violations:
        print(f"  {violation.format()}")
    print(
        "\nA label casa em TODO PR: o negativo satisfaz o `any` para qualquer\n"
        "arquivo que não seja o excluído.\n"
    )
    print(REMEDIATION)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    if not args.config.exists():
        print(f"✗ config do labeler não encontrada: {args.config}")
        return 1

    violations = scan_config(yaml.safe_load(args.config.read_text(encoding="utf-8")) or {})
    if not violations:
        print(f"✓ {args.config.name}: nenhum glob negativo sob chave `any-*`")
        return 0
    _report(violations, args.config.name)
    return 1


if __name__ == "__main__":
    sys.exit(main())
