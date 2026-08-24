"""Golden de execução das três vias de conversão ME→BRL (ADR-390 · A40.l63).

O #1494 marcou o §Critério 1 da lane `[x]` sobre teste unitário: nenhum golden
citava `taxa_fonte`, e `test_e5_golden_execution.py` não descia até
`patrimonio.caixa_detalhes`. Unitário exercita a função; golden exercita o
artefato que o pipeline escreve.
"""

from __future__ import annotations

from pathlib import Path

from tests.test_e5_golden_execution import (
    _BASELINE_MIN,
    _E3_FIXTURE,
    _REPO,
    _new_e5_ctx,
    _write_e5_config,
)

_E3_USD = (
    _REPO / "tests" / "fixtures" / "pipeline_golden" / "e3" / "minimal-conta-usd-3_reconciled.json"
)
_FIX_E2 = _REPO / "tests" / "fixtures" / "pipeline_golden" / "e2"
_BASELINE_INFORME = _FIX_E2 / "minimal-baseline-informe-1.5_consolidated.json"
_BASELINE_ME_IRPF = _FIX_E2 / "minimal-baseline-me-irpf-1.5_consolidated.json"

# `compute_caixa` só publica `caixa_detalhes` quando há posição corrente
# (`has_current_positions`); sem isso cai no residual IRPF e devolve `[]`. Uma
# posição sintética mínima liga o ramo — o que se mede aqui é o carimbo da
# conversão no E5, não a consolidação do E4.
_POSICAO_CORRENTE_MINIMA = {
    "dados": [
        {
            "proprietario": "david",
            "descricao": "CDB sintético (golden)",
            "instituicao": "Itau",
            "tipo": "renda_fixa",
            "valor_atual": 1000.0,
        }
    ],
    "total_por_membro": {"david": 1000.0},
    "total_geral": 1000.0,
    "fontes": [],
    "n_posicoes": 1,
}


def _tenant(tmp_path: Path, nome: str) -> Path:
    t = tmp_path / nome
    t.mkdir()
    _write_e5_config(t)
    return t


def _caixa_detalhes_do_run(tenant: Path, *, e3_fixture: Path, baseline: Path) -> list[dict]:
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws

    ctx = _new_e5_ctx(tenant, e3_fixture=e3_fixture, baseline=baseline)
    e4_mws(ctx)
    ctx.artifact_store.write(
        "categorize_transactions", "investimentos", dict(_POSICAO_CORRENTE_MINIMA)
    )
    e5_mws(ctx)
    payload = ctx.artifact_store.read("E5", "analise_financeira")
    assert payload is not None
    return payload["patrimonio"]["caixa_detalhes"]


def test_golden_informe_31_12_carimba_ptax(tmp_path: Path):
    detalhes = _caixa_detalhes_do_run(
        _tenant(tmp_path, "informe"), e3_fixture=_E3_USD, baseline=_BASELINE_INFORME
    )
    assert detalhes, "run sem caixa_detalhes — o golden não exercita a via"
    # Toda linha publicada carrega o carimbo (ADR-390 §Emenda E1).
    assert all("conversao" in d for d in detalhes)
    ptax = next(d for d in detalhes if d["conversao"]["taxa_fonte"] == "ptax_31_12")
    assert ptax["conversao"]["taxa"] == "6.1917"
    assert ptax["conversao"]["taxa_data"] == "2024-12-31"
    assert ptax["conversao"]["status"] == "converted"
    assert ptax["fonte"] == "informe_31_12"


def test_golden_extrato_me_com_taxas_json_carimba_market_rate(tmp_path: Path):
    detalhes = _caixa_detalhes_do_run(
        _tenant(tmp_path, "extrato"), e3_fixture=_E3_USD, baseline=_BASELINE_MIN
    )
    usd = [d for d in detalhes if d["moeda"] == "USD"]
    assert usd, f"extrato USD não chegou ao caixa: {detalhes}"
    conv = usd[0]["conversao"]
    assert conv["taxa_fonte"] == "market_rate_corrente"
    assert conv["status"] == "converted"
    # `taxas.json` não versiona data: nulo porque a data não existe, não porque
    # se perdeu no caminho (ADR-390 §Emenda E3).
    assert conv["taxa_data"] is None


def test_golden_extrato_me_sem_cotacao_alguma_carimba_default_hardcoded(tmp_path: Path):
    """§Escopo 2 da lane — o caso que ninguém sabia quando disparava."""
    # Sem remover o `taxas.json` legado que o tenant golden copia, a via
    # resolve para `market_rate_corrente` e o ramo do default nunca roda.
    tenant = _tenant(tmp_path, "sem_taxas")
    (tenant / "config" / "taxas.json").unlink()
    detalhes = _caixa_detalhes_do_run(tenant, e3_fixture=_E3_USD, baseline=_BASELINE_MIN)
    usd = [d for d in detalhes if d["moeda"] == "USD"]
    assert usd, f"extrato USD não chegou ao caixa: {detalhes}"
    conv = usd[0]["conversao"]
    assert conv["taxa_fonte"] == "default_hardcoded"
    assert conv["taxa"] == "5.80"
    # Constante de política não tem data de observação (ADR-390 §Emenda E3).
    assert conv["taxa_data"] is None


def test_golden_me_so_irpf_carimba_identity_e_nao_se_diz_extrato(tmp_path: Path):
    detalhes = _caixa_detalhes_do_run(
        _tenant(tmp_path, "irpf"), e3_fixture=_E3_FIXTURE, baseline=_BASELINE_ME_IRPF
    )
    irpf = [d for d in detalhes if d["tipo"] == "moeda_estrangeira_irpf"]
    assert irpf, f"fallback ADR-245 não disparou: {detalhes}"
    linha = irpf[0]
    assert linha["conversao"]["taxa_fonte"] == "irpf_ja_em_brl"
    assert linha["conversao"]["status"] == "identity"
    # `moeda` ≡ unidade de `saldo_original` (ADR-245 L3 emendada).
    assert linha["moeda"] == "BRL"
    # A linha não veio de extrato bancário (ADR-238 §Emenda 2026-08-24).
    assert linha["fonte"] == "baseline_irpf"


# As vias são mutuamente exclusivas por desenho: o informe 31/12 **substitui** a
# linha do extrato (ADR-238 D5) e o fallback ADR-245 só dispara com
# `not has_foreign_in_e3`. Nenhum par coexiste num mesmo workspace — por isso
# três runs, e não um.
_VIAS = {
    "extrato": (_E3_USD, _BASELINE_MIN, "market_rate_corrente"),
    "informe": (_E3_USD, _BASELINE_INFORME, "ptax_31_12"),
    "irpf": (_E3_FIXTURE, _BASELINE_ME_IRPF, "irpf_ja_em_brl"),
}


def test_golden_as_tres_vias_produzem_taxa_fonte_distinto(tmp_path: Path):
    """§Critério 1 da A40.l63, medido sobre o artefato E5 de três runs reais."""
    vistas: dict[str, set[str]] = {}
    for nome, (e3, base, esperada) in _VIAS.items():
        detalhes = _caixa_detalhes_do_run(_tenant(tmp_path, nome), e3_fixture=e3, baseline=base)
        assert all("conversao" in d for d in detalhes), nome
        vistas[nome] = {
            d["conversao"]["taxa_fonte"] for d in detalhes if d["conversao"]["taxa_fonte"]
        }
        assert esperada in vistas[nome], (nome, vistas[nome])
    # Distintas de verdade: nenhuma via colapsa na outra.
    assert len(set().union(*vistas.values())) >= 3, vistas
