"""Unit tests A17 L3 P5 (ADR-238 §D1) — detectors CBE / Carnê-leão / GCAP cambial."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.wise_fiscal_flags import (
    FiscalFlag,
    detect_all_wise_flags,
    detect_cbe_threshold,
    detect_gcap_cambial_exposure,
    detect_juros_me_carne_leao,
)

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


def test_cbe_ignora_eur_no_threshold():
    """Threshold é em USD; EUR não soma para CBE neste detector simplificado V1."""
    saldos = [_saldo_exterior(moeda="EUR", saldo="2000000.00")]
    assert detect_cbe_threshold(saldos) == []


def test_cbe_ignora_cdb_domestico_em_usd():
    """Só `tipo=conta_exterior` conta — CDB doméstico USD (sintético) ignorado."""
    saldos = [_saldo_exterior(tipo="cdb", saldo="2000000.00")]
    assert detect_cbe_threshold(saldos) == []


def test_cbe_lista_vazia_retorna_vazio():
    assert detect_cbe_threshold([]) == []


# ─────────────────────── Carnê-leão ─────────────────────────────────────────


def test_carne_leao_rfb_13_em_usd_emite_flag():
    flags = detect_juros_me_carne_leao([_rendimento()])
    assert len(flags) == 1
    assert flags[0].code == "CARNELEAO"
    assert flags[0].severity == "atencao"
    assert flags[0].codigo_rfb == "13"
    assert flags[0].moeda == "USD"


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
