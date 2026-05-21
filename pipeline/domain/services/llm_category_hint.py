"""Mapeia `category_hint` do LLM → categoria canônica (ADR-242).

Vocabulário enum em 5 grupos referendado pelo financial-planner. Hint apenas
preenche `nao_identificado` (regra determinística vence). Sentinel
``info_fiscal_anual`` exclui linha do fluxo de caixa (informe IR acumulado).
"""

from __future__ import annotations

# =============================================================================
# Vocabulário enum (ADR-242 — sob revisão do financial-planner)
# =============================================================================

# Sentinel: linha do informe IR (acumulado anual, valor a declarar) — exclui
# do fluxo de caixa mensal. Caller deve skipar a transação.
INFO_FISCAL_ANUAL = "info_fiscal_anual"

# Receitas (6) — separadas para distinguir ativa vs. passiva (Perini).
_HINTS_RECEITA: dict[str, str] = {
    "salario": "salario",
    "pro_labore_pj": "pro_labore",
    "aluguel_recebido": "aluguel_recebido",
    "rendimento_renda_fixa": "rendimento_aplicacao",
    "dividendo_jcp": "dividendos",
    "ganho_capital_resgate": "rendimento_aplicacao",
}

# Moradia & vida essencial (6) — separa juros vs. amortização (Cerbasi).
# Discricionárias (4). Futuro & passivos (4). Operacionais (2, last group).
_HINTS_DESPESA: dict[str, str] = {
    # Moradia
    "moradia_financiamento_juros": "moradia",
    "moradia_financiamento_amortizacao": "moradia",
    "moradia_aluguel_pago": "moradia",
    "moradia_outros": "moradia",
    # Vida essencial
    "alimentacao": "alimentacao",
    "transporte": "transporte",
    # Discricionárias
    "saude": "saude",
    "educacao": "educacao",
    "lazer_assinatura": "lazer",
    "vestuario_pessoal": "vestuario",
    # Futuro & passivos
    "aporte_investimento": "aporte_investimento",
    "seguro_previdencia": "seguros",
    "imposto_pago": "impostos",
    "juros_divida_consumo": "juros_dividas",
}

# Operacional (flag, não categoria de fluxo):
# - `transferencia_interna`: caller já detecta via patterns; hint reforça.
# - INFO_FISCAL_ANUAL: linha excluída do fluxo (ver docstring).
_HINT_TRANSFERENCIA_INTERNA = "transferencia_interna"

# Conjunto canônico para validação de vocabulário (Pydantic Literal futuro).
ALL_HINTS: frozenset[str] = frozenset(
    list(_HINTS_RECEITA) + list(_HINTS_DESPESA) + [_HINT_TRANSFERENCIA_INTERNA, INFO_FISCAL_ANUAL]
)


# =============================================================================
# API
# =============================================================================


def is_info_fiscal_anual(hint: str | None) -> bool:
    """True quando o hint marca a transação como **excluída do fluxo**."""
    return hint == INFO_FISCAL_ANUAL


def is_internal_transfer_hint(hint: str | None) -> bool:
    """True quando o hint reforça detecção de transferência interna."""
    return hint == _HINT_TRANSFERENCIA_INTERNA


def map_hint_to_income_category(hint: str | None) -> str | None:
    """Retorna categoria canônica de **receita** para o hint, ou ``None``."""
    if not hint:
        return None
    return _HINTS_RECEITA.get(hint)


def map_hint_to_expense_category(hint: str | None) -> str | None:
    """Retorna categoria canônica de **despesa** para o hint, ou ``None``."""
    if not hint:
        return None
    return _HINTS_DESPESA.get(hint)
