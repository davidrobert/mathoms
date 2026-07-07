"""Unit tests A17 L3 P5 (ADR-238 §D1) — detectors CBE / Carnê-leão / GCAP cambial."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pipeline.domain.services.ptax_types import PtaxQuote
from pipeline.domain.services.wise_fiscal_flags import (
    FiscalFlag,
    detect_all_wise_flags,
    detect_cbe_threshold,
    detect_gcap_cambial_exposure,
    detect_juros_me_carne_leao,
    detect_juros_me_mal_alocado,
    detect_rfb41_em_me,
    detect_variacao_cambial_isentos,
)


def _ptax_fake(rates: dict[str, str]):
    """PtaxGetter de teste: moeda → PtaxQuote em 31/12 do ano_base."""

    def getter(moeda: str, ano_base: int):
        rate = rates.get(moeda)
        if rate is None:
            return None
        return PtaxQuote(rate=Decimal(rate), observed_at=date(ano_base, 12, 31))

    return getter


# ─────────────────────── factories ──────────────────────────────────────────


def _saldo_exterior(**overrides) -> dict:
    base = {
        "tipo": "conta_exterior",
        "descricao": "Wise USD account",
        "codigo_rfb": "62",
        "saldo": "500000.00",
        "moeda": "USD",
    }
    base.update(overrides)
    return base


def _rendimento(**overrides) -> dict:
    base = {
        "codigo_rfb": "13",
        "moeda": "USD",
        "valor": "1500.00",
        "fonte_pagadora_nome": "Interactive Brokers",
        "fonte_pagadora_cnpj": "",
    }
    base.update(overrides)
    return base


def _bem_exterior(**overrides) -> dict:
    base = {
        "codigo_rfb": "62",
        "moeda": "USD",
        "valor": "10000.00",
        "descricao": "Conta Wise USD",
    }
    base.update(overrides)
    return base


# ─────────────────────── CBE BACEN ──────────────────────────────────────────


def test_cbe_acima_threshold_emite_flag():
    saldos = [
        _saldo_exterior(saldo="700000.00"),
        _saldo_exterior(saldo="400000.00"),
    ]
    flags = detect_cbe_threshold(saldos)
    assert len(flags) == 1
    assert flags[0].code == "CBE"
    assert flags[0].severity == "info"
    assert flags[0].valor_original == Decimal("1100000")
    assert flags[0].moeda == "USD"
    assert "1.000.000" in flags[0].descricao or "1,000,000" in flags[0].descricao


def test_cbe_exatamente_no_threshold_nao_emite_flag():
    """USD 1MM = threshold; só > 1MM dispara CBE (Circular 3.624/2013)."""
    saldos = [_saldo_exterior(saldo="1000000.00")]
    assert detect_cbe_threshold(saldos) == []


def test_cbe_abaixo_threshold_nao_emite_flag():
    saldos = [_saldo_exterior(saldo="999999.99")]
    assert detect_cbe_threshold(saldos) == []


def test_cbe_ignora_eur_sem_ptax():
    """Sem PTAX injetado, degrada para soma nominal USD — EUR não soma (shipped P5)."""
    saldos = [_saldo_exterior(moeda="EUR", saldo="2000000.00")]
    assert detect_cbe_threshold(saldos) == []


def test_cbe_converte_eur_para_usd_via_ptax():
    # EUR 1MM × 6,4344 / 6,1917 ≈ USD 1,039k > USD 1MM → flag.
    """P5.4 (co-design 2026-07-07): posição EUR convertida por PTAX cruza o threshold."""
    saldos = [_saldo_exterior(moeda="EUR", saldo="1000000.00")]
    ptax = _ptax_fake({"USD": "6.1917", "EUR": "6.4344"})
    flags = detect_cbe_threshold(saldos, ptax, 2024)
    assert len(flags) == 1
    assert flags[0].code == "CBE"
    assert flags[0].needs_review is False


def test_cbe_multimoeda_soma_equivalente_usd():
    """USD nominal + EUR convertido somam para o threshold."""
    saldos = [
        _saldo_exterior(moeda="USD", saldo="600000.00"),
        _saldo_exterior(moeda="EUR", saldo="450000.00"),
    ]
    ptax = _ptax_fake({"USD": "6.00", "EUR": "6.60"})
    # 600k + 450k×6,6/6,0 = 600k + 495k = USD 1.095k > 1MM
    assert len(detect_cbe_threshold(saldos, ptax, 2024)) == 1


def test_cbe_ptax_ausente_para_moeda_degrada_sem_flag():
    """PTAX USD ok mas EUR ausente → EUR fica de fora (graceful, sem raise)."""
    saldos = [_saldo_exterior(moeda="EUR", saldo="2000000.00")]
    ptax = _ptax_fake({"USD": "6.00"})
    assert detect_cbe_threshold(saldos, ptax, 2024) == []


def test_cbe_ignora_cdb_domestico_em_usd():
    """Só `tipo=conta_exterior` conta — CDB doméstico USD (sintético) ignorado."""
    saldos = [_saldo_exterior(tipo="cdb", saldo="2000000.00")]
    assert detect_cbe_threshold(saldos) == []


def test_cbe_lista_vazia_retorna_vazio():
    assert detect_cbe_threshold([]) == []


# ─────────────────────── Carnê-leão ─────────────────────────────────────────


def test_carne_leao_rfb_13_em_usd_emite_footnote_info():
    """Bem alocado (código 13 em tributáveis) → footnote info sem needs_review
    (co-design financial-planner 2026-07-07, A33.l2 P5.3)."""
    flags = detect_juros_me_carne_leao([_rendimento()])
    assert len(flags) == 1
    assert flags[0].code == "CARNELEAO"
    assert flags[0].severity == "info"
    assert flags[0].needs_review is False
    assert flags[0].codigo_rfb == "13"
    assert flags[0].moeda == "USD"


def test_carne_leao_mal_alocado_em_isentos_needs_review():
    """Código 13 + ME fora de tributáveis → needs_review (DARF mensal em risco)."""
    flags = detect_juros_me_mal_alocado([_rendimento()], [])
    assert len(flags) == 1
    assert flags[0].code == "CARNELEAO"
    assert flags[0].severity == "atencao"
    assert flags[0].needs_review is True


def test_carne_leao_mal_alocado_em_exclusiva_needs_review():
    flags = detect_juros_me_mal_alocado([], [_rendimento(moeda="EUR")])
    assert len(flags) == 1
    assert flags[0].needs_review is True


def test_carne_leao_mal_alocado_brl_nao_emite():
    """Código 13 em BRL fora de tributáveis não é caso de carnê-leão exterior."""
    assert detect_juros_me_mal_alocado([_rendimento(moeda="BRL")], []) == []


def test_carne_leao_rfb_13_em_brl_nao_emite():
    """Juros tributáveis em BRL não vão para carnê-leão exterior."""
    flags = detect_juros_me_carne_leao([_rendimento(moeda="BRL")])
    assert flags == []


def test_carne_leao_outro_codigo_rfb_nao_emite():
    """codigo_rfb != 13 → fora do escopo carnê-leão."""
    flags = detect_juros_me_carne_leao([_rendimento(codigo_rfb="11")])
    assert flags == []


def test_carne_leao_multiplos_rendimentos_um_flag_cada():
    rendimentos = [
        _rendimento(valor="1000.00"),
        _rendimento(moeda="EUR", valor="2000.00"),
    ]
    flags = detect_juros_me_carne_leao(rendimentos)
    assert len(flags) == 2
    assert {f.moeda for f in flags} == {"USD", "EUR"}


def test_carne_leao_fonte_truncada_em_50_chars():
    """Fonte longa truncada na narrativa para evitar descricao gigante."""
    long_name = "X" * 200
    flags = detect_juros_me_carne_leao([_rendimento(fonte_pagadora_nome=long_name)])
    assert flags[0].descricao.count("X") <= 60  # 50 + margem


# ─────────────────────── GCAP cambial ────────────────────────────────────────


def test_gcap_detecta_exposicao_conta_exterior():
    saldos = [_saldo_exterior()]
    flags = detect_gcap_cambial_exposure(bens_direitos=[], saldos_31_12=saldos)
    assert len(flags) == 1
    assert flags[0].code == "GCAP"
    assert flags[0].severity == "atencao"


def test_gcap_detecta_exposicao_via_bens_direitos_rfb_62():
    bens = [_bem_exterior()]
    flags = detect_gcap_cambial_exposure(bens_direitos=bens, saldos_31_12=[])
    assert len(flags) == 1
    assert flags[0].code == "GCAP"


def test_gcap_nao_dispara_sem_exposicao_externa():
    """Sem conta_exterior nem RFB 62 → sem GCAP."""
    flags = detect_gcap_cambial_exposure(bens_direitos=[], saldos_31_12=[])
    assert flags == []


def test_gcap_brl_ignorado():
    """conta_exterior em BRL (degenerate) — sem variação cambial relevante."""
    saldos = [_saldo_exterior(moeda="BRL", saldo="100000.00")]
    flags = detect_gcap_cambial_exposure(bens_direitos=[], saldos_31_12=saldos)
    assert flags == []


def test_gcap_agrega_moedas_no_descricao():
    """Múltiplas moedas → uma flag única com soma por moeda."""
    saldos = [
        _saldo_exterior(moeda="USD", saldo="10000.00"),
        _saldo_exterior(moeda="EUR", saldo="5000.00"),
    ]
    flags = detect_gcap_cambial_exposure(bens_direitos=[], saldos_31_12=saldos)
    assert len(flags) == 1
    descricao = flags[0].descricao
    assert "USD" in descricao
    assert "EUR" in descricao
    assert flags[0].metadata["moedas_expostas"] == ["EUR", "USD"]


# ─────────────────────── Variação cambial em isentos (P5.2) ─────────────────


def test_variacao_cambial_em_isentos_needs_review():
    isentos = [{"descricao": "Variação cambial sobre saldo USD", "valor": "350.00", "moeda": "USD"}]
    flags = detect_variacao_cambial_isentos(isentos, has_exterior=True)
    assert len(flags) == 1
    assert flags[0].code == "GCAP_ISENTO"
    assert flags[0].needs_review is True


def test_variacao_cambial_acento_insensitive():
    """Regex é acento-insensitive: "variação" e "variacao" casam igual."""
    isentos = [{"descricao": "variacao cambial", "valor": "1.00", "moeda": "USD"}]
    assert len(detect_variacao_cambial_isentos(isentos, has_exterior=True)) == 1


def test_variacao_cambial_exchange_gain_e_fx():
    isentos = [
        {"descricao": "Exchange gain on balance", "valor": "1.00", "moeda": "USD"},
        {"descricao": "FX adjustment", "valor": "2.00", "moeda": "EUR"},
    ]
    assert len(detect_variacao_cambial_isentos(isentos, has_exterior=True)) == 2


def test_variacao_cambial_sem_conta_exterior_nao_flagra():
    """Predicado exige has_conta_exterior — payload 100% doméstico não flagra."""
    isentos = [{"descricao": "Variação cambial", "valor": "1.00", "moeda": "USD"}]
    assert detect_variacao_cambial_isentos(isentos, has_exterior=False) == []


def test_variacao_cambial_descricao_inocente_nao_flagra():
    """ "Rendimento de poupança" não casa o regex — sem falso-positivo."""
    isentos = [{"descricao": "Rendimento de poupança", "valor": "100.00", "moeda": "BRL"}]
    assert detect_variacao_cambial_isentos(isentos, has_exterior=True) == []


def test_variacao_cambial_fx_word_bounded():
    """ "FX" só casa word-bounded — "prefixado" não dispara."""
    isentos = [{"descricao": "CDB prefixado", "valor": "10.00", "moeda": "BRL"}]
    assert detect_variacao_cambial_isentos(isentos, has_exterior=True) == []


# ─────────────────────── Código 41 em ME (P5.1) ─────────────────────────────


def test_rfb41_em_moeda_estrangeira_needs_review():
    bens = [{"codigo_rfb": "41", "moeda": "USD", "valor": "5000.00", "descricao": "Conta Wise"}]
    flags = detect_rfb41_em_me(bens, has_exterior=False)
    assert len(flags) == 1
    assert flags[0].code == "RFB41_ME"
    assert flags[0].needs_review is True
    assert "62" in flags[0].descricao


def test_rfb41_brl_com_conta_exterior_no_payload_flagra():
    """41 em BRL mas payload tem posição exterior → predicado do co-design dispara."""
    bens = [{"codigo_rfb": "41", "moeda": "BRL", "valor": "1000.00", "descricao": "Conta"}]
    assert len(detect_rfb41_em_me(bens, has_exterior=True)) == 1


def test_rfb41_puro_brl_domestico_nao_flagra():
    """Código 41 puro em BRL é legítimo — não flagar (predicado ESTREITO)."""
    bens = [{"codigo_rfb": "41", "moeda": "BRL", "valor": "1000.00", "descricao": "Conta Itaú"}]
    assert detect_rfb41_em_me(bens, has_exterior=False) == []


def test_rfb41_codigo_62_correto_nao_flagra():
    bens = [_bem_exterior()]
    assert detect_rfb41_em_me(bens, has_exterior=True) == []


# ─────────────────────── Aggregator ──────────────────────────────────────────


def test_detect_all_wise_flags_payload_completo():
    """Payload com exposição + juros + saldo > 1MM dispara todas as 3 flags."""
    payload = {
        "saldos_31_12": [
            _saldo_exterior(saldo="1500000.00"),
        ],
        "rendimentos_tributaveis": [_rendimento()],
        "bens_direitos": [],
    }
    flags = detect_all_wise_flags(payload)
    codes = {f.code for f in flags}
    assert {"CBE", "CARNELEAO", "GCAP"}.issubset(codes)


def test_detect_all_wise_flags_payload_vazio():
    assert detect_all_wise_flags({}) == []


def test_detect_all_wise_flags_so_brl():
    """Conta doméstica BRL pura → zero flags (Wise não está em jogo)."""
    payload = {
        "saldos_31_12": [
            {"tipo": "cdb", "moeda": "BRL", "saldo": "5000.00", "codigo_rfb": "70"},
        ],
        "rendimentos_tributaveis": [],
        "bens_direitos": [],
    }
    assert detect_all_wise_flags(payload) == []


# ─────────────────────── Invariantes do FiscalFlag ───────────────────────────


def test_fiscal_flag_e_frozen():
    """FiscalFlag é dataclass frozen — não pode ser mutada após criação."""
    flag = FiscalFlag(code="CBE", severity="info", title="x", descricao="y")
    import dataclasses

    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        flag.code = "GCAP"  # type: ignore[misc]


def test_fiscal_flag_needs_review_default_false():
    flag = FiscalFlag(code="CBE", severity="info", title="x", descricao="y")
    assert flag.needs_review is False


def test_fiscal_flag_format_inclui_code_e_title():
    """Warnings tipados expõem .format() (ADR-097 D1)."""
    flag = FiscalFlag(code="GCAP", severity="atencao", title="Título", descricao="Corpo")
    assert flag.format() == "[GCAP] Título: Corpo"


def test_detect_all_payload_3_cenarios_needs_review():
    """Golden P5 (co-design 2026-07-07): 41-em-ME + cambial-isento + juros mal-alocado
    → 3 pontos needs_review agregáveis."""
    payload = {
        "saldos_31_12": [_saldo_exterior(saldo="1000.00")],
        "rendimentos_tributaveis": [],
        "rendimentos_isentos": [
            {"descricao": "Variação cambial sobre saldo", "valor": "10.00", "moeda": "USD"},
            _rendimento(valor="42.10"),
        ],
        "rendimentos_exclusiva": [],
        "bens_direitos": [
            {"codigo_rfb": "41", "moeda": "USD", "valor": "1000.00", "descricao": "Conta Wise"}
        ],
    }
    flags = detect_all_wise_flags(payload)
    needs = [f for f in flags if f.needs_review]
    assert {f.code for f in needs} == {"RFB41_ME", "GCAP_ISENTO", "CARNELEAO"}
    assert len(needs) == 3
