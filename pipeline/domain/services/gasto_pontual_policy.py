"""``GastoPontualPolicy`` — a definição de "gasto pontual", num objeto só (A40.l98).

Existiam **três** produtores de gasto pontual em produção com filtros disjuntos, e
o que **prescrevia** era o que menos filtrava:

======================================  ==========================================
produtor                                excluía
======================================  ==========================================
``FluxoEnricherConfig``                 ``aporte_investimento`` ([[ADR-333]])
``consumo_pontuais.py::_is_pontual``    transferência detectada + 3 categorias
``ConsumoConscienteCalculator``         só ``recurrent_categories``
======================================  ==========================================

O quarto eixo era o **limiar**: o endpoint da lista não passava ``threshold`` e caía
num ``Decimal("2000")`` hardcoded, enquanto o KPI lia
``scoring.json::thresholds_alertas.consumo_consciente_min``. Os dois valiam 2000 e
**coincidiam por acaso** — editar o ``scoring.json`` os separava em silêncio.

``detector`` é opcional em ``classify`` porque ele **não é aplicável dentro do
E5**: o E4 roteia transferência detectada para ``kind="transferencia"``
(``transaction_classifier.py`` passo 1) e ela nunca chega a ``despesas.dados`` —
filtro ali seria inerte **por construção**, e foi medido como tal
(``tests/test_e5_base_gasto_pontual.py``). Na LISTA ele é vivo por outro motivo:
o detector do endpoint é resolvido do ``TransferConfig`` do **DB**, que pode ter
mudado depois do run que produziu o artefato.

Os dois conjuntos são **deliberadamente não iguais**: ``transferencia_patrimonial``
sai do denominador da taxa de poupança ([[ADR-333]]) e move ``folga_mensal``;
``transferencia_de_conta`` sai só da base do pontual. Fundi-los não é refactor, é
mudança de número — ``transferencia_familiar`` é plausivelmente consumo, e a decisão
é do ``financial-planner``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Protocol


# ``transferencia_por_categoria`` cobre os DOIS conjuntos: o rótulo é mais grosso
# que os conjuntos de propósito — fundir os CONJUNTOS mudaria ``folga_mensal``,
# fundir os RÓTULOS não muda número nenhum.
class VeredictoPontual(str, Enum):
    """Por que um lançamento entrou (ou não) na base — enum FECHADO. Sem veredito
    por item o residual não tem como ser atribuído por causa ([[ADR-425]] §D2)."""

    incluido = "incluido"
    recorrente = "recorrente"
    transferencia_por_categoria = "transferencia_por_categoria"
    transferencia_detectada = "transferencia_detectada"
    nao_identificado = "nao_identificado"


class _DetectorDeTransferencia(Protocol):
    def is_internal_transfer(self, description: str, *, banco: str = "") -> bool: ...


_DEFAULT_CONSUMO_MIN = 2000.0

# [[ADR-333]] — poupança realizada não é consumo: sai do denominador da taxa de
# poupança (segue em ``despesa_total`` → ``fluxo_liquido`` preservado).
_DEFAULT_TRANSFERENCIA_PATRIMONIAL = frozenset({"aporte_investimento"})

# Movimentação entre contas do próprio titular ou da família — não sai de
# ``despesa_consumo`` (a decisão sobre ``transferencia_familiar`` é do
# ``financial-planner``), mas nunca é "gasto pontual relevante".
_DEFAULT_TRANSFERENCIA_DE_CONTA = frozenset(
    {"transferencia_entre_contas", "transferencia_familiar", "transferencias_internas"}
)

# [[ADR-425]] §D1 — o balde-lixo default do categorizador. Não é ruído a
# excluir: é **ausência de medição**, e fica fora de numerador que sustenta
# conselho justamente por isso. Segue no inventário (a lista do card), que é
# onde a família consegue agir sobre ele.
_DEFAULT_NAO_CLASSIFICADAS = frozenset({"nao_identificado"})

_DEFAULT_RECORRENTES = frozenset(
    {
        "moradia",
        "financiamentos",
        "seguros",
        "assinaturas",
        "impostos",
        "servicos_domesticos",
        # Labels PJ ([[ADR-236]] §D2): tributo e folha da PJ são obrigação
        # recorrente, não "gasto pontual relevante" cortável. Sem isso um DAS de
        # R$ 5k/guia entra em ``total_pontuais``/``pontuais_janela`` e infla o
        # inventário e o ``equivalente_meses_poupanca`` (A40.l4).
        "das_simples",
        "iss",
        "folha_pj",
    }
)


@dataclass(frozen=True)
class GastoPontualPolicy:
    """Vocabulário único dos três produtores — conjuntos nomeados + limiar."""

    consumo_min: float = _DEFAULT_CONSUMO_MIN
    transferencia_patrimonial: frozenset[str] = _DEFAULT_TRANSFERENCIA_PATRIMONIAL
    transferencia_de_conta: frozenset[str] = _DEFAULT_TRANSFERENCIA_DE_CONTA
    recorrentes: frozenset[str] = _DEFAULT_RECORRENTES
    nao_classificadas: frozenset[str] = _DEFAULT_NAO_CLASSIFICADAS

    @property
    def nao_consumo_pontual(self) -> frozenset[str]:
        """A exclusão de **natureza** por categoria — a união dos dois conjuntos."""
        return self.transferencia_patrimonial | self.transferencia_de_conta

    # Cláusula de POPULAÇÃO, separada das de natureza: o limiar não diz o que o
    # lançamento é, só se ele é grande o bastante para o card. Aceita ``Decimal``
    # sem converter — a lista carrega ``Decimal`` e passar por ``float`` aqui
    # seria dinheiro em float ([[ADR-090]]).
    def is_relevante(self, quantia: Decimal | float) -> bool:
        return abs(quantia) >= self.consumo_min

    def classify(
        self,
        categoria: str,
        *,
        descricao: str = "",
        banco: str = "",
        detector: _DetectorDeTransferencia | None = None,
    ) -> VeredictoPontual:
        """As cláusulas de **natureza**, na mesma ordem para os três produtores."""
        if categoria in self.recorrentes:
            return VeredictoPontual.recorrente
        if categoria in self.nao_consumo_pontual:
            return VeredictoPontual.transferencia_por_categoria
        if detector is not None and detector.is_internal_transfer(descricao, banco=banco):
            return VeredictoPontual.transferencia_detectada
        if categoria in self.nao_classificadas:
            return VeredictoPontual.nao_identificado
        return VeredictoPontual.incluido

    @classmethod
    def from_scoring(cls, scoring: dict | None = None) -> "GastoPontualPolicy":
        """``scoring.json::thresholds_alertas.consumo_consciente_min`` — fonte única
        do limiar, para a lista e para o KPI."""
        alertas = (scoring or {}).get("thresholds_alertas") or {}
        return cls(consumo_min=_coerce_min(alertas.get("consumo_consciente_min")))


def _coerce_min(raw: object) -> float:
    """Limiar ausente ou ilegível degrada ao default — nunca a ``0``, que faria
    a base engolir o extrato inteiro."""
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            return _DEFAULT_CONSUMO_MIN
    return _DEFAULT_CONSUMO_MIN
