"""Templates determinísticos de narrativa do changelog (v2.D.1 · ADR-148)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.types.snapshot_changelog import ComparisonItem

# Templates por (delta_signal/cenário) × (polaridade da seção).
# Polaridade: "asset" = mais é melhor (S1, S2, S3, T2)
#             "expense" = mais não é necessariamente melhor (T5)
# Verbos neutros ("subiu/recuou/avançou") evitam viés em despesas;
# variação na cauda temporal evita repetição em listas longas.

SECTION_POLARITY: dict[str, str] = {
    "S1": "asset",
    "S2": "asset",
    "S3": "asset",
    "T2": "asset",
    "T5": "expense",
}

TEMPLATES: dict[tuple[str, str], str] = {
    ("up", "asset"): "{section_label} avançou {pct_str} no mês",
    ("up", "expense"): "{section_label} subiu {pct_str} no mês",
    ("down", "asset"): "{section_label} recuou {pct_str} no mês",
    ("down", "expense"): "{section_label} recuou {pct_str} no mês",
    ("stable", "asset"): "{section_label} sem variação relevante no mês",
    ("stable", "expense"): "{section_label} sem variação relevante no mês",
    ("from_zero", "asset"): "{section_label} passou a registrar {after_brl} (antes sem valor)",
    ("from_zero", "expense"): "{section_label} passou a registrar {after_brl} (antes sem valor)",
    ("to_zero", "asset"): "{section_label} zerou neste relatório",
    ("to_zero", "expense"): "{section_label} zerou neste relatório",
    ("both_zero", "asset"): "{section_label} segue sem valor registrado",
    ("both_zero", "expense"): "{section_label} segue sem valor registrado",
}


def format_summary(item: ComparisonItem) -> str:
    """Render de `ChangelogEntry.summary` por template determinístico."""
    template_key = _select_template(item)
    polarity = SECTION_POLARITY.get(item.section_id, "asset")
    template = TEMPLATES[(template_key, polarity)]
    return template.format(
        section_label=item.section_label,
        pct_str=_format_pct(item.delta_pct),
        after_brl=_format_brl(item.after),
    )


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
    """Formata `Decimal` BRL pt-BR `R$ 1.234,56`."""
    sign = "-" if value < 0 else ""
    abs_val = abs(value).quantize(Decimal("0.01"))
    int_part, _, frac_part = f"{abs_val:f}".partition(".")
    int_with_sep = _group_thousands(int_part)
    frac_part = (frac_part + "00")[:2]
    return f"R$ {sign}{int_with_sep},{frac_part}"


def _group_thousands(int_str: str) -> str:
    """Insere `.` separador de milhar pt-BR."""
    chunks: list[str] = []
    for i in range(len(int_str), 0, -3):
        chunks.append(int_str[max(i - 3, 0) : i])
    return ".".join(reversed(chunks))


__all__ = ["SECTION_POLARITY", "TEMPLATES", "format_summary"]
