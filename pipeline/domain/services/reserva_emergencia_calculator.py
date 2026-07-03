"""``EmergencyReserveCalculator`` — análise de reserva de emergência (A6d.3.3 — ADR-100).

Substitui ``scripts/e5_analyze.analyze_reserva_emergencia`` por um serviço puro
sem globals. Consome o dict ``fluxo`` produzido por ``CashFlowBuilder`` e o
dict ``patrimonio`` produzido por :class:`PatrimonioCalculator`.

Config carregada de ``config/scoring.json`` sob a chave ``reserva_emergencia``:

.. code-block:: json

    {
      "niveis_meses": [6, 12],
      "classificacao": [
        {"minimo_meses": 12, "label": "Excelente"},
        {"minimo_meses": 6,  "label": "Adequada"},
        {"minimo_meses": 0,  "label": "Insuficiente"}
      ]
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.domain.services.patrimonio_types import MemberIdentity, safe_float


@dataclass(frozen=True)
class ReservaClassificacao:
    """Faixa de avaliação de reserva (mínimo de meses → label)."""

    minimo_meses: int
    label: str


@dataclass(frozen=True)
class ReservaEmergenciaConfig:
    """Config do :class:`EmergencyReserveCalculator`."""

    members: MemberIdentity
    niveis_meses: tuple[int, ...] = (6, 12)
    classificacao: tuple[ReservaClassificacao, ...] = (
        ReservaClassificacao(minimo_meses=12, label="Excelente"),
        ReservaClassificacao(minimo_meses=6, label="Adequada"),
        ReservaClassificacao(minimo_meses=0, label="Insuficiente"),
    )

    @classmethod
    def from_scoring_json(cls, scoring: dict, members: MemberIdentity) -> "ReservaEmergenciaConfig":
        """Constrói config a partir de ``config/scoring.json`` (estrutura legada)."""
        reserva_cfg = scoring.get("reserva_emergencia", {}) or {}
        niveis = reserva_cfg.get("niveis_meses") or [6, 12]
        classif_raw = reserva_cfg.get("classificacao") or [
            {"minimo_meses": 12, "label": "Excelente"},
            {"minimo_meses": 6, "label": "Adequada"},
            {"minimo_meses": 0, "label": "Insuficiente"},
        ]
        return cls(
            members=members,
            niveis_meses=tuple(int(n) for n in niveis),
            classificacao=tuple(
                ReservaClassificacao(
                    minimo_meses=int(faixa.get("minimo_meses", 0)),
                    label=str(faixa.get("label", "")),
                )
                for faixa in classif_raw
            ),
        )


class EmergencyReserveCalculator:
    """Calcula reserva de emergência + avaliação de cobertura.

    Uso::

        config = ReservaEmergenciaConfig.from_scoring_json(scoring, identity)
        calc = EmergencyReserveCalculator(config)
        report = calc.calculate(fluxo=fluxo, patrimonio=patrimonio)
    """

    def __init__(self, config: ReservaEmergenciaConfig) -> None:
        self._config = config

    def calculate(self, *, fluxo: dict, patrimonio: dict) -> dict:
        """Produz dict paridade com ``analyze_reserva_emergencia`` legado.

        ADR-306 §D4: denominador usa a janela canônica 12m (``janela_12m``),
        não a média full-period diluída. ``despesa_mensal_media`` é ponte
        transitória — A28.l1 troca para ``despesa_mensal_essencial`` da
        mesma janela.
        """
        identity = self._config.members
        despesa_mensal, janela, janela_meses = _resolve_base_mensal(fluxo)

        inv_titular = safe_float(patrimonio.get(identity.key_inv_titular, 0))
        inv_conjuge = (
            safe_float(patrimonio.get(identity.key_inv_conjuge, 0)) if identity.conjuge_key else 0.0
        )
        caixa = safe_float(patrimonio.get("caixa_moeda_estrangeira", 0))
        total_liquida = inv_titular + inv_conjuge + caixa

        cobertura_meses = total_liquida / despesa_mensal if despesa_mensal > 0 else 0.0

        niveis_calc = {n: despesa_mensal * n for n in self._config.niveis_meses}
        nivel_keys = sorted(niveis_calc.keys())

        composicao_liquida = {
            identity.key_inv_titular: inv_titular,
            identity.key_inv_conjuge: inv_conjuge,
            "caixa_moeda_estrangeira": caixa,
            "total_liquido": round(total_liquida, 2),
            "cobertura_meses": round(cobertura_meses, 1),
        }

        avaliacao = self._classify(cobertura_meses)

        return {
            "despesas_mensais": round(despesa_mensal, 2),
            "janela": janela,
            "janela_meses": janela_meses,
            "nivel_6_meses": round(niveis_calc.get(6, despesa_mensal * 6), 2),
            "nivel_12_meses": round(niveis_calc.get(12, despesa_mensal * 12), 2),
            "composicao_liquida": {k: round(v, 2) for k, v in composicao_liquida.items()},
            "total_liquida": round(total_liquida, 2),
            "cobertura_meses": round(cobertura_meses, 1),
            "avaliacao_liquidity": avaliacao,
            "niveis": [f"{n} meses" for n in nivel_keys],
        }

    def _classify(self, cobertura_meses: float) -> str:
        """Avalia cobertura iterando faixas ordenadas por ``minimo_meses`` desc.

        Primeira faixa cujo ``minimo_meses`` é ≤ cobertura → vence.
        Fallback se nenhuma casar: ``"Insuficiente"``.
        """
        ordered = sorted(
            self._config.classificacao,
            key=lambda f: f.minimo_meses,
            reverse=True,
        )
        for faixa in ordered:
            if cobertura_meses >= faixa.minimo_meses:
                return faixa.label
        return "Insuficiente"


def _resolve_base_mensal(fluxo: dict) -> tuple[float, str, int]:
    """Retorna ``(despesa_mensal, janela, janela_meses)`` — janela 12m canônica (ADR-306)."""
    j12m = (fluxo or {}).get("janela_12m") or {}
    if isinstance(j12m, dict) and j12m.get("despesa_mensal_media") is not None:
        return (
            safe_float(j12m.get("despesa_mensal_media", 0)),
            "12m",
            int(safe_float(j12m.get("n_meses", 0))),
        )
    return (
        safe_float((fluxo or {}).get("despesa_mensal_media", 0)),
        "full",
        int(safe_float((fluxo or {}).get("janela_meses", 0))),
    )
