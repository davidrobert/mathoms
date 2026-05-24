"""Unit tests A17 L3 P3 (ADR-238 D5) — BaselineInformeMerger + Wise PTAX graceful."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.baseline_informe_merger import (
    BaselineInformeMerger,
    BaselineMergeResult,
)

# ─────────────────────── factories de informe ───────────────────────────────


def _saldo(**overrides) -> dict:
    base = {
        "tipo": "cdb",
        "descricao": "CDB DI 100% Itaú 90 dias",
        "codigo_rfb": "70",
        "saldo": "5000.00",
        "moeda": "BRL",
        "fonte_pagadora_cnpj": "60746948000112",
    }
    base.update(overrides)
    return base


def _saldo_wise(**overrides) -> dict:
    base = {
        "tipo": "conta_exterior",
        "descricao": "Wise USD account",
        "codigo_rfb": "62",
        "saldo": "1000.00",
        "moeda": "USD",
        "fonte_pagadora_cnpj": "23945200000115",
    }
    base.update(overrides)
    return base


def _informe(
    saldos: list[dict], *, ano_base: int = 2024, cnpj_emissor: str = "60746948000112"
) -> dict:
    return {
        "ano_base": ano_base,
        "tipo_informe": "financeiro_pf",
        "fonte_pagadora_cnpj": cnpj_emissor,
        "fonte_pagadora_nome": "Banco X",
        "confidence": 0.95,
        "prompt_version": "informe-pf-v1.0.0",
        "financeiro_pf": {
            "cnpj_emissor": cnpj_emissor,
            "nome_emissor": "Banco X",
            "saldos_31_12": saldos,
        },
    }


def _ptax_table(taxas: dict[tuple[str, int], Decimal]):
    """Factory de ptax_getter — `taxas[(moeda, ano)] → Decimal` ou None se ausente."""

    def _get(moeda: str, ano: int):
        return taxas.get((moeda, ano))

    return _get


# ─────────────────────── empty / edge cases ─────────────────────────────────


def test_merge_sem_informes_retorna_baseline_intacto():
    merger = BaselineInformeMerger()
    base = {"imoveis_consolidados": [{"id": "a"}]}
    r = merger.merge(base, [])
    assert isinstance(r, BaselineMergeResult)
    assert r.informes_processed == 0
    assert r.saldos_added == 0
    assert r.warnings == []
    assert r.baseline["informe_pf_saldos_31_12"] == []
    assert r.baseline["imoveis_consolidados"] == [{"id": "a"}]


def test_merge_informe_sem_saldos_31_12_zero_entradas():
    merger = BaselineInformeMerger()
    informe = _informe(saldos=[])
    r = merger.merge({}, [informe])
    assert r.informes_processed == 1
    assert r.saldos_added == 0


# ─────────────────────── BRL doméstico (no PTAX needed) ──────────────────────


def test_merge_brl_cdb_simples():
    merger = BaselineInformeMerger()
    informe = _informe(saldos=[_saldo()])
    r = merger.merge({}, [informe])
    assert r.saldos_added == 1
    entry = r.baseline["informe_pf_saldos_31_12"][0]
    assert entry["moeda"] == "BRL"
    assert entry["saldo_original"] == "5000.00"
    assert entry["saldo_brl"] == "5000.00"
    assert entry["taxa_ptax_aplicada"] == "1"
    assert entry["ptax_status"] == "applied"
    assert entry["ano_base"] == 2024
    assert entry["tipo"] == "cdb"
    assert entry["codigo_rfb"] == "70"


def test_merge_brl_nao_chama_ptax_getter():
    """BRL não precisa cotação — ptax_getter NÃO deve ser chamado."""
    calls: list = []

    def _spy(moeda: str, ano: int):
        calls.append((moeda, ano))
        return None

    merger = BaselineInformeMerger(ptax_getter=_spy)
    merger.merge({}, [_informe(saldos=[_saldo()])])
    assert calls == []  # zero chamadas


# ─────────────────────── Wise USD → BRL via PTAX ────────────────────────────


def test_merge_wise_usd_com_ptax_disponivel():
    """Wise USD 1000 + PTAX 5.20 → saldo_brl=5200.00."""
    ptax = _ptax_table({("USD", 2024): Decimal("5.20")})
    merger = BaselineInformeMerger(ptax_getter=ptax)
    r = merger.merge({}, [_informe(saldos=[_saldo_wise(saldo="1000.00")])])
    assert r.saldos_added == 1
    entry = r.baseline["informe_pf_saldos_31_12"][0]
    assert entry["moeda"] == "USD"
    assert entry["saldo_original"] == "1000.00"
    assert entry["saldo_brl"] == "5200.00"
    assert entry["taxa_ptax_aplicada"] == "5.20"
    assert entry["ptax_status"] == "applied"
    assert entry["codigo_rfb"] == "62"
    assert r.warnings == []


def test_merge_wise_usd_sem_ptax_graceful_degradation():
    """PTAX ausente → saldo_brl=None + warning emitido (não raise)."""
    merger = BaselineInformeMerger(ptax_getter=_ptax_table({}))  # vazio
    r = merger.merge({}, [_informe(saldos=[_saldo_wise()])])
    assert r.saldos_added == 1
    entry = r.baseline["informe_pf_saldos_31_12"][0]
    assert entry["saldo_brl"] is None
    assert entry["taxa_ptax_aplicada"] is None
    assert entry["ptax_status"] == "missing"
    assert len(r.warnings) == 1
    assert "PTAX USD/BRL ausente" in r.warnings[0]
    assert "31/12/2024" in r.warnings[0]


def test_merge_wise_eur_via_ptax():
    """Suporta EUR (Avenue Europe, Wise EUR account)."""
    ptax = _ptax_table({("EUR", 2024): Decimal("5.60")})
    merger = BaselineInformeMerger(ptax_getter=ptax)
    r = merger.merge({}, [_informe(saldos=[_saldo_wise(moeda="EUR", saldo="500.00")])])
    entry = r.baseline["informe_pf_saldos_31_12"][0]
    assert entry["moeda"] == "EUR"
    assert entry["saldo_brl"] == "2800.00"


# ─────────────────────── CBE BACEN warning (> USD 1MM) ──────────────────────


def test_merge_cbe_bacen_warning_quando_excede_1MM_usd():
    """Total exterior > USD 1MM emite warning CBE."""
    ptax = _ptax_table({("USD", 2024): Decimal("5.20")})
    merger = BaselineInformeMerger(ptax_getter=ptax)
    saldos = [
        _saldo_wise(saldo="700000.00"),  # USD 700k
        _saldo_wise(saldo="400000.00", fonte_pagadora_cnpj="11111111000111"),  # USD 400k
    ]
    r = merger.merge({}, [_informe(saldos=saldos)])
    assert r.saldos_added == 2
    cbe_warnings = [w for w in r.warnings if "CBE BACEN" in w]
    assert len(cbe_warnings) == 1
    assert "USD 1100000.00" in cbe_warnings[0]
    assert "USD 1MM" in cbe_warnings[0]


def test_merge_cbe_nao_dispara_quando_abaixo_threshold():
    ptax = _ptax_table({("USD", 2024): Decimal("5.20")})
    merger = BaselineInformeMerger(ptax_getter=ptax)
    r = merger.merge({}, [_informe(saldos=[_saldo_wise(saldo="50000.00")])])
    assert all("CBE BACEN" not in w for w in r.warnings)


def test_merge_cbe_apenas_conta_exterior_usd_contabilizada():
    """CDB doméstico em USD (raro) não conta para CBE — só `conta_exterior`."""
    ptax = _ptax_table({("USD", 2024): Decimal("5.20")})
    merger = BaselineInformeMerger(ptax_getter=ptax)
    saldos = [
        # USD 2MM em CDB doméstico (cenário sintético — tipo errado pra CBE)
        _saldo_wise(tipo="cdb", saldo="2000000.00", codigo_rfb="70"),
    ]
    # NB: SaldoProduto Pydantic rejeitaria isso (validator), mas aqui testamos
    # o merger pure que aceita dict cru. Tipo != conta_exterior → não conta CBE.
    r = merger.merge({}, [_informe(saldos=saldos)])
    assert all("CBE BACEN" not in w for w in r.warnings)


# ─────────────────────── Múltiplos informes ─────────────────────────────────


def test_merge_multiplos_informes_concatena_saldos():
    """Itaú + Nubank + Wise — cada um contribui suas saldos_31_12."""
    ptax = _ptax_table({("USD", 2024): Decimal("5.20")})
    merger = BaselineInformeMerger(ptax_getter=ptax)
    informes = [
        _informe(saldos=[_saldo(descricao="Itaú CDB")], cnpj_emissor="60746948000112"),
        _informe(
            saldos=[_saldo(descricao="Nubank", tipo="conta_pagamento", codigo_rfb="41")],
            cnpj_emissor="18236120000158",
        ),
        _informe(saldos=[_saldo_wise(saldo="2000.00")], cnpj_emissor="23945200000115"),
    ]
    r = merger.merge({}, informes)
    assert r.informes_processed == 3 and r.saldos_added == 3
    entries = r.baseline["informe_pf_saldos_31_12"]
    assert {e["cnpj_emissor"] for e in entries} == {
        "60746948000112",
        "18236120000158",
        "23945200000115",
    }


def test_merge_preserva_outras_chaves_do_baseline():
    """Merger acrescenta `informe_pf_saldos_31_12` sem tocar imoveis/veiculos/investimentos."""
    merger = BaselineInformeMerger()
    base = {
        "imoveis_consolidados": [{"id": "imovel-1"}],
        "veiculos_consolidados": [{"placa": "ABC1234"}],
        "investimentos_consolidados": [{"id": "inv-1"}],
        "dividas": [],
    }
    r = merger.merge(base, [_informe(saldos=[_saldo()])])
    assert r.baseline["imoveis_consolidados"] == [{"id": "imovel-1"}]
    assert r.baseline["veiculos_consolidados"] == [{"placa": "ABC1234"}]
    assert r.baseline["investimentos_consolidados"] == [{"id": "inv-1"}]
    assert r.baseline["dividas"] == []
    assert len(r.baseline["informe_pf_saldos_31_12"]) == 1
