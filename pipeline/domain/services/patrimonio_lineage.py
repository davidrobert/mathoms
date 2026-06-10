"""Bloco ``_lineage`` field-level do patrimônio (ADR-279 · walking skeleton A24.l5).

Lineage de 2 níveis intra-E5: ``patrimonio.liquido`` (formula bruto −
dividas) e ``patrimonio.bruto`` (aggregation das categorias da composição).
Os componentes são uma view tipada sobre o dict que
``PatrimonioCalculator.calculate`` já retorna (padrão ``componentes_calculo``
de ADR-216 D9) — mesmos floats serializados, nunca recálculo paralelo.
``value`` é string decimal 2 casas: escapa do ``to_cents``/manifesto do
``golden_diff``. Inputs NÃO apontam para E4/E3 — o calculador funde fallback
IRPF + residual de caixa, então ref direta a E4 mentiria no caso
``has_current_positions``; o salto até ``SourceRef`` é F5 (l6).
``member_hashes`` fica vazio: patrimônio é baseline-fed — hashes são
obrigatórios só em agregados transaction-fed (l6).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.domain.lineage_registry import LINEAGE_RULE_REFS
from pipeline.domain.services.lineage_fields import (
    LineageBlock,
    LineageField,
    e5_input_ref,
    lineage_block,
    money_str,
    sorted_inputs,
)

PatrimonioReport = dict[str, Any]


@dataclass(frozen=True)
class PatrimonioComponentes:
    """Componentes do payload de patrimônio (mesmos floats serializados)."""

    bruto: float
    dividas: float
    liquido: float
    composicao: tuple[tuple[str, float], ...]


def componentes_from_report(report: PatrimonioReport) -> PatrimonioComponentes:
    """View tipada sobre o dict de ``PatrimonioCalculator.calculate``."""
    return PatrimonioComponentes(
        bruto=report["bruto"],
        dividas=report["dividas"],
        liquido=report["liquido"],
        composicao=tuple((c["categoria"], c["valor"]) for c in report["composicao"]),
    )


def patrimonio_lineage_fields(componentes: PatrimonioComponentes) -> dict[str, LineageField]:
    """Entradas de ``_lineage.fields`` do patrimônio (shape ADR-279)."""
    return {
        "patrimonio.liquido": _liquido_field(componentes),
        "patrimonio.bruto": _bruto_field(componentes),
    }


def build_patrimonio_lineage(componentes: PatrimonioComponentes) -> LineageBlock:
    """Bloco ``_lineage`` (shape ADR-279): zero timestamp/UUID, inputs sorted."""
    return lineage_block(patrimonio_lineage_fields(componentes))


def _liquido_field(c: PatrimonioComponentes) -> LineageField:
    return {
        "value": money_str(c.liquido),
        "label": "Patrimônio líquido",
        "transform": "bruto − dividas",
        "rule_ref": dict(LINEAGE_RULE_REFS["patrimonio.liquido"]),
        "edge_type": "formula",
        "member_hashes": [],
        "inputs": sorted_inputs(
            [e5_input_ref("patrimonio.bruto"), e5_input_ref("patrimonio.dividas")]
        ),
    }


def _bruto_field(c: PatrimonioComponentes) -> LineageField:
    refs = [
        e5_input_ref(f"patrimonio.composicao[{categoria}].valor") for categoria, _ in c.composicao
    ]
    return {
        "value": money_str(c.bruto),
        "label": "Patrimônio bruto",
        "transform": "soma das categorias da composição",
        "rule_ref": dict(LINEAGE_RULE_REFS["patrimonio.bruto"]),
        "edge_type": "aggregation",
        "member_hashes": [],
        "inputs": sorted_inputs(refs),
    }
