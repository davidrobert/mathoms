"""Semântica dos percentis do cone IF (ADR-361) — população, censura, coerência.
Os percentis saíam de ``primeiro_true[alguma_vez]`` (só quem atinge a meta no
horizonte) enquanto a probabilidade usava ``n`` cheio: o "P50" publicado era a
mediana dos bem-sucedidos, mais otimista quanto pior o plano.
"""

from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from pipeline.domain.services.if_monte_carlo import (
    _MC_SEED,
    IFMonteCarloConfig,
    MonteCarloIFResult,
    _lognormal_params,
    _simular_caminhos,
    run_monte_carlo_if,
)

_META = 10_000_000.0
_ANO_BASE = 2026
_IDADE_ATUAL = 40

# Grade do pior plano ao melhor. A taxa de sucesso é o eixo que governa o viés:
# com sucesso alto a censura não morde; com sucesso baixo ela é tudo.
_GRADE = [
    pytest.param(0.15, 0.0, id="sucesso~44pct"),
    pytest.param(0.20, 0.0, id="sucesso~62pct"),
    pytest.param(0.30, 0.0, id="sucesso~83pct"),
    pytest.param(0.15, 5_000.0, id="sucesso~81pct"),
    pytest.param(0.20, 5_000.0, id="sucesso~88pct"),
    pytest.param(0.30, 5_000.0, id="sucesso~95pct"),
    pytest.param(0.50, 5_000.0, id="sucesso~99pct"),
    pytest.param(0.70, 0.0, id="sucesso~99pct-sem-aporte"),
]

# Anos são inteiros, então a CDF é escada e o quantil discreto cai onde ela salta.
# 10 pp cobre a discretização com folga; o cálculo condicional errava 26 pp no
# P50 e 49 pp no P90.
_TOLERANCIA_PP = 0.10


def _config(pv_ratio: float, pmt: float, sigma: float = 0.11) -> IFMonteCarloConfig:
    return IFMonteCarloConfig(
        patrimonio_investivel=Decimal(str(_META * pv_ratio)),
        meta_if=Decimal(str(_META)),
        sigma_anual=sigma,
        retorno_real_esperado=0.05,
        horizonte_anos=40,
        ano_base=_ANO_BASE,
        aporte_mensal=Decimal(str(pmt)),
    )


def _cone(cfg: IFMonteCarloConfig, idade_meta: int = 65) -> MonteCarloIFResult:
    return run_monte_carlo_if(
        cfg, ano_base=_ANO_BASE, idade_titular_atual=_IDADE_ATUAL, idade_meta_if=idade_meta
    )


def _cdf_base_cheia(cfg: IFMonteCarloConfig):
    """(taxa de sucesso, P(atingir até o ano t)) medidos sobre ``n`` cheio."""
    mu, sigma_log = _lognormal_params(cfg.retorno_real_esperado, cfg.sigma_anual)
    pv = float(cfg.patrimonio_investivel)
    _, _, primeiro, alguma_vez, _ = _simular_caminhos(pv, float(cfg.meta_if), cfg, mu, sigma_log)

    def prob_ate(ano_relativo: int) -> float:
        return float(np.mean(alguma_vez & (primeiro + 1 <= ano_relativo)))

    return float(alguma_vez.mean()), prob_ate


def _pares_publicados(r: MonteCarloIFResult) -> list[tuple[float, int]]:
    """(piso, ano) dos percentis que saíram como ano — censurado fica de fora."""
    return [
        (k, ano)
        for k, ano in ((0.10, r.p10_ano_if), (0.50, r.p50_ano_if), (0.90, r.p90_ano_if))
        if ano is not None
    ]


@pytest.mark.parametrize("pv_ratio,pmt", _GRADE)
def test_ano_publicado_entrega_a_probabilidade_que_o_rotulo_promete(pv_ratio: float, pmt: float):
    """Invariante que define um percentil de tempo-até-o-evento: Pk ⇒ k%."""
    # O cálculo condicional publicava o ano dos sobreviventes sob um rótulo que
    # promete uma fração da população inteira.
    cfg = _config(pv_ratio, pmt)
    _, prob_ate = _cdf_base_cheia(cfg)
    for k, ano in _pares_publicados(_cone(cfg)):
        entregue = prob_ate(ano - _ANO_BASE)
        assert abs(entregue - k) <= _TOLERANCIA_PP, (
            f"P{int(k * 100)} publicado como {ano}, mas a chance de atingir a meta "
            f"até lá é {entregue:.1%}, não {k:.0%} (erro {abs(entregue - k) * 100:.0f} pp)"
        )


@pytest.mark.parametrize("pv_ratio,pmt", _GRADE)
def test_percentil_publicado_exige_taxa_de_sucesso_que_o_sustente(pv_ratio: float, pmt: float):
    """``Pk`` só é ano se a taxa de sucesso o define, com folga de 5 pp."""
    # Sem a folga, P50 com sucesso 50,2% é o ano dos últimos caminhos a cruzar:
    # instável ao horizonte e ao seed, e o relatório reemitido pula anos.
    cfg = _config(pv_ratio, pmt)
    sucesso, _ = _cdf_base_cheia(cfg)
    for k, ano in _pares_publicados(_cone(cfg)):
        assert sucesso >= k + 0.05, (
            f"P{int(k * 100)} publicado como {ano} com taxa de sucesso "
            f"{sucesso:.1%} — abaixo do piso de {k + 0.05:.0%}"
        )


def test_p90_alem_do_horizonte_nao_vira_ano():
    """Sucesso ~88% → o cenário adverso não cabe em 40 anos."""
    # A perna que existe para mostrar risco era a mais corrompida: publicava
    # "P90 = 36 anos" quando o P90 verdadeiro está fora do horizonte.
    resultado = _cone(_config(0.20, 5_000.0))
    assert resultado.p50_ano_if is not None, "P50 deveria sobreviver com sucesso ~88%"
    assert resultado.p90_ano_if is None, "P90 não é definível com sucesso < 95%"
    assert resultado.p90_censurado is True
    assert resultado.horizonte_anos == 40


def test_sucesso_abaixo_de_50pct_nao_publica_ano_central():
    """A guarda pedida: na mediana a meta não é atingida no horizonte."""
    resultado = _cone(_config(0.15, 0.0))
    assert resultado.p50_ano_if is None
    assert resultado.p50_censurado is True
    assert resultado.prob_if_ate_horizonte < 0.50


def test_perna_favoravel_nunca_sai_sozinha():
    """Censura sem guarda de assimetria criaria um viés novo, otimista."""
    # Com sucesso ~44% o P10 continua definível (10% + folga). Publicar "cenário
    # favorável: 2050" sem central nem adversa é pior que o defeito original —
    # some a má notícia e sobra só a boa.
    resultado = _cone(_config(0.15, 0.0))
    assert resultado.p50_ano_if is None
    assert (
        resultado.p10_ano_if is None
    ), "perna favorável publicada sem a central — censura virou viés otimista"
    assert resultado.p10_censurado is True


def test_plano_saudavel_nao_perde_nenhum_percentil():
    """Contraprova: a censura não pode morder plano folgado."""
    r = _cone(_config(0.50, 5_000.0))
    assert (r.p10_censurado, r.p50_censurado, r.p90_censurado) == (False, False, False)
    assert r.p10_ano_if is not None and r.p50_ano_if is not None and r.p90_ano_if is not None
    assert r.p10_ano_if <= r.p50_ano_if <= r.p90_ano_if


def test_cone_suprimido_nao_e_censura_estatistica():
    """``null`` sozinho significaria duas coisas — o consumidor precisa saber qual."""
    # O parecer lê ``$.if_monte_carlo`` cru, sem o schema: sem marcador explícito
    # não há como diferenciar "não simulamos" de "simulamos e não chega".
    suprimido = _cone(_config(0.05, 0.0))  # if_pct < 15% → gate de dado
    assert suprimido.exibir_cone is False
    assert suprimido.p50_ano_if is None
    assert suprimido.p50_censurado is False


def test_censura_com_cone_exibido_e_observavel():
    """Par do teste acima: censura só existe com o cone ligado."""
    censurado = _cone(_config(0.15, 0.0))
    assert censurado.exibir_cone is True
    assert censurado.p50_ano_if is None
    assert censurado.p50_censurado is True


def test_censura_e_monotonica():
    """P50 censurado ⇒ P90 censurado; nunca o inverso."""
    for pv_ratio, pmt in ((0.15, 0.0), (0.20, 5_000.0), (0.50, 5_000.0)):
        r = _cone(_config(pv_ratio, pmt))
        if r.p50_censurado:
            assert r.p90_censurado, f"P50 censurado sem P90 em pv={pv_ratio} pmt={pmt}"


def test_taxa_de_sucesso_e_publicada_na_base_cheia():
    """``prob_if_ate_horizonte`` é o denominador que decide a censura."""
    # Sem ele no payload, o consumidor teria de inferir a censura de um ``null``.
    cfg = _config(0.20, 0.0)
    sucesso, _ = _cdf_base_cheia(cfg)
    resultado = _cone(cfg)
    assert resultado.prob_if_ate_horizonte == pytest.approx(sucesso, abs=1e-4)
    assert 0.0 <= resultado.prob_if_ate_horizonte <= 1.0


def test_familia_ja_independente_nao_le_probabilidade_zero():
    """``horizonte_meta = 0`` devolvia 0,0 — sentinela lida como medição."""
    # `prazo=0` faz `primeiro_true < 0` nunca ser verdadeiro, então quem já
    # atingiu a meta lia "0% de chance de atingir IF". A meta está atingida em
    # t=0, o que é independente da simulação — logo 1,0, e sem cone.
    cfg = IFMonteCarloConfig(
        patrimonio_investivel=Decimal("6000000"),
        meta_if=Decimal("5000000"),
        aporte_mensal=Decimal("0"),
        ano_base=_ANO_BASE,
    )
    resultado = run_monte_carlo_if(
        cfg, ano_base=_ANO_BASE, idade_titular_atual=55, idade_meta_if=55
    )
    assert resultado.prob_if_ate_idade_meta == 1.0
    assert resultado.exibir_cone is False
    assert resultado.motivo_sem_cone == "meta já atingida"


def test_censura_e_deterministica_sob_o_seed_de_modelo():
    """ADR-360 preservada: a censura não reintroduz dependência de entropia."""
    cfg = _config(0.20, 5_000.0)
    assert _cone(cfg) == _cone(cfg)
    assert _cone(cfg).seed_usado == _MC_SEED
