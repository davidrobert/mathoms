#!/usr/bin/env python3
"""Coerência nav ↔ seção do `report_layout.yaml` (A40.l7 · RV3-04)."""
# `enabled: false` com entrada de nav viva entregava âncora morta em 100% dos
# relatórios — e o TÍTULO da seção desligada chegava ao cliente pelo drawer
# mobile, que foi por onde uma marca vazou (#1286). Mora fora do
# codegen_report_layout.py só por tamanho: aquele módulo está no teto de 500
# linhas do P2. O codegen chama `validate_nav_targets` ANTES de emitir —
# gerado que já contém o defeito não é gate.

from __future__ import annotations

from typing import Any

# Seções que o shell renderiza sem entrada em `sections`/`appendices`. Espelha
# SHELL_SECTION_TITLES em frontend/src/components/report/ReportShell.tsx; a
# paridade é travada por tests/test_report_layout_nav_targets.py.
SHELL_RENDERED_SECTIONS = frozenset({"V0"})


class NavTargetError(ValueError):
    """Entrada de nav aponta para seção que o relatório não vai renderizar."""


def declared_sections(layout: dict[str, Any]) -> tuple[set[str], set[str]]:
    """(ids declarados no YAML, ids desligados por `enabled: false`)."""
    est = layout["estrategico"]
    declared = (est.get("sections") or []) + (est.get("appendices") or [])
    return {s["id"] for s in declared}, {s["id"] for s in declared if not s.get("enabled", True)}


def _links(layout: dict[str, Any]) -> list[tuple[str, str]]:
    """Pares (modo, section_id) de toda entrada de nav/ToC."""
    nav = (layout.get("navigation") or {}).items()
    return [(mode, lnk["section_id"]) for mode, gs in nav for g in gs for lnk in g["links"]]


def _dead_link_reason(target: str, ids: set[str], disabled: set[str]) -> str | None:
    """Por que este alvo não é renderizável — ou None se estiver saudável."""
    if target in disabled:
        return "está `enabled: false`"
    if target not in ids and target not in SHELL_RENDERED_SECTIONS:
        return "não é seção nem apêndice"
    return None


def _dead_links(layout: dict[str, Any], ids: set[str], disabled: set[str]) -> list[str]:
    """Entradas de nav sem seção renderizada do outro lado."""
    return [
        f"navigation.{mode}: '{target}' {reason}"
        for mode, target in _links(layout)
        if (reason := _dead_link_reason(target, ids, disabled))
    ]


def _unlinked(layout: dict[str, Any], ids: set[str], disabled: set[str]) -> list[str]:
    """Direção inversa: seção habilitada que o índice não alcança."""
    linked = {target for _mode, target in _links(layout)}
    return [
        f"seção '{sid}' está habilitada mas não tem entrada de nav"
        for sid in sorted(ids - disabled - linked)
    ]


def validate_nav_targets(layout: dict[str, Any]) -> None:
    """Assert bidirecional entre `navigation` e as seções habilitadas."""
    ids, disabled = declared_sections(layout)
    problems = _dead_links(layout, ids, disabled) + _unlinked(layout, ids, disabled)
    if problems:
        raise NavTargetError(
            "coerência nav ↔ seção quebrada:\n  - "
            + "\n  - ".join(problems)
            + "\n\nLigue a seção, remova a entrada de nav, ou (se o shell a "
            "renderiza fora do YAML) declare o id em SHELL_RENDERED_SECTIONS."
        )
