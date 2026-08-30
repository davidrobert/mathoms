"""Travas de retenção do E3 ([[ADR-364]] §Emenda 2026-08-09, [[A40.l2]] §3d).

A janela TOCTOU e os contadores publicados. Cada teste nomeia a mutação que o derruba —
sem isso a trava vira decoração, que é como a lane chegou aqui quatro vezes.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pipeline.domain.services.cross_document_collapse_types import (
    CANAL_COLAPSO,
    CollapseCandidate,
    CollapseMeasurement,
    CollapseRemoval,
    OverrideRetentionGuard,
    ProximityCandidate,
    RetencaoInstavel,
)
from scripts.reconcile_transactions import (
    _e3_collapse_retention,
    _e3_revalida_retencao,
)

_STAGE = Path(__file__).resolve().parents[3] / "scripts" / "reconcile_transactions.py"


class _Result:
    def __init__(self, measurement, removals=()):
        self.collapse_measurement = measurement
        self.removals = removals


def _candidato(
    gate: str, *, colapsavel: bool = True, origens: tuple[str, ...] = ("manual",)
) -> CollapseCandidate:
    return CollapseCandidate(
        key_digest=f"k-{gate}",
        gate_digest=gate,
        mes="2026-01",
        valor_cents=1000,
        moeda="BRL",
        direction="out",
        removal_targets=(),
        blocked_reason=None,
        n_rows=2,
        n_provenances=2,
        survivor_cardinality=1,
        removable_rows=1,
        retido_por_override=not colapsavel,
        retido_por_sources=() if colapsavel else origens,
    )


def _proximo() -> ProximityCandidate:
    return ProximityCandidate(
        mes="2025-10",
        valor_cents=1000,
        moeda="BRL",
        direction="out",
        datas=("2025-10-26", "2025-10-27"),
        delta_dias=1,
        n_rows=2,
        n_provenances=2,
    )


def _corte(n: int = 1) -> tuple[CollapseRemoval, ...]:
    return (
        CollapseRemoval(
            canal=CANAL_COLAPSO,
            count=n,
            valor_cents=-1000,
            cross_source_count=n,
            source="x",
            meses=(("2026-01", n),),
        ),
    )


def _guard(*, denied=(), lido=True) -> OverrideRetentionGuard:
    return OverrideRetentionGuard(
        denied_digests=frozenset(denied),
        overrides_ativos=len(denied),
        sem_snapshot=0,
        denied_por_source={"manual": len(denied)} if denied else {},
        lido=lido,
    )


def _instala_guard(monkeypatch, guard) -> None:
    monkeypatch.setattr(
        "scripts.reconcile_transactions._e3_retention_guard", lambda ctx, store: guard
    )


def test_override_criado_durante_o_stage_sobre_chave_cortada_derruba_o_run(monkeypatch):
    """Mutação: trocar o `raise` por um log — o artefato commitaria com o override destruído."""
    _instala_guard(monkeypatch, _guard(denied=["g1"]))
    result = _Result(CollapseMeasurement(candidates=(_candidato("g1"),)), _corte())

    with pytest.raises(RetencaoInstavel, match="1 override"):
        _e3_revalida_retencao(None, None, result)


# Mutação: levantar aqui também — derrubaria run de sombra por override concorrente, que é
# ruído puro. Mutação inversa: devolver `False` — o gate do flip (§3e) aceitaria como base um
# run cuja medição já estava velha no instante em que foi escrita.
def test_na_sombra_o_run_segue__mas_a_instabilidade_fica_publicada(monkeypatch):
    """Sem corte publicado nada foi destruído: só a predição envelheceu."""
    _instala_guard(monkeypatch, _guard(denied=["g1"]))
    result = _Result(CollapseMeasurement(candidates=(_candidato("g1"),)))

    guard, instavel = _e3_revalida_retencao(None, None, result)

    assert instavel is True
    assert _e3_collapse_retention(result, guard, instavel=instavel)["retencao_instavel"] is True


# Mutação: fazer `nao_lido()` devolver digests parciais (uma leitura que falhou no meio). A
# interseção passaria a ser não-vazia sobre leitura incompleta, e a ausência da guarda `lido`
# em `_e3_revalida_retencao` — hoje dispensável — viraria licença para cortar.
def test_nao_lido_nasce_sem_digests__e_por_isso_o_toctou_dispensa_guarda():
    """`nao_lido()` não carrega digest nenhum: a interseção é vazia por construção."""
    assert OverrideRetentionGuard.nao_lido().denied_digests == frozenset()


def test_chave_ja_retida_nao_conta_como_invadida(monkeypatch):
    """O candidato retido não está no conjunto cortado — acusá-lo derrubaria todo run em
    que a retenção FUNCIONOU. Mutação: trocar `sera_colapsado` por `collapsible`."""
    _instala_guard(monkeypatch, _guard(denied=["g1"]))
    result = _Result(
        CollapseMeasurement(candidates=(_candidato("g1", colapsavel=False),)), _corte()
    )

    _g, instavel = _e3_revalida_retencao(None, None, result)

    assert instavel is False


def test_contadores_distinguem_zero_medido_de_nao_medido():
    """Sem `lido` no payload, "0 retido" e "não consegui ler" imprimem o mesmo caractere."""
    medido = _e3_collapse_retention(
        _Result(CollapseMeasurement(candidates=(_candidato("g1"),))), _guard(), instavel=False
    )

    assert medido["lido"] is True and medido["retido_por_override"] == 0
    assert (
        _e3_collapse_retention(_Result(CollapseMeasurement()), _guard(lido=False), instavel=False)
        is None
    )


def test_run_so_com_proximidade_ainda_publica_o_numero():
    """A classe D±1 vive onde a chave day-exact NÃO forma grupo — `candidates` vazia."""
    # Sem a cláusula de `proximidade_d1` na guarda de early-return, o payload voltaria
    # `None` exatamente no run que a [[A40.l102]] foi medir, e o número que justifica a
    # lane nunca chegaria ao `output_summary`. Guarda que suprime o único sinal do run
    # é a forma sutil do zero-ambíguo que esta lane já pagou.
    result = _Result(CollapseMeasurement(proximidade_d1=(_proximo(),)))

    payload = _e3_collapse_retention(result, _guard(lido=False), instavel=False)

    assert payload is not None
    assert payload["candidatos"] == 0  # a passada principal não viu nada...
    assert payload["proximidade_d1"]["candidatos"] == 1  # ...e a classe D±1 viu
    assert payload["proximidade_d1"]["rows"] == 2
    # Tamanho do risco, não remoção planejada: nada nesta classe tem alvo.
    assert payload["proximidade_d1"]["cents_em_risco"] == 1000


def test_contadores_expoem_o_denominador_e_o_preditor():
    result = _Result(
        CollapseMeasurement(
            candidates=(_candidato("g1"), _candidato("g2", colapsavel=False)),
            reservatorio_llm_sem_gemea=17,
        ),
        _corte(3),
    )

    payload = _e3_collapse_retention(result, _guard(denied=["g2"]), instavel=False)

    assert payload["candidatos"] == 2 and payload["colapsaveis"] == 1
    assert payload["retido_por_override"] == 1
    assert payload["reservatorio_llm_sem_gemea"] == 17
    assert payload["removals_publicadas"] == 1


def _corpo_do_stage() -> list[ast.stmt]:
    arvore = ast.parse(_STAGE.read_text(encoding="utf-8"))
    fn = next(
        n
        for n in ast.walk(arvore)
        if isinstance(n, ast.FunctionDef) and n.name == "main_with_store"
    )
    return fn.body


def _indice_da_chamada(corpo: list[ast.stmt], nome: str) -> int:
    for i, stmt in enumerate(corpo):
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == nome:
                    return i
    return -1


# Foi assim que a atribuição por grupo (§3c1c) passou 13 testes enquanto o call-site estava
# revertido. A ordem importa: revalidar ANTES de reconciliar leria o guard velho.
def test_o_stage_revalida_logo_apos_reconciliar__nao_so_a_funcao_isolada():
    """AST do call-site: os testes acima passam verdes com a chamada removida do stage."""
    corpo = _corpo_do_stage()
    reconcilia = _indice_da_chamada(corpo, "_e3_run_reconciliation")
    revalida = _indice_da_chamada(corpo, "_e3_revalida_retencao")

    assert reconcilia >= 0, "call-site da reconciliação sumiu — o teste passaria por vacuidade"
    assert revalida > reconcilia, "stage não revalida o guard depois de reconciliar"


def test_o_stage_publica_os_contadores_no_output_summary():
    """Mutação: apagar o `detail["collapse_retention"] = ...` — a série que a ADR-364 §5
    promove a gatilho de rollback nunca chegaria ao `pipeline_stage_logs`."""
    fonte = _STAGE.read_text(encoding="utf-8")

    assert _indice_da_chamada(_corpo_do_stage(), "_e3_collapse_retention") >= 0
    assert '"collapse_retention"' in fonte


# O passo (1) da ordem de construção da re-ancoragem ([[ADR-364]] §Emenda 2026-08-09) compara
# `retido[rule]` contra `retido[manual]`. Sem estes dois contadores ele é indecidível — foi o
# desvio que o PR do 3d publicou (agregado + `denied_por_source`) e que este PR quita.
def test_contadores_separam_a_origem_da_retencao():
    """Mutação: emitir só o agregado. O passo (1) volta a não ter instrumento."""
    result = _Result(
        CollapseMeasurement(
            candidates=(
                _candidato("g1", colapsavel=False, origens=("rule",)),
                _candidato("g2", colapsavel=False, origens=("manual",)),
                _candidato("g3", colapsavel=False, origens=("manual", "rule")),
                _candidato("g4"),
            )
        )
    )

    payload = _e3_collapse_retention(result, _guard(denied=["g1", "g2", "g3"]), instavel=False)

    assert payload["retido_por_override"] == 3
    assert payload["retido_por_override_rule"] == 2
    assert payload["retido_por_override_manual"] == 2


# Mutação: somar como partição (`manual` = total − `rule`). O passo (1) leria
# `retido[manual] = 1` onde há 2, e desligaria `source='rule'` sobre comparação errada.
def test_chave_negada_por_DUAS_origens_conta_nos_dois():
    """Não são partições: uma chave editada à mão E coberta por regra pertence às duas."""
    result = _Result(
        CollapseMeasurement(
            candidates=(_candidato("g1", colapsavel=False, origens=("manual", "rule")),)
        )
    )

    payload = _e3_collapse_retention(result, _guard(denied=["g1"]), instavel=False)

    assert payload["retido_por_override"] == 1
    assert payload["retido_por_override_manual"] == payload["retido_por_override_rule"] == 1
