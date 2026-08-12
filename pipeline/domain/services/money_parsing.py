"""Parse canônico de valor monetário em string — as duas convenções do corpus."""

# O corpus real traz ISO (`"243285.37"`, emitido pelos nossos próprios stages) e pt-BR
# (`"243.285,37"`, vindo de documento/LLM). Antes deste módulo havia 9 implementações
# divergentes: 4 strippavam `.` incondicionalmente e inflavam ISO em 100×, 1 devolvia
# 0 em pt-BR (dinheiro desaparecia), 1 deflacionava USD em 1000× e só uma acertava.
#
# O ×100 chegou ao relatório entregue: `consolidate_baseline.safe_float("243285.37")`
# → 24328537.0 → `investimentos_consolidados.valores_31_12` → patrimônio líquido, IF
# (798% contra 16,7% real), prazo de IF e gap. Ver tests/unit/pipeline/test_money_parsing.py
# e o gate dev/check_money_parsing.py.

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

# Vocabulário de ausência do E5 (espelha `parecer_pos_llm_guardrails._ABSENCE_SENTINELS`
# e `pipeline/llm/value_formatter`): artefato antigo carrega "N/D" em campo numérico.
_SENTINELAS_AUSENCIA = frozenset({"", "n/d", "nan", "none", "null", "-", "—", "r$"})
# Ordem importa: token com letra sai antes do símbolo solto, senão "US$" deixa "US".
_MOEDAS = ("R$", "US$", "U$", "BRL", "USD", "EUR", "€", "£", "$")


def _limpar(raw: str) -> str:
    """Remove símbolo de moeda e todo espaço (inclusive NBSP)."""
    texto = raw.strip()
    for token in _MOEDAS:
        texto = texto.replace(token, "")
    return "".join(c for c in texto if not c.isspace())


# `"5.000.000"` repete o ponto — decimal não repete. `"5.000"` tem exatamente 3 dígitos
# depois, assinatura do agrupamento; `"243285.37"` tem 2, assinatura da decimal.
# Ambíguo de verdade só sobra para valor com 3 casas decimais, que não ocorre em dinheiro.
def _e_agrupador(texto: str, sep: str) -> bool:
    """Separador é de milhar (não decimal) quando repete ou agrupa 3 dígitos."""
    if texto.count(sep) > 1:
        return True
    return len(texto) - texto.rfind(sep) - 1 == 3


def _normalizar_separadores(texto: str) -> str:
    """Deixa o texto em forma ISO (`.` decimal, sem agrupador)."""
    tem_ponto, tem_virgula = "." in texto, "," in texto
    if tem_ponto and tem_virgula:
        # O ÚLTIMO separador é o decimal; o outro é agrupador. Cobre pt-BR
        # ("1.234,56") e US/EU ("1,234.56") sem precisar saber o locale.
        if texto.rfind(",") > texto.rfind("."):
            return texto.replace(".", "").replace(",", ".")
        return texto.replace(",", "")
    if tem_virgula:
        return texto.replace(",", "") if _e_agrupador(texto, ",") else texto.replace(",", ".")
    if tem_ponto and _e_agrupador(texto, "."):
        return texto.replace(".", "")
    return texto


# Ausência devolve `None` de propósito: zero coerced foi o que fabricou KPI falso
# (r5/M28). Quem precisa de zero decide isso no call-site.
def parse_valor_monetario(raw: Any) -> Decimal | None:
    """Valor monetário → ``Decimal``; ``None`` para ausência (nunca 0 coerced)."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, (int, float)):
        return Decimal(str(raw))
    if not isinstance(raw, str):
        return None
    texto = _limpar(raw)
    if texto.strip().lower() in _SENTINELAS_AUSENCIA:
        return None
    try:
        return Decimal(_normalizar_separadores(texto))
    except InvalidOperation:
        return None


# Existe porque migrar as 9 assinaturas para `Decimal` no mesmo PR do fix de correção
# mudaria API pública de services de domínio. Novo código usa o `Decimal` direto.
def valor_monetario_float(raw: Any, default: float = 0.0) -> float:
    """Shim para call-site legado que assina ``float``."""
    valor = parse_valor_monetario(raw)
    return default if valor is None else float(valor)


__all__ = ["parse_valor_monetario", "valor_monetario_float"]
