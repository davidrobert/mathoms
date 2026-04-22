"""E5NarrativasBuilder — orquestrador das narrativas E5.N (A6d.3.2).

Compõe os três narradores por seção (:class:`PerfilFamiliaNarrator`,
:class:`SummariesNarrator`, :class:`ChartsNarrator`) sobre um
:class:`NarrativasContext` único. Substitui os 425 locs de
``scripts/e5n_narrativas.build_narrativas`` por delegação limpa a
serviços de domínio com injeção de contexto (ISP/R9/ADR-097).

Uso típico::

    builder = E5NarrativasBuilder.from_family_config(family)
    narrativas = builder.build(metrics, family)
    # {"perfil_familia": {...}, "summaries": {...}, "charts": {...}}

Paridade 100% com ``scripts.e5n_narrativas.build_narrativas`` legado
coberta por ``tests/test_e5n_main_with_store_parity.py``.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Any

from pipeline.domain.services.narrativas.charts_narrator import ChartsNarrator
from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.perfil_familia_narrator import (
    PerfilFamiliaNarrator,
)
from pipeline.domain.services.narrativas.summaries_narrator import (
    SummariesNarrator,
)


class E5NarrativasBuilder:
    """Orquestra os três narradores e retorna o objeto ``narrativas`` completo."""

    def __init__(self, ctx: NarrativasContext):
        self._ctx = ctx
        self._perfil = PerfilFamiliaNarrator(ctx)
        self._summaries = SummariesNarrator(ctx)
        self._charts = ChartsNarrator(ctx)

    @classmethod
    def from_family_config(cls, family: dict[str, Any]) -> "E5NarrativasBuilder":
        """Constrói o builder a partir de ``family_members.json``."""
        return cls(NarrativasContext.from_family_config(family))

    def build(
        self,
        metrics: dict[str, Any],
        family: dict[str, Any],
        *,
        today: _date | None = None,
    ) -> dict[str, Any]:
        """Retorna ``{"perfil_familia": ..., "summaries": ..., "charts": ...}``.

        Extrai ``riscos`` e ``decisoes`` de ``metrics`` (populados por
        ``goals.json`` no E5) e roteia para os narradores. Mantém o mesmo
        tratamento defensivo do legado (``isinstance`` guards) para aceitar
        estruturas malformadas sem quebrar.
        """
        riscos_raw = metrics.get("riscos_prioritarios", [])
        riscos: list[dict[str, Any]] = riscos_raw if isinstance(riscos_raw, list) else []
        riscos_nomes: list[str] = [r.get("nome", "") for r in riscos if isinstance(r, dict)]

        decisoes_raw = metrics.get("decisoes_prioritarias", [])
        decisoes: list[str] = list(decisoes_raw) if isinstance(decisoes_raw, list) else []

        return {
            "perfil_familia": self._perfil.narrate(metrics, family, today=today),
            "summaries": self._summaries.narrate(metrics, family, riscos_nomes, decisoes),
            "charts": self._charts.narrate(metrics, family, riscos, decisoes),
        }
