#!/usr/bin/env python3
"""Vocabulário compartilhado do ledger: os 5 vereditos fail-closed da rubrica + o
resultado de uma transição de stage. Módulo próprio desde a A42.l3 para quebrar o ciclo
entre ``dev.ledger_conservation`` (que re-exporta as duas pernas) e ``dev.ledger_e2e3``
(que precisa dos vereditos). Sem código — só o contrato.
"""

from __future__ import annotations

from dataclasses import dataclass

# Vereditos fail-closed (rubrica ledger-certify).
CONSERVADO = "conservado"
COBERTO_SEM_VALOR = "coberto-sem-verificação-de-valor"
DEDUP_LEGITIMO = "dedup/transfer-legítimo"
PERDA_SILENCIOSA = "perda/dupla-contagem-silenciosa"  # P0
NAO_VERIFICAVEL = "não-verificável"


@dataclass(frozen=True)
class ConservationResult:
    transition: str  # "E2->E3" | "E3->E4"
    count_in: int
    count_out: int
    value_in_cents: int | None
    value_out_cents: int | None
    dups: int
    verdict: str
    detail: str
    # Termos que a perna E2→E3 declarava em PROSA sem computar (A42.l3, item 8).
    # `semeado` é a população E2 ANTES do filtro de reconciliabilidade: a diferença
    # `semeado - count_in` existia e nenhuma linha do relatório a declarava.
    semeado: int | None = None
    exclusoes_run: int | None = None
    # `count_in - count_out - exclusoes_run`. POSITIVO = rows que entraram no reconcile
    # e não estão em artefato nem em canal declarado (perda). NEGATIVO = as exclusões
    # declaradas EXCEDEM o gap (sobre-declaração). `None` = não computável.
    residuo: int | None = None
