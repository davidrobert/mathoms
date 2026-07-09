"""Templates determinísticos de narrativa do changelog (v2.D.1 · ADR-148)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.types.snapshot_changelog import ComparisonItem

# Templates por (delta_signal/cenário) × (polaridade) × (número).
# Polaridade: "asset" = mais é melhor (S1, S2, S3, T2)
#             "expense" = mais não é necessariamente melhor (T5)
# Verbos polaridade-aware ("cresceu/recuou" para asset, "subiu/recuou"
# para expense) evitam viés positivo em despesas. `section_label_inline`
# aplica sentence case (primeira palavra em maiúscula, demais em
# minúscula) para que a prosa fique gramaticalmente correta — o card
# acima continua usando o label em Title Case como header.
#
# Número detectado por heurística pt-BR (`_is_plural`): última palavra
# do label termina em "s" ⇒ plural. Cobre os labels default
# ("Aportes" plural, "Despesas Totais" plural; "Patrimônio Líquido",
# "Receita Total", "Patrimônio Bruto" singulares). Override de label via
# `SnapshotChangelogConfig.section_labels` herda o mesmo critério.

SECTION_POLARITY: dict[str, str] = {
    "S1": "asset",
    "S2": "asset",
    "S3": "asset",
    "T2": "asset",
    "T5": "expense",
    "M_PL": "asset",
    "M_TAXA_POUPANCA": "asset",
    "M_RESERVA_MESES": "asset",
    "M_AUVP_DESVIO": "expense",
}

# (template_key, polarity, number) → template string.
# Em `stable`/`from_zero`/`to_zero`/`both_zero`, polarity é irrelevante
# (formas idênticas) — entradas duplicadas mantidas por simetria do lookup.
TEMPLATES: dict[tuple[str, str, str], str] = {
    # ----- up / asset -----
    ("up", "asset", "singular"): (
        "{section_label_inline} cresceu {delta_brl} desde o relatório anterior (+{pct_str})"
    ),
    ("up", "asset", "plural"): (
        "{section_label_inline} cresceram {delta_brl} desde o relatório anterior (+{pct_str})"
    ),
    # ----- up / expense -----
    ("up", "expense", "singular"): (
        "{section_label_inline} subiu {delta_brl} desde o relatório anterior (+{pct_str})"
    ),
    ("up", "expense", "plural"): (
        "{section_label_inline} subiram {delta_brl} desde o relatório anterior (+{pct_str})"
    ),
    # ----- down (asset == expense) -----
    ("down", "asset", "singular"): (
        "{section_label_inline} recuou {delta_brl} desde o relatório anterior (−{pct_str})"
    ),
    ("down", "asset", "plural"): (
        "{section_label_inline} recuaram {delta_brl} desde o relatório anterior (−{pct_str})"
    ),
    ("down", "expense", "singular"): (
        "{section_label_inline} recuou {delta_brl} desde o relatório anterior (−{pct_str})"
    ),
    ("down", "expense", "plural"): (
        "{section_label_inline} recuaram {delta_brl} desde o relatório anterior (−{pct_str})"
    ),
    # ----- stable -----
    ("stable", "asset", "singular"): (
        "{section_label_inline} sem variação relevante desde o relatório anterior"
    ),
    ("stable", "asset", "plural"): (
        "{section_label_inline} sem variação relevante desde o relatório anterior"
    ),
    ("stable", "expense", "singular"): (
        "{section_label_inline} sem variação relevante desde o relatório anterior"
    ),
    ("stable", "expense", "plural"): (
        "{section_label_inline} sem variação relevante desde o relatório anterior"
    ),
    # ----- from_zero -----
    ("from_zero", "asset", "singular"): (
        "{section_label_inline} passou a registrar {after_brl} (antes sem valor)"
    ),
    ("from_zero", "asset", "plural"): (
        "{section_label_inline} passaram a registrar {after_brl} (antes sem valor)"
    ),
    ("from_zero", "expense", "singular"): (
        "{section_label_inline} passou a registrar {after_brl} (antes sem valor)"
    ),
    ("from_zero", "expense", "plural"): (
        "{section_label_inline} passaram a registrar {after_brl} (antes sem valor)"
    ),
    # ----- to_zero -----
    ("to_zero", "asset", "singular"): "{section_label_inline} zerou neste relatório",
    ("to_zero", "asset", "plural"): "{section_label_inline} zeraram neste relatório",
    ("to_zero", "expense", "singular"): "{section_label_inline} zerou neste relatório",
    ("to_zero", "expense", "plural"): "{section_label_inline} zeraram neste relatório",
    # ----- both_zero -----
    ("both_zero", "asset", "singular"): "{section_label_inline} segue sem valor registrado",
    ("both_zero", "asset", "plural"): "{section_label_inline} seguem sem valor registrado",
    ("both_zero", "expense", "singular"): "{section_label_inline} segue sem valor registrado",
    ("both_zero", "expense", "plural"): "{section_label_inline} seguem sem valor registrado",
}


def format_summary(item: ComparisonItem) -> str:
    """Render de `ChangelogEntry.summary` por template determinístico (verbo carrega sinal; `delta_brl` absoluto)."""
    template_key = _select_template(item)
    polarity = SECTION_POLARITY.get(item.section_id, "asset")
    number = "plural" if _is_plural(item.section_label) else "singular"
    template = TEMPLATES[(template_key, polarity, number)]
    return template.format(
        section_label_inline=_to_sentence_case(item.section_label),
        pct_str=_format_pct(item.delta_pct),
        after_brl=_format_value(item.after, item.unit),
        delta_brl=_format_value(abs(item.after - item.before), item.unit),
    )


def _format_value(value: Decimal, unit: str) -> str:
    """Formata pelo `unit` da métrica: brl → R$; pp/meses → absoluto pt-BR."""
    if unit == "pp":
        return f"{value.quantize(Decimal('0.1'))} pp".replace(".", ",")
    if unit == "meses":
        n = value.quantize(Decimal("0.1"))
        suffix = "mês" if abs(n) == Decimal("1") else "meses"
        return f"{n} {suffix}".replace(".", ",")
    return _format_brl(value)


def _select_template(item: ComparisonItem) -> str:
    """Escolhe chave do template — cobre os 6 cenários."""
    if item.before == 0 and item.after == 0:
        return "both_zero"
    if item.before == 0 and item.after != 0:
        return "from_zero"
    if item.before != 0 and item.after == 0:
        return "to_zero"
    return item.delta_signal


def _format_pct(delta_pct: Decimal | None) -> str:
    """Formata `delta_pct` em pt-BR (vírgula); `None` → `—`."""
    if delta_pct is None:
        return "—"
    rounded = abs(delta_pct).quantize(Decimal("0.1"))
    return f"{rounded}%".replace(".", ",")


def _format_brl(value: Decimal) -> str:
    """Formata `Decimal` BRL pt-BR `R$ 1.234,56` (sinal `−` quando negativo)."""
    sign = "−" if value < 0 else ""
    abs_val = abs(value).quantize(Decimal("0.01"))
    int_part, _, frac_part = f"{abs_val:f}".partition(".")
    int_with_sep = _group_thousands(int_part)
    frac_part = (frac_part + "00")[:2]
    return f"R$ {sign}{int_with_sep},{frac_part}"


def _to_sentence_case(label: str) -> str:
    """`'Patrimônio Líquido'` → `'Patrimônio líquido'` (primeira palavra capitalizada)."""
    parts = label.split(" ", 1)
    if len(parts) == 1:
        return parts[0]
    return parts[0] + " " + parts[1].lower()


def _is_plural(label: str) -> bool:
    """Heurística pt-BR: última palavra termina em `'s'` ⇒ plural (cobre labels default; falsos-positivos `'Lápis'`/`'Ônibus'` aceitáveis em finanças)."""
    last_word = label.split()[-1] if label.strip() else ""
    return last_word.lower().endswith("s")


def _group_thousands(int_str: str) -> str:
    """Insere `.` separador de milhar pt-BR."""
    chunks: list[str] = []
    for i in range(len(int_str), 0, -3):
        chunks.append(int_str[max(i - 3, 0) : i])
    return ".".join(reversed(chunks))


__all__ = [
    "SECTION_POLARITY",
    "TEMPLATES",
    "_is_plural",
    "_to_sentence_case",
    "format_summary",
]
