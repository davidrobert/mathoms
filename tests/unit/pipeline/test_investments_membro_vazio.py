"""ADR-346 §4b (LC-02) — membro-vazio cross-período: colapsa no ÚNICO irmão
resolvido do mesmo inst; 0 = mantém; ≥2 = needs_review. Cobre
``investments_consolidator._collapse_empty_member`` (certificação ledger-certify r2)."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.investments_consolidator import (  # noqa: E402
    InvestmentsConsolidator,
    InvestmentsConsolidatorConfig,
)

_NOW = datetime(2026, 4, 19)


def _c() -> InvestmentsConsolidator:
    return InvestmentsConsolidator(InvestmentsConsolidatorConfig.from_family(None), now=_NOW)


def _snap(
    src: str, membro: str, valor, *, data_ref: str = "2026-03-31", ticker: str = "BTC"
) -> dict:
    return {
        "_source": src,
        "instituicao": "binance",
        "membro": membro,
        "data_referencia": data_ref,
        "total": valor,
        "posicoes": [{"nome": ticker, "valor_total": valor}],
    }


def test_membro_vazio_colapsa_no_unico_irmao_resolvido() -> None:
    # Snapshot binance stale sem membro (mar) + resolvido (dez), mesmo inst → colapsa
    # no irmão (most-recent vence); NÃO soma os dois (era dupla-contagem cross-período).
    out = _c().consolidate(
        [_snap("mar.xlsx", "", 1000.0, data_ref="2025-03-31"), _snap("dez.xlsx", "david", 5000.0)]
    )
    assert out.total_geral == 5000.0  # não 6000
    assert "" not in out.total_por_membro
    assert out.total_por_membro.get("david") == 5000.0


def test_membro_vazio_com_dois_membros_resolvidos_vira_needs_review() -> None:
    # Guard de unicidade: ≥2 membros resolvidos → não colapsa às cegas; membro-vazio
    # vira needs_review (não some, não é atribuído à pessoa errada).
    out = _c().consolidate(
        [
            _snap("b0.xlsx", "", 100.0, data_ref="2025-03-31"),
            _snap("bd.xlsx", "david", 200.0, ticker="ETH"),
            _snap("bm.xlsx", "mariana", 300.0, ticker="SOL"),
        ]
    )
    assert out.total_por_membro.get("needs_review") == 100.0
    assert "" not in out.total_por_membro
