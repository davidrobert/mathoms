"""Fixture realista de transações + detector blacklist."""

from __future__ import annotations

import random

from pipeline.domain.services.internal_transfer_detector import (
    InternalTransferConfig,
    InternalTransferDetector,
)

# RNG seed deterministic — runs reproducible.
RNG = random.Random(424242)

RECURRENT_DESPESAS = (
    "IFOOD DELIVERY",
    "IFOOD RAPPI",
    "MERCADO LIVRE COMPRA",
    "MERCADOLIVRE ML",
    "UBER TRIP",
    "UBER EATS",
    "FARMACIA SAO PAULO",
    "DROGASIL DROGARIA",
    "NETFLIX BR",
    "SPOTIFY PREMIUM",
    "POSTO IPIRANGA COMBUSTIVEL",
    "AMAZON PRIME",
    "RESTAURANTE ITALIA",
    "PADARIA BELA VISTA",
    "ACADEMIA SMART FIT",
    "CONDOMINIO EDIFICIO",
    "ENERGIA ELETRICA ENEL",
)
RECURRENT_RECEITAS = (
    "SALARIO EMPRESA XYZ",
    "PIX RECEBIDO MARIA SILVA",
    "RENDIMENTO POUPANCA",
    "TED RECEBIDO CONSULTORIA",
)
INTERNAL_TRANSFERS = (
    "TED ENTRE CONTAS PROPRIAS",
    "PIX CONTA POUPANCA",
    "TRANSFERENCIA ENTRE CONTAS",
    "RESGATE APLICACAO AUTOMATICA",
    "APLICACAO AUTOMATICA POUPANCA",
)
NOISE = (
    "COMPRA ESTABELECIMENTO 123",
    "DEBITO AUTOMATICO BANCO",
    "TARIFA BANCARIA",
    "JUROS ROTATIVO CARTAO",
    "SAQUE 24H",
)
CATEGORIES_POOL = ("Alimentação", "Transporte", "Lazer", "Outros", "Outros", "Outros", "Outros")


def gen_periods_24_months() -> list[str]:
    """24 meses a partir de 202405 → 202604."""
    periods: list[str] = []
    year, month = 2024, 5
    for _ in range(24):
        periods.append(f"{year:04d}{month:02d}")
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return periods


def rand_day(period: str) -> str:
    return f"{period[:4]}-{period[4:]}-{RNG.randint(1, 28):02d}"


def build_e4_item(*, descricao: str, period: str, valor: str, categoria: str = "Outros") -> dict:
    return {
        "data": rand_day(period),
        "descricao": descricao,
        "valor": valor,
        "banco": "itau",
        "categoria": categoria,
        "titular": "Dogfood User",
        "moeda": "BRL",
        "tipo_conta": "conta_corrente",
        "origem": None,
    }


def pick_desc_and_amount(roll: float) -> tuple[str, str]:
    """Distribuição: 55% despesas / 15% transfer / 8% receitas / 22% noise."""
    if roll < 0.55:
        return RNG.choice(RECURRENT_DESPESAS), f"{RNG.uniform(15, 250):.2f}"
    if roll < 0.70:
        return RNG.choice(INTERNAL_TRANSFERS), f"{RNG.uniform(500, 5000):.2f}"
    if roll < 0.78:
        return RNG.choice(RECURRENT_RECEITAS), f"{RNG.uniform(2000, 12000):.2f}"
    return RNG.choice(NOISE), f"{RNG.uniform(20, 800):.2f}"


def gen_one_period(period: str, *, count: int) -> list[dict]:
    out: list[dict] = []
    for _ in range(count):
        desc, valor = pick_desc_and_amount(RNG.random())
        cat = RNG.choice(CATEGORIES_POOL)
        out.append(build_e4_item(descricao=desc, period=period, valor=valor, categoria=cat))
    return out


def gen_all_items(periods: list[str], per_period: int = 120) -> list[dict]:
    items: list[dict] = []
    for p in periods:
        items.extend(gen_one_period(p, count=per_period))
    return items


def split_e4_payload(items: list[dict]) -> tuple[dict, dict]:
    """Separa despesas vs receitas; agrupa por categoria. (despesas_payload, receitas_payload)."""
    despesas: dict[str, list[dict]] = {}
    receitas: dict[str, list[dict]] = {}
    for it in items:
        is_receita = "SALARIO" in it["descricao"] or "RECEBIDO" in it["descricao"]
        (receitas if is_receita else despesas).setdefault(it["categoria"], []).append(it)
    return {"dados": despesas}, {"dados": receitas}


def build_detector() -> InternalTransferDetector:
    """Detector de transferências internas com patterns dogfood-realistas."""
    return InternalTransferDetector(
        InternalTransferConfig(
            internal_patterns=(
                "ENTRE CONTAS",
                "POUPANCA",
                "APLICACAO AUTOMATICA",
                "RESGATE APLICACAO",
            ),
            global_transfer_patterns=("PIX CONTA",),
        )
    )


__all__ = [
    "RNG",
    "build_detector",
    "build_e4_item",
    "gen_all_items",
    "gen_one_period",
    "gen_periods_24_months",
    "pick_desc_and_amount",
    "rand_day",
    "split_e4_payload",
]
