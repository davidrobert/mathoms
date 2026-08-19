"""PD-5 (r7) — percentual em PROSA do E5 sai em pt-BR, com vírgula.

O achado: `pontos_fortes[].descricao` publicava "57.3%" (en-US) e o renderer
mostra a string crua — prosa não passa pelos formatadores do frontend, que
acertam nos campos numéricos estruturados. A responsabilidade é do **produtor**:
`replace(".", ",")` espalhado pelos consumidores multiplica o mesmo bug por
superfície.

O gate mede a **string publicada** pelo produtor real, não a intenção do
call-site: qualquer novo `f"{x:.1f}%"` em prosa destes produtores reprova, mesmo
que o autor tenha escrito "formato pt-BR" no comentário.
"""

from __future__ import annotations

import re

import pytest

from pipeline.domain.services.narrativas.tributario_narrator import _fmt_fator_r
from pipeline.domain.services.pontos_fortes_analyzer import (
    PontosFortesAnalyzer,
    PontosFortesConfig,
)

# Decimal en-US colado a dígito. `\d\.\d` casa "57.3"; não casa "R$ 1.234"
# (separador de milhar tem 3 dígitos e é validado por gate próprio em
# `format_helpers._monetary_format_errors`).
DECIMAL_EN_US = re.compile(r"\d\.\d")


def _prosa_pontos_fortes(taxa_poupanca_pct: float, endividamento_pct: float) -> list[str]:
    """Descrições publicadas pelo produtor real, com valores fracionários."""
    analyzer = PontosFortesAnalyzer(PontosFortesConfig())
    itens = analyzer.analyze(
        score={},
        ratios={
            "taxa_poupanca_recorrente_pct": taxa_poupanca_pct,
            "taxa_endividamento_pct": endividamento_pct,
        },
        patrimonio={},
        fluxo={},
        reserva={},
        goals={},
    )
    return [item.descricao for item in itens]


@pytest.mark.parametrize(
    ("taxa", "endiv"),
    [(57.3, 4.2), (22.7, 12.9), (31.5, 19.4)],
)
def test_pontos_fortes_nao_publica_decimal_en_us(taxa: float, endiv: float) -> None:
    for descricao in _prosa_pontos_fortes(taxa, endiv):
        assert not DECIMAL_EN_US.search(descricao), f"decimal en-US em prosa: {descricao!r}"


def test_pontos_fortes_publica_virgula_no_valor_fracionario() -> None:
    """Controle positivo: o número CHEGA à prosa — o gate acima não passa por omissão."""
    prosa = " ".join(_prosa_pontos_fortes(57.3, 4.2))
    assert "57,3%" in prosa
    assert "4,2%" in prosa


def test_pontos_fortes_valor_inteiro_nao_ganha_casa_decimal() -> None:
    """`fmt_percent` colapsa 30.0 → "30%". Sem isto, "30,0%" viraria ruído novo."""
    prosa = " ".join(_prosa_pontos_fortes(40.0, 3.0))
    assert "40%" in prosa
    assert "40,0%" not in prosa


@pytest.mark.parametrize("fator", [0.285, 0.317, 0.28])
def test_fator_r_nao_publica_decimal_en_us(fator: float) -> None:
    publicado = _fmt_fator_r(fator)
    assert not DECIMAL_EN_US.search(publicado), f"decimal en-US: {publicado!r}"


def test_fator_r_ausente_continua_vazio() -> None:
    """O call-site gateia em string vazia; formatar `None` como "0%" criaria fato."""
    assert _fmt_fator_r(None) == ""
