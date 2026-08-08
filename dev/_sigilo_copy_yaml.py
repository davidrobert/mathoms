#!/usr/bin/env python3
"""Varredura §13 de copy que nasce em YAML de config (internals de ``dev/check_sigilo_terms.py``).

Superfície própria porque a semântica difere do line-scan das outras duas:
aqui parseamos o YAML e varremos os valores escalares. O parser descarta
comentário, então a atribuição §13.4 do rationale (``# ordem AUVP…``) fica
preservada sem precisar de um stripper de ``#`` — que o ``strip_comments``
do módulo principal não tem.

Caso de origem: ``config/report_layout.yaml`` titulava a seção 2.5 de
"Proteção Patrimonial — Pilar AUVP"; o título chega ao TOC do relatório via
codegen (ADR-076) sem tocar ``frontend/src/(app|components)``.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import yaml

# YAMLs de config cuja copy é renderizada ao usuário. Lista fechada: config
# não é user-facing por default — só entra arquivo com codegen para a UI.
COPY_YAML_FILES = frozenset({"config/report_layout.yaml"})


def is_copy_yaml(rel_path: str) -> bool:
    """True se rel_path é YAML de config cuja copy é renderizada ao usuário."""
    return rel_path in COPY_YAML_FILES


def _value_children(node: yaml.Node) -> list[yaml.Node]:
    """Filhos em posição de VALOR — chave de mapping fica de fora."""
    if isinstance(node, yaml.MappingNode):
        return [value for _key, value in node.value]
    if isinstance(node, yaml.SequenceNode):
        return list(node.value)
    return []


# Chave é nome de campo do schema (`title`, `id`), não copy. Em `chart_titles`
# a chave é o id do gráfico e o VALOR é o título renderizado — varrer valores
# cobre o caso sem gerar hit em id técnico.
def _string_values(node: yaml.Node) -> Iterator[tuple[int, str]]:
    """(line, valor) de cada escalar string em posição de valor."""
    if isinstance(node, yaml.ScalarNode) and node.tag.endswith(":str"):
        yield node.start_mark.line + 1, node.value
    for child in _value_children(node):
        yield from _string_values(child)


# Varre TODO valor string em vez de allowlist de chaves (`title`/`label`):
# `chart_titles` e `navigation[].label` já são copy fora desse trio, e chave
# nova entraria sem gate — verde falso.
def find_hits(path: Path, pattern: re.Pattern[str]) -> list[tuple[int, str, str]]:
    """Hits de `pattern` nos valores string do YAML: (line, termo, linha crua)."""
    try:
        content = path.read_text(encoding="utf-8")
        root = yaml.compose(content)
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return []
    if root is None:
        return []
    lines = content.splitlines()
    return [
        (line_no, match.group(1), lines[line_no - 1].strip())
        for line_no, value in _string_values(root)
        for match in pattern.finditer(value)
        if line_no <= len(lines)
    ]
