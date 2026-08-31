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
from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from pipeline.domain.services.brl_prose import fmt_brl_prosa
from pipeline.domain.services.diagnostico_comportamental_analyzer import (
    NAO_IDENTIFICADO_INSUFICIENTE_PCT,
    NAO_IDENTIFICADO_PARCIAL_PCT,
)
from pipeline.domain.services.gasto_pontual_policy import (
    GastoPontualPolicy,
    VeredictoPontual,
)

_CENTAVO = Decimal("0.01")
_NAO_IDENTIFICADO = VeredictoPontual.nao_identificado.value


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
    mes_fim: str = ""


def _periodo_extremos(periodo: str) -> tuple[str, str]:
    """Extremos de ``"YYYY-MM a YYYY-MM"``; vazios se malformado."""
    partes = [p.strip() for p in periodo.split(" a ")]
    if len(partes) != 2:
        return "", ""
    inicio, fim = partes
    return (inicio if len(inicio) == 7 else "", fim if len(fim) == 7 else "")


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


# O limite SUPERIOR não existia (A40.l101, escape sem dono): o denominador roda
# sobre a janela fechada e o numerador ia de ``mes_inicio`` a ``+∞``, então um
# lançamento posterior ao fim da janela entrava só de um lado — o mesmo pontual
# publicava 6,0 ou 12,0 conforme o corte.
def _dentro_da_janela(mes: str, mes_inicio: str, mes_fim: str) -> bool:
    """Sem ``mes_inicio`` (janela full) tudo entra; ``YYYY-MM`` lexicográfico."""
    if not mes_inicio:
        return True
    if not mes:
        return False
    return mes >= mes_inicio and (not mes_fim or mes <= mes_fim)


def _sem_zero_negativo(publicada: float) -> float:
    """``-0.0`` sairia ``"R$ -0,00"`` na prosa; ``-0.0`` é falsy e ``nan`` não."""
    return 0.0 if publicada == 0 else publicada


def _folga_em_prosa(publicada: float) -> str:
    """Trecho reusado pelo motivo e pela prosa — ``nan``/``inf`` não viram ``"R$ NaN"``."""
    if not math.isfinite(publicada):
        return "folga mensal indeterminada"
    return f"folga mensal de {fmt_brl_prosa(publicada, decimals=2)}"


def _item_pontual(txn: dict, categoria: str, quantia: Decimal) -> "GastoPontualItem":
    data_str = str(txn.get("data", ""))
    banco = str(txn.get("banco", ""))
    tipo_conta = str(txn.get("tipo_conta", ""))
    return GastoPontualItem(
        descricao=str(txn.get("descricao", "N/D")),
        conta_cartao=f"{banco} ({tipo_conta})" if tipo_conta else banco,
        data=data_str,
        mes=data_str[:7] if len(data_str) >= 7 else "",
        valor=float(quantia),
        categoria=categoria,
    )


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
class BaldePontual:
    # ``pct`` NÃO é campo ([[ADR-425]] §D2) e hoje ninguém o deriva — o card imprime
    # absolutos. Quando alguém precisar dele, a razão é
    # ``publicado / (publicado + excluidos.nao_identificado)``: ``recorrente`` e
    # ``transferencia_*`` ficam fora do denominador porque são exclusão deliberada,
    # não falha de medição.
    """Um balde da base: quanto e quantos."""

    # ``Decimal`` e não ``float`` ([[ADR-090]]): é o único ponto do módulo que
    # ACUMULA dinheiro, e a identidade de conservação tem de fechar ao centavo. O
    # ``float`` volta só no ``to_dict``, que é o wire.

    total: Decimal = Decimal("0")
    contagem: int = 0

    def mais(self, quantia: Decimal) -> "BaldePontual":
        return BaldePontual(self.total + quantia, self.contagem + 1)

    @property
    def publicavel(self) -> Decimal:
        """O valor como ele sai no wire — 2 casas. Ler daqui, nunca de ``total``."""
        return self.total.quantize(_CENTAVO)

    def to_dict(self) -> dict:
        return {"valor": float(self.publicavel), "contagem": self.contagem}


@dataclass(frozen=True)
class BasePontuais:
    """O que a base do gasto pontual exclui, **por causa** — declarado na
    superfície que a publica ([[ADR-425]] §D2).

    Invariante: ``bruto.valor == publicado.valor + Σ excluidos[].valor``. O
    universo é *todo lançamento acima do limiar*: recortar o ``bruto`` mais
    estreito reintroduziria um filtro não declarado, que é o defeito que esta
    base existe para remover.
    """

    publicado: BaldePontual
    excluidos: dict[str, BaldePontual]

    # Soma os baldes JÁ QUANTIZADOS, não os `Decimal` crus: quem lê o payload soma
    # os valores publicados, e somar cru antes de arredondar quebrava a identidade
    # no wire — `100,005 + 200,005` publicava `300,01` ao lado de `100,00 + 200,00`.
    # O objeto cuja função é declarar conservação não pode falhar a própria.
    @property
    def bruto(self) -> BaldePontual:
        baldes = [self.publicado, *self.excluidos.values()]
        return BaldePontual(
            sum((b.publicavel for b in baldes), Decimal("0")),
            sum(b.contagem for b in baldes),
        )

    # A razão é `publicado / (publicado + nao_identificado)` — a fatia MEDIDA sobre o
    # que era medível na mesma natureza. `recorrente` e `transferencia_*` ficam fora
    # do denominador: são exclusão deliberada, não falha de medição. Usar `bruto`
    # daria ~10-15% no dogfood e não seria cobertura de coisa nenhuma (refutação do
    # `senior-cto`, registrada na [[ADR-425]] §Emenda).
    # ``None`` quando não há denominador: um ``alta`` sobre medição que não houve é
    # afirmação sobre o dinheiro da família ([[ADR-394]] §D7). Diverge da
    # [[ADR-353]] D2 de propósito — lá o nível controla DENSIDADE e ``alta`` é o
    # comportamento antigo; aqui ele é **rótulo publicado**.
    @property
    def cobertura_nivel(self) -> str | None:
        """Veredito ordinal, régua da [[ADR-353]] D1 — as constantes são IMPORTADAS."""
        nao_medido = self.excluidos.get(_NAO_IDENTIFICADO)
        medivel = self.publicado.publicavel + (nao_medido.publicavel if nao_medido else 0)
        if medivel <= 0:
            return None
        share = float(100 - self.publicado.publicavel / medivel * 100)
        if share > NAO_IDENTIFICADO_INSUFICIENTE_PCT:
            return "insuficiente"
        if share > NAO_IDENTIFICADO_PARCIAL_PCT:
            return "parcial"
        return "alta"

    def to_dict(self) -> dict:
        return {
            "bruto": self.bruto.to_dict(),
            "publicado": self.publicado.to_dict(),
            "excluidos": {k: v.to_dict() for k, v in sorted(self.excluidos.items())},
            "cobertura_nivel": self.cobertura_nivel,
            "cobertura_motivo": None
            if self.cobertura_nivel
            else "sem_base_medivel: nenhum lançamento acima do limiar foi classificado",
        }


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
    base: BasePontuais = field(default_factory=lambda: BasePontuais(BaldePontual(), {}))

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
            "base_pontuais": self.base.to_dict(),
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
        dados = (despesas or {}).get("dados", {}) or {}

        window = self._resolve_janela(fluxo)
        candidates, base = self._triar(dados)
        candidates.sort(key=lambda x: x.valor, reverse=True)
        total_pontuais = float(base.publicado.total)

        pontuais_janela = sum(
            c.valor
            for c in candidates
            if _dentro_da_janela(c.mes, window.mes_inicio, window.mes_fim)
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
            base=base,
        )

    # -- Helpers --

    # A40.l98 — a exclusão de natureza é a UNIÃO dos dois conjuntos de categoria.
    # Antes daqui só saía `recorrentes`: o aporte (`transferencia_patrimonial`,
    # [[ADR-333]]) e a transferência entre contas entravam na base que o parecer
    # usa para prescrever contenção de consumo. Sem detector — dentro do E5 ele é
    # inerte por construção (ver `GastoPontualPolicy.classify`).
    #
    # [[ADR-425]] §D1 — `nao_identificado` também sai daqui: é ausência de
    # MEDIÇÃO, não ruído, e `total_pontuais*` é numerador que sustenta conselho
    # (o parecer ancora nele o risco "gastos pontuais elevados"). Ele segue no
    # inventário — o balde de `excluidos` traz total e contagem, e a lista do
    # card traz as linhas, que é onde a família consegue agir.
    def _triar(self, dados: dict[str, Any]) -> tuple[list[GastoPontualItem], BasePontuais]:
        """Todo lançamento acima do limiar recebe um veredito — o descartado sai
        atribuído a uma causa, não em silêncio."""
        incluidos: list[GastoPontualItem] = []
        excluidos: dict[str, BaldePontual] = {}
        publicado = BaldePontual()
        for cat, transacoes in dados.items():
            if not isinstance(transacoes, list):
                continue
            veredito = self._policy.classify_por_categoria(str(cat))
            for quantia, txn in self._relevantes(transacoes):
                balde = veredito.value if veredito is not VeredictoPontual.incluido else None
                if balde is None:
                    incluidos.append(_item_pontual(txn, str(cat), quantia))
                    publicado = publicado.mais(quantia)
                    continue
                excluidos[balde] = excluidos.get(balde, BaldePontual()).mais(quantia)
        return incluidos, BasePontuais(publicado, excluidos)

    # O corte de provisionado NÃO é feito aqui: quem o faz é `split_provisionado`,
    # UMA vez, e o adapter entrega as despesas já realizadas. Um segundo corte
    # divergiria em silêncio do primeiro — medido na A40.l98: `data` nula
    # (`scripts/e2/banks/wise.py:153`) e `data` com hora no dia do corte caíam só
    # deste lado, e sumiam até do `bruto`, que existe para revelar perda.
    def _relevantes(self, transacoes: list) -> Iterator[tuple[Decimal, dict]]:
        for txn in transacoes:
            if not isinstance(txn, dict):
                continue
            bruto = _safe_float(txn.get("valor", 0))
            if self._policy.is_relevante(bruto):
                yield Decimal(str(bruto)), txn

    def _resolve_janela(self, fluxo: dict[str, Any]) -> "_ConsumoWindow":
        j12m = fluxo.get("janela_12m") if isinstance(fluxo, dict) else None
        if j12m:
            n_meses = _safe_float(j12m.get("n_meses", 12)) or 12.0
            inicio, fim = _periodo_extremos(str(j12m.get("periodo", "")))
            return _ConsumoWindow(
                receita_rec_mensal=_safe_float(j12m.get("receita_recorrente_mensal", 0)),
                despesa_consumo_mensal=_consumo_mensal(j12m, n_meses),
                n_meses=n_meses,
                janela="12m",
                mes_inicio=inicio,
                mes_fim=fim,
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
