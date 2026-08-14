"""Invariantes de conservação por balde sobre goldens E5 (A23.l2 · guard-rail G-b) — a "segunda testemunha" que quebra sozinha se um rebaseline cimentar valor errado. Cents int (ADR-090), tolerância zero (identidade algébrica no mesmo payload, não paridade). Identidades validadas no O3: bruto == Σ composicao[].valor (por balde); liquido == bruto − dividas; fluxo_liquido == receita_total − despesa_total."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from pipeline.llm.schemas.e16_irpf_full import (
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
)
from tests.pipeline_golden_substrate import load_fixture, run_e3_e4_e5, write_e5_config
from tests.unit.pipeline._passive_income_builders import (
    bem,
    decl,
    exclusiva,
    exterior_rend,
    isento,
)

_REPO = Path(__file__).resolve().parents[1]
_FIX = _REPO / "tests" / "fixtures" / "pipeline_golden"
_E3_MIN = _FIX / "e3" / "minimal-conta-3_reconciled.json"
_E3_MIXED = _FIX / "e3" / "minimal-conta-com-despesa-3_reconciled.json"
_BASELINE = _FIX / "e2" / "minimal-baseline-1.5_consolidated.json"
_BASELINE_DIV = _FIX / "e2" / "minimal-baseline-divergent-1.5_consolidated.json"


def _cents(value) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _e3_key(path: Path) -> str:
    return path.stem.replace("-3_reconciled", "")


_CASES = {
    "minimal": (_E3_MIN, None, None),
    "mixed": (_E3_MIXED, None, {"lazer": ["CINEMA"]}),
    "baseline": (_E3_MIN, _BASELINE, None),
    "divergent": (_E3_MIN, _BASELINE_DIV, None),
}


@pytest.fixture(params=sorted(_CASES), ids=sorted(_CASES))
def e5_payload(request, tmp_path: Path) -> dict:
    e3_path, baseline_path, expense_kw = _CASES[request.param]
    write_e5_config(tmp_path, expense_keywords=expense_kw)
    return run_e3_e4_e5(
        tmp_path,
        e3_payloads={_e3_key(e3_path): load_fixture(e3_path)},
        baseline=load_fixture(baseline_path) if baseline_path else None,
    )


# ADR-376 (A40.l38) — conservação EXCLUSIVA do caixa: todo banco com extrato
# elegível entra no caixa exatamente 1× (sem denylist de instituição), e nenhum
# banco com extrato elegível aparece também como posição cash-like no E4. A
# elegibilidade é re-derivada aqui de forma independente (segunda testemunha).
# Nível: ``analyze_via_store`` com posições E4 seeded — o harness E3-only de
# ``run_e3_e4_e5`` produz ``has_current_positions=False`` e o caminho de caixa
# nem executa (caixa residual do IRPF, ``detalhes=[]``).
_CASH_LIKE_TIPOS = frozenset(
    {"saldo", "saldo_em_conta", "caixa", "conta_corrente", "conta_pagamento", "cash"}
)


def _saldos_elegiveis_cents(e3_payloads: dict[str, dict]) -> int:
    latest: dict[tuple, tuple[str, float]] = {}
    for key, data in e3_payloads.items():
        tipo = (data.get("tipo_conta") or "").lower()
        if "fatura" in tipo or "poupan" in tipo or "pj" in tipo:
            continue
        if data.get("saldo_final") is None or data.get("saldo_final_unknown", False):
            continue
        acct = (
            (data.get("banco") or "").lower(),
            tipo,
            (data.get("moeda") or "BRL").upper(),
            (data.get("titular") or "").lower(),
        )
        fim = (data.get("periodo_cobertura") or {}).get("fim") or ""
        if acct not in latest or (fim, key) > (latest[acct][0], ""):
            latest[acct] = (fim, float(data["saldo_final"]))
    return sum(_cents(saldo) for _, saldo in latest.values())


def _assert_caixa_exclusivo(
    patrimonio: dict, e3_payloads: dict[str, dict], e4_investimentos: dict
) -> None:
    detalhes = patrimonio.get("caixa_detalhes") or []
    soma_detalhes = sum(_cents(d.get("valor_brl", 0)) for d in detalhes)
    assert _cents(patrimonio["caixa_total_brl"]) == max(0, soma_detalhes)
    assert soma_detalhes == _saldos_elegiveis_cents(e3_payloads)
    bancos_caixa = {(d.get("conta") or "").split(" (")[0].lower() for d in detalhes}
    for pos in e4_investimentos.get("dados", []) or []:
        instituicao = (pos.get("instituicao") or "").lower()
        if instituicao in bancos_caixa:
            assert (pos.get("tipo") or "").lower() not in _CASH_LIKE_TIPOS, (
                f"banco {instituicao!r} tem extrato elegível no caixa E também posição "
                f"cash-like no E4 ({pos.get('nome')!r}) — dupla contagem; decida a "
                f"precedência com produtor real (ADR-376 §3)"
            )


_E4_INVESTIMENTOS_STUB = {
    "total_geral": 500_000,
    "n_posicoes": 1,
    "total_por_membro": {"david": 500_000},
    "dados": [{"nome": "CDB Sintético", "instituicao": "itau", "tipo": "cdb", "membro": "david"}],
}


def _analyze_caixa(e3_payloads: dict[str, dict]) -> dict:
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.domain.services.e5_analyzer_adapter import E5AnalyzerAdapter

    store = InMemoryArtifactStore()
    store.seed("E4", "investimentos", _E4_INVESTIMENTOS_STUB)
    for key, payload in e3_payloads.items():
        store.seed("E3", key, payload)
    return E5AnalyzerAdapter().analyze_via_store(store).patrimonio_full


def test_caixa_conservation_exclusiva_inclui_banco_de_corretora():
    """O extrato de banco 'de investimento' (PicPay) entra no caixa (ADR-376)."""
    minimal = load_fixture(_E3_MIN)
    picpay = dict(minimal, banco="picpay", saldo_final=750.0, transacoes=[], transacoes_total=0)
    e3_payloads = {_e3_key(_E3_MIN): minimal, "picpay-conta": picpay}
    patrimonio = _analyze_caixa(e3_payloads)
    detalhes = patrimonio["caixa_detalhes"]
    assert any(
        d["conta"].lower().startswith("picpay") for d in detalhes
    ), "fixture vacuosa — o banco de corretora precisa aparecer no caixa"
    _assert_caixa_exclusivo(patrimonio, e3_payloads, _E4_INVESTIMENTOS_STUB)


def test_caixa_exclusao_tipada_para_poupanca():
    """Poupança fica fora do caixa COM razão tipada no payload (ADR-376 §4)."""
    minimal = load_fixture(_E3_MIN)
    poupanca = dict(
        minimal,
        banco="bradesco",
        tipo_conta="extratopoupanca",
        saldo_final=300.0,
        transacoes=[],
        transacoes_total=0,
    )
    e3_payloads = {_e3_key(_E3_MIN): minimal, "bradesco-poupanca": poupanca}
    patrimonio = _analyze_caixa(e3_payloads)
    _assert_caixa_exclusivo(patrimonio, e3_payloads, _E4_INVESTIMENTOS_STUB)
    exclusoes = patrimonio.get("caixa_exclusoes") or []
    assert [(e["banco"], e["motivo"]) for e in exclusoes] == [("bradesco", "poupanca")]


def test_guard_cash_like_dispara_com_produtor_sintetico():
    """Polaridade do gate: se um produtor E4 emitir posição cash-like para banco
    com extrato elegível, ``_assert_caixa_exclusivo`` acusa (tripwire, não passa)."""
    e3 = {
        "picpay-conta": {
            "banco": "picpay",
            "tipo_conta": "extratoconta",
            "moeda": "BRL",
            "saldo_final": 100.0,
        }
    }
    patrimonio = {
        "caixa_total_brl": 100.0,
        "caixa_detalhes": [{"conta": "picpay (extratoconta)", "valor_brl": 100.0, "moeda": "BRL"}],
    }
    e4_inv = {
        "dados": [{"nome": "Saldo em conta", "instituicao": "picpay", "tipo": "saldo_em_conta"}]
    }
    with pytest.raises(AssertionError, match="dupla contagem"):
        _assert_caixa_exclusivo(patrimonio, e3, e4_inv)


def test_patrimonio_bruto_equals_sum_of_buckets(e5_payload: dict):
    """bruto == Σ composicao[].valor (decomposição patrimonial por balde)."""
    pat = e5_payload["patrimonio"]
    soma = sum(_cents(b.get("valor", 0)) for b in pat.get("composicao", []))
    assert _cents(pat["bruto"]) == soma


def test_patrimonio_liquido_equals_bruto_minus_dividas(e5_payload: dict):
    pat = e5_payload["patrimonio"]
    assert _cents(pat["liquido"]) == _cents(pat["bruto"]) - _cents(pat.get("dividas", 0))


def test_fluxo_liquido_equals_receita_minus_despesa(e5_payload: dict):
    fc = e5_payload["fluxo_caixa"]
    assert _cents(fc["fluxo_liquido"]) == _cents(fc["receita_total"]) - _cents(fc["despesa_total"])


# F2-DB7 (A24.l1): decomposição POR CATEGORIA — Goodhart-safe. Mover tx entre
# categorias mantém o total e passa nos testes acima; estes quebram. Identidade
# sobre o payload serializado (round(v,2) por valor — analyze_finances.py:1444-1453);
# vale exato em cents porque dados bancários são 2dp (categorize_transactions round(Σ,2)).


def test_despesa_total_equals_sum_per_category(e5_payload: dict):
    fc = e5_payload["fluxo_caixa"]
    soma = sum(_cents(v) for v in fc.get("despesas_por_categoria", {}).values())
    assert _cents(fc["despesa_total"]) == soma


def test_receita_total_equals_sum_por_fonte(e5_payload: dict):
    fc = e5_payload["fluxo_caixa"]
    soma = sum(_cents(v) for v in fc.get("por_fonte", {}).values())
    assert _cents(fc["receita_total"]) == soma


def test_receita_total_equals_recorrente_plus_one_time(e5_payload: dict):
    fc = e5_payload["fluxo_caixa"]
    split = _cents(fc["receita_recorrente"]) + _cents(fc["receita_one_time"])
    assert _cents(fc["receita_total"]) == split


# I5-I7 — corte de provisionado. O headline e a série mensal têm que fechar entre
# si (I5), a série não pode passar do `data_corte` (I6) e o bloco que saiu tem que
# fechar consigo mesmo (I7). I6 é a que morde: sem o corte, uma receita com data
# futura estica `labels` para depois de hoje e o card que ancora a janela no
# último label divide receita de N meses por N+1.


def _mensal(payload: dict) -> dict:
    return payload["fluxo_caixa"]["receita_despesa_mensal_detalhado"]


def _label_para_mes(label: str) -> str:
    ano, mes = label.split("/")
    return f"20{ano}-{mes}"


def _assert_i5(payload: dict) -> None:
    fc = payload["fluxo_caixa"]
    mensal = _mensal(payload)
    assert _cents(fc["receita_total"]) == sum(_cents(v) for v in mensal["totais_receita"])
    assert _cents(fc["despesa_total"]) == sum(_cents(v) for v in mensal["totais_despesa"])


def _assert_i6(payload: dict) -> None:
    fc = payload["fluxo_caixa"]
    labels = _mensal(payload)["labels"]
    assert len(labels) == fc["janela_meses"]
    if labels:
        assert max(_label_para_mes(x) for x in labels) <= fc["data_corte"][:7]


def _assert_i7(payload: dict) -> None:
    prov = payload["fluxo_caixa"]["provisionado"]
    assert _cents(prov["receita_brl"]) == sum(_cents(v) for v in prov["por_fonte"].values())
    assert _cents(prov["despesa_brl"]) == sum(_cents(v) for v in prov["por_categoria"].values())


def test_i5_headline_fecha_com_a_serie_mensal(e5_payload: dict):
    _assert_i5(e5_payload)


def test_i6_serie_nao_passa_do_data_corte(e5_payload: dict):
    _assert_i6(e5_payload)


def test_i7_provisionado_fecha_consigo_mesmo(e5_payload: dict):
    _assert_i7(e5_payload)


# `reference_date` INJETADA. O stage re-deriva `TODAY = date.today()` a cada run
# (analyze_finances:119), então pinar o global não basta — congelamos o `date` do
# módulo. Sem pinar, o corpus futuro viraria passado com o calendário e o teste
# pararia de morder.
_REFERENCE_DATE = date(2026, 2, 10)


class _DataCongelada(date):
    @classmethod
    def today(cls) -> date:
        return _REFERENCE_DATE


_JCP_PROVISIONADO = {
    "data": "2026-03-05",
    "descricao": "PIX recebido JCP provisionado",
    "valor": 500.0,
}


@pytest.fixture
def e5_com_provisionado(tmp_path: Path, monkeypatch) -> dict:
    """E5 sobre corpus com 1 receita datada DEPOIS do `data_corte` injetado."""
    monkeypatch.setattr("scripts.analyze_finances.date", _DataCongelada)
    e3 = load_fixture(_E3_MIXED)
    e3["transacoes"] = [*e3["transacoes"], dict(_JCP_PROVISIONADO)]
    e3["transacoes_total"] = len(e3["transacoes"])
    e3["saldo_final"] = 570.0
    e3["periodo_cobertura"]["fim"] = "2026-03-31"
    write_e5_config(tmp_path, expense_keywords={"lazer": ["CINEMA"]})
    return run_e3_e4_e5(tmp_path, e3_payloads={_e3_key(_E3_MIXED): e3})


def test_i6_corta_transacao_futura_da_serie(e5_com_provisionado: dict):
    fc = e5_com_provisionado["fluxo_caixa"]
    assert fc["data_corte"] == _REFERENCE_DATE.isoformat()
    _assert_i6(e5_com_provisionado)
    assert _mensal(e5_com_provisionado)["labels"] == ["26/01"]


def test_i5_e_i7_com_provisionado(e5_com_provisionado: dict):
    _assert_i5(e5_com_provisionado)
    _assert_i7(e5_com_provisionado)


def test_provisionado_sai_do_realizado_sem_sumir(e5_com_provisionado: dict):
    """A receita futura não entra em `por_fonte`/`receita_total` e é declarada à parte."""
    fc = e5_com_provisionado["fluxo_caixa"]
    prov = fc["provisionado"]
    assert prov["transacoes"] == 1
    assert _cents(prov["receita_brl"]) == _cents(_JCP_PROVISIONADO["valor"])
    assert prov["primeiro_mes"] == prov["ultimo_mes"] == "2026-03"
    assert _cents(fc["receita_total"]) == _cents(100.0)
    assert _cents(prov["despesa_brl"]) == 0


def test_janelas_table_ready_fecham_em_centavos(e5_payload: dict):
    for janela in e5_payload["fluxo_caixa"]["janelas"].values():
        fontes = janela["tabela_receitas_por_fonte_mensal"]
        naturezas = janela["tabela_receita_por_natureza_mensal"]
        consumo = janela["tabela_consumo_por_categoria_mensal"]
        assert sum(_cents(row["mensal_media"]) for row in fontes) == _cents(
            janela["receita_mensal_media"]
        )
        assert sum(_cents(row["mensal_media"]) for row in naturezas) == _cents(
            janela["receita_mensal_media"]
        )
        assert sum(_cents(row["mensal_media"]) for row in consumo) == _cents(
            janela["despesa_consumo_mensal_media"]
        )


def test_janelas_separam_consumo_de_transferencia(e5_payload: dict):
    for janela in e5_payload["fluxo_caixa"]["janelas"].values():
        bruto = _cents(janela["despesa_mensal_media"])
        consumo = _cents(janela["despesa_consumo_mensal_media"])
        transferencia = _cents(janela["transferencia_patrimonial_mensal"])
        assert bruto == consumo + transferencia
        assert all(
            row["categoria"] != "aporte_investimento"
            for row in janela["tabela_consumo_por_categoria_mensal"]
        )


def test_janela_interativa_12m_reconcilia_com_legado(e5_payload: dict):
    fc = e5_payload["fluxo_caixa"]
    nova = fc["janelas"]["12m"]
    legada = fc["janela_12m"]
    assert nova["janela_meses"] == legada["janela_meses"]
    assert _cents(nova["receita_total"]) == _cents(legada["receita_total"])
    assert _cents(nova["despesa_total"]) == _cents(legada["despesa_total"])


def test_janelas_nao_reintroduzem_mes_provisionado(e5_com_provisionado: dict):
    fc = e5_com_provisionado["fluxo_caixa"]
    for janela in fc["janelas"].values():
        assert janela["mes_fim"] is None or janela["mes_fim"] <= fc["data_corte"][:7]


# DE-02 (R3.4b) + A37.l7 PR-2: conservação da renda passiva observada (ADR-191 +
# ADR-336). O numerador da TRS (renda_passiva_anual) é só yield RECORRENTE — a
# distribuição de lucro PJ do titular (renda de trabalho, ADR-191) e o ganho de
# capital (realização one-time, ADR-336) vivem em campos irmãos explícitos
# (renda_ativa_pj_excluida_brl / ganho_capital_excluido_brl), FORA do dict de
# fontes — o dict fecha com o headline (auto-conservativo). Exige fixture
# IRPF-bearing com ambos excluídos >0, senão o teste é vacuoso (0==0).
# CNPJ/empresa fictícios (ACME LTDA), PII-zero.
_QUOTA_ACME = "QUOTAS DA EMPRESA ACME SERVICOS LTDA CNPJ 12.345.678/0001-90"
_YIELD_BUCKETS = ("dividendos", "jcp", "aplicacoes", "exterior", "alugueis")


def _irpf_bearing_payload() -> dict:
    """IRPF sintético com os 6 buckets não-zero + distribuição PJ do titular."""
    return decl(
        isentos=[
            isento(CodigoRendimentoIsento.lucros_dividendos, "12000.00"),
            isento(
                CodigoRendimentoIsento.lucros_dividendos,
                "284000.00",
                fonte="12.345.678/0001-90 ACME SERVICOS LTDA",
                descricao="Lucros e dividendos recebidos",
            ),
        ],
        exclusiva_list=[
            exclusiva(CodigoRendimentoTribExclusiva.jcp, "30000.00"),
            exclusiva(CodigoRendimentoTribExclusiva.rendimentos_aplicacoes_financeiras, "3000.00"),
            exclusiva(CodigoRendimentoTribExclusiva.ganho_capital, "20000.00"),
        ],
        exterior=[exterior_rend("8000.00")],
        bens=[bem(descricao=_QUOTA_ACME, valor="500000.00")],
    ).model_dump(mode="json")


def _run_irpf_bearing_e5(tmp_path: Path) -> dict:
    write_e5_config(tmp_path)
    return run_e3_e4_e5(
        tmp_path,
        e3_payloads={_e3_key(_E3_MIN): load_fixture(_E3_MIN)},
        baseline=load_fixture(_BASELINE),
        irpf_payloads={"irpfdeclaracao_2024": _irpf_bearing_payload()},
    )


def test_renda_passiva_conservation(tmp_path: Path):
    e5 = _run_irpf_bearing_e5(tmp_path)
    pi = e5["passive_income"]
    assert pi["status"] == "ok", "fixture vacuosa — passive_income precisa ser 'ok'"
    fonte = pi["renda_passiva_por_fonte_brl"]
    distribuicao = _cents(pi["renda_ativa_pj_excluida_brl"])
    ganho = _cents(pi["ganho_capital_excluido_brl"])
    assert distribuicao > 0 and ganho > 0, "guard anti-vacuidade (exclusão seria 0)"
    yield_rec = sum(_cents(fonte[k]) for k in _YIELD_BUCKETS)
    anual = _cents(pi["renda_passiva_anual_brl"])
    assert anual == yield_rec == sum(_cents(v) for v in fonte.values())


def test_renda_passiva_dict_nao_carrega_componentes_excluidos(tmp_path: Path):
    """A37.l7 PR-2: contrato novo — consumidor que somava o dict antigo (com
    distribuicao_pj_titular/ganho_capital dentro) falha explicitamente (KeyError),
    não recebe silenciosamente um valor que quebra a conservação."""
    e5 = _run_irpf_bearing_e5(tmp_path)
    fonte = e5["passive_income"]["renda_passiva_por_fonte_brl"]
    assert set(fonte) == set(_YIELD_BUCKETS)
    with pytest.raises(KeyError):
        fonte["distribuicao_pj_titular"]
    with pytest.raises(KeyError):
        fonte["ganho_capital"]


def test_cv17_runtime_check_passes_on_golden(tmp_path: Path):
    """CV17 (A37.l7 · CTO-01) é o gêmeo runtime de test_renda_passiva_conservation:
    sobre o mesmo payload IRPF-bearing não-vacuoso, o check de `validate_cross`
    tem que ficar verde — prova que o gate cobre o payload real, não só o golden."""
    from scripts import validate_cross

    e5 = _run_irpf_bearing_e5(tmp_path)
    assert _cents(e5["passive_income"]["renda_ativa_pj_excluida_brl"]) > 0, "guard anti-vacuidade"
    result = validate_cross._cv17_renda_passiva_conservacao(e5)
    assert result is not None and result.passed
    assert result.severity == "info"
