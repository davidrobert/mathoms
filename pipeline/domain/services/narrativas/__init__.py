"""Pacote ``narrativas`` — E5.N Caminho B puro (A6d.3.2).

Decompõe ``scripts/e5n_narrativas.build_narrativas`` (425 linhas) em
narradores por seção, orquestrados por :class:`E5NarrativasBuilder`.

Entry points:
- :class:`NarrativasContext` — value object de configuração (keys dinâmicas
  por membro: titular/cônjuge), construído a partir de ``family_members``.
- :class:`PerfilFamiliaNarrator`, :class:`SummariesNarrator`,
  :class:`ChartsNarrator` — narradores de seção.
- :class:`E5NarrativasBuilder` — orquestrador que compõe os 3 narradores.

Paridade 100% com ``scripts.e5n_narrativas.build_narrativas`` legado é
garantida por ``tests/test_e5n_main_with_store_parity.py``.
"""

from pipeline.domain.services.narrativas.builder import E5NarrativasBuilder
from pipeline.domain.services.narrativas.charts_narrator import ChartsNarrator
from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.format_helpers import (
    fmt_currency,
    fmt_num,
    fmt_percent,
    fmt_usd,
    validate_narrativas,
)
from pipeline.domain.services.narrativas.perfil_familia_narrator import (
    PerfilFamiliaNarrator,
)
from pipeline.domain.services.narrativas.summaries_narrator import (
    SummariesNarrator,
)

__all__ = [
    "E5NarrativasBuilder",
    "NarrativasContext",
    "PerfilFamiliaNarrator",
    "SummariesNarrator",
    "ChartsNarrator",
    "fmt_currency",
    "fmt_num",
    "fmt_percent",
    "fmt_usd",
    "validate_narrativas",
]
