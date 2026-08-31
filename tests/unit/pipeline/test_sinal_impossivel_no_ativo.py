"""O par `secao` + valor negativo era o único caso MUDO do classificador.

Emenda [[ADR-394]] D1 (2026-08-31): o sinal veta a **magnitude**, não o eixo — a
`secao` decide corretamente que é bem, e o negativo é defeito de medição do valor.
O PGD da Receita não aceita negativo em Bens e Direitos, logo o sinal não veio da
declaração; é nosso. Antes da emenda, `_warnings_for` devolvia `[]` para esse par,
contra o D3 (*"divergência entre degraus vira review_reason, nunca silêncio"*).
"""

from __future__ import annotations

import pytest

from pipeline.domain.services.baseline_item_classifier import (
    SinalImpossivelNoAtivo,
    classify_baseline_item,
)


def _classify(valor_cents: int, secao: str | None = "bens_direitos"):
    return classify_baseline_item(
        codigo="11", valor_cents=valor_cents, secao=secao, categoria_hint="imovel"
    )


def test_secao_manda_no_eixo_e_o_sinal_nao_promove_a_passivo():
    """O conserto NÃO é reclassificar: imóvel financiado é ativo, e o negativo é
    defeito de medição. Mover para passivo fabricaria dívida que a Receita proíbe
    declarar (o saldo devedor não vai em Dívidas e Ônus Reais)."""
    assert _classify(-12345).eixo.value == "ativo"


def test_negativo_em_ativo_deixa_de_ser_mudo():
    warnings = _classify(-12345).warnings

    assert [type(w).__name__ for w in warnings] == ["SinalImpossivelNoAtivo"]
    assert "magnitude não apurada" in warnings[0].format()


def test_positivo_em_ativo_segue_silencioso():
    """Não-inércia pelo outro lado: o warning discrimina o sinal, não a `secao`."""
    assert _classify(12345).warnings == ()


def test_passivo_com_valor_negativo_nao_dispara_o_warning_novo():
    """Negativo em dívida não é impossível — o warning é escopado a ativo."""
    warnings = _classify(-12345, secao="dividas_onus").warnings

    assert not any(isinstance(w, SinalImpossivelNoAtivo) for w in warnings)


@pytest.mark.parametrize("secao", ["bens_direitos", None])
def test_o_warning_carrega_o_valor_ofensor(secao):
    """[[ADR-097]] D1: warning é dataclass tipada com o valor ofensor, não string."""
    warnings = [
        w for w in _classify(-999, secao=secao).warnings if isinstance(w, SinalImpossivelNoAtivo)
    ]

    if secao is None:  # sem `secao`, o sinal decide o eixo e o caso não é este
        assert warnings == []
        return
    assert warnings[0].valor_cents == -999
