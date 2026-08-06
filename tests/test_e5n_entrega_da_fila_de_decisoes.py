"""A40.l10 (RV4-02) — a primeira decisão do dono chega às DUAS superfícies.

Até 2026-08-05 o ``charts.top5_decisoes`` enumerava ``decisoes[1:5]`` e o
``summaries.s10`` enumerava ``decisoes[1:4]``: a primeira decisão registrada
pelo dono não aparecia em nenhuma das duas, e a S10 é a única seção do
relatório que responde "o que fazer" (``report_layout.yaml`` §S10
``summary_source: "s10"``).

O defeito era invisível à suíte porque **toda** fixture do repo põe um título
de aporte no índice 0 (``narrativas_synthetic.DECISOES``,
``test_e5n_no_dead_data``, ``test_narrativas_empty_field_guards``) — descartar
``decisoes[0]`` e reimprimi-lo como "Prioridade 1: Aporte mensal ..." produzia
um texto plausível. Por isso a fixture aqui abre com uma decisão que **não** é
de aporte: é o que separa este teste do bug.
"""

from __future__ import annotations

from typing import Any

from pipeline.domain.services.narrativas import (
    ChartsNarrator,
    NarrativasContext,
    SummariesNarrator,
)
from tests.test_e5n_builder_decomposition import _FAMILY_BASE, _build_metrics

# O item [0] NÃO é de aporte: com o slice antigo ele sumia e o leitor via o
# aporte ocupando "Prioridade 1" no lugar dele.
_PRIMEIRA = "Renegociar financiamento imobiliario"
_DECISOES = [
    _PRIMEIRA,
    "Contratar seguro de vida",
    "Consolidar reserva de emergencia",
    "Revisar alocacao em renda variavel",
    "Avaliar holding patrimonial",
]

_RISCOS = [{"nome": "r1", "prob": "a", "impacto": "a"}]


def _chart(decisoes: list[str], **metric_overrides: Any) -> dict[str, str]:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    metrics = {**_build_metrics(), **metric_overrides}
    return ChartsNarrator(ctx).narrate(metrics, _FAMILY_BASE, _RISCOS, decisoes)["top5_decisoes"]


def _s10(decisoes: list[str], **metric_overrides: Any) -> str:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    metrics = {**_build_metrics(), **metric_overrides}
    return SummariesNarrator(ctx).narrate(metrics, _FAMILY_BASE, ["r1"], decisoes)["s10"]


# ── A primeira decisão é entregue, nas duas superfícies ────────────────


def test_chart_entrega_a_primeira_decisao_como_prioridade_1():
    assert f"Prioridade 1: {_PRIMEIRA}" in _chart(_DECISOES)["conclusion"]


def test_s10_entrega_a_primeira_decisao():
    assert _PRIMEIRA in _s10(_DECISOES)


def test_chart_entrega_toda_a_fila_recebida():
    conclusion = _chart(_DECISOES)["conclusion"]
    for decisao in _DECISOES:
        assert decisao in conclusion, f"decisão perdida na renderização: {decisao!r}"


def test_s10_nao_descarta_a_cauda_com_fila_curta():
    """Com 3 decisões o ramo antigo não listava NENHUMA — só a contagem."""
    curta = _DECISOES[:3]
    s10 = _s10(curta)
    for decisao in curta:
        assert decisao in s10, f"decisão perdida no s10: {decisao!r}"


def test_contagem_do_context_bate_com_os_itens_enumerados():
    """O ``context`` contava N e o ``conclusion`` listava N-1: a aritmética
    fechava por acidente porque o aporte reocupava a vaga."""
    conclusion = _chart(_DECISOES)["conclusion"]
    assert conclusion.count("Prioridade ") == len(_DECISOES)


# ── O aporte é enquadramento, não item numerado ───────────────────────


def test_aporte_nao_ocupa_posicao_na_fila():
    conclusion = _chart(_DECISOES)["conclusion"]
    assert "Prioridade 1: Aporte" not in conclusion
    assert "Meta vigente de aporte mensal" in conclusion


def test_meta_de_aporte_zerada_omite_a_frase_inteira():
    """``R$ 0,00`` não é meta — a frase inteira sai."""
    conclusion = _chart(_DECISOES, meta_aporte_mensal=0)["conclusion"]
    assert "aporte" not in conclusion.lower()
    assert f"Prioridade 1: {_PRIMEIRA}" in conclusion
    assert "R$ 0,00" not in _s10(_DECISOES, meta_aporte_mensal=0)


# ── Empty states honestos ─────────────────────────────────────────────


def test_fila_vazia_nao_afirma_prioridade_nem_cita_aporte():
    conclusion = _chart([])["conclusion"]
    assert "Prioridade" not in conclusion
    assert "aporte" not in conclusion.lower()
    assert "Nenhuma decisão priorizada" in conclusion


def test_s10_com_fila_vazia_nao_afirma_prioridade():
    s10 = _s10([])
    assert "Nenhuma decisão estratégica priorizada" in s10
    assert "R$ 0,00" not in s10
