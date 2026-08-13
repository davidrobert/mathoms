"""σ do cone agregado pelos pesos do alvo declarado (ADR-374 · A40.l25)."""

# Cada teste aqui corresponde a uma linha do §Critério de aceite da ADR-374. Os
# valores vêm do seed vigente (`backend/app/scripts/seed_economic_assumptions.py`):
# se o seed mudar, estes testes mudam junto, e isso é SINAL, não ruído.

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.if_sigma_agregado import (
    AGREGACAO_SOMA_PONDERADA,
    BASE_ALVO_DECLARADO,
    BASE_ALVO_MAIS_IMOVEIS_OBSERVADOS,
    PROCEDENCIA_GLOBAL,
    PROCEDENCIA_WORKSPACE_OVERRIDE,
    PremissaDeClasse,
    agregar_sigma_do_alvo,
)

# σ do seed baseline 2026, em pct — o que o snapshot da ADR-219 publica.
_SIGMA_SEED_PCT = {
    "caixa": "0.500",
    "rf_pos": "1.500",
    "rf_pre": "3.500",
    "rf_inflacao": "4.000",
    "acoes_br": "22.000",
    "acoes_intl": "18.000",
    "fii": "15.000",
    "imoveis_diretos": "10.000",
}

# Alvo do fixture golden (`tests/test_e5_golden_execution.py::_GOALS_MIN`).
_ALVO_PADRAO = {
    "rf_pos_pct": 20,
    "rf_pre_pct": 10,
    "rf_ipca_pct": 10,
    "acoes_br_pct": 25,
    "acoes_int_pct": 15,
    "fiis_pct": 10,
    "caixa_pct": 10,
}
_ALVO_CONSERVADOR = {"rf_pos_pct": 60, "rf_ipca_pct": 20, "caixa_pct": 20}
_ALVO_AGRESSIVO = {"acoes_br_pct": 45, "acoes_int_pct": 25, "fiis_pct": 20, "rf_pos_pct": 10}


def _premissas(*, override: tuple[str, ...] = (), ausentes: tuple[str, ...] = ()):
    return {
        classe: PremissaDeClasse(
            sigma_anual_pct=None if classe in ausentes else Decimal(pct),
            veio_de_override=classe in override,
        )
        for classe, pct in _SIGMA_SEED_PCT.items()
    }


def _alvo(bruto: dict[str, int]) -> dict[str, Decimal]:
    return {chave: Decimal(str(valor)) for chave, valor in bruto.items()}


def _sigma(bruto: dict[str, int], **kwargs):
    return agregar_sigma_do_alvo(alvo_pct=_alvo(bruto), premissas=_premissas(), **kwargs)


# --- os três números do §Critério de aceite ---------------------------------


@pytest.mark.parametrize(
    "nome,alvo,esperado",
    [
        ("padrão", _ALVO_PADRAO, "0.1080"),
        ("conservador", _ALVO_CONSERVADOR, "0.0180"),
        ("agressivo", _ALVO_AGRESSIVO, "0.1755"),
    ],
)
def test_reproduz_os_sigmas_do_seed_vigente(nome: str, alvo: dict, esperado: str) -> None:
    # Assertado no valor NÃO-arredondado: o agressivo cai em meia exata a 1 decimal
    # (17,55) e seria frágil justamente na convenção de arredondamento que esta lane
    # gastou um PR inteiro consertando (#1360, meio-para-par vs. meio-para-cima).
    resultado = _sigma(alvo)
    assert resultado is not None, nome
    assert resultado.sigma_anual == Decimal(esperado)


def test_a_invariancia_morreu_mesma_familia_alvos_diferentes_sigmas_diferentes() -> None:
    """O teste que prova o motivo da ADR: hoje é impossível, os três davam 0,11."""
    sigmas = {
        _sigma(alvo).sigma_anual for alvo in (_ALVO_PADRAO, _ALVO_CONSERVADOR, _ALVO_AGRESSIVO)
    }
    assert len(sigmas) == 3


def test_a_faixa_declaravel_vai_de_meio_por_cento_a_vinte_e_dois() -> None:
    """Todo `_pct` aceita `maximum: 100`, então os dois extremos são declaráveis."""
    assert _sigma({"caixa_pct": 100}).sigma_anual == Decimal("0.005")
    assert _sigma({"acoes_br_pct": 100}).sigma_anual == Decimal("0.22")


# --- caixa entra na normalização (o guard contra reusar `_normalize_alvo`) ---


def test_caixa_entra_na_base_de_normalizacao() -> None:
    """Reusar `_normalize_alvo` (que exclui caixa) daria 11,94% em vez de 10,80%."""
    assert _sigma(_ALVO_PADRAO).sigma_anual == Decimal("0.1080")
    sem_caixa = {k: v for k, v in _ALVO_PADRAO.items() if k != "caixa_pct"}
    # Mesmo alvo sem a linha de caixa normaliza sobre 90 e sobe — é o número que a
    # ADR cita como consequência de reusar a normalização errada.
    assert _sigma(sem_caixa).sigma_anual > Decimal("0.119")


# --- o mapa de nomes (3 de 7 não derivam por sufixo) ------------------------


@pytest.mark.parametrize(
    "chave_do_alvo,classe_esperada",
    [("rf_ipca_pct", "rf_inflacao"), ("acoes_int_pct", "acoes_intl"), ("fiis_pct", "fii")],
)
def test_as_tres_chaves_que_nao_derivam_por_sufixo_mapeiam(
    chave_do_alvo: str, classe_esperada: str
) -> None:
    """`removesuffix('_pct')` daria `rf_ipca`/`acoes_int`/`fiis`, que não existem."""
    # Sem o mapa explícito, D4 abortaria e a feature ficaria em fallback em 100%
    # dos runs parecendo entregue.
    resultado = _sigma({chave_do_alvo: 100})
    assert resultado is not None
    assert resultado.classes_contribuintes == ((classe_esperada, Decimal(1)),)
    assert resultado.sigma_anual == Decimal(_SIGMA_SEED_PCT[classe_esperada]) / 100


# --- D3 / D4: os dois caminhos de fallback ----------------------------------


def test_sem_alvo_declarado_devolve_none() -> None:
    """D3 — sem alvo não há vetor de pesos; o caller mantém a constante."""
    assert agregar_sigma_do_alvo(alvo_pct={}, premissas=_premissas()) is None
    assert agregar_sigma_do_alvo(alvo_pct=_alvo({"rf_pos_pct": 0}), premissas=_premissas()) is None


def test_classe_com_peso_positivo_sem_premissa_aborta_a_agregacao_inteira() -> None:
    """D4 — definida se e somente se toda classe de peso positivo tem σ vigente."""
    premissas = _premissas(ausentes=("acoes_br",))
    assert agregar_sigma_do_alvo(alvo_pct=_alvo(_ALVO_PADRAO), premissas=premissas) is None


def test_classe_ausente_com_peso_ZERO_nao_aborta() -> None:
    """Peso zero não entra na soma — é aritmética, não threshold."""
    # `acoes_br` não está no alvo conservador, então a ausência dela é irrelevante.
    premissas = _premissas(ausentes=("acoes_br",))
    resultado = agregar_sigma_do_alvo(alvo_pct=_alvo(_ALVO_CONSERVADOR), premissas=premissas)
    assert resultado is not None and resultado.sigma_anual == Decimal("0.0180")


def test_aborta_pelo_caminho_de_abort_nao_pelo_resultado() -> None:
    """Exercita o RAMO de D4: a classe existe no mapa mas sem σ, com peso positivo."""
    premissas = {"caixa": PremissaDeClasse(sigma_anual_pct=None)}
    assert agregar_sigma_do_alvo(alvo_pct=_alvo({"caixa_pct": 100}), premissas=premissas) is None


# --- D9: imóvel de renda entra com peso observado ---------------------------


def test_imovel_no_pool_entra_com_peso_observado_e_a_base_diz_mista() -> None:
    """D9 — pool 60/40 com alvo conservador: 0,6·1,80 + 0,4·10,00 = 5,08%."""
    # Sem D9, D1 publicaria 1,80% contra limite real de 5,08% — cone 2,8× mais
    # ESTREITO por ausência de dado, e a falha concentra-se no ICP (aluguel +
    # carteira defensiva), não num edge case.
    resultado = _sigma(_ALVO_CONSERVADOR, peso_imoveis=Decimal("0.4"))
    assert resultado is not None
    assert resultado.sigma_anual == Decimal("0.0508")
    assert resultado.base_pesos == BASE_ALVO_MAIS_IMOVEIS_OBSERVADOS


def test_sem_imovel_a_base_de_pesos_e_o_alvo_puro() -> None:
    assert _sigma(_ALVO_CONSERVADOR).base_pesos == BASE_ALVO_DECLARADO


def test_imovel_no_pool_nunca_desce_abaixo_do_minimo_do_pool() -> None:
    """§Critério de aceite: `σ_agregado ≥ min(σ do pool)` com imóvel."""
    resultado = _sigma(_ALVO_CONSERVADOR, peso_imoveis=Decimal("0.4"))
    assert resultado.sigma_anual >= Decimal("0.005")


def test_imovel_cobrindo_o_pool_inteiro_dispensa_o_alvo() -> None:
    """`cat2_efetivo == investivel_efetivo` ⇒ só imóvel contribui."""
    resultado = agregar_sigma_do_alvo(alvo_pct={}, premissas=_premissas(), peso_imoveis=Decimal(1))
    assert resultado is not None and resultado.sigma_anual == Decimal("0.10")


# --- D6: campos de auditoria ------------------------------------------------


def test_procedencia_e_override_quando_qualquer_contribuinte_veio_de_override() -> None:
    premissas = _premissas(override=("rf_pos",))
    resultado = agregar_sigma_do_alvo(alvo_pct=_alvo(_ALVO_CONSERVADOR), premissas=premissas)
    assert resultado.procedencia == PROCEDENCIA_WORKSPACE_OVERRIDE


def test_override_em_classe_que_NAO_contribui_mantem_global() -> None:
    """Procedência descreve o número publicado, não a tabela inteira."""
    premissas = _premissas(override=("acoes_br",))  # fora do alvo conservador
    resultado = agregar_sigma_do_alvo(alvo_pct=_alvo(_ALVO_CONSERVADOR), premissas=premissas)
    assert resultado.procedencia == PROCEDENCIA_GLOBAL


def test_agregacao_e_valor_enumerado() -> None:
    """D6 — enumerado, não string livre: senão cada call-site inventa a sua."""
    assert _sigma(_ALVO_PADRAO).agregacao == AGREGACAO_SOMA_PONDERADA


def test_classes_contribuintes_declara_codigos_e_pesos_finais() -> None:
    """R2 do co-design: o consumidor do gatilho não re-deriva peso fora do domínio."""
    resultado = _sigma(_ALVO_CONSERVADOR, peso_imoveis=Decimal("0.4"))
    assert dict(resultado.classes_contribuintes) == {
        "rf_pos": Decimal("0.36"),
        "rf_inflacao": Decimal("0.12"),
        "caixa": Decimal("0.12"),
        "imoveis_diretos": Decimal("0.4"),
    }
    assert sum(p for _, p in resultado.classes_contribuintes) == Decimal(1)


def test_classe_de_peso_zero_nao_aparece_entre_as_contribuintes() -> None:
    contribuintes = dict(_sigma(_ALVO_CONSERVADOR).classes_contribuintes)
    assert "acoes_br" not in contribuintes


# --- a invariante de sanidade, no decimal que o config recebe ---------------


def test_erro_de_cem_vezes_derruba_a_invariante() -> None:
    """Prova da §Critério de aceite: o gate mede o DECIMAL, não o pct."""
    # Em pct, `1,5 ≤ 10,8 ≤ 22` passa — foi por isso que a redação anterior da ADR
    # declarava potência que a invariante não tinha. Premissa em decimal (0.015 em
    # vez de 1.5) é o erro simétrico e cai no teto duro.
    premissas = {
        classe: PremissaDeClasse(sigma_anual_pct=Decimal(pct) * 100)
        for classe, pct in _SIGMA_SEED_PCT.items()
    }
    with pytest.raises(ValueError, match="teto duro"):
        agregar_sigma_do_alvo(alvo_pct=_alvo(_ALVO_PADRAO), premissas=premissas)


def test_sigma_fica_dentro_do_envelope_das_contribuintes() -> None:
    """`min(σᵢ | wᵢ>0) ≤ σ ≤ max(σᵢ | wᵢ>0)` para todos os alvos de aceite."""
    for alvo in (_ALVO_PADRAO, _ALVO_CONSERVADOR, _ALVO_AGRESSIVO):
        resultado = _sigma(alvo)
        sigmas = [
            Decimal(_SIGMA_SEED_PCT[classe]) / 100 for classe, _ in resultado.classes_contribuintes
        ]
        assert min(sigmas) <= resultado.sigma_anual <= max(sigmas)
