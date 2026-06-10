"""Bridge nó-de-lineage → código (ADR-281 B2).

Dict literal eager — NÃO decorator import-side-effect (banido por
CLAUDE.md §Dependências; fora da exceção ADR-111 (a)). Refactor-safe via
``dev/check_lineage_refs.py``: cada ``ref`` (``module:qualname``) resolve
por import real e cada ``adr`` existe em ``docs/adr/``. Constante imutável
registrada em ``docs/reference/STATELESS_AUDIT.md`` §2, categoria (a).
"""

from __future__ import annotations

_PATRIMONIO_CALCULATE = (
    "pipeline.domain.services.patrimonio_calculator:PatrimonioCalculator.calculate"
)

LINEAGE_RULE_REFS: dict[str, dict[str, str]] = {
    "patrimonio.liquido": {"adr": "ADR-145", "ref": _PATRIMONIO_CALCULATE},
    "patrimonio.bruto": {"adr": "ADR-145", "ref": _PATRIMONIO_CALCULATE},
}
