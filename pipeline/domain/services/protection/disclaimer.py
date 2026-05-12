"""Disclaimer fiduciário canônico (ADR-192 §"Atualizações pós-revisão") — todo ``rationale`` carrega este aviso para evitar leitura como recomendação fiduciária."""

from __future__ import annotations

DISCLAIMER_TEMPLATE: str = (
    "Estimativa metodológica baseada em {sources}; não constitui recomendação "
    "fiduciária. Consultar corretor habilitado pela Susep e planejador CFP®. "
    "Dados fiscais válidos para {effective_date}."
)


def render_disclaimer(*, sources: str, effective_date: str) -> str:
    """Renderiza o disclaimer canônico."""
    return DISCLAIMER_TEMPLATE.format(sources=sources, effective_date=effective_date)


__all__ = ["DISCLAIMER_TEMPLATE", "render_disclaimer"]
