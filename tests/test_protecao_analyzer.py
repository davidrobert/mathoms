"""A19 L1 P1 (ADR-240 D2/D3/D8) — ProtecaoAnalyzer determinístico + 3 cenários golden."""

from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.protecao_analyzer import (
    FamilyMemberSnapshot,
    FiscalSnapshot,
    PatrimonioSnapshot,
    ProtecaoInput,
    _gap_auto_sinal,
    _pct_renda_sinal,
    compute_protecao,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "config" / "schemas" / "protecao_patrimonial.schema.json"


# ─────────────────────── Helpers ──────────────────────────────────────────


def _corretor(nome="Bedoni", cnpj="12345678000199", susep="202020138") -> dict:
    return {"susep_code": susep, "nome": nome, "cpf_or_cnpj": cnpj, "cnpj_or_cpf_kind": "cnpj"}


def _cob_material(modo: str, lmi=None, pct=None, premio="1000.00") -> dict:
    return {
        "tipo": "material",
        "nome": "Casco",
        "lmi_modo": modo,
        "lmi_brl": lmi,
        "lmi_fipe_percentual": pct,
        "premio_brl": premio,
    }


def _bem_veiculo(id_: str, placa: str, marca: str, modelo: str, ano: int, cob: dict) -> dict:
    return {
        "tipo": "veiculo",
        "placa": placa,
        "veiculo_id": id_,
        "marca": marca,
        "modelo": modelo,
        "ano_modelo": ano,
        "coberturas": [cob],
    }


def _bem_imovel(id_: str, cob: dict) -> dict:
    return {
        "tipo": "imovel",
        "endereco": {"logradouro": "Rua X", "cidade": "Rio", "uf": "RJ"},
        "tipo_imovel": "casa",
        "imovel_id": id_,
        "coberturas": [cob],
    }


def _apolice(numero, seguradora, inicio, fim, premio, corretor, bens) -> dict:
    return {
        "apolice_numero": numero,
        "seguradora": seguradora,
        "vigencia_inicio": inicio,
        "vigencia_fim": fim,
        "premio_total_brl": premio,
        "forma_pagamento": "cartao",
        "corretor": corretor,
        "bens_segurados": bens,
        "confidence": 0.95,
    }


def _apolice_auto_simples() -> dict:
    bem = _bem_veiculo(
        "v-1", "ABC1D23", "YAMAHA", "NMAX", 2024, _cob_material("fipe_percentual", pct="1.00")
    )
    return _apolice(
        "AUTO-1", "tokiomarine", "2026-03-01", "2027-03-01", "1500.00", _corretor(), [bem]
    )


def _apolice_combinada() -> dict:
    bem_v = _bem_veiculo(
        "v-toro",
        "XYZ9A87",
        "FIAT",
        "TORO",
        2022,
        _cob_material("valor_fixo", lmi="60000.00", premio="1800.00"),
    )
    bem_i = _bem_imovel("p-1", _cob_material("valor_fixo", lmi="600000.00", premio="650.00"))
    return _apolice(
        "COMB-1",
        "porto",
        "2026-04-10",
        "2027-04-10",
        "3250.00",
        _corretor("Mrr Miseg", "98765432000111", "202020150"),
        [bem_v, bem_i],
    )


# ─────────────────────── Cenário A — workspace COM seguros ────────────────


def test_cenario_a_owner_com_seguros_kpi_g_soma_premios():
    """Caso owner: 2 apólices vigentes (auto + combinada Toro+casa). KPI G hero."""
    inp = ProtecaoInput(
        apolices=[_apolice_auto_simples(), _apolice_combinada()],
        vehicles_by_id={
            "v-1": {"fipe_value_brl": Decimal("80000")},
            "v-toro": {"fipe_value_brl": Decimal("100000")},
        },
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("200000"),
    )
    out = compute_protecao(inp)
    assert out["premio_total_anual_brl"] == "4750.00"
    assert len(out["apolices_vigentes"]) == 2
    assert out["seguradoras_count"] == 2
    assert out["corretoras_count"] == 2


def test_cenario_a_decomposicao_separa_auto_e_residencial():
    """ADR-352: combinada Porto (veículo 1800 + imóvel 650) rateia o prêmio total por
    cobertura — auto e residencial separados, Σ == premio_total cent-exato."""
    inp = ProtecaoInput(
        apolices=[_apolice_auto_simples(), _apolice_combinada()],
        vehicles_by_id={},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("200000"),
    )
    decomp = compute_protecao(inp)["premio_decomposicao"]
    # auto_simples 1500 → auto; combinada 3250 rateado 1800:650 → auto 2387.76 + resid 862.24
    assert decomp["auto"] == "3887.76"
    assert decomp["residencial"] == "862.24"
    assert sum(Decimal(v) for v in decomp.values()) == Decimal("4750.00")


def _apolice_sem_detalhe(premio="6022.27") -> dict:
    return _apolice("SEMBEM-1", "porto", "2026-01-01", "2027-01-01", premio, _corretor(), [])


def test_apolice_sem_bens_vai_para_nao_identificado():
    """ADR-352 D3 (RV2-26): apólice sem bens_segurados não fabrica 'auto' — nao_identificado."""
    inp = ProtecaoInput(
        apolices=[_apolice_sem_detalhe()],
        vehicles_by_id={},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("200000"),
    )
    decomp = compute_protecao(inp)["premio_decomposicao"]
    assert decomp == {"nao_identificado": "6022.27"}
    assert "auto" not in decomp


def test_premio_decomposicao_conserva_total_cent_exato():
    """ADR-352 D2: Σ premio_decomposicao == premio_total_anual (cent-exato) em mix."""
    inp = ProtecaoInput(
        apolices=[_apolice_combinada(), _apolice_sem_detalhe("999.99")],
        vehicles_by_id={},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("200000"),
    )
    out = compute_protecao(inp)
    soma = sum(Decimal(v) for v in out["premio_decomposicao"].values())
    assert soma == Decimal(out["premio_total_anual_brl"])  # 3250 + 999.99


def test_cenario_a_pct_renda_em_faixa_cerbasi_ok():
    """4750 / 200000 = 0.02375 → faixa 'ok' (1% ≤ pct ≤ 3%)."""
    inp = ProtecaoInput(
        apolices=[_apolice_auto_simples(), _apolice_combinada()],
        vehicles_by_id={},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("200000"),
    )
    out = compute_protecao(inp)
    assert Decimal(out["pct_renda_anual"]) == Decimal("0.023750")
    assert _pct_renda_sinal(Decimal(out["pct_renda_anual"])) == "ok"


def test_cenario_a_gap_auto_kpi_c():
    """v-1: LMI = 100% FIPE 80k = 80k, gap=0 ok. v-toro: LMI 60k vs FIPE 100k, gap=0.40 atencao."""
    inp = ProtecaoInput(
        apolices=[_apolice_auto_simples(), _apolice_combinada()],
        vehicles_by_id={
            "v-1": {"fipe_value_brl": Decimal("80000")},
            "v-toro": {"fipe_value_brl": Decimal("100000")},
        },
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("200000"),
    )
    out = compute_protecao(inp)
    gaps = {b["veiculo_id"]: b for b in out["bens_com_gap_cobertura"]}
    assert gaps["v-1"]["sinal"] == "ok"
    assert gaps["v-1"]["gap_pct"] == "0.000000"
    assert gaps["v-toro"]["sinal"] == "atencao"
    assert Decimal(gaps["v-toro"]["gap_pct"]) == Decimal("0.400000")


# ─────────────────────── Cenário B — workspace SEM apólices ───────────────


def test_cenario_b_workspace_sem_apolices_premio_zero():
    inp = ProtecaoInput(
        apolices=[],
        vehicles_by_id={},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("100000"),
    )
    out = compute_protecao(inp)
    assert out["premio_total_anual_brl"] == "0.00"
    assert out["apolices_vigentes"] == []
    assert out["bens_com_gap_cobertura"] == []
    assert out["corretoras_count"] == 0
    assert out["seguradoras_count"] == 0


def _inp_empty(**kwargs) -> ProtecaoInput:
    """Helper para Input vazio (sem apolices, sem vehicles)."""
    defaults = dict(
        apolices=[],
        vehicles_by_id={},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("100000"),
    )
    defaults.update(kwargs)
    return ProtecaoInput(**defaults)


def _gap_vida(out: dict) -> dict:
    return [g for g in out["gap_qualitativo"] if g["categoria"] == "vida"][0]


def test_cenario_b_flag_vida_false_sem_family_members():
    """G5: sem family_members → flag False silenciosamente."""
    out = compute_protecao(_inp_empty())
    vida = _gap_vida(out)
    assert vida["flag"] is False
    assert vida["rationale"] == "sem family_members"


def test_cenario_b_flag_vida_true_com_dependente_menor():
    inp = _inp_empty(
        family_members=(
            FamilyMemberSnapshot(parentesco="titular", idade=42),
            FamilyMemberSnapshot(parentesco="filho", idade=8, is_dependente=True),
        ),
    )
    vida = _gap_vida(compute_protecao(inp))
    assert vida["flag"] is True
    assert vida["rationale"] == "dependentes_menores_18"


def test_cenario_b_flag_saude_quando_sem_evidencia():
    inp = ProtecaoInput(
        apolices=[],
        vehicles_by_id={},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("100000"),
    )
    out = compute_protecao(inp)
    saude = [g for g in out["gap_qualitativo"] if g["categoria"] == "saude"][0]
    assert saude["flag"] is True
    assert saude["rationale"] == "sem_evidencia_cobertura"


def test_cenario_b_flag_saude_false_quando_irpf_tem_deducao_saude():
    inp = ProtecaoInput(
        apolices=[],
        vehicles_by_id={},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("100000"),
        fiscal=FiscalSnapshot(has_deducao_saude_irpf=True),
    )
    out = compute_protecao(inp)
    saude = [g for g in out["gap_qualitativo"] if g["categoria"] == "saude"][0]
    assert saude["flag"] is False
    assert saude["rationale"] == "evidencia_pagamento_saude"


# ─────────────────────── Cenário C — combinada multi-bem ─────────────────


def test_cenario_c_combinada_subgrupo_bens_com_2_linhas():
    """Critério aceite ADR-240 G6 (c): apólice combinada gera 2 entries em bens_segurados."""
    inp = ProtecaoInput(
        apolices=[_apolice_combinada()],
        vehicles_by_id={"v-toro": {"fipe_value_brl": Decimal("100000")}},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("200000"),
    )
    out = compute_protecao(inp)
    apolice_resumo = out["apolices_vigentes"][0]
    assert apolice_resumo["bens_count"] == 2
    assert sorted(apolice_resumo["tipos_bem"]) == ["imovel", "veiculo"]


# ─────────────────────── Vigência (vigentes / vencendo / vencidas) ────────


def test_vigencia_separacao_vigente_vencendo_vencida():
    base = _apolice_auto_simples()
    inp = _inp_empty(
        apolices=[
            base,
            {**base, "apolice_numero": "VEN-1", "vigencia_fim": "2026-06-20"},
            {**base, "apolice_numero": "OLD-1", "vigencia_fim": "2025-12-31"},
        ]
    )
    out = compute_protecao(inp)
    assert len(out["apolices_vigentes"]) == 2  # base + VEN-1
    assert [a["apolice_numero"] for a in out["apolices_vencendo"]] == ["VEN-1"]
    assert [a["apolice_numero"] for a in out["apolices_vencidas"]] == ["OLD-1"]


# ─────────────────────── Faixas de sinal (Cerbasi + gap auto) ─────────────


@pytest.mark.parametrize(
    "pct,sinal",
    [
        ("0.005", "atencao"),  # < 1%
        ("0.02", "ok"),
        ("0.04", "ok_forte"),
        ("0.07", "atencao"),  # > 5%
    ],
)
def test_pct_renda_sinal_cerbasi(pct, sinal):
    assert _pct_renda_sinal(Decimal(pct)) == sinal


@pytest.mark.parametrize(
    "gap,sinal",
    [
        ("0.05", "ok"),
        ("0.15", "atencao_branda"),
        ("0.30", "atencao"),
    ],
)
def test_gap_auto_sinal_faixas(gap, sinal):
    assert _gap_auto_sinal(Decimal(gap)) == sinal


# ─────────────────────── Schema validation hook (ADR-212) ─────────────────


def test_payload_valida_schema():
    """Payload do compute_protecao deve passar pelo schema JSON (ADR-212 PR3a)."""
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text())
    inp = ProtecaoInput(
        apolices=[_apolice_auto_simples(), _apolice_combinada()],
        vehicles_by_id={
            "v-1": {"fipe_value_brl": Decimal("80000")},
            "v-toro": {"fipe_value_brl": Decimal("100000")},
        },
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("200000"),
    )
    out = compute_protecao(inp)
    jsonschema.validate(out, schema)  # no raise


# ─────────────────────── Edge: renda zero → pct = "0.000000" ─────────────


def test_renda_zero_nao_divide_e_pct_zero():
    inp = ProtecaoInput(
        apolices=[_apolice_auto_simples()],
        vehicles_by_id={},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("0"),
    )
    out = compute_protecao(inp)
    assert out["pct_renda_anual"] == "0.000000"


# ─────────────────────── A37.l11 — canonicalização de seguradora ──────────

_CATALOGO_SEGURADORAS = {"porto": "Porto Seguro", "tokiomarine": "Tokio Marine"}


def _inp_variantes_porto() -> ProtecaoInput:
    """3 apólices vigentes: tokiomarine + 2 da mesma cia (`porto` e `portoseguro`)."""
    variante = _apolice_combinada()
    variante["apolice_numero"] = "COMB-2"
    variante["seguradora"] = "portoseguro"
    return ProtecaoInput(
        apolices=[_apolice_auto_simples(), _apolice_combinada(), variante],
        vehicles_by_id={},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("200000"),
        seguradoras_catalog=_CATALOGO_SEGURADORAS,
    )


def test_seguradoras_count_unifica_variantes_da_mesma_cia():
    """Regressão A37.l11 (PD-05): LLM emitiu `porto` E `portoseguro` para a
    mesma cia no mesmo run — count naive dava 3; canonicalizado contra o
    catálogo (`portoseguro` casa "Porto Seguro" por nome normalizado) dá 2."""
    out = compute_protecao(_inp_variantes_porto())
    assert out["seguradoras_count"] == 2


def test_apolice_resumo_display_name_unico_para_variantes():
    """As duas variantes da mesma cia rendem UM display name via catálogo."""
    out = compute_protecao(_inp_variantes_porto())
    resumos = {r["apolice_numero"]: r for r in out["apolices_vigentes"]}
    assert resumos["COMB-1"]["seguradora"] == "porto"
    assert resumos["COMB-2"]["seguradora"] == "porto"
    nomes = {resumos["COMB-1"]["seguradora_nome"], resumos["COMB-2"]["seguradora_nome"]}
    assert nomes == {"Porto Seguro"}
    assert resumos["AUTO-1"]["seguradora_nome"] == "Tokio Marine"


def test_sem_catalogo_resumo_degrada_para_display_capitalizado():
    """Caller sem catálogo (CLI isolado / artifacts antigos): count naive é
    preservado e o display name degrada para o code capitalizado — nunca cru."""
    inp = ProtecaoInput(
        apolices=[_apolice_auto_simples(), _apolice_combinada()],
        vehicles_by_id={},
        data_referencia=date(2026, 6, 1),
        renda_anual_liquida_brl=Decimal("200000"),
    )
    out = compute_protecao(inp)
    assert out["seguradoras_count"] == 2
    resumos = {r["apolice_numero"]: r for r in out["apolices_vigentes"]}
    assert resumos["AUTO-1"]["seguradora_nome"] == "Tokiomarine"
    assert resumos["COMB-1"]["seguradora_nome"] == "Porto"
