"""Invariante 4a — três produtores medem o mesmo estoque de imóvel e ninguém os amarra (RV6-07 · PLAN-deterministic-authority §Onda 0 item 0b). `patrimonio.imoveis_investimento` (PatrimonioCalculator), `imoveis_geradores + imoveis_nao_geradores` (split ADR-142/ADR-215 §6) e `goals.alocacao_alvo.derived.imoveis_fisicos_brl` (AlocacaoAlvoDeviation sobre a tabela de classes ADR-193). Escrito RED: é o critério de aceite da Onda 1. Arquivo próprio — em `test_e5_conservation_invariants.py` estouraria o teto de 500 linhas (P2)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from tests.pipeline_golden_substrate import load_fixture, run_dogfood_pipeline, write_e5_config

_FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "pipeline_golden" / "dogfood"

# `_enrich_alocacao_with_deviation` exige `rf_pos_pct` na RAIZ de `alocacao_alvo`
# (e5_serialization.py:441); aninhado sob `inputs`, o `derived` nasce vazio e o
# invariante viraria "campo ausente" em vez de "produtores discordam".
_ALOCACAO_ALVO_V2 = {
    "rf_pos_pct": 30.0,
    "rf_pre_pct": 10.0,
    "rf_ipca_pct": 10.0,
    "acoes_br_pct": 20.0,
    "acoes_int_pct": 15.0,
    "fiis_pct": 10.0,
    "caixa_pct": 5.0,
    "meta_version": 2,
    "inputs": {},
    "derived": {},
}

_IMOVEL_LEGITIMO = {
    "codigo": "11",
    "descricao": "Rua Exemplo, 100",
    "categoria": "imovel",
    "valor_brl": 600000.0,
    "membro": "alex",
    "ano": 2024,
}
# O financiamento com o rótulo flipado pela re-extração (r6): mesmo código RFB do
# imóvel legítimo, categoria de ativo, valor negativo.
_FINANCIAMENTO_ROTULADO_ATIVO = {
    **_IMOVEL_LEGITIMO,
    "descricao": "FINANCIAMENTO IMOVEL FICTICIO",
    "valor_brl": -150000.0,
}
_FINANCIAMENTO_CORRETO = {
    **_FINANCIAMENTO_ROTULADO_ATIVO,
    "codigo": "51",
    "categoria": "outros",
}


def _cents(value) -> int:
    """ADR-090: comparação monetária é int de centavos, nunca float."""
    return int((Decimal(str(value or 0)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _goals_com_alvo() -> dict:
    return {
        "independencia_financeira": {"if_meta": 1_000_000.0, "trs_pct": 4.0},
        "alocacao_alvo": _ALOCACAO_ALVO_V2,
    }


def _run_dogfood_com_alvo(tmp_path: Path, itens: list[dict]) -> dict:
    """Roda E1.5c→E5 sobre o corpus dogfood com os `itens` de baseline dados."""
    baseline = load_fixture(_FIX / "baseline-1.5.json")
    baseline["itens"] = itens
    write_e5_config(tmp_path, goals=_goals_com_alvo())
    extratos = {
        "extrato-a": load_fixture(_FIX / "extrato-a-2_extract.json"),
        "extrato-b": load_fixture(_FIX / "extrato-b-2_extract.json"),
    }
    return run_dogfood_pipeline(tmp_path, raw_baseline=baseline, e2_extracts=extratos)


def _termos_4a(e5: dict) -> tuple[int, int, int]:
    """Os três medidores do mesmo estoque, em cents."""
    patrimonio = e5.get("patrimonio") or {}
    derived = ((e5.get("goals") or {}).get("alocacao_alvo") or {}).get("derived") or {}
    assert "imoveis_fisicos_brl" in derived, (
        "guard anti-vacuidade: `derived` vazio faria o invariante comparar com 0 e "
        f"falhar por campo ausente, não por discordância (derived={sorted(derived)})"
    )
    split = _cents(patrimonio.get("imoveis_geradores")) + _cents(
        patrimonio.get("imoveis_nao_geradores")
    )
    return (
        _cents(patrimonio.get("imoveis_investimento")),
        split,
        _cents(derived.get("imoveis_fisicos_brl")),
    )


# Guard de instrumento: sem ele, o RED do irmão abaixo seria indistinguível de "o
# invariante nunca valeu" — e a Onda 1 estaria perseguindo um alvo impossível.
def test_invariante_4a_vale_no_payload_limpo(tmp_path: Path) -> None:
    """Sobre corpus limpo os três produtores já concordam — o alvo da Onda 1 existe."""
    itens = [_IMOVEL_LEGITIMO, _FINANCIAMENTO_CORRETO]
    imoveis_investimento, split, fisicos = _termos_4a(_run_dogfood_com_alvo(tmp_path, itens))
    assert imoveis_investimento > 0, "guard anti-vacuidade: 0 ≡ 0 ≡ 0 passaria sem exercitar nada"
    assert imoveis_investimento == split == fisicos


# Sobre o payload r6 os três divergem porque cada produtor trata o negativo de um
# jeito: o PatrimonioCalculator o SOMA ao estoque (600k−150k=450k) e
# `_aggregate_carteira` o DESCARTA (`if valor > 0`, alocacao_alvo_deviation.py:186),
# mantendo 600k. Nenhuma das duas leituras é sinalizada — e é o mesmo imóvel.
@pytest.mark.xfail(
    strict=True,
    reason="RED até A40.l66 (seam extração/consolidação) — critério de aceite da Onda 1",
)
def test_invariante_4a_entre_agregados(tmp_path: Path) -> None:
    """`imoveis_investimento` ≡ geradores+não-geradores ≡ `imoveis_fisicos_brl`, cents, tolerância zero."""
    itens = [_IMOVEL_LEGITIMO, _FINANCIAMENTO_ROTULADO_ATIVO]
    imoveis_investimento, split, fisicos = _termos_4a(_run_dogfood_com_alvo(tmp_path, itens))
    assert imoveis_investimento > 0, "guard anti-vacuidade"
    assert imoveis_investimento == split == fisicos
