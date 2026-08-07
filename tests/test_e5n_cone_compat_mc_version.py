"""Compat de leitura do cone entre ``mc_version`` 3.0 e 4.0 (ADR-369 D3)."""

# O rename das chaves do cone é rename-only: artefato gravado sob 3.0 continua na
# base (backfill descartado — ADR-369 D4), e um re-run parcial de
# ``generate_narratives`` sobre ele tem de produzir a MESMA frase. Sem o ramo de
# compat, os anos chegariam ``None`` ao narrador e a conclusão cairia na frase
# determinística — a mais otimista do relatório, e sem incerteza declarada —
# exatamente quando a mediana não atinge a meta (o defeito que a ADR-361 D9
# fechou). A falha é silenciosa, não ruidosa: os guards do narrador usam ``.get``.

from __future__ import annotations

from typing import Any

import scripts.generate_narratives as e5n
from tests.test_e5n_narrativas_coerentes import _charts, _e5_data_minimal, _metrics_base

_ANOS = {"favoravel": 2039, "central": 2046, "adverso": 2058}


def _bloco_v3() -> dict[str, Any]:
    """Bloco do cone como um artefato 3.0 real o gravou (chaves pré-rename)."""
    return {
        "p10_ano_if": _ANOS["favoravel"],
        "p10_censurado": False,
        "p50_ano_if": _ANOS["central"],
        "p50_censurado": False,
        "p90_ano_if": _ANOS["adverso"],
        "p90_censurado": False,
        "prob_if_ate_idade_meta": 0.31,
        "prob_if_ate_horizonte": 0.99,
        "idade_meta_usada": 65,
        "sigma_usado": 0.11,
        "exibir_cone": True,
        "mc_version": "3.0",
        "seed_usado": 360,
        "n_simulacoes_usado": 50_000,
        "horizonte_anos": 40,
    }


def _bloco_v4() -> dict[str, Any]:
    """Mesmos VALORES sob as chaves de 4.0 — o rename não mexe em número."""
    return {
        "ano_if_cenario_favoravel": _ANOS["favoravel"],
        "ano_if_cenario_favoravel_censurado": False,
        "ano_if_cenario_central": _ANOS["central"],
        "ano_if_cenario_central_censurado": False,
        "ano_if_cenario_adverso": _ANOS["adverso"],
        "ano_if_cenario_adverso_censurado": False,
        "prob_if_ate_idade_meta": 0.31,
        "prob_if_ate_horizonte_simulado": 0.99,
        "idade_meta_usada": 65,
        "sigma_usado": 0.11,
        "exibir_cone": True,
        "mc_version": "4.0",
        "seed_usado": 360,
        "n_simulacoes_usado": 50_000,
        "horizonte_simulado_anos": 40,
    }


def _metrics_do_bloco(bloco: dict[str, Any]) -> dict[str, Any]:
    data = _e5_data_minimal()
    data["if_monte_carlo"] = bloco
    return e5n.load_metrics_from_e5(data)


def test_artefato_3_0_chega_ao_narrador_sob_os_nomes_de_4_0():
    """A tradução acontece no read-site; o narrador só conhece os nomes novos."""
    metrics = _metrics_do_bloco(_bloco_v3())
    assert metrics["mc_ano_if_cenario_favoravel"] == _ANOS["favoravel"]
    assert metrics["mc_ano_if_cenario_central"] == _ANOS["central"]
    assert metrics["mc_ano_if_cenario_adverso"] == _ANOS["adverso"]
    assert metrics["mc_prob_if_ate_horizonte_simulado"] == 0.99
    assert metrics["mc_horizonte_simulado_anos"] == 40
    assert metrics["mc_ano_if_cenario_central_censurado"] is False


def test_frase_do_cone_e_identica_em_3_0_e_4_0():
    """Rename-only: mesma entrada, mesma prosa — é o que ``4.0`` declara."""
    frase_v3 = _charts(_metrics_base() | _metrics_do_bloco(_bloco_v3()))
    frase_v4 = _charts(_metrics_base() | _metrics_do_bloco(_bloco_v4()))
    conclusao_v3 = frase_v3["projecao_3cenarios"]["conclusion"]
    assert conclusao_v3 == frase_v4["projecao_3cenarios"]["conclusion"]
    # E é a frase do cone, não a determinística: sem compat, o teste acima
    # passaria com as DUAS caindo no fallback (mesma prosa, ambas erradas).
    assert f"meta em {_ANOS['central']}" in conclusao_v3
    assert "trajetória projetada aponta a meta para" not in conclusao_v3


def test_artefato_sem_carimbo_e_lido_como_v1():
    """``mc_version`` ausente = artefato pré-ADR-360 — chaves antigas também."""
    sem_carimbo = {k: v for k, v in _bloco_v3().items() if k != "mc_version"}
    metrics = _metrics_do_bloco(sem_carimbo)
    assert metrics["mc_ano_if_cenario_central"] == _ANOS["central"]


def test_major_de_duas_casas_nao_ordena_por_string():
    """``"10.0" >= "4.0"`` é falso em str — o major é comparado como int."""
    assert e5n._mc_major({"mc_version": "10.0"}) == 10
    assert e5n._mc_major({"mc_version": "3.0"}) == 3
    assert e5n._mc_major({}) == 1


def test_probabilidade_pre_5_0_vira_ausencia_em_vez_de_ser_reaproveitada():
    """A `prob` antiga media outra coisa — copiá-la para a chave nova é fabricar."""
    # Artefato 4.0 tem `prob_if_ate_idade_meta`: P(o modelo bater a data que ele
    # mesmo imprimiu). Publicá-la sob `prob_if_ate_prazo_declarado` faria o
    # narrador dizer "os N anos que você declarou" sobre um número que nunca viu
    # prazo declarado nenhum — exatamente a inversão que a ADR-369 D2 impede.
    metrics = _metrics_do_bloco(_bloco_v4())
    assert metrics["mc_prob_if_ate_prazo_declarado"] is None
    assert metrics["mc_prazo_declarado_anos"] is None
    assert "contrato anterior" in metrics["mc_motivo_sem_prazo_declarado"]


def test_frase_de_artefato_pre_5_0_publica_o_cone_e_declara_a_ausencia():
    """O cone (rename-only) sobrevive; a probabilidade não, e isso é dito."""
    conclusao = _charts(_metrics_base() | _metrics_do_bloco(_bloco_v4()))
    frase = conclusao["projecao_3cenarios"]["conclusion"]
    assert f"meta em {_ANOS['central']}" in frase
    assert "ainda não respondeu em quantos anos" in frase
    # E nunca a frase determinística, que é a mais otimista do relatório.
    assert "trajetória projetada aponta a meta para" not in frase
