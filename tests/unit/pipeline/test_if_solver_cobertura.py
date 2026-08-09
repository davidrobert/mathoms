"""ADR-373 — o que o solver de prazo IF projeta, e o que retém por escolha.

`_solve_prazo` só resolvia o ramo `r > 0 and aporte > 0`; todo o resto virava
ausência. Dois casos calculáveis caíam junto com o genuinamente inatingível.
A A40.l26 separou os três: um passa a projetar (retorno real zero é premissa
declarável), um continua retido **por metodologia** (aporte não declarado não é
capacidade), e um continua ausente porque não converge mesmo.
"""

from __future__ import annotations

from datetime import date

import pytest

from pipeline.domain.services.if_projector import (
    MOTIVO_APORTE_NAO_DECLARADO,
    MOTIVO_SEM_TRAJETORIA,
    IFProjector,
    IFProjectorConfig,
    default_if_absent,
    motivo_prazo_indefinido,
    solve_prazo_anos,
)

_REF = date(2026, 4, 19)
_DOB = date(1985, 6, 15)


def _cfg(**over) -> IFProjectorConfig:
    base = {
        "if_meta": 100_000_000.0,
        "if_trs_pct": 4.0,
        "titular_dob": _DOB,
        "aporte_mensal": 0.0,
        "retorno_real_anual_pct": 6.0,
        "reference_date": _REF,
    }
    base.update(over)
    return IFProjectorConfig(**base)


# ── Retorno real zero é premissa DECLARÁVEL (goal.if.schema.json: minimum 0) ──


def test_retorno_zero_com_aporte_projeta_prazo_linear() -> None:
    """Mutação que mata: manter o guard `r > 0` — volta a devolver `None`."""
    prazo = solve_prazo_anos(investivel=100_000, if_meta=1_000_000, r=0.0, aporte_mensal=10_000)

    # (1.000.000 − 100.000) / 10.000 = 90 meses = 7,5 anos.
    assert prazo == pytest.approx(7.5)


def test_prazo_linear_chega_ao_payload_e_propaga_idade_e_ano() -> None:
    """O ramo novo tem de atravessar `project`, não só a função pura."""
    p = IFProjector(_cfg(retorno_real_anual_pct=0.0, aporte_mensal=100_000)).project(
        investivel=40_000_000
    )

    assert p.prazo_anos_realista == pytest.approx(50.0)
    assert p.ano_if == 2076
    assert p.idade_titular_if == 90
    assert p.motivo_prazo_indefinido is None


# ── Aporte não declarado: calculável, retido por metodologia ────────────────


def test_aporte_zero_com_retorno_positivo_continua_ausente() -> None:
    """Mutação que mata: projetar capitalização pura aqui."""
    # `n = ln(FV/PV)/ln(1+r)` converge (no dogfood, ~35 anos), mas publicá-lo sob
    # `prazo_anos_realista` seria o produto escolher a premissa "você não aporta"
    # em nome da família e reportá-la como o prazo dela. E aporte 0 nem sequer é
    # declarável: `goal.aporte_mensal.schema.json` exige `exclusiveMinimum: 0`,
    # então o zero é sempre ausência de insumo.
    p = IFProjector(_cfg()).project(investivel=13_000_000)

    assert p.prazo_anos_realista is None
    assert p.ano_if is None
    assert p.idade_titular_if is None


def test_aporte_zero_nomeia_o_insumo_que_falta_e_nao_afirma_inviabilidade() -> None:
    p = IFProjector(_cfg()).project(investivel=13_000_000)

    assert p.motivo_prazo_indefinido == MOTIVO_APORTE_NAO_DECLARADO
    assert "aportar por mês" in p.motivo_prazo_indefinido
    assert "não há trajetória" not in p.motivo_prazo_indefinido


def test_sem_aporte_e_sem_retorno_e_o_unico_que_afirma_inviabilidade() -> None:
    assert motivo_prazo_indefinido(aporte_mensal=0.0, r=0.0) == MOTIVO_SEM_TRAJETORIA
    assert "não há trajetória" in MOTIVO_SEM_TRAJETORIA


def test_nenhum_motivo_diz_nao_projetavel() -> None:
    """A redação antiga nomeava a nossa incapacidade; é falsa no caso comum."""
    for motivo in (MOTIVO_APORTE_NAO_DECLARADO, MOTIVO_SEM_TRAJETORIA):
        assert "não projetável" not in motivo


# ── Não-convergência genuína continua ausente ───────────────────────────────


def test_patrimonio_zero_sem_aporte_continua_ausente() -> None:
    """Guard contra `ln(FV/0)` — não há de onde compor."""
    assert solve_prazo_anos(investivel=0, if_meta=1_000_000, r=0.005, aporte_mensal=0) is None


def test_meta_ja_atingida_continua_zero() -> None:
    assert solve_prazo_anos(investivel=2_000_000, if_meta=1_000_000, r=0.0, aporte_mensal=0) == 0.0


# ── Ausência de retorno ≠ 0% declarado ─────────────────────────────────────


def test_retorno_ausente_cai_no_default_e_nao_em_zero() -> None:
    """Mutação que mata: voltar a `_safe_float(cfg.get(chave, 6.0))`."""
    # O adapter emite a chave com `None`, então `.get(chave, 6.0)` nunca dispara
    # o default e `_safe_float(None)` é 0,0 — "campo ausente" virava "0% declarado".
    # Com o ramo linear preenchido, isso passaria a PROJETAR sobre uma premissa
    # que ninguém declarou.
    goals = {
        "independencia_financeira": {
            "if_meta": 1_000_000,
            "trs_pct": 4.0,
            "retorno_real_anual_pct": None,
        }
    }

    cfg = IFProjectorConfig.from_configs(goals=goals, titular_dob=_DOB)

    assert cfg.retorno_real_anual_pct == 6.0


def test_zero_declarado_permanece_zero() -> None:
    """O outro lado: quem declarou 0% não é sobrescrito pelo default."""
    assert default_if_absent(0, 6.0) == 0.0
    assert default_if_absent(None, 6.0) == 6.0
