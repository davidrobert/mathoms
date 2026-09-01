#!/usr/bin/env python3
"""Drift fresco↔persistido do E3, por grupo — divergência é drift, não perda. Extraído
de ``dev.ledger_certify_core`` na A42.l3, quando o núcleo bateu as 500 linhas ao ganhar a
âncora do LC5-03. Funções puras; o count vem normalizado pelos canais de ``remocoes``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.ledger_conservation import declared_removed_count


@dataclass
class DriftSummary:
    """Sumário do cross-check fresco↔persistido (drift, não perda)."""

    matched: int
    count_diff: list
    fresh_only: list
    persisted_only: list


# A42.l20 — somar só `transacoes_duplicadas_removidas` lia apenas o canal
# `cross_file_dedup`: um canal declarado (o colapso cross-documento) saía como *count
# divergente*. `declared_removed_count` é o mesmo normalizador da conservação E2→E3, e
# degrada ao campo legado quando o artefato não tem `remocoes`.
def _e3_count(payload) -> int:
    """População que o grupo PRESTA CONTA: sobreviventes + remoções declaradas."""
    if not isinstance(payload, dict):
        return -1
    return int(payload.get("transacoes_total", 0)) + declared_removed_count(payload)


def _count_diffs(fresh_e3: dict, persisted_e3: dict) -> tuple[int, list[str]]:
    matched, diffs = 0, []
    for key, fresh in fresh_e3.items():
        pers = persisted_e3.get(key)
        if pers is None:
            continue
        f_n, p_n = _e3_count(fresh), _e3_count(pers)
        (diffs.append(f"{key}: n_tx fresco {f_n} != persistido {p_n}") if f_n != p_n else None)
        matched += int(f_n == p_n)
    return matched, diffs


def _drift(fresh_e3: dict, persisted_e3: dict) -> DriftSummary:
    """Cross-check fresco↔persistido por grupo — divergência = drift (reporta, não falha)."""
    # O count vem normalizado pelos canais de `remocoes` (ver `_e3_count`), então remoção
    # DECLARADA dos dois lados não é divergência. O que sobra tem TRÊS causas: keying/dedup
    # mudou pós-run, artefato de run parcial, OU a config do harness diverge da do run
    # (ex.: `collapse_enforce`) num eixo que nenhum canal declara. Atribuir só as duas
    # primeiras foi o defeito da A42.l20.
    matched, count_diff = _count_diffs(fresh_e3, persisted_e3)
    return DriftSummary(
        matched=matched,
        count_diff=count_diff,
        fresh_only=sorted(set(fresh_e3) - set(persisted_e3)),
        persisted_only=sorted(set(persisted_e3) - set(fresh_e3)),
    )
