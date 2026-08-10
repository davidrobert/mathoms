"""Nota one-shot de recalibração — regra de exibição (A40.l25 · ADR-360)."""
# Cada teste aqui corresponde a uma forma da nota MENTIR: afirmar movimento sem
# os dois lados, oferecer comparação de número que esta tela não publica, ou
# imprimir a probabilidade antiga (que a ADR-369 D2 declara incomparável).

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.application.report.recalibracao_note import build_recalibracao_note


@dataclass
class _Snap:
    content_json: dict[str, Any]
    period_yyyymm: str | None = "202601"


def _snap(mc_version: str | None, **bloco: Any) -> _Snap:
    corpo: dict[str, Any] = {"exibir_cone": True, "p50_ano_if": 2046, **bloco}
    if mc_version is not None:
        corpo["mc_version"] = mc_version
    return _Snap({"if_monte_carlo": corpo})


def _atual_5(**bloco: Any) -> _Snap:
    padrao = {
        "p50_ano_if": 2049,
        "prob_if_ate_prazo_declarado": 0.31,
        "prazo_declarado_anos": 20,
        "ano_alvo_declarado": 2046,
    }
    return _snap("5.0", **{**padrao, **bloco})


def test_sem_relatorio_anterior_nunca_mostra() -> None:
    assert build_recalibracao_note(None, _atual_5()) is None


def test_bloco_do_anterior_ilegivel_falha_fechada() -> None:
    """Ausência de evidência ≠ evidência de v1: sem os dois lados, cala."""
    ilegivel = _Snap({"goals": {}})
    assert build_recalibracao_note(ilegivel, _atual_5()) is None


def test_mc_version_ausente_em_bloco_legivel_dispara_como_v1() -> None:
    nota = build_recalibracao_note(_snap(None), _atual_5(period=None))
    assert nota is not None
    facetas = [f["faceta"] for f in nota["facetas"]]
    assert facetas == ["ano_cone", "probabilidade_alvo"]


def test_rename_only_nao_produz_nota() -> None:
    """3.0 → 4.0: valores idênticos, nenhuma faceta, nenhuma nota."""
    atual = _snap("4.0", p50_ano_if=2046)
    assert build_recalibracao_note(_snap("3.0"), atual) is None


def test_dois_relatorios_na_mesma_versao_nao_produzem_nota() -> None:
    anterior = _snap("5.0", p50_ano_if=2049)
    assert build_recalibracao_note(anterior, _atual_5()) is None


def test_probabilidade_antiga_nunca_aparece_no_payload() -> None:
    anterior = _snap("3.0", prob_if_ate_horizonte_simulado=0.58)
    nota = build_recalibracao_note(anterior, _atual_5())
    assert nota is not None
    serializado = repr(nota)
    assert "0.58" not in serializado
    prob = next(f for f in nota["facetas"] if f["faceta"] == "probabilidade_alvo")
    assert "prob_anterior" not in prob and "probabilidade_anterior" not in prob


def test_faceta_de_ano_some_quando_o_ano_nao_se_moveu() -> None:
    """Sem movimento visível não há inferência errada a prevenir."""
    nota = build_recalibracao_note(_snap(None, p50_ano_if=2049), _atual_5())
    assert nota is not None
    assert [f["faceta"] for f in nota["facetas"]] == ["probabilidade_alvo"]


def test_sem_cone_na_tela_a_faceta_de_ano_cala() -> None:
    nota = build_recalibracao_note(_snap(None), _atual_5(exibir_cone=False))
    assert nota is not None
    assert [f["faceta"] for f in nota["facetas"]] == ["probabilidade_alvo"]


def test_sem_prazo_declarado_a_faceta_de_probabilidade_cala() -> None:
    nota = build_recalibracao_note(_snap("3.0"), _atual_5(prob_if_ate_prazo_declarado=None))
    assert nota is None


def test_todas_as_facetas_suprimidas_nao_rende_nota() -> None:
    atual = _atual_5(exibir_cone=False, prob_if_ate_prazo_declarado=None)
    assert build_recalibracao_note(_snap(None), atual) is None


def test_competencia_igual_dispensa_a_clausula_de_atribuicao() -> None:
    """Re-run do mesmo período: a diferença é limpa, sem dado novo misturado."""
    anterior = _snap("3.0")
    anterior.period_yyyymm = "202601"
    atual = _atual_5()
    atual.period_yyyymm = "202601"
    nota = build_recalibracao_note(anterior, atual)
    assert nota is not None and nota["competencia_mudou"] is False


def test_competencia_diferente_exige_a_clausula_de_atribuicao() -> None:
    anterior = _snap("3.0")
    anterior.period_yyyymm = "202512"
    nota = build_recalibracao_note(anterior, _atual_5())
    assert nota is not None and nota["competencia_mudou"] is True
    assert nota["periodo_anterior"] == "202512"


def test_par_de_ano_carrega_os_dois_lados() -> None:
    nota = build_recalibracao_note(_snap(None), _atual_5())
    ano = next(f for f in nota["facetas"] if f["faceta"] == "ano_cone")
    assert ano["ano_anterior"] == 2046 and ano["ano_novo"] == 2049
