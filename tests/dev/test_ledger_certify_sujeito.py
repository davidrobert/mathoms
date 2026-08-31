#!/usr/bin/env python3
"""Teste de TROCA DE SUJEITOS — [[ADR-421]] §Critério de aceite (A42.l14).

Antes desta lane, trocar `persisted_e3` por um universo grosseiramente diferente
deixava os oito campos de rubrica IDÊNTICOS; só `drift` reagia. A causa era a
fixture: `test_ledger_certify_core.py` passava `persisted_e3=fresh_e3`, o mesmo
objeto, e nenhum teste conseguia discriminar os dois universos.

Aqui os dois sujeitos rendem vereditos OPOSTOS em todo eixo, e trocá-los troca os
blocos integralmente. Eixo que ignore o argumento quebra a simetria — e eixo NOVO
adicionado depois sem wiring cai no mesmo teste. Mora em arquivo próprio porque a
[[A42.l3]] reescreve `test_ledger_certify_core.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dev.ledger_certify_core import build_report, format_report
from dev.ledger_conservation import CONSERVADO, NAO_VERIFICAVEL

_E3_BOM = {"g1": {"transacoes_total": 2, "transacoes": [{"valor": 1.0}, {"valor": 2.0}]}}
# `transacoes_total` != len(transacoes) ⇒ NAO_VERIFICAVEL (rubrica de grupo E3).
_E3_RUIM = {"g1": {"transacoes_total": 99, "transacoes": [{"valor": 1.0}]}}

_INVEST_LIMPO = {"dados": []}
_INVEST_DUPLICADO = {
    "dados": [
        {"tipo": "CDB", "instituicao": "Banco X", "descricao": "CDB 2028", "valor_atual": 1000.0},
        {"tipo": "cdb", "instituicao": "banco x", "descricao": "CDB 2028", "valor_atual": 1000.0},
    ]
}


def _e4(invest: dict) -> dict:
    return {
        "despesas": {
            "total_geral": 3.0,
            "totais_por_categoria": {"a": 3.0},
            "dados": {"a": [{"valor": 1.0}, {"valor": 2.0}]},
            "total_transacoes": 2,
        },
        "investimentos": invest,
    }


def _fake_result() -> SimpleNamespace:
    classified = [SimpleNamespace(natural_key={"x": 1}, valor=1.0)]
    return SimpleNamespace(classified=classified, cash_flow=SimpleNamespace(transferencias_count=0))


def _fake_e3_result() -> SimpleNamespace:
    return SimpleNamespace(
        statements_loaded=1, statements_reconciled=1, skipped_inputs=0, artifacts_written=1
    )


def _report(*, publicado_e3: dict, publicado_e4: dict):
    """`build_report` cuja RE-DERIVAÇÃO é sempre a mesma — só o sujeito publicado muda."""
    return build_report(
        "ws-uuid",
        "run-1",
        [{"transacoes": [{"valor": 1.0}, {"valor": 2.0}]}],
        _fake_e3_result(),
        _fake_result(),
        _e4(_INVEST_LIMPO),
        _E3_BOM,
        publicado_e3,
        e4_persisted=publicado_e4,
    )


def _bloco(texto: str, titulo: str) -> str:
    assert titulo in texto, f"bloco ausente: {titulo}"
    return titulo + texto.split(titulo, 1)[1].split("\n## ", 1)[0]


def test_trocar_o_sujeito_troca_o_eixo_e3() -> None:
    bom = _report(publicado_e3=_E3_BOM, publicado_e4=_e4(_INVEST_LIMPO))
    ruim = _report(publicado_e3=_E3_RUIM, publicado_e4=_e4(_INVEST_LIMPO))
    assert bom.e3_groups[0].verdict == CONSERVADO
    assert ruim.e3_groups[0].verdict == NAO_VERIFICAVEL


def test_trocar_o_sujeito_troca_o_eixo_de_investimento() -> None:
    limpo = _report(publicado_e3=_E3_BOM, publicado_e4=_e4(_INVEST_LIMPO))
    sujo = _report(publicado_e3=_E3_BOM, publicado_e4=_e4(_INVEST_DUPLICADO))
    assert limpo.investment_collisions == []
    assert len(sujo.investment_collisions) == 1


def test_os_blocos_de_rubrica_mudam_integralmente_com_o_sujeito() -> None:
    """Simetria: sujeitos opostos ⇒ textos distintos nos DOIS eixos de unidade."""
    bom = format_report(_report(publicado_e3=_E3_BOM, publicado_e4=_e4(_INVEST_LIMPO)))
    ruim = format_report(_report(publicado_e3=_E3_RUIM, publicado_e4=_e4(_INVEST_DUPLICADO)))
    assert _bloco(bom, "## Eixo E3 (por grupo)") != _bloco(ruim, "## Eixo E3 (por grupo)")
    assert _bloco(bom, "## Eixo E4 (por balde)") != _bloco(ruim, "## Eixo E4 (por balde)")


def test_toda_linha_de_veredito_declara_o_substrato() -> None:
    """D2: o rótulo vai na LINHA — copy-paste para o MOC não pode perder o sujeito."""
    texto = format_report(_report(publicado_e3=_E3_BOM, publicado_e4=_e4(_INVEST_LIMPO)))
    for titulo in ("## Eixo E3 (por grupo)", "## Eixo E4 (por balde)"):
        linhas = [ln for ln in _bloco(texto, titulo).split("\n") if ln.startswith("- ")]
        assert linhas, f"bloco sem linha de veredito: {titulo}"
        assert all(ln.endswith("[entregue]") for ln in linhas), titulo


def test_sem_artefato_publicado_a_linha_diz_sombra() -> None:
    """D6: sem insumo no sujeito o eixo declara `sombra` — nunca herda calado."""
    texto = format_report(_report(publicado_e3={}, publicado_e4={}))
    linhas = [
        ln for ln in _bloco(texto, "## Eixo E4 (por balde)").split("\n") if ln.startswith("- ")
    ]
    assert all(ln.endswith("[sombra]") for ln in linhas)
