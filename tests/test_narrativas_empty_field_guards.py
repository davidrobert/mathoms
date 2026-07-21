"""Guards de campo vazio nas narrativas E5.N (Onda R3.2 — PD-01/PD-02/PD-06).

Campo biográfico/estrutural ausente omite a cláusula inteira, sem buracos de
template ("Formado em .", "residência na ", " como contador", "0 viagens/ano
entre R$ 0,00 e R$ 0,00"). Fixtures reusadas do golden decomposition test.
"""

from __future__ import annotations

from datetime import date

from pipeline.domain.services.narrativas import (
    ChartsNarrator,
    NarrativasContext,
    PerfilFamiliaNarrator,
    SummariesNarrator,
)
from tests.test_e5n_builder_decomposition import _FAMILY_BASE, _build_metrics

_TODAY = date(2026, 4, 20)

_DECISOES_5 = ["Aporte mensal", "CPA expatriado", "Fechar holding", "Revisar seguros", "DAS"]


def _narrate_top5(metrics: dict) -> str:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    out = ChartsNarrator(ctx).narrate(metrics, _FAMILY_BASE, [], _DECISOES_5)
    return out["top5_decisoes"]["conclusion"]


def _narrate_s10(metrics: dict) -> str:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    return SummariesNarrator(ctx).narrate(metrics, _FAMILY_BASE, [], _DECISOES_5)["s10"]


# ── A37.l2 (PD-01): guard de distribuição de aporte vazia + keys dinâmicas ──
# Regressão pré-fix (verificada em c61c1c29): Goal com ``distribuicao={}``
# gerava 4 parcelas hardcoded "R$ 0,00" no top5_decisoes e no s10.


def test_top5_decisoes_distribuicao_vazia_sem_parcelas_zero():
    m = {**_build_metrics(), "aporte_distribuicao": {}}
    conclusion = _narrate_top5(m)
    assert "R$ 0,00" not in conclusion
    assert "(" not in conclusion.split("Prioridade 2")[0]
    assert "a distribuir entre as classes sub-representadas" in conclusion


def test_top5_decisoes_distribuicao_ausente_trata_como_vazia():
    """Metrics antigos (sem a key) não podem quebrar nem imprimir zeros."""
    m = _build_metrics()
    m.pop("aporte_distribuicao")
    conclusion = _narrate_top5(m)
    assert "R$ 0,00" not in conclusion
    assert "a distribuir entre as classes sub-representadas" in conclusion


def test_top5_decisoes_distribuicao_zerada_trata_como_vazia():
    m = {**_build_metrics(), "aporte_distribuicao": {"cofrinhos_itau": 0, "ivvb11": 0}}
    conclusion = _narrate_top5(m)
    assert "R$ 0,00" not in conclusion
    assert "a distribuir entre as classes sub-representadas" in conclusion


def test_top5_decisoes_instrumentos_arbitrarios_todos_aparecem():
    m = {
        **_build_metrics(),
        "aporte_distribuicao": {"cdb_liquidez": 6_000, "etf_global": 9_000, "fii_hglg11": 0},
    }
    conclusion = _narrate_top5(m)
    assert "com divisão (R$ 6k CDB Liquidez, R$ 9k ETF Global)" in conclusion
    assert "R$ 0,00" not in conclusion


def test_top5_decisoes_keys_legadas_preservam_rotulos():
    conclusion = _narrate_top5(_build_metrics())
    assert "com divisão (R$ 5k Cofrinhos, R$ 8k IPCA+, R$ 4k IVVB11, R$ 3k Wise USD)" in conclusion


def test_summaries_s10_distribuicao_vazia_sem_parcelas_zero():
    m = {**_build_metrics(), "aporte_distribuicao": {}}
    s10 = _narrate_s10(m)
    assert "R$ 0,00" not in s10
    assert "a distribuir entre as classes sub-representadas" in s10


def test_summaries_s10_instrumentos_arbitrarios_todos_aparecem():
    m = {**_build_metrics(), "aporte_distribuicao": {"cdb_liquidez": 6_000, "acoes_br": 2_500}}
    s10 = _narrate_s10(m)
    assert "(R$ 6k CDB Liquidez, R$ 2,5k Acoes Br)" in s10
    assert "R$ 0,00" not in s10


def test_load_metrics_from_e5_propaga_distribuicao(tmp_path, monkeypatch):
    """Wiring: ``goals_cfg.aportes.distribuicao`` → ``metrics.aporte_distribuicao``."""
    import scripts.generate_narratives as e5n

    e5n._init_config(tmp_path)
    monkeypatch.setattr(e5n, "_load_taxas", lambda: {})
    e5_data = {
        "patrimonio": {},
        "goals": {},
        "fluxo_caixa": {},
        "ratios": {},
        "score": {},
        "reserva_emergencia": {},
    }
    dist = {"cdb_liquidez": 6_000.0, "etf_global": 9_000.0}
    metrics = e5n.load_metrics_from_e5(e5_data, goals_cfg={"aportes": {"distribuicao": dist}})
    assert metrics["aporte_distribuicao"] == dist
    metrics_vazio = e5n.load_metrics_from_e5(e5_data, goals_cfg={})
    assert metrics_vazio["aporte_distribuicao"] == {}


def test_perfil_familia_left_sem_buracos_de_fragmento():
    """PD-01: fragmentos do bloco `left` guardados (sem 'Formado em .', 'é  desde')."""
    fam = {
        "titular": "alex",
        "membros": {
            "alex": {"nome_curto": "Alex", "data_nascimento": "1985-03-10"},
            "bia": {"papel": "conjuge", "nome_curto": "Bia", "data_nascimento": "1987-07-22"},
        },
    }
    m = {**_build_metrics(), "salario_conjuge": 0}
    left = PerfilFamiliaNarrator(NarrativasContext.from_family_config(fam)).narrate(
        m, fam, today=_TODAY
    )["left"]
    for hole in ("Formado em .", "Opera como .", "é  desde", "Especialista em ,", "mestre em ."):
        assert hole not in left
    assert "salário-base de R$ 0,00" not in left


def test_summaries_s4_omite_endereco_vazio():
    """PD-02: s4 sem rua → 'residência (' e não 'residência na ('."""
    fam = {**_FAMILY_BASE, "endereco": {}}
    s = SummariesNarrator(NarrativasContext.from_family_config(fam)).narrate(
        _build_metrics(), fam, [], []
    )
    assert "residência na " not in s["s4"] and "residência (" in s["s4"]


def test_summaries_s8_omite_contador_e_holding_vazios():
    """PD-02: s8 sem contador/holding → sem ' como contador' nem 'pendente para .'."""
    m = {**_build_metrics(), "contador_nome": "", "holding_prazo": ""}
    s = SummariesNarrator(NarrativasContext.from_family_config(_FAMILY_BASE)).narrate(
        m, _FAMILY_BASE, [], []
    )
    assert " como contador" not in s["s8"]
    assert "pendente para ." not in s["s8"] and "pendente para 0" not in s["s8"]


def test_summaries_s5_viagens_zero_usa_empty_state():
    """PD-06: 0 viagens / faixa R$ 0–0 → empty-state, não '0 viagens/ano'."""
    m = {**_build_metrics(), "viagens_anuais_estimadas": 0, "custo_viagem_minimo": 0}
    m["custo_viagem_maximo"] = 0
    s = SummariesNarrator(NarrativasContext.from_family_config(_FAMILY_BASE)).narrate(
        m, _FAMILY_BASE, [], []
    )
    assert "0 viagens/ano" not in s["s5"] and "entre R$ 0,00 e R$ 0,00" not in s["s5"]
    assert "não identificado automaticamente" in s["s5"]
