"""FP-5B: o card cambial declara de que componentes é feito e o que não apurou.

Medido no r7 (ws-1b9f2cf5, run 33514dc4): `detalhes` = 4 entradas, TODAS
`tipo=="caixa"`; o braço de carteira contribuiu ZERO. Não porque a carteira
seja zero — o bucket `Internacional` vale 2,84% da carteira financeira na
tabela de classes — mas porque os dois leem UNIVERSOS DIFERENTES:
`investimentos.fonte == "irpf_bens"` alimenta a tabela, enquanto
`compute_exposicao_cambial` lê `investimentos_atuais["dados"]` (posições
atuais do E4), vazio nesse workspace. Zero silencioso sob semântica de
cobertura total.

O gate mede o MECANISMO: componente não apurado ⇒ `tier == "indeterminado"`,
e caixa × carteira são disjuntos POR CONSTRUÇÃO (somar o bucket ao caixa sem
de-dup inflaria o KPI e viraria dano de sinal — "você já está protegido" para
quem não está). Ver ADR-403.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.exposicao_cambial_analyzer import (
    DEFINICAO_VERSAO_CORRENTE,
    THRESHOLD_AMARELO_PCT,
    THRESHOLD_VERDE_PCT,
    Cobertura,
    compute_exposicao_cambial,
)


def _caixa(moeda: str, brl: Decimal | int, conta: str = "conta-sintetica") -> dict:
    """Boundary: `caixa_detalhes` é dict do payload E5 (ADR-090 — Decimal no call-site)."""
    return {"conta": conta, "moeda": moeda, "valor_brl": brl, "saldo_original": brl}


def _pos(descricao: str, brl: Decimal | int, instituicao: str = "") -> dict:
    return {"descricao": descricao, "valor_atual": brl, "instituicao": instituicao}


def _compute(caixa=None, posicoes=None, denom: Decimal | int = 1000):
    return compute_exposicao_cambial(
        caixa_detalhes=caixa or [],
        investimentos_atuais={"dados": posicoes} if posicoes is not None else None,
        investivel_financeiro=denom,
    )


# =============================================================================
# Composição declarada
# =============================================================================


def test_publica_os_dois_componentes_nomeados():
    d = _compute(caixa=[_caixa("USD", Decimal("100"))]).to_dict()

    assert set(d["componentes"]) == {"caixa_fx", "carteira_lastro_estrangeiro"}
    assert d["componentes"]["caixa_fx"]["cobertura"] == Cobertura.apurado.value
    assert d["definicao_versao"] == DEFINICAO_VERSAO_CORRENTE


def test_total_soma_apenas_componentes_apurados():
    """v1: a carteira é observacional — publicada com cobertura, fora do total."""
    d = _compute(
        caixa=[_caixa("USD", Decimal("100"))], posicoes=[_pos("ETF global", Decimal("900"))]
    ).to_dict()

    assert d["componentes"]["carteira_lastro_estrangeiro"]["valor_brl"] == 900.0
    assert d["componentes"]["carteira_lastro_estrangeiro"]["cobertura"] != Cobertura.apurado.value
    assert d["total_brl"] == 100.0


# =============================================================================
# Invariante de cobertura — o coração do achado
# =============================================================================


@pytest.mark.parametrize("pct_alvo", [50.0, 7.0, 1.0])
def test_componente_nao_apurado_suprime_o_veredito(pct_alvo):
    """`∃ cobertura ≠ apurado ⇒ tier == indeterminado`, em qualquer banda."""
    d = _compute(caixa=[_caixa("USD", Decimal(str(pct_alvo)))], denom=100).to_dict()

    assert d["pct_investivel_financeiro"] == pytest.approx(pct_alvo)
    assert d["tier"] == "indeterminado"


def test_sem_posicoes_tambem_e_indeterminado_nao_verde():
    """Universo vazio é ausência de medida, não ausência de exposição."""
    assert _compute(caixa=[_caixa("USD", Decimal("50"))], denom=100).to_dict()["tier"] != "verde"


# =============================================================================
# De-dup: caixa e carteira são disjuntos POR CONSTRUÇÃO
# =============================================================================


def test_conta_em_moeda_estrangeira_nao_entra_na_carteira():
    """A mesma conta em ME não pode contar como caixa E como ativo internacional."""
    conta_me = {
        "descricao": "Conta em moeda estrangeira",
        "valor_atual": Decimal("500"),
        "moeda": "USD",
    }
    d = _compute(caixa=[_caixa("USD", Decimal("500"))], posicoes=[conta_me]).to_dict()

    assert d["componentes"]["carteira_lastro_estrangeiro"]["valor_brl"] == 0.0
    assert d["total_brl"] == 500.0


# A [[ADR-400]] (DE-1) decidiu que custódia estrangeira É resposta legítima para a
# pergunta de LASTRO CAMBIAL — ela só não é resposta para a pergunta de CLASSE, e
# por isso saiu do `asset_classifier` e virou `_CUSTODIA_ESTRANGEIRA` aqui. Este
# teste fixa esse contrato e, junto com o de baixo, prova que o de-dup continua
# valendo mesmo com a custódia como gatilho independente.
def test_custodia_estrangeira_sozinha_conta_como_carteira():
    """ADR-400: custódia responde lastro cambial, não classe do ativo."""
    brl_na_wise = {
        "descricao": "CDB pós-fixado",
        "valor_atual": Decimal("700"),
        "instituicao": "Wise",
    }
    d = _compute(posicoes=[brl_na_wise]).to_dict()

    assert d["componentes"]["carteira_lastro_estrangeiro"]["valor_brl"] == 700.0


# O gatilho de custódia da [[ADR-400]] tornou o de-dup MAIS necessário, não menos:
# uma conta em ME num custodiante estrangeiro casa `_is_caixa_me` E
# `_tem_custodia_estrangeira`. Sem a guarda, ela entraria nos dois componentes.
def test_conta_em_me_em_custodiante_estrangeiro_nao_dobra():
    conta_me_na_wise = {
        "descricao": "Saldo em conta",
        "valor_atual": Decimal("500"),
        "moeda": "USD",
        "instituicao": "Wise",
    }
    d = _compute(caixa=[_caixa("USD", Decimal("500"))], posicoes=[conta_me_na_wise]).to_dict()

    assert d["componentes"]["carteira_lastro_estrangeiro"]["valor_brl"] == 0.0
    assert d["total_brl"] == 500.0


# =============================================================================
# Referência da banda — piso de proteção, não alvo de alocação
# =============================================================================


def test_banda_declara_contra_o_que_mede():
    d = _compute(caixa=[_caixa("USD", Decimal("100"))]).to_dict()
    ref = d["referencia_banda"]

    assert ref["tipo"] == "piso_protecao"
    assert ref["verde_min_pct"] == THRESHOLD_VERDE_PCT
    assert ref["amarelo_min_pct"] == THRESHOLD_AMARELO_PCT


# Este card é diagnóstico de ESTOQUE e não prescreve aporte em classe. Se
# alguém recalibrar o piso para a faixa de alocação, os dois objetos voltam a
# colidir — era a contradição "card diz verde, comparativo manda comprar".
def test_banda_nao_e_o_alvo_de_alocacao_da_adr_224():
    """A faixa 20–30% USD (ADR-224 §6) é ALVO DE ALOCAÇÃO, dono `acoes_int`."""
    ref = _compute(caixa=[_caixa("USD", Decimal("100"))]).to_dict()["referencia_banda"]

    assert ref["dono_prescricao_alocacao"] == "acoes_int"
    assert ref["verde_min_pct"] < 20.0


# =============================================================================
# CV18 — conservação e cobertura no run inteiro (não só no analyzer)
# =============================================================================


def _cv18(bloco: dict):
    from scripts.validate_cross import _cv18_exposicao_cambial_cobertura

    return _cv18_exposicao_cambial_cobertura({"exposicao_cambial": bloco})


def test_cv18_aceita_o_payload_que_o_analyzer_produz():
    """Alimentado pelo PRODUTOR real, não por dict à mão."""
    assert _cv18(_compute(caixa=[_caixa("USD", Decimal("100"))]).to_dict()).passed


def test_cv18_pega_veredito_forte_demais_para_a_cobertura():
    bloco = _compute(caixa=[_caixa("USD", Decimal("50"))], denom=100).to_dict()
    bloco["tier"] = "verde"  # componente indeterminado + veredito afirmativo

    r = _cv18(bloco)
    assert not r.passed
    assert r.severity == "error"


def test_cv18_pega_soma_que_nao_fecha():
    bloco = _compute(caixa=[_caixa("USD", Decimal("100"))]).to_dict()
    bloco["total_brl"] = 999.0

    assert not _cv18(bloco).passed


def _e5(bloco: dict, internacional: Decimal | int | None = None) -> dict:
    e5: dict = {"exposicao_cambial": bloco}
    if internacional is not None:
        e5["investimentos"] = {
            "tabela_classes": [
                {"categoria": "Renda Fixa", "valor": Decimal("1")},
                {"categoria": "Internacional", "valor": internacional},
            ]
        }
    return e5


def _cv18_e5(e5: dict):
    from scripts.validate_cross import _cv18_exposicao_cambial_cobertura

    return _cv18_exposicao_cambial_cobertura(e5)


# O componente e o bucket medem o MESMO conceito por duas rotas
# (`investimentos_atuais["dados"]` × `irpf_bens`). É o predicado que impede um
# v2 futuro de flipar a cobertura sem antes reconciliar os universos.
def test_cv18_exige_reconciliacao_quando_a_carteira_se_declara_apurada():
    """Divergir do bucket `Internacional` é erro de conservação, não tolerância."""
    bloco = _compute(
        caixa=[_caixa("USD", Decimal("100"))], posicoes=[_pos("ETF global", Decimal("900"))]
    ).to_dict()
    bloco["componentes"]["carteira_lastro_estrangeiro"]["cobertura"] = "apurado"
    bloco["total_brl"] = 1000.0
    # Cobertura completa ⇒ o veredito destrava (PV10-01). Sem isto a fixture testaria
    # a discordância tier×cobertura, não a reconciliação que o nome do teste promete.
    bloco["tier"] = "verde"

    assert _cv18_e5(_e5(bloco, Decimal("900"))).passed
    assert not _cv18_e5(_e5(bloco, Decimal("42"))).passed


def test_cv18_nao_exige_reconciliacao_com_carteira_nao_apurada():
    """v1 declara a carteira indeterminada — cobrar igualdade ali seria falso-fail."""
    bloco = _compute(
        caixa=[_caixa("USD", Decimal("100"))], posicoes=[_pos("ETF global", Decimal("900"))]
    ).to_dict()

    assert _cv18_e5(_e5(bloco, Decimal("42"))).passed


# =============================================================================
# PV10-01 — o termo de cobertura discrimina, e o produtor v1 não o exercita
# =============================================================================


# Era o lado que o `or` absorvia. Um v2 que reconcilia os universos e esquece de
# destravar `_tier` para de publicar banda em silêncio — e o check dizia verde.
def test_cv18_pega_veredito_fraco_demais_para_a_cobertura():
    """Cobertura completa com a faixa suprimida: o artefato contradiz a si mesmo."""
    bloco = _compute(caixa=[_caixa("USD", Decimal("100"))]).to_dict()
    bloco["componentes"]["carteira_lastro_estrangeiro"]["cobertura"] = "apurado"

    assert bloco["tier"] == "indeterminado"
    assert not _cv18(bloco).passed


# Trava o falso-positivo simétrico: exigir cobertura completa aqui reprovaria 100%
# dos runs de produção, que é exatamente o que `_componentes` declara não medir.
def test_cv18_aceita_cobertura_incompleta_com_veredito_suprimido():
    """O estado SANCIONADO da v1 (ADR-403): não apurou, não afirma faixa — e passa."""
    bloco = _compute(caixa=[_caixa("USD", Decimal("100"))]).to_dict()

    assert bloco["componentes"]["carteira_lastro_estrangeiro"]["cobertura"] != "apurado"
    assert bloco["tier"] == "indeterminado"
    assert _cv18(bloco).passed


# O que a rodada U2 (§r10 PV10-01) não mediu: os contraexemplos de CV18 são todos
# dicts editados à mão. Varrendo os INPUTS do produtor, ele emite UM único par
# (cobertura, tier) — `carteira` é fixada `indeterminado` em `_componentes` desde
# #1568 — logo CV18 publica `passed: true` em todo run e não poderia fazer diferente.
# Este teste é o tripwire: quando a v2 destravar a carteira, ele reprova e obriga
# quem fizer isso a reler CV18 em vez de herdar um check que nunca disparou.
def test_produtor_v1_emite_uma_unica_forma_de_cobertura():
    formas = set()
    for caixa in ([], [_caixa("USD", Decimal("100"))], [_caixa("EUR", Decimal("9999"))]):
        for posicoes in (None, [], [_pos("ETF global", Decimal("900"))]):
            for denom in (0, 100, 1_000_000):
                d = _compute(caixa=caixa, posicoes=posicoes, denom=denom).to_dict()
                cobs = tuple(sorted((k, c["cobertura"]) for k, c in d["componentes"].items()))
                formas.add((cobs, d["tier"]))
                assert _cv18(d).passed, "produtor v1 não deveria conseguir reprovar CV18"

    assert formas == {
        (
            (
                ("caixa_fx", "apurado"),
                ("carteira_lastro_estrangeiro", "indeterminado"),
            ),
            "indeterminado",
        )
    }
