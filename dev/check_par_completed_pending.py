#!/usr/bin/env python3
"""`(completed, pending)` não nasce de novo — prova de fecho da A40.l84 (RV8-08).

Uso: ``python3 dev/check_par_completed_pending.py`` (exit 1 = par novo; 0 = ok/vazio).
Lê o DB de ``MATHOMS_DATABASE_URL``. É CLI própria de propósito: o
``preflight_unified_review`` que o consome não é citado por nenhuma ``SKILL.md``, e um
predicado que só roda dentro de uma rodada unificada morre em silêncio quando a rodada
para de acontecer.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

# Runs r7 (2026-08-18) e r8 (2026-08-24), anteriores ao fecho da lane e PRESERVADOS:
# marcá-los `approved` diria que alguém conferiu, e ninguém conferiu (doutrina da ADR-417
# D3, que recusou `dismissed` pelo mesmo motivo). Congelados por ID para o check medir
# QUAIS e nunca QUANTOS — contador diz "2, ok" com uma row nova entrando e outra saindo
# por `ON DELETE CASCADE`.
PAR_HISTORICO = frozenset(
    {
        "33514dc4-115b-45fe-8976-03e25ba971c8",
        "d0f6260a-10f5-4b9c-82d0-dcf36650b995",
    }
)

_SQL = (
    "SELECT r.id FROM pipeline_runs r JOIN stage_reviews sr ON sr.pipeline_run_id = r.id "
    "WHERE r.status = 'completed' AND sr.status NOT IN ('approved', 'edited')"
)


def pares_no_banco(db) -> set[str] | None:
    """Ids de run com o par proibido; ``None`` quando não há run nenhum a medir."""
    if not db.execute(text("SELECT 1 FROM pipeline_runs LIMIT 1")).first():
        return None
    return {row[0] for row in db.execute(text(_SQL))}


def veredito(ids: set[str] | None) -> tuple[str, str]:
    """``(nivel, detalhe)`` — banco vazio é WARN, nunca PASS."""
    if ids is None:
        # Gate fechando sobre ausência de dado é o modo de falha do gate Fernet, que
        # passava por não ter o que medir.
        return "WARN", "sem runs no banco — nada a medir"
    novos = ids - PAR_HISTORICO
    if novos:
        alvos = ", ".join(sorted(i[:8] for i in novos))
        return "FAIL", f"{len(novos)} run(s) completaram sobre conferência sem decisão: {alvos}"
    return "PASS", f"nenhum par novo ({len(ids & PAR_HISTORICO)}/2 históricos preservados)"


def main() -> int:
    from backend.app.core.database import SyncSessionLocal

    with SyncSessionLocal() as db:
        nivel, detalhe = veredito(pares_no_banco(db))
    print(f"[{nivel}] par-completed-pending  {detalhe}")
    if nivel == "FAIL":
        print("  -> o guard da A40.l84 foi contornado; investigue por onde antes de analisar")
    return 1 if nivel == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
