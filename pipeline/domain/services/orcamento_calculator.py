"""OrcamentoProspectivoCalculator — orçamento mensal médio por categoria
(Sessão A5a · Fase 8).

Extrai ``analyze_orcamento_prospectivo`` (e5_analyze.py:1428) em domain
service puro. Calcula média mensal de cada categoria de despesa a partir de
``despesas_por_categoria`` e ``num_months`` (derivado de
``receita_despesa_mensal_detalhado.labels``).

Função pura, sem I/O nem config externa.
"""

from __future__ import annotations

from dataclasses import dataclass

# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class OrcamentoProspectivo:
    """Output de ``OrcamentoProspectivoCalculator.calculate``."""

    categorias: dict[str, float]
    total: float
    media_mensal: float
    legenda: str
    # ADR-306 — média full-period rotulada (migração para 12m é follow-up).
    janela: str = "full"
    janela_meses: int = 0

    def to_legacy_dict(self) -> dict:
        return {
            "categorias": {k: round(v, 2) for k, v in self.categorias.items()},
            "total": round(self.total, 2),
            "media_mensal": round(self.media_mensal, 2),
            "legenda": self.legenda,
            "janela": self.janela,
            "janela_meses": self.janela_meses,
        }


# =============================================================================
# Service
# =============================================================================


class OrcamentoProspectivoCalculator:
    """Calcula orçamento prospectivo (média mensal) por categoria de despesa.

    Recebe ``despesas_por_categoria: dict[str, float]`` (total acumulado no
    período) e ``num_months: int``. Divide cada total pelo número de meses
    para obter a média mensal esperada.

    Quando ``num_months == 0``, retorna orçamento zerado com legenda
    explicativa (paridade com legado que retorna ``categorias = {}``).
    """

    def calculate(
        self,
        despesas_por_categoria: dict[str, float],
        *,
        num_months: int,
    ) -> OrcamentoProspectivo:
        if num_months <= 0:
            return OrcamentoProspectivo(
                categorias={},
                total=0.0,
                media_mensal=0.0,
                legenda=(
                    "Orçamento prospectivo não disponível — sem meses de " "dados (num_months=0)."
                ),
            )

        categorias = {
            cat: float(total) / num_months for cat, total in (despesas_por_categoria or {}).items()
        }
        total_mensal = sum(categorias.values())

        legenda = (
            f"Orçamento prospectivo baseado na média dos últimos {num_months} meses. "
            "Recomenda-se revisar mensalmente e ajustar projeções."
        )

        return OrcamentoProspectivo(
            categorias=categorias,
            total=total_mensal,
            media_mensal=total_mensal,
            legenda=legenda,
            janela_meses=num_months,
        )
