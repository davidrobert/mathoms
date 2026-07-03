"""ConsumoConscienteCalculator — identifica gastos pontuais relevantes
(Sessão A5b · Fase 8).

Extrai ``analyze_consumo_consciente`` (e5_analyze.py:2039) em domain service
puro. Varre transações de despesas, exclui categorias recorrentes, mantém
items com valor ≥ threshold e agrega métricas (folga mensal, teto sugerido,
equivalente-meses-aporte).

Função pura, recebe dicts + config tipada (R9/ISP). Sem I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace(",", "."))
        except ValueError:
            return 0.0
    return 0.0


# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class _ConsumoWindow:
    receita_rec_mensal: float
    despesa_mensal_media: float
    n_meses: float
    janela: str
    mes_inicio: str


def _periodo_inicio(periodo: str) -> str:
    """Extrai o mês inicial de ``"YYYY-MM a YYYY-MM"`` (vazio se malformado)."""
    inicio = periodo.split(" a ")[0].strip()
    return inicio if len(inicio) == 7 else ""


def _dentro_da_janela(mes: str, mes_inicio: str) -> bool:
    """Sem ``mes_inicio`` (janela full) tudo entra; compara ``YYYY-MM`` lexicográfico."""
    if not mes_inicio:
        return True
    return bool(mes) and mes >= mes_inicio


_DEFAULT_RECURRENT = frozenset(
    {
        "moradia",
        "financiamentos",
        "seguros",
        "assinaturas",
        "impostos",
        "servicos_domesticos",
    }
)


@dataclass(frozen=True)
class ConsumoConscienteConfig:
    """Threshold + categorias recorrentes + aporte mensal.

    Sources no legado:
    - ``consumo_min`` ← ``scoring.json::thresholds_alertas.consumo_consciente_min``
      (default R$ 2000)
    - ``recurrent_categories`` — hardcoded no legado
    - ``aporte_mensal`` ← ``goals.json::aportes.meta_aporte_mensal``
    """

    consumo_min: float = 2000.0
    recurrent_categories: frozenset[str] = _DEFAULT_RECURRENT
    aporte_mensal: float = 0.0
    teto_multiplier: float = 1.15

    @classmethod
    def from_configs(
        cls,
        *,
        scoring: dict | None = None,
        goals: dict | None = None,
    ) -> "ConsumoConscienteConfig":
        alertas = (scoring or {}).get("thresholds_alertas") or {}
        aportes = (goals or {}).get("aportes") or {}

        return cls(
            consumo_min=_safe_float(alertas.get("consumo_consciente_min", 2000)),
            aporte_mensal=_safe_float(aportes.get("meta_aporte_mensal", 0)),
        )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class GastoPontualItem:
    descricao: str
    conta_cartao: str
    data: str
    mes: str
    valor: float
    categoria: str
    observacao: str = ""

    def to_dict(self) -> dict:
        return {
            "descricao": self.descricao,
            "conta_cartao": self.conta_cartao,
            "data": self.data,
            "mes": self.mes,
            "valor": round(self.valor, 2),
            "categoria": self.categoria,
            "observacao": self.observacao,
        }


@dataclass(frozen=True)
class ConsumoConsciente:
    itens: tuple[GastoPontualItem, ...]
    total_pontuais: float
    equivalente_meses_aporte: float
    folga_mensal: float
    folga_pct: float
    teto_sugerido: float
    analise: str
    # ADR-306 §D6 — folga derivada da janela canônica; pontuais da janela
    # expostos para o teste de reconciliação algébrica.
    janela: str = "full"
    janela_meses: int = 0
    total_pontuais_janela: float = 0.0

    def to_legacy_dict(self) -> dict:
        return {
            "itens": [i.to_dict() for i in self.itens],
            "total_pontuais": round(self.total_pontuais, 2),
            "total_pontuais_janela": round(self.total_pontuais_janela, 2),
            "equivalente_meses_aporte": self.equivalente_meses_aporte,
            "folga_mensal": round(self.folga_mensal, 2),
            "folga_pct": self.folga_pct,
            "teto_sugerido": round(self.teto_sugerido, 2),
            "analise": self.analise,
            "janela": self.janela,
            "janela_meses": self.janela_meses,
        }


# =============================================================================
# Service
# =============================================================================


class ConsumoConscienteCalculator:
    """Identifica gastos pontuais relevantes + métricas de folga."""

    def __init__(self, config: ConsumoConscienteConfig | None = None) -> None:
        self._config = config or ConsumoConscienteConfig()

    def calculate(
        self,
        fluxo: dict[str, Any],
        despesas: dict[str, Any],
    ) -> ConsumoConsciente:
        cfg = self._config
        dados = (despesas or {}).get("dados", {}) or {}

        candidates = self._collect_candidates(dados)
        candidates.sort(key=lambda x: x.valor, reverse=True)
        total_pontuais = sum(c.valor for c in candidates)

        equivalente = round(total_pontuais / cfg.aporte_mensal, 1) if cfg.aporte_mensal > 0 else 0.0

        window = self._resolve_janela(fluxo)

        # ADR-306 §D6: pontuais da folga restritos à janela canônica —
        # misturar pontuais full-period com denominador 12m inflava a folga.
        total_pontuais_janela = sum(
            c.valor for c in candidates if _dentro_da_janela(c.mes, window.mes_inicio)
        )
        pontual_mensal = total_pontuais_janela / window.n_meses if window.n_meses > 0 else 0.0
        despesas_recorrentes_mensal = window.despesa_mensal_media - pontual_mensal
        folga_mensal = window.receita_rec_mensal - despesas_recorrentes_mensal
        folga_pct = (
            round((folga_mensal / window.receita_rec_mensal * 100), 1)
            if window.receita_rec_mensal > 0
            else 0.0
        )
        teto_sugerido = despesas_recorrentes_mensal * cfg.teto_multiplier

        analise = self._build_analise(
            n_candidates=len(candidates),
            total_pontuais=total_pontuais,
            equivalente_meses=equivalente,
        )

        return ConsumoConsciente(
            itens=tuple(candidates),
            total_pontuais=total_pontuais,
            equivalente_meses_aporte=equivalente,
            folga_mensal=folga_mensal,
            folga_pct=folga_pct,
            teto_sugerido=teto_sugerido,
            analise=analise,
            janela=window.janela,
            janela_meses=int(window.n_meses),
            total_pontuais_janela=total_pontuais_janela,
        )

    # -- Helpers --

    def _collect_candidates(self, dados: dict[str, Any]) -> list[GastoPontualItem]:
        cfg = self._config
        out: list[GastoPontualItem] = []
        for cat, transacoes in dados.items():
            if cat in cfg.recurrent_categories:
                continue
            if not isinstance(transacoes, list):
                continue
            for txn in transacoes:
                if not isinstance(txn, dict):
                    continue
                valor = _safe_float(txn.get("valor", 0))
                if valor < cfg.consumo_min:
                    continue
                data_str = str(txn.get("data", ""))
                banco = str(txn.get("banco", ""))
                tipo_conta = str(txn.get("tipo_conta", ""))
                conta_cartao = f"{banco} ({tipo_conta})" if tipo_conta else banco
                out.append(
                    GastoPontualItem(
                        descricao=str(txn.get("descricao", "N/D")),
                        conta_cartao=conta_cartao,
                        data=data_str,
                        mes=data_str[:7] if len(data_str) >= 7 else "",
                        valor=valor,
                        categoria=str(cat),
                    )
                )
        return out

    def _resolve_janela(self, fluxo: dict[str, Any]) -> "_ConsumoWindow":
        j12m = fluxo.get("janela_12m") if isinstance(fluxo, dict) else None
        if j12m:
            return _ConsumoWindow(
                receita_rec_mensal=_safe_float(j12m.get("receita_recorrente_mensal", 0)),
                despesa_mensal_media=_safe_float(j12m.get("despesa_mensal_media", 0)),
                n_meses=_safe_float(j12m.get("n_meses", 12)) or 12.0,
                janela="12m",
                mes_inicio=_periodo_inicio(str(j12m.get("periodo", ""))),
            )
        return _ConsumoWindow(
            receita_rec_mensal=_safe_float((fluxo or {}).get("receita_recorrente_mensal", 0)),
            despesa_mensal_media=_safe_float((fluxo or {}).get("despesa_mensal_media", 0)),
            n_meses=_safe_float((fluxo or {}).get("num_months", 12)) or 12.0,
            janela="full",
            mes_inicio="",
        )

    def _build_analise(
        self, *, n_candidates: int, total_pontuais: float, equivalente_meses: float
    ) -> str:
        cfg = self._config
        if n_candidates > 0:
            return (
                f"Identificados {n_candidates} gastos pontuais ≥ R$ {cfg.consumo_min:,.0f} "
                f"no período analisado. O total de R$ {total_pontuais:,.2f} equivale a "
                f"{equivalente_meses:.1f} meses de aporte."
            )
        return (
            f"Nenhum gasto pontual relevante ≥ R$ {cfg.consumo_min:,.0f} identificado "
            "no período analisado — padrão de consumo dentro dos limites recorrentes."
        )
