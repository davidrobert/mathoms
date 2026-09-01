"""Regressão da [[A40.l114]] — ano-base que afirma um 31/12 ainda não ocorrido.

Medido no run ``40d1af2a`` (2026-09-01): uma tela de posição do Itaú capturada em
**29/03/2026** entrou como ``valores_31_12["2026"]``. O ``max(years)`` levou o eixo
do domicílio inteiro para 2026, e aí ``_resolve_item_valor`` não achou a chave em
nenhum item de 2025 — 7 imóveis, 7 veículos e as 4 dívidas do titular foram
publicados como **zero**, com o total de dívida ``0,00`` ao lado de uma lista que
somava ``R$ 230.459,13`` na mesma página.

A fixture precisa das **duas** condições juntas — item em ano não fechado *e*
dívidas chaveadas só em anos anteriores. Faltando uma, o teste passa com o defeito
vivo, porque o eixo não chega a divergir das chaves da dívida.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipeline.domain.review_reason import BLOCKING_CODES, ReviewReasonCode
from pipeline.domain.services import patrimonio_resolvers as pr
from pipeline.domain.services.endividamento_analyzer import (
    EndividamentoAnalyzer,
    TotalDividasContraditorioError,
)
from pipeline.domain.services.financial_score_calculator import (
    FinancialScoreCalculator,
    FinancialScoreConfig,
)
from pipeline.domain.services.patrimonio_types import (
    MemberIdentity,
    resolve_value_year,
    safe_float,
    ultimo_ano_31_12_fechado,
)
from pipeline.domain.services.pontos_fortes_analyzer import (
    PontosFortesAnalyzer,
    PontosFortesConfig,
)
from pipeline.domain.services.saldo_divida_resolver import resolver_saldo
from pipeline.stages.extract_baseline import _ano_nao_fechado_reason

TITULAR = "fulano_de_tal"
CONJUGE = "beltrana_de_tal"
SALDO_TOTAL = 230459.13


@pytest.fixture
def identity() -> MemberIdentity:
    return MemberIdentity(
        titular_key=TITULAR, conjuge_key=CONJUGE, titular_nome="", conjuge_nome=""
    )


def _dividas_do_titular() -> list[dict]:
    """Chaveadas só em anos JÁ fechados — metade da condição do defeito."""
    return [
        {
            "proprietario": TITULAR,
            "tipo": "financiamento_imobiliario",
            "ano_referencia": 2025,
            "saldo_31_12": {"2025": 205381.88, "2024": 234642.79},
        },
        {
            "proprietario": TITULAR,
            "tipo": "financiamento_imobiliario",
            "ano_referencia": 2025,
            "saldo_31_12": {"2025": 25077.25},
        },
    ]


@pytest.fixture
def baseline() -> dict:
    """Corpus mínimo com a forma do defeito: um item em ano NÃO fechado."""
    aberto = str(ultimo_ano_31_12_fechado() + 1)
    investimento = {"descricao": "CDB-DI", "valores_31_12": {aberto: 116374.26}}
    imovel = {"descricao": "Casa", "valores_31_12": {"2025": 1639527.70}}
    return {
        # A tela de meio de ano: único item do corpus no ano ainda em curso.
        "investimentos_consolidados": [{**investimento, "proprietario": TITULAR}],
        "imoveis_consolidados": [{**imovel, "proprietario": TITULAR}],
        "dividas": _dividas_do_titular(),
        "patrimonio_por_ano": {aberto: {"total_bens": 1755901.96, "total_dividas": SALDO_TOTAL}},
    }


def test_ultimo_31_12_fechado_so_alcanca_o_ano_corrente_no_proprio_31_12():
    assert ultimo_ano_31_12_fechado(date(2026, 9, 1)) == 2025
    assert ultimo_ano_31_12_fechado(date(2026, 12, 30)) == 2025
    assert ultimo_ano_31_12_fechado(date(2026, 12, 31)) == 2026
    assert ultimo_ano_31_12_fechado(date(2027, 1, 1)) == 2026


def test_eixo_recusa_o_ano_que_nao_fechou(baseline):
    """O item de meio de ano não pode arrastar o eixo do domicílio."""
    ano_aberto = str(ultimo_ano_31_12_fechado() + 1)
    summary_year, _, _ = pr._resolve_summary_year(baseline)
    assert summary_year == ano_aberto, "a fixture perdeu a condição que ela existe para criar"
    assert resolve_value_year(baseline, summary_year) == "2025"


def test_eixo_por_membro_tambem_recusa(baseline, identity):
    """`anos_base_por_membro` recomputa do zero — filtrar só no domicílio não o alcança."""
    ano_titular, _ = pr.anos_base_por_membro(baseline, identity, "2025")
    assert ano_titular == "2025"


def test_total_de_divida_nao_sai_zero(baseline, identity):
    titular_div, conjuge_div = pr._split_dividas(baseline, identity, "2025")
    assert titular_div == pytest.approx(SALDO_TOTAL)
    assert conjuge_div == 0.0


def test_os_tres_produtores_do_total_concordam(baseline, identity):
    """O agregado, a lista de itens e o resolvedor leem o mesmo campo."""
    titular_div, conjuge_div = pr._split_dividas(baseline, identity, "2025")
    soma_resolver = sum(float(resolver_saldo(dv, "2025").valor) for dv in baseline["dividas"])
    analise = EndividamentoAnalyzer().analyze(
        {"bruto": 1755901.96, "dividas": titular_div + conjuge_div},
        [],
        dividas_baseline=baseline["dividas"],
        ano_ref="2025",
        identity=identity,
    )
    soma_itens = sum(d.saldo_devedor for d in analise.dividas)
    assert titular_div + conjuge_div == pytest.approx(soma_resolver)
    assert soma_itens == pytest.approx(soma_resolver)
    assert analise.total_dividas == pytest.approx(SALDO_TOTAL)


# Os dois consertos desta lane são INDEPENDENTEMENTE suficientes para o total de
# dívida — descoberto ao escrever este contrafactual, que reprovou por medir o
# alvo errado. Um gate único sobre a dívida passaria com QUALQUER um dos dois
# revertido, então cada um precisa do seu próprio alvo.
def test_o_filtro_de_ano_e_load_bearing(baseline, identity):
    """Contrafactual do eixo: imóvel não tem carry-forward, então ele isola o filtro."""
    ano_aberto = str(ultimo_ano_31_12_fechado() + 1)
    com_eixo_certo, _ = pr._split_imoveis(baseline, identity, "2025")
    com_eixo_aberto, _ = pr._split_imoveis(baseline, identity, ano_aberto)
    assert sum(i["valor_31_12_ano_base"] for i in com_eixo_certo) == pytest.approx(1639527.70)
    assert (
        sum(i["valor_31_12_ano_base"] for i in com_eixo_aberto) == 0.0
    ), "sem o filtro de ano o imóvel não zera — fixture inerte"


def test_o_produtor_unico_de_saldo_e_load_bearing(baseline):
    """Contrafactual do resolvedor: a expressão antiga zera onde a nova resolve."""
    ano_aberto = str(ultimo_ano_31_12_fechado() + 1)
    for dv in baseline["dividas"]:
        antiga = safe_float(dv["saldo_31_12"].get(ano_aberto, 0))
        assert antiga == 0.0, "a expressão antiga não zera — fixture inerte"
        assert float(resolver_saldo(dv, ano_aberto).valor) > 0


def test_ano_ausente_nao_publica_zero_silencioso():
    """Ano-base legítimo fora das chaves: carry-forward declarado, nunca zero mudo."""
    dv = {"saldo_31_12": {"2024": 100.0}, "tipo": "financiamento_imobiliario"}
    resolvido = resolver_saldo(dv, "2025")
    assert resolvido.valor == 100
    assert resolvido.carry_forward is True
    assert resolvido.ano == "2024"
    assert resolvido.defasagem == 1


def test_ausencia_na_declaracao_que_cobre_o_ano_e_quitacao():
    """C3 — zero DECLARADO, distinto do zero mudo que a lane pegou."""
    dv = {"saldo_31_12": {"2024": 100.0}}
    resolvido = resolver_saldo(dv, "2025", anos_declarados=frozenset({"2025"}))
    assert resolvido.valor == 0
    assert resolvido.quitada is True


def test_saldo_ilegivel_nao_conta_como_apurado():
    assert resolver_saldo({"saldo_31_12": {"sem-ano": 5}}, "2025").apurado is False
    assert resolver_saldo({"saldo_31_12": {"2025": 5}}, "2025").apurado is True


def test_tripwire_reprova_total_zero_com_itens(identity):
    """Critério 4 — contradição interna não chega a publicar."""
    dividas = [{"proprietario": TITULAR, "saldo_31_12": {"2025": 205381.88}}]
    with pytest.raises(TotalDividasContraditorioError):
        EndividamentoAnalyzer().analyze(
            {"bruto": 1000000.0, "dividas": 0.0},
            [],
            dividas_baseline=dividas,
            ano_ref="2025",
            identity=identity,
        )


def test_tripwire_nao_dispara_sem_divida(identity):
    analise = EndividamentoAnalyzer().analyze(
        {"bruto": 1000000.0, "dividas": 0.0},
        [],
        dividas_baseline=[],
        ano_ref="2025",
        identity=identity,
    )
    assert analise.total_dividas == 0.0


# ---------------------------------------------------------------------------
# Critério 3 — o score não emite nota sobre total suprimido
# ---------------------------------------------------------------------------


def _calculadora() -> FinancialScoreCalculator:
    scoring = json.loads(Path("config/scoring.json").read_text())
    return FinancialScoreCalculator(FinancialScoreConfig.from_scoring_json(scoring))


def _score(
    taxa: float | None,
    *,
    taxa_poupanca: float = 25,
    cobertura: float = 8,
    if_pct: float = 40,
    concentracao: float = 40,
) -> dict:
    ratios = {
        "taxa_poupanca_recorrente_pct": taxa_poupanca,
        "autonomia_financeira_meses": cobertura,
        "concentracao_imobiliaria": concentracao,
        "taxa_endividamento_pct": taxa,
    }
    return _calculadora().calculate(
        ratios=ratios, patrimonio={}, goals={"if_pct": if_pct}, reserva=None
    )


def _componente(score: dict) -> dict:
    return next(c for c in score["componentes"] if c["code"] == "taxa_endividamento")


def test_endividamento_suprimido_nao_recebe_nota():
    comp = _componente(_score(None))
    assert comp["nota"] is None
    assert comp["valor"] is None
    assert comp["status"] == "suprimido"


def test_peso_do_suprimido_sai_do_denominador():
    """8,0 é a soma dos pesos; sem o componente de peso 1,5 sobram 6,5."""
    assert _score(None)["formula"].endswith("/ 6.5")
    assert _score(11.45)["formula"].endswith("/ 8")


def test_supressao_nao_pode_render_classificacao_melhor_que_o_piso():
    """Sem isto, "endividamento não apurado" COMPRA uma faixa: 6,8 "Bom" sobre 5,6."""
    # Este perfil straddle a fronteira 6,0 das bandas: renormalizado sobre 6,5 dá
    # "Bom"; com o suprimido em nota 0 sobre 8,0 dá "Regular". Fixture escolhida
    # para discriminar — com valor e piso na MESMA banda o teste não mede nada.
    suprimido = _score(None, taxa_poupanca=30, cobertura=10, if_pct=50, concentracao=10)
    calc = _calculadora()
    assert suprimido["piso"] < suprimido["valor"]
    assert calc._classify(suprimido["valor"]) == "Bom"
    assert calc._classify(suprimido["piso"]) == "Regular"
    assert suprimido["classificacao"] == "Regular"


def test_zero_real_continua_valendo_nota_maxima():
    """Família sem dívida NÃO é punida — a supressão é que deixa de ser premiada."""
    comp = _componente(_score(0.0))
    assert comp["nota"] == 10.0
    assert comp["status"] == "emitted"


def test_o_publicado_no_run_reproduz_com_o_defeito_e_some_com_o_conserto():
    """Contrafactual da superfície: 0,0 dava nota 10,0; o valor real dá 8,6."""
    assert _componente(_score(0.0))["nota"] == 10.0
    assert _componente(_score(11.45))["nota"] == 8.6


def _titulos_de_pontos_fortes(taxa: float | None) -> list[str]:
    itens = PontosFortesAnalyzer(PontosFortesConfig()).analyze(
        score={},
        ratios={"taxa_endividamento_pct": taxa},
        patrimonio={},
        fluxo={},
        reserva={},
        goals={},
    )
    return [i.titulo for i in itens]


# O zero voltava pela porta dos fundos: com o score já consertado, este analyzer
# ainda coagia `None` para 0 e imprimia "Endividamento Mínimo" como Ponto Forte.
def test_ponto_forte_de_endividamento_cala_sob_supressao():
    assert any("Endividamento" in t for t in _titulos_de_pontos_fortes(0.0))
    assert not any("Endividamento" in t for t in _titulos_de_pontos_fortes(None))


# ---------------------------------------------------------------------------
# Critério 1 (parte declarativa) — a recusa do ano chega a quem revisa
# ---------------------------------------------------------------------------


def _reason(ano: int) -> dict | None:
    return _ano_nao_fechado_reason(
        Path("informe_previdencia_202603.pdf"),
        SimpleNamespace(reference_year=ano),
        artifact_key="informe_previdencia_202603",
    )


def test_ano_fechado_nao_gera_razao():
    assert _reason(ultimo_ano_31_12_fechado()) is None


def test_ano_nao_fechado_declara_o_ofensor_e_o_esperado():
    teto = ultimo_ano_31_12_fechado()
    r = _reason(teto + 1)
    assert r["code"] == ReviewReasonCode.domain_ano_referencia_nao_fechado.value
    assert r["offending_value"] == f"ano_referencia={teto + 1}"
    assert r["expected"] == f"ano_referencia <= {teto}"


def test_o_code_existe_no_contrato_que_o_valida():
    """Code que o schema rejeita reprovaria em `strict` — emissor e contrato juntos."""
    schema = json.loads(Path("config/schemas/review_reason.schema.json").read_text())
    assert (
        ReviewReasonCode.domain_ano_referencia_nao_fechado.value
        in schema["properties"]["code"]["enum"]
    )


def test_a_razao_e_warn_first_e_nao_pausa_o_run():
    """O documento é dado real — só não é foto de 31/12 ([[ADR-357]])."""
    assert ReviewReasonCode.domain_ano_referencia_nao_fechado not in BLOCKING_CODES
