#!/usr/bin/env python3
"""Gates de glob em .github/labeler.yml e nas matrizes `files_yaml` dos workflows: (1) glob negativo sob `any-glob-to-*` faz a label casar em todo PR; (2) `**` colado a texto no mesmo segmento não cruza `/` e casa muito menos do que aparenta."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / ".github" / "labeler.yml"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
ANY_KEY_PREFIX = "any-glob-to-"

# `**` vira globstar só como segmento inteiro; colado a texto, compila para
# `[^/]*` e para na primeira barra.
_GLUED_GLOBSTAR = re.compile(r"(?:^|(?<=/))\*\*(?=[^/])")

REMEDIATION_NEGATIVE = """\
Correção — exclusão vive em `all-globs-to-all-files` (idiom da doc da v5,
onde o negativo precisa valer para TODOS os arquivos do PR):

  'area:x':
    - changed-files:
        - any-glob-to-any-file: ['src/**']
        - all-globs-to-all-files: ['!src/docs/**']

Se o path excluído já é coberto intencionalmente pelo glob positivo,
prefira remover o negativo — é mais barato que a semântica composta."""

REMEDIATION_GLOBSTAR = """\
Correção — use `**/*.ext` no lugar de `**.ext`. `config/**.yaml` compila para
`config/[^/]*\\.yaml`: casa config/pipeline.json-vizinhos na raiz e ignora
config/prompts/*.yaml. `config/**/*.yaml` casa os dois, igual em minimatch
(actions/labeler) e micromatch (tj-actions/changed-files).

Medido 2026-08-03: `**.go` casava 0 dos 14 arquivos .go no minimatch, e
`config/**.yaml` deixava os 5 prompts fora do filtro `pipeline` do ci.yml.

CUIDADO em glob NEGATIVO: ali alargar a exclusão ESTREITA o gate. `!**.md`
virar `!**/*.md` tiraria 22 .md fora de docs/ do job que roda o gate de PII —
a forma certa foi `!*.md`, que fixa o comportamento medido. A sugestão acima é
mecânica; em `!…` confirme a intenção antes de aplicar."""


@dataclass(frozen=True)
class NegativeGlobUnderAny:
    """Glob negativo numa chave `any-*`, que torna o matcher sempre verdadeiro."""

    label: str
    key: str
    glob: str

    def format(self) -> str:
        return f"[ANY-NEGATIVE] {self.label}: `{self.key}` contém `{self.glob}`"


@dataclass(frozen=True)
class GluedGlobstar:
    """`**` colado a texto no mesmo segmento — não desce em subpasta."""

    label: str
    key: str
    glob: str

    def format(self) -> str:
        suggestion = suggest_globstar(self.glob)
        fix = f" → use `{suggestion}`" if suggestion else ""
        return f"[GLUED-GLOBSTAR] {self.label}: `{self.key}` contém `{self.glob}`{fix}"


def suggest_globstar(glob: str) -> str | None:
    """Reescreve `a/**.ext` como `a/**/*.ext`; devolve None se não houver troca óbvia."""
    negated, bare = glob.startswith("!"), glob.lstrip("!")
    fixed = _GLUED_GLOBSTAR.sub("**/*", bare)
    if fixed == bare:
        return None
    return f"!{fixed}" if negated else fixed


def _is_glued(glob: str) -> bool:
    """True se algum segmento contém `**` sem ser exatamente `**`."""
    return any(seg != "**" and "**" in seg for seg in glob.lstrip("!").split("/"))


def _as_glob_list(value: object) -> list[str]:
    """Normaliza o valor de um matcher — a v5 aceita string única ou lista."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _iter_node(label: str, node: object) -> Iterator[tuple[str, str, str]]:
    """Desce por `changed-files`, `all:` e `any:` emitindo (label, chave, glob)."""
    if isinstance(node, list):
        for item in node:
            yield from _iter_node(label, item)
        return
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        globs = _as_glob_list(value)
        for glob in globs:
            yield label, str(key), glob
        if not globs:
            yield from _iter_node(label, value)


def iter_globs(config: dict[str, object]) -> Iterator[tuple[str, str, str]]:
    """Emite (label, chave de matcher, glob) para toda label do labeler."""
    for label, node in config.items():
        yield from _iter_node(str(label), node)


def iter_workflow_globs(filters: dict[str, object]) -> Iterator[tuple[str, str, str]]:
    """`files_yaml` é `{grupo: [globs]}` — sem chave de matcher intermediária."""
    for group, globs in filters.items():
        for glob in _as_glob_list(globs):
            yield str(group), "files_yaml", glob


def scan_config(config: dict[str, object]) -> list[NegativeGlobUnderAny]:
    """Negativos sob `any-*` em todas as labels do arquivo de config do labeler."""
    return [
        NegativeGlobUnderAny(label, key, glob)
        for label, key, glob in iter_globs(config)
        if key.startswith(ANY_KEY_PREFIX) and glob.startswith("!")
    ]


def scan_globstars(triples: Iterable[tuple[str, str, str]]) -> list[GluedGlobstar]:
    """`**` colado, em qualquer chave — glob errado é errado sob `any-*` e `all-*`."""
    return [GluedGlobstar(label, key, glob) for label, key, glob in triples if _is_glued(glob)]


def _find_files_yaml(node: object) -> str | None:
    """Acha o bloco `files_yaml:` do step tj-actions/changed-files no workflow."""
    if isinstance(node, dict):
        value = node.get("files_yaml")
        if isinstance(value, str):
            return value
        return next((found for found in map(_find_files_yaml, node.values()) if found), None)
    if isinstance(node, list):
        return next((found for found in map(_find_files_yaml, node) if found), None)
    return None


def load_workflow_filters(path: Path) -> dict[str, object]:
    """Extrai a matriz `files_yaml` do ci.yml — YAML aninhado como string."""
    block = _find_files_yaml(yaml.safe_load(path.read_text(encoding="utf-8")))
    return yaml.safe_load(block) or {} if block else {}


def _report(findings: list[object], targets: str) -> None:
    """Imprime as violações e só a remediação das classes presentes."""
    print(f"✗ {targets}: {len(findings)} glob(s) com problema\n")
    for finding in findings:
        print(f"  {finding.format()}")  # type: ignore[attr-defined]
    if any(isinstance(f, NegativeGlobUnderAny) for f in findings):
        print(
            "\nA label casa em TODO PR: o negativo satisfaz o `any` para qualquer\n"
            "arquivo que não seja o excluído.\n"
        )
        print(REMEDIATION_NEGATIVE)
    if any(isinstance(f, GluedGlobstar) for f in findings):
        print("\nO glob casa só a raiz do prefixo — subpasta fica de fora.\n")
        print(REMEDIATION_GLOBSTAR)


def _scan_workflows(paths: Iterable[Path]) -> tuple[list[str], list[GluedGlobstar]]:
    """Varre cada workflow que declare `files_yaml`; ignora os que não têm."""
    names: list[str] = []
    findings: list[GluedGlobstar] = []
    for path in sorted(paths):
        filters = load_workflow_filters(path)
        if not filters:
            continue
        names.append(path.name)
        findings += scan_globstars(iter_workflow_globs(filters))
    return names, findings


def _scan_all(config_path: Path, workflow_dir: Path) -> tuple[str, list[object]]:
    """Junta labeler + workflows num par (alvos legíveis, achados)."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    findings: list[object] = [*scan_config(config), *scan_globstars(iter_globs(config))]
    wf_names, wf_findings = _scan_workflows(workflow_dir.glob("*.yml"))
    return " + ".join([config_path.name, *wf_names]), findings + wf_findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--workflow-dir", type=Path, default=WORKFLOW_DIR)
    args = parser.parse_args()

    if not args.config.exists():
        print(f"✗ config do labeler não encontrada: {args.config}")
        return 1

    targets, findings = _scan_all(args.config, args.workflow_dir)
    if not findings:
        print(f"✓ {targets}: nenhum negativo sob `any-*`, nenhum `**` colado")
        return 0
    _report(findings, targets)
    return 1


if __name__ == "__main__":
    sys.exit(main())
