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
_RESERVA_CALCULATE = (
    "pipeline.domain.services.reserva_emergencia_calculator:EmergencyReserveCalculator.calculate"
)
_FLUXO_ENRICH = "pipeline.domain.services.fluxo_caixa_enricher:FluxoCaixaEnricher.enrich"
_INVESTIMENTOS_ANALYZE = (
    "pipeline.domain.services.investimentos_classes_analyzer:InvestimentosClassesAnalyzer.analyze"
)
_ENDIVIDAMENTO_ANALYZE = (
    "pipeline.domain.services.endividamento_analyzer:EndividamentoAnalyzer.analyze"
)

LINEAGE_RULE_REFS: dict[str, dict[str, str]] = {
    "patrimonio.liquido": {"adr": "ADR-145", "ref": _PATRIMONIO_CALCULATE},
    "patrimonio.bruto": {"adr": "ADR-145", "ref": _PATRIMONIO_CALCULATE},
    # A24.l6 — reserva é baseline-fed (saldos líquidos, não K4); ADR canônica
    # da regra de reserva de emergência (bandas/denominador) é a ADR-218.
    "reserva_emergencia.total_liquida": {"adr": "ADR-218", "ref": _RESERVA_CALCULATE},
    # Despesa total agrega a partição de categorias do catálogo ADR-137
    # (dedup K4 a montante é ADR-255); o enforcer do campo E5 é o enricher.
    "fluxo_caixa.despesa_total": {"adr": "ADR-137", "ref": _FLUXO_ENRICH},
    # Total investido soma as classes da taxonomia canônica ADR-193 (posições
    # com chave própria ADR-271, não K4).
    "investimentos.total": {"adr": "ADR-193", "ref": _INVESTIMENTOS_ANALYZE},
    # A25.l6 — fluxo líquido (capacidade de poupança) é formula sobre os
    # agregados do mesmo enricher; reusa o enforcer de fluxo (ADR-137).
    "fluxo_caixa.fluxo_liquido": {"adr": "ADR-137", "ref": _FLUXO_ENRICH},
    # A25.l6 — endividamento consolida dívidas do baseline (agregado Debt,
    # ADR-227); nó distinto de patrimonio.dividas com o mesmo valor — o
    # lineage é declarado no enforcer do campo, não re-derivado.
    "endividamento.total_dividas": {"adr": "ADR-227", "ref": _ENDIVIDAMENTO_ANALYZE},
}
