"""Templates determinísticos de narrativa do changelog (v2.D.1 · ADR-143)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.types.snapshot_changelog import ComparisonItem

# Débito v2.D.1.1 (BACKLOG): product-designer revisa cópia antes de v2.8 flipar YAML.
TEMPLATES: dict[str, str] = {
    "up": "{section_label} cresceu {pct_str} desde o relatório anterior",
    "down": "{section_label} caiu {pct_str} desde o relatório anterior",
    "stable": "{section_label} permanece estável desde o relatório anterior",
    "from_zero": "{section_label} passou a registrar valor (antes zero, agora {after_brl})",
    "to_zero": "{section_label} zerou desde o relatório anterior",
    "both_zero": "{section_label} permanece em zero",
}


def format_summary(item: ComparisonItem) -> str:
    """Render de `ChangelogEntry.summary` por template determinístico."""
    template = TEMPLATES[_select_template(item)]
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


__all__ = ["TEMPLATES", "format_summary"]
