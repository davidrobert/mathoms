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

Os dois conjuntos são **deliberadamente não iguais**: ``transferencia_patrimonial``
sai do denominador da taxa de poupança ([[ADR-333]]) e move ``folga_mensal``;
``transferencia_de_conta`` sai só da base do pontual. Fundi-los não é refactor, é
mudança de número — ``transferencia_familiar`` é plausivelmente consumo, e a decisão
é do ``financial-planner``.
"""

from __future__ import annotations

from dataclasses import dataclass

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

    @property
    def nao_consumo_pontual(self) -> frozenset[str]:
        """A exclusão de **natureza** por categoria — a união dos dois conjuntos.

        Hoje cada produtor tem metade dela; convergir os três é o PR seguinte.
        """
        return self.transferencia_patrimonial | self.transferencia_de_conta

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
