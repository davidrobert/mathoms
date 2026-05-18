"""Seed baseline 2026 de ``economic_assumptions`` (ADR-219 wave 1, idempotente)."""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.models.economic_assumption import (
    EconomicAssetClass,
    EconomicAssumption,
)

logger = logging.getLogger("mathoms.seed.economic_assumptions")


@dataclass(frozen=True)
class _BaselineRow:
    classe_auvp: str
    retorno_real_esperado_pct_anual: Decimal
    sigma_anual_pct: Decimal
    fonte: str


# Baseline 2026 — números são entry-point auditável; revisões trimestrais
# entram via console interno (wave 2). Valores em pct (não decimal): 4.5
# significa 4.5% a.a. real, não 0.045.
_BASELINE_2026: tuple[_BaselineRow, ...] = (
    _BaselineRow(
        classe_auvp="caixa",
        retorno_real_esperado_pct_anual=Decimal("0.000"),
        sigma_anual_pct=Decimal("0.500"),
        fonte="Baseline conservador — caixa não preserva poder de compra real.",
    ),
    _BaselineRow(
        classe_auvp="rf_pos",
        retorno_real_esperado_pct_anual=Decimal("3.500"),
        sigma_anual_pct=Decimal("1.500"),
        fonte="CDI projetado − IPCA esperado × (1 − IR efetivo 17.5%); fonte Selic Focus + IPCA Focus 2026.",
    ),
    _BaselineRow(
        classe_auvp="rf_pre",
        retorno_real_esperado_pct_anual=Decimal("4.000"),
        sigma_anual_pct=Decimal("3.500"),
        fonte="Curva pré-fixada média 5y − IPCA × (1 − IR 17.5%); fonte Tesouro Direto + ETTJ.",
    ),
    _BaselineRow(
        classe_auvp="rf_inflacao",
        retorno_real_esperado_pct_anual=Decimal("5.500"),
        sigma_anual_pct=Decimal("4.000"),
        fonte="NTN-B 2035 yield real médio 2024-2026; fonte Tesouro Direto.",
    ),
    _BaselineRow(
        classe_auvp="acoes_br",
        retorno_real_esperado_pct_anual=Decimal("7.000"),
        sigma_anual_pct=Decimal("22.000"),
        fonte="Ibovespa real long-run 2000-2025 (mediana de janelas móveis 10y).",
    ),
    _BaselineRow(
        classe_auvp="acoes_intl",
        retorno_real_esperado_pct_anual=Decimal("6.500"),
        sigma_anual_pct=Decimal("18.000"),
        fonte="S&P500 + MSCI World real long-run 1950-2025 hedgeado a BRL.",
    ),
    _BaselineRow(
        classe_auvp="fii",
        retorno_real_esperado_pct_anual=Decimal("6.000"),
        sigma_anual_pct=Decimal("15.000"),
        fonte="IFIX yield real long-run 2014-2025 + valorização.",
    ),
    _BaselineRow(
        classe_auvp="imoveis_diretos",
        retorno_real_esperado_pct_anual=Decimal("4.500"),
        sigma_anual_pct=Decimal("10.000"),
        fonte="FipeZap aluguel + valorização real 2010-2025 médio nacional, líquido de IR carnê-leão típico.",
    ),
    _BaselineRow(
        classe_auvp="cambio_usd",
        retorno_real_esperado_pct_anual=Decimal("1.500"),
        sigma_anual_pct=Decimal("12.000"),
        fonte="USD/BRL real 2000-2025 — paridade poder de compra de longo prazo.",
    ),
    _BaselineRow(
        classe_auvp="cambio_eur",
        retorno_real_esperado_pct_anual=Decimal("1.000"),
        sigma_anual_pct=Decimal("13.000"),
        fonte="EUR/BRL real 2000-2025.",
    ),
)

_BASELINE_EFFECTIVE_FROM = date(2026, 1, 1)
_BASELINE_CREATED_BY = "seed_economic_assumptions_baseline_2026"


def _row_already_present(session: Session, classe: str) -> bool:
    return (
        session.query(EconomicAssumption)
        .filter_by(classe_auvp=classe, effective_from=_BASELINE_EFFECTIVE_FROM)
        .first()
        is not None
    )


def _build_assumption(row: _BaselineRow) -> EconomicAssumption:
    return EconomicAssumption(
        id=str(uuid.uuid4()),
        classe_auvp=row.classe_auvp,
        retorno_real_esperado_pct_anual=row.retorno_real_esperado_pct_anual,
        sigma_anual_pct=row.sigma_anual_pct,
        fonte=row.fonte,
        effective_from=_BASELINE_EFFECTIVE_FROM,
        effective_to=None,
        created_by=_BASELINE_CREATED_BY,
        created_at=datetime.now(timezone.utc),
    )


def seed_baseline_economic_assumptions(session: Session) -> int:
    """Insere baseline para classes ainda não cobertas. Retorna nº de inserções."""
    existing_codes = {c.code for c in session.query(EconomicAssetClass).all()}
    inserted = 0
    for row in _BASELINE_2026:
        if row.classe_auvp not in existing_codes:
            logger.warning("skip %s — classe ausente em economic_asset_class", row.classe_auvp)
            continue
        if _row_already_present(session, row.classe_auvp):
            continue
        session.add(_build_assumption(row))
        inserted += 1
    session.commit()
    return inserted


def _dry_run(session: Session) -> int:
    """Reporta inserções pendentes sem persistir."""
    existing_codes = {c.code for c in session.query(EconomicAssetClass).all()}
    existing_keys = {
        (r.classe_auvp, r.effective_from.isoformat())
        for r in session.query(EconomicAssumption).all()
    }
    to_insert = [
        row.classe_auvp
        for row in _BASELINE_2026
        if row.classe_auvp in existing_codes
        and (row.classe_auvp, _BASELINE_EFFECTIVE_FROM.isoformat()) not in existing_keys
    ]
    logger.info("dry-run: would insert %d rows: %s", len(to_insert), to_insert)
    return 0


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Não persiste; só reporta.")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with SyncSessionLocal() as session:
        if args.dry_run:
            return _dry_run(session)
        n = seed_baseline_economic_assumptions(session)
        logger.info("inserted %d rows (effective_from=%s)", n, _BASELINE_EFFECTIVE_FROM)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
