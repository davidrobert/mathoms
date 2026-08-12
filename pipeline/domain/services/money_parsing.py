"""Parse canônico de valor monetário em string — as duas convenções do corpus."""

# ESCOPO: **somente dinheiro**. Taxa, cotação, σ, valor de cota, percentual, peso e
# contagem de meses NÃO passam por `parse_valor_monetario` — a regra dos 3 dígitos é
# verdadeira para dinheiro e falsa para eles. Use `parse_taxa_ou_cotacao`.

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
#
# Grupo de milhar NUNCA tem zero à esquerda: `"0.025"` não é 25, é vinte e cinco
# milésimos. Sem essa guarda, `pct_renda_anual` (contrato `^-?\d+(\.\d{1,6})?$`,
# domínio 0..1 por ADR-240) virava 1000× (review data-engineer do PR #1417).
#
# Dinheiro com 3 casas decimais NÃO existe, mas taxa e cotação existem — e para elas
# esta função está errada por construção. Use `parse_taxa_ou_cotacao`.
def _e_agrupador(texto: str, sep: str) -> bool:
    """Separador é de milhar (não decimal) quando repete ou agrupa 3 dígitos."""
    if texto.count(sep) > 1:
        return True
    if len(texto) - texto.rfind(sep) - 1 != 3:
        return False
    return not texto[: texto.rfind(sep)].lstrip("+-").startswith("0")


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


# Taxa, cotação, σ, valor de cota e percentual têm 3+ decimais legítimos, então a regra
# de agrupamento de `parse_valor_monetario` está ERRADA para eles: `"5,432"` é cotação
# USD/BRL, não cinco mil e quatrocentos e trinta e dois. Aqui a vírgula é SEMPRE decimal
# e ponto de milhar não é reconhecido — grandeza desse tipo não vem agrupada.
#
# Existe porque `sigma_anual_pct`/`retorno_real_esperado_pct_anual` viajam como `str`
# sobre `Numeric(6,3)` (`economic_assumptions_snapshot.py:43-47`) e a ADR-374 §Sanidade
# de unidade manda escrever a conversão `str → Decimal`. Sem esta função, quem
# implementar a A40.l25 usaria o parser monetário e obteria σ = 22000%.
def parse_taxa_ou_cotacao(raw: Any) -> Decimal | None:
    """Taxa/cotação/percentual → ``Decimal``; a vírgula é sempre decimal."""
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
        return Decimal(texto.replace(",", "."))
    except InvalidOperation:
        return None


__all__ = ["parse_taxa_ou_cotacao", "parse_valor_monetario", "valor_monetario_float"]
