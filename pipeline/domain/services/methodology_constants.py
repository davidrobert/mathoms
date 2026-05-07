"""Constantes metodológicas universais (rules-as-code, ADR-143/177).

Thresholds e referências de mercado que **não variam por cliente**. Antes
viviam em ``config/goals.json``; ADR-177 (Sprint A10.2) consolidou em
módulo enforcer com docstring justificando a fonte.

Mudar qualquer valor aqui exige PR + revisão (gate intencional). Override
por cliente, quando aplicável, vai em Goal type dedicado (ex.: range
default ``EQUITY_TARGET_*`` pode ser overridden por ``ALOCACAO_ALVO`` em
sprint futura).

Source: [ADR-177](docs/DECISIONS.md#adr-177--thresholds-e-referências-metodológicas-como-código).
"""

from __future__ import annotations

from decimal import Decimal

# =============================================================================
# Imóveis — yield bruto FII/imóvel BR (referência de mercado)
# =============================================================================
# Yield bruto observável em FIIs/imóveis residenciais BR. Faixa narrada
# em S5/S6 do relatório como "potencial de 4-6%" — referência educativa,
# não promessa.
# Source: AUVP/Perini (FIIs), CVM cap rates BR. Aplica ADR-177.

YIELD_POTENCIAL_FII_BR_PCT_MIN: Decimal = Decimal("4.0")
YIELD_POTENCIAL_FII_BR_PCT_MAX: Decimal = Decimal("6.0")


# =============================================================================
# Concentração imobiliária — bandeira patrimonial
# =============================================================================
# Concentração imobiliária >50% do patrimônio líquido = sinal de alerta
# (Perini "Viver de Renda" — passivo imobilizado / AUVP — diversificação).
# Aplica ADR-177.

IMOVEL_PCT_PATRIMONIO_IDEAL: Decimal = Decimal("50")


# =============================================================================
# Equity (RV) — range default por perfil de risco
# =============================================================================
# Range default de % alvo em renda variável (ações, ETFs RV). Cliente
# pode customizar via Goal ``ALOCACAO_ALVO`` (campo ``acoes_pct``).
# Estes valores são o **fallback** quando o workspace não tem Goal
# preenchido — não a verdade absoluta.
# Aplica ADR-177.

EQUITY_PCT_ALVO_DEFAULT_MIN: Decimal = Decimal("20")
EQUITY_PCT_ALVO_DEFAULT_MAX: Decimal = Decimal("25")


# =============================================================================
# Simulação cenário "cônjuge sem trabalhar" (ADR-167)
# =============================================================================
# Fator de redução do aporte mensal quando a renda do cônjuge desaparece
# (cenário de estresse). 0.66 = manter 66% do aporte total — convergente
# Cerbasi (renda dupla → casal preserva ~2/3 da poupança quando uma renda
# cessa). Heurística sem livro-âncora direto, mas estabilizada nos
# goldens E5.N.
# Aplica ADR-167 + ADR-177.

APORTE_REDUZIDO_FATOR_CONJUGE: Decimal = Decimal("0.66")


# =============================================================================
# Stress test imobiliário
# =============================================================================
# Queda de mercado imobiliário aplicada em stress test patrimonial.
# Valor padrão da metodologia; a chave hoje não tem leitor vivo (zero
# consumidores no pipeline pós-cleanup), mas a constante fica documentada
# aqui para uso futuro do stress test analyzer (lane futura).
# Aplica ADR-177.

STRESS_TEST_IMOVEL_QUEDA_PCT: Decimal = Decimal("20")


__all__ = [
    "APORTE_REDUZIDO_FATOR_CONJUGE",
    "EQUITY_PCT_ALVO_DEFAULT_MAX",
    "EQUITY_PCT_ALVO_DEFAULT_MIN",
    "IMOVEL_PCT_PATRIMONIO_IDEAL",
    "STRESS_TEST_IMOVEL_QUEDA_PCT",
    "YIELD_POTENCIAL_FII_BR_PCT_MAX",
    "YIELD_POTENCIAL_FII_BR_PCT_MIN",
]
