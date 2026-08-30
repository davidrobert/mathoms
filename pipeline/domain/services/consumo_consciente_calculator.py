"""ConsumoConscienteCalculator — identifica gastos pontuais relevantes
(Sessão A5b · Fase 8).

Extrai ``analyze_consumo_consciente`` (e5_analyze.py:2039) em domain service
puro. Varre transações de despesas, exclui categorias recorrentes, mantém
items com valor ≥ threshold e agrega métricas (folga mensal,
equivalente-meses-aporte).

Função pura, recebe dicts + config tipada (R9/ISP). Sem I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from pipeline.domain.services.brl_prose import fmt_brl_prosa
from pipeline.domain.services.gasto_pontual_policy import GastoPontualPolicy


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
    despesa_consumo_mensal: float
    n_meses: float
    janela: str
    mes_inicio: str


def _periodo_inicio(periodo: str) -> str:
    """Extrai o mês inicial de ``"YYYY-MM a YYYY-MM"`` (vazio se malformado)."""
    inicio = periodo.split(" a ")[0].strip()
    return inicio if len(inicio) == 7 else ""


def _consumo_mensal(j12m: dict[str, Any], n_meses: float) -> float:
    """Despesa de consumo mensal da janela — ``despesa_consumo`` ([[ADR-333]]).

    Chave ausente (payload anterior à ADR-333) degrada para a despesa bruta:
    ``.get("despesa_consumo", 0)`` daria folga == receita inteira.
    """
    if n_meses <= 0:
        return 0.0
    bruto_mensal = _safe_float(j12m.get("despesa_mensal_media", 0))
    consumo = j12m.get("despesa_consumo")
    return _safe_float(consumo) / n_meses if consumo is not None else bruto_mensal


def _dentro_da_janela(mes: str, mes_inicio: str) -> bool:
    """Sem ``mes_inicio`` (janela full) tudo entra; compara ``YYYY-MM`` lexicográfico."""
    if not mes_inicio:
        return True
    return bool(mes) and mes >= mes_inicio


def _sem_zero_negativo(publicada: float) -> float:
    """``-0.0`` sairia ``"R$ -0,00"`` na prosa; ``-0.0`` é falsy e ``nan`` não."""
    return 0.0 if publicada == 0 else publicada


def _folga_em_prosa(publicada: float) -> str:
    """Trecho reusado pelo motivo e pela prosa — ``nan``/``inf`` não viram ``"R$ NaN"``."""
    if not math.isfinite(publicada):
        return "folga mensal indeterminada"
    return f"folga mensal de {fmt_brl_prosa(publicada, decimals=2)}"


def _motivo_folga_nao_positiva(folga_em_prosa: str, n_meses: float) -> str:
    """Motivo de máquina, forma ``"<slug>: <detalhe>"`` ([[ADR-394]] §D7); a copy da
    família vive na prosa do E5."""
    return (
        f"folga_nao_positiva: a janela de {n_meses:.0f} meses fechou sem poupança "
        f"({folga_em_prosa}) — o gasto pontual não tem equivalente em meses"
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
    # ``None`` e não ``0,0``: um zero publicado é uma afirmação sobre a poupança
    # da família, e fora do domínio de definição o sistema não a mediu
    # ([[ADR-394]] §D7, forma de ``investimentos_cobertura.valor_publicavel``).
    equivalente_meses_poupanca: float | None
    folga_mensal: float
    folga_pct: float | None
    analise: str
    motivo_supressao: str | None = None
    # Folga derivada da janela canônica (ADR-306 §D1); pontuais da janela
    # expostos para o inventário e para o gate de base ([[ADR-422]]).
    janela: str = "full"
    janela_meses: int = 0
    pontuais_janela: float = 0.0

    def to_legacy_dict(self) -> dict:
        return {
            "itens": [i.to_dict() for i in self.itens],
            "total_pontuais": round(self.total_pontuais, 2),
            "total_pontuais_janela": round(self.pontuais_janela, 2),
            "equivalente_meses_poupanca": self.equivalente_meses_poupanca,
            "folga_mensal": round(self.folga_mensal, 2),
            "folga_pct": self.folga_pct,
            "analise": self.analise,
            "motivo_supressao": self.motivo_supressao,
            "janela": self.janela,
            "janela_meses": self.janela_meses,
        }


# =============================================================================
# Service
# =============================================================================


class ConsumoConscienteCalculator:
    """Identifica gastos pontuais relevantes + métricas de folga."""

    def __init__(self, policy: GastoPontualPolicy | None = None) -> None:
        self._policy = policy or GastoPontualPolicy()

    def calculate(
        self,
        fluxo: dict[str, Any],
        despesas: dict[str, Any],
    ) -> ConsumoConsciente:
        cfg = self._policy
        dados = (despesas or {}).get("dados", {}) or {}

        candidates = self._collect_candidates(dados)
        candidates.sort(key=lambda x: x.valor, reverse=True)
        total_pontuais = sum(c.valor for c in candidates)

        window = self._resolve_janela(fluxo)

        pontuais_janela = sum(
            c.valor for c in candidates if _dentro_da_janela(c.mes, window.mes_inicio)
        )
        # ADR-422: a folga É a poupança da janela. Devolver ``pontuais_janela/n``
        # ao numerador — o que a ADR-306 §D6 prescrevia — publicava um segundo
        # "quanto sobra" sobre o MESMO denominador da taxa de poupança, maior
        # dela por exatamente a provisão do gasto pontual, e era o maior dos dois
        # que prescrevia (RR6-01). Base é ``despesa_consumo`` (ADR-333): com a
        # bruta, o aporte da janela reintroduz a divergência por outro termo.
        folga_mensal = window.receita_rec_mensal - window.despesa_consumo_mensal
        # Gatear por um número e dividir por outro publica um par que o leitor
        # não recompõe: `to_legacy_dict` publica a folga ARREDONDADA, então é
        # ela que serve de denominador (A40.l101 · cético `sinal-trocado`).
        folga_publicada = _sem_zero_negativo(round(folga_mensal, 2))
        folga_pct = (
            round((folga_mensal / window.receita_rec_mensal * 100), 2)
            if window.receita_rec_mensal > 0
            else None
        )
        # ADR-422: numerador e denominador na MESMA janela. Media contra o aporte
        # DECLARADO (`goals.meta_aporte_mensal`) sobre o estoque full-period —
        # duas bases e um denominador editável pelo usuário; no dogfood o fator
        # de inflação era 4,9× (46,1 meses onde a poupança sustenta 4,1).
        #
        # A guarda `else 0.0` que aqui morre veio TRANSPLANTADA da fórmula
        # anterior, cujo denominador era a meta DECLARADA (>= 0, e `0` queria
        # dizer "não configurou"). Sobre a folga — quantidade MEDIDA que vai a
        # negativo — `<= 0` passou a querer dizer "a família não poupou nada", e
        # `0,0` é o MENOR valor da régua: o pior mundo publicava o melhor número
        # (A40.l101 · [[ADR-422]] §Emenda 2026-08-30).
        folga_em_prosa = _folga_em_prosa(folga_publicada)
        if math.isfinite(folga_publicada) and folga_publicada > 0:
            equivalente = round(pontuais_janela / folga_publicada, 1)
            motivo = None
        else:
            equivalente = None
            motivo = _motivo_folga_nao_positiva(folga_em_prosa, window.n_meses)

        analise = self._build_analise(
            n_candidates=len(candidates),
            total_pontuais=total_pontuais,
            pontuais_janela=pontuais_janela,
            equivalente_meses=equivalente,
            janela_meses=window.n_meses,
            folga_em_prosa=folga_em_prosa,
        )

        return ConsumoConsciente(
            itens=tuple(candidates),
            total_pontuais=total_pontuais,
            equivalente_meses_poupanca=equivalente,
            folga_mensal=folga_mensal,
            folga_pct=folga_pct,
            analise=analise,
            motivo_supressao=motivo,
            janela=window.janela,
            janela_meses=int(window.n_meses),
            pontuais_janela=pontuais_janela,
        )

    # -- Helpers --

    def _collect_candidates(self, dados: dict[str, Any]) -> list[GastoPontualItem]:
        cfg = self._policy
        out: list[GastoPontualItem] = []
        for cat, transacoes in dados.items():
            if cat in cfg.recorrentes:
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
            n_meses = _safe_float(j12m.get("n_meses", 12)) or 12.0
            return _ConsumoWindow(
                receita_rec_mensal=_safe_float(j12m.get("receita_recorrente_mensal", 0)),
                despesa_consumo_mensal=_consumo_mensal(j12m, n_meses),
                n_meses=n_meses,
                janela="12m",
                mes_inicio=_periodo_inicio(str(j12m.get("periodo", ""))),
            )
        return _ConsumoWindow(
            receita_rec_mensal=_safe_float((fluxo or {}).get("receita_recorrente_mensal", 0)),
            despesa_consumo_mensal=_safe_float((fluxo or {}).get("despesa_mensal_media", 0)),
            n_meses=_safe_float((fluxo or {}).get("num_months", 12)) or 12.0,
            janela="full",
            mes_inicio="",
        )

    def _build_analise(
        self,
        *,
        n_candidates: int,
        total_pontuais: float,
        pontuais_janela: float,
        equivalente_meses: float | None,
        janela_meses: float,
        folga_em_prosa: str,
    ) -> str:
        cfg = self._policy
        minimo = fmt_brl_prosa(cfg.consumo_min)
        if n_candidates == 0:
            return (
                f"Nenhum gasto pontual relevante ≥ {minimo} identificado "
                "no período analisado — padrão de consumo dentro dos limites recorrentes."
            )
        cabeca = (
            f"Identificados {n_candidates} gastos pontuais ≥ {minimo} "
            f"no período analisado, somando {fmt_brl_prosa(total_pontuais, decimals=2)}. "
        )
        janela = fmt_brl_prosa(pontuais_janela, decimals=2)
        # Sem este ramo a prosa AFIRMA "equivalentes a 0.0 meses de poupança" num
        # mundo sem poupança nenhuma — e com o campo suprimido ela levanta
        # ``TypeError`` no ``:.1f``. É a trava que impede o "—" do card de virar
        # neutralidade: a ausência tem de vir declarada, não nua (A40.l101).
        if equivalente_meses is None:
            return (
                f"{cabeca}Na janela de {janela_meses:.0f} meses são {janela}, que não se "
                f"convertem em meses de poupança: a janela fechou com "
                f"{folga_em_prosa} — a receita recorrente não cobriu o consumo."
            )
        return (
            f"{cabeca}Na janela de 12 meses são "
            f"{janela}, equivalentes a {equivalente_meses:.1f} meses de poupança."
        )
