"""A38.l7 — fatura Santander Unique layout 2026 classifica deterministicamente.

O parser (parse_santander_unique) já extrai total/vencimento/tx desse layout;
o gap era só a classificação: a TypeRule exigia adjacência "SANTANDER UNIQUE",
ausente no layout 2026 (produto = "UNIQUE MASTERCARD"; "SANTANDER" no rótulo do
cartão numa linha vizinha) → conf 0.0, doc nunca chegava ao parser.
"""

from __future__ import annotations

from backend.app.services.classification.type_classifier import detect_type_by_content

_UNIQUE_2026 = (
    "Olá, David! Esta é a fatura do seu cartão SANTANDER DAVID ROBERT - 5228 XXXX XXXX 2506\n"
    "UNIQUE MASTERCARD contendo compras e pagamentos\n"
    "realizados até 08/07. Total a Pagar Vencimento Seu limte é\n"
    "R$ 1.234,56 15/07/2026 R$ 20.000,00\n"
)


def test_fatura_unique_layout_2026_classifica_faturaunique() -> None:
    rule, req, sup = detect_type_by_content(_UNIQUE_2026)
    assert rule is not None and rule.code == "faturaunique"
    assert req == 1 and sup >= 1  # conf ≥ 0.8 (era 0.0 antes da A38.l7)


def test_mastercard_de_outro_emissor_nao_vira_faturaunique() -> None:
    """Co-ocorrência com SANTANDER é obrigatória — Mastercard genérico não casa."""
    outro = "Fatura do seu cartão ITAU VISA PLATINUM\nMASTERCARD contendo compras\n"
    rule, _, _ = detect_type_by_content(outro)
    assert rule is None or rule.code != "faturaunique"


def test_santander_unique_classico_continua_classificando() -> None:
    classico = "SANTANDER UNIQUE\nTotal a Pagar R$ 500,00\nVencimento da Fatura 10/02/2026\n"
    rule, _, _ = detect_type_by_content(classico)
    assert rule is not None and rule.code == "faturaunique"
