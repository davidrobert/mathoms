"""A38.l6 — TypeRule de subtipo de moeda p/ extrato estilo Wise + período por extenso."""

from __future__ import annotations

from backend.app.services.classification.period_extractor import extract_period_from_content
from backend.app.services.classification.type_classifier import detect_type_by_content

_PREVIEW_USD = (
    "Wise Payments Ltd.\n"
    "Extrato em USD\n"
    "22 de julho de 2025 [GMT-03:00] - 22 de julho de 2026 [GMT-03:00]\n"
    "Titular da Conta Número da conta Routing number\n"
    "USD em 22 de julho de 2026 [GMT-03:00] 1.000,00 USD\n"
    "Descrição Entrada Saída Valor\n"
)


def test_extrato_em_usd_classifica_subtipo_deterministico() -> None:
    rule, req, sup = detect_type_by_content(_PREVIEW_USD)
    assert rule is not None and rule.code == "extratocontausd"
    assert req == len(rule.required) and sup >= 1


def test_extrato_em_brl_classifica_subtipo() -> None:
    rule, _, _ = detect_type_by_content(_PREVIEW_USD.replace("USD", "BRL"))
    assert rule is not None and rule.code == "extratocontabrl"


def test_extrato_generico_nao_roubado_pelo_subtipo() -> None:
    preview = "EXTRATO DE CONTA CORRENTE\nSALDO ANTERIOR\nAgência: 123 Conta: 456-7\n"
    rule, _, _ = detect_type_by_content(preview)
    assert rule is not None and rule.code == "extratoconta"


def test_periodo_range_por_extenso() -> None:
    assert (
        extract_period_from_content(
            "22 de julho de 2025 [GMT-03:00] - 22 de julho de 2026 [GMT-03:00]"
        )
        == "202507_202607"
    )


def test_periodo_mes_ano_simples_preservado() -> None:
    assert extract_period_from_content("fatura de maio/2026") == "202605"
