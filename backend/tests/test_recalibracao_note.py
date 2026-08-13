"""Nota one-shot de recalibração — regra de exibição (A40.l25 · ADR-360)."""
# Cada teste aqui corresponde a uma forma da nota MENTIR: afirmar movimento sem
# os dois lados, oferecer comparação de número que esta tela não publica, ou
# imprimir a probabilidade antiga (que a ADR-369 D2 declara incomparável).
#
# O lado ATUAL do par sai do PRODUTOR REAL (`monte_carlo_to_dict` sobre uma
# simulação de verdade), nunca de um dict escrito à mão. A versão anterior desta
# suíte fabricava `p50_ano_if` nos dois lados e por isso passava enquanto a nota
# estava inerte em produção: a chave morreu no rename de `mc_version` 4.0
# (ADR-369 D3) e o código lia só ela. Teste e código compartilhavam a crença
# errada — fixture que inventa o payload não é gate.
#
# O lado ANTERIOR pode ser um bloco histórico congelado, porque o produtor
# daquelas chaves não existe mais; ele está rotulado como tal.

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from backend.app.application.report.recalibracao_note import build_recalibracao_note
from pipeline.domain.services.if_monte_carlo import (
    IFMonteCarloConfig,
    PrazoDeclarado,
    run_monte_carlo_if,
)
from pipeline.domain.services.if_monte_carlo_payload import monte_carlo_to_dict

_PRAZO = PrazoDeclarado(anos=20, ano_alvo=2046, declarado_em="2026-01-15")


@dataclass
class _Snap:
    content_json: dict[str, Any]
    period_yyyymm: str | None = "202601"


def _bloco_do_produtor(patrimonio: str) -> dict[str, Any]:
    """Bloco `if_monte_carlo` como o pipeline de HOJE o grava."""
    config = IFMonteCarloConfig(
        patrimonio_investivel=Decimal(patrimonio),
        meta_if=Decimal("1000000"),
        retorno_real_esperado=0.06,
        aporte_mensal=Decimal("5000"),
    )
    return monte_carlo_to_dict(run_monte_carlo_if(config, ano_base=2026, prazo_declarado=_PRAZO))


def _atual(mc_version: str = "5.0", *, patrimonio: str = "400000", **override: Any) -> _Snap:
    corpo = {**_bloco_do_produtor(patrimonio), "mc_version": mc_version, **override}
    return _Snap({"if_monte_carlo": corpo})


def _ano_de(snap: _Snap) -> int:
    return snap.content_json["if_monte_carlo"]["ano_if_cenario_central"]


# Bloco do cone como um artefato PRÉ-4.0 real o gravou. Espelha
# `tests/test_e5n_cone_compat_mc_version.py::_bloco_v3`; congelado de propósito,
# porque é o lado do par que a base ainda guarda e que nenhum produtor atual
# reproduz (backfill descartado — ADR-369 D4).
_BLOCO_LEGADO_PRE_4_0: dict[str, Any] = {
    "p10_ano_if": 2039,
    "p10_censurado": False,
    "p50_ano_if": 2046,
    "p50_censurado": False,
    "p90_ano_if": 2058,
    "p90_censurado": False,
    "prob_if_ate_idade_meta": 0.31,
    "prob_if_ate_horizonte": 0.58,
    "idade_meta_usada": 65,
    "sigma_usado": 0.11,
    "exibir_cone": True,
    "seed_usado": 360,
    "n_simulacoes_usado": 50_000,
    "horizonte_anos": 40,
}


def _anterior_legado(mc_version: str | None, **override: Any) -> _Snap:
    """Snapshot com o bloco pré-4.0; `mc_version=None` é o artefato v1 sem carimbo."""
    corpo = {**_BLOCO_LEGADO_PRE_4_0, **override}
    if mc_version is not None:
        corpo["mc_version"] = mc_version
    return _Snap({"if_monte_carlo": corpo})


def _facetas(nota: dict[str, Any] | None) -> list[str]:
    return [f["faceta"] for f in (nota or {}).get("facetas", [])]


# --- o defeito que esta suíte não pegava -----------------------------------


def test_faceta_do_ano_renderiza_sobre_o_payload_do_produtor() -> None:
    """Regressão: a chave do ano tem de ser a que o pipeline de hoje EMITE."""
    # Com `p50_ano_if` no lugar de `ano_if_cenario_central`, o lado atual vinha
    # `None` e esta faceta — o motivo da nota existir — nunca chegava à tela.
    anterior, atual = _anterior_legado(None), _atual()
    nota = build_recalibracao_note(anterior, atual)
    assert nota is not None
    assert "ano_cone" in _facetas(nota)


def test_o_leitor_do_ano_acha_o_ano_no_bloco_do_produtor() -> None:
    """Rename futuro do cone falha aqui, alto, em vez de calar a nota."""
    # Behavioral e não introspectivo: asserir a constante contra si mesma seria
    # tautologia. Aqui o leitor de produção corre sobre o payload de produção.
    from backend.app.application.report.recalibracao_note import _ano_cone

    assert _ano_cone(_bloco_do_produtor("400000")) is not None


def test_par_2_0_para_5_0_le_os_dois_lados_do_rename() -> None:
    """Chave antiga à esquerda, chave de hoje à direita, e o ano se moveu no meio."""
    # 2.0 e não 3.0: o ledger só move `ano_cone` até o major 3, então um par
    # 3.0→5.0 não deve render essa faceta — quem tinha 3.0 já viu aquele ano.
    # A instância que atravessa o rename E move o ano começa em v1 ou 2.0.
    atual = _atual()
    nota = build_recalibracao_note(_anterior_legado("2.0"), atual)
    ano = next(f for f in nota["facetas"] if f["faceta"] == "ano_cone")
    assert ano["ano_anterior"] == 2046 and ano["ano_novo"] == _ano_de(atual)


def test_par_3_0_para_5_0_nao_reoferece_o_ano_ja_visto() -> None:
    """Só a faceta que ESTE par moveu — o ano de 3.0 é o mesmo de 5.0."""
    nota = build_recalibracao_note(_anterior_legado("3.0"), _atual())
    assert _facetas(nota) == ["probabilidade_alvo"]


# --- falha fechada em ausência de evidência --------------------------------


def test_sem_relatorio_anterior_nunca_mostra() -> None:
    assert build_recalibracao_note(None, _atual()) is None


def test_bloco_do_anterior_ilegivel_falha_fechada() -> None:
    """Ausência de evidência ≠ evidência de v1: sem os dois lados, cala."""
    ilegivel = _Snap({"goals": {}})
    assert build_recalibracao_note(ilegivel, _atual()) is None


def test_mc_version_ausente_em_bloco_legivel_dispara_como_v1() -> None:
    nota = build_recalibracao_note(_anterior_legado(None), _atual())
    assert _facetas(nota) == ["ano_cone", "probabilidade_alvo"]


# --- supressão por par e por faceta ----------------------------------------


def test_rename_only_nao_produz_nota() -> None:
    """3.0 → 4.0: valores idênticos, nenhuma faceta, nenhuma nota."""
    assert build_recalibracao_note(_anterior_legado("3.0"), _atual("4.0")) is None


def test_dois_relatorios_na_mesma_versao_nao_produzem_nota() -> None:
    assert build_recalibracao_note(_atual(patrimonio="300000"), _atual()) is None


def test_faceta_de_ano_some_quando_o_ano_nao_se_moveu() -> None:
    """Sem movimento visível não há inferência errada a prevenir."""
    atual = _atual()
    anterior = _anterior_legado(None, p50_ano_if=_ano_de(atual))
    assert _facetas(build_recalibracao_note(anterior, atual)) == ["probabilidade_alvo"]


def test_sem_cone_na_tela_a_faceta_de_ano_cala() -> None:
    nota = build_recalibracao_note(_anterior_legado(None), _atual(exibir_cone=False))
    assert _facetas(nota) == ["probabilidade_alvo"]


def test_sem_prazo_declarado_a_faceta_de_probabilidade_cala() -> None:
    atual = _atual(prob_if_ate_prazo_declarado=None)
    assert build_recalibracao_note(_anterior_legado("3.0"), atual) is None


def test_todas_as_facetas_suprimidas_nao_rende_nota() -> None:
    atual = _atual(exibir_cone=False, prob_if_ate_prazo_declarado=None)
    assert build_recalibracao_note(_anterior_legado(None), atual) is None


# --- o número antigo da probabilidade nunca é publicado --------------------


def test_probabilidade_antiga_nunca_aparece_no_payload() -> None:
    nota = build_recalibracao_note(_anterior_legado("3.0"), _atual())
    assert nota is not None
    assert "0.58" not in repr(nota)
    prob = next(f for f in nota["facetas"] if f["faceta"] == "probabilidade_alvo")
    assert "prob_anterior" not in prob and "probabilidade_anterior" not in prob


# --- cláusula de atribuição dado↔modelo ------------------------------------


def test_competencia_igual_dispensa_a_clausula_de_atribuicao() -> None:
    """Re-run do mesmo período: a diferença é limpa, sem dado novo misturado."""
    anterior = _anterior_legado("3.0")
    anterior.period_yyyymm = "202601"
    atual = _atual()
    atual.period_yyyymm = "202601"
    nota = build_recalibracao_note(anterior, atual)
    assert nota is not None and nota["competencia_mudou"] is False


def test_competencia_diferente_exige_a_clausula_de_atribuicao() -> None:
    anterior = _anterior_legado("3.0")
    anterior.period_yyyymm = "202512"
    nota = build_recalibracao_note(anterior, _atual())
    assert nota is not None and nota["competencia_mudou"] is True
    assert nota["periodo_anterior"] == "202512"


def test_par_de_ano_carrega_os_dois_lados() -> None:
    atual = _atual()
    nota = build_recalibracao_note(_anterior_legado(None), atual)
    ano = next(f for f in nota["facetas"] if f["faceta"] == "ano_cone")
    assert ano["ano_anterior"] == 2046 and ano["ano_novo"] == _ano_de(atual)
