"""Controle positivo da guarda anti-vacuo dos cross-checks da rodada unificada.

A regra vem do §10 do `U2` (item 2) e reprovou de novo no `U3`: um check que
compara **zero** celulas e imprime ✅ — ou que imprime 647 divergencias sobre uma
intersecao vazia — nao e veredito. A guarda mora no FORMATO de saida, e um check
sem controle positivo que dispara nao pode ser confiado (§10 `U2`, item 1).
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout

import pytest

from dev._unified_xchecks.base import _cents, veredito


def _saida(n_comparado: int, n_esperado: int, divergentes: int) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        veredito("CTRL", n_comparado, n_esperado, divergentes)
    return buf.getvalue()


@pytest.mark.parametrize(
    ("n_comparado", "n_esperado", "divergentes", "esperado"),
    [
        (0, 10, 0, "INAPLICAVEL"),
        (3, 10, 0, "INAPLICAVEL"),
        (10, 10, 0, "FECHA"),
        (10, 10, 2, "DIVERGE"),
        (0, 10, 647, "INAPLICAVEL"),
    ],
)
def test_veredito_discrimina(n_comparado, n_esperado, divergentes, esperado):
    assert esperado in _saida(n_comparado, n_esperado, divergentes)


def test_vacuo_nunca_sai_verde():
    """O caso que enganou o `U3`: divergencia alta sobre populacao vazia."""
    saida = _saida(0, 1540, 647)
    assert "FECHA" not in saida and "DIVERGE" not in saida


def test_par_de_denominadores_sempre_publicado():
    """`n_comparado` e `n_esperado` na MESMA linha do veredito, em todo caso."""
    for args in ((0, 10, 0), (3, 10, 0), (10, 10, 0), (10, 10, 2)):
        saida = _saida(*args)
        assert f"n_comparado={args[0]}" in saida
        assert f"n_esperado={args[1]}" in saida


def test_cents_nao_confunde_bool_com_numero():
    assert _cents(True) is None
    assert _cents(None) is None
    assert _cents("1.23") == 123
    assert _cents(0) == 0


# ---------------------------------------------------------------------------
# X5 — poder discriminante (`PV12-04`, lane A42.l21)
#
# O predicado antigo marcava os MESMOS 3 stages em `U2`/`U3`/`U4` sob o rotulo
# unico "contrato falso": nao podia ficar verde, logo nao informava nada. Estes
# controles cobrem os dois lados — o cenario saudavel PODE sair verde, e cada
# causa que sustenta o verde e falsificavel isoladamente.
# ---------------------------------------------------------------------------

_SKIP = {"skipped": True, "reason": "No unprocessed documents for LLM extraction"}


def _cenario_saudavel() -> tuple[list, dict]:
    """Reproduz o run 7d860f0b medido no `U4`: 3 causas benignas distintas."""
    logs = [
        ("unlock_documents", "completed", {"success": True}),
        ("extract_with_llm", "completed", dict(_SKIP)),
        ("analyze_finances", "completed", {"success": True}),
        ("generate_narratives", "completed", {"success": True}),
        ("validate_cross", "completed", {"success": True}),
    ]
    return logs, {"analyze_finances": 1}


def _classes(diag: dict) -> dict[str, str]:
    return {linha[0]: linha[4] for linha in diag["linhas"]}


def test_fixture_separa_as_tres_causas():
    """Antes do gate: a fixture DISCRIMINA. Colapsar estas 3 em 1 era o PV12-04."""
    from dev._unified_xchecks.execucao import classificar

    classes = _classes(classificar(*_cenario_saudavel()))
    tres = [classes[s] for s in ("extract_with_llm", "generate_narratives", "validate_cross")]
    assert len(set(tres)) == 3, tres


def test_cenario_saudavel_pode_sair_verde():
    """O que o check antigo nao conseguia: ausencia de ofensor."""
    from dev._unified_xchecks.execucao import classificar

    diag = classificar(*_cenario_saudavel())
    assert diag["ofensores"] == {} and diag["vencidas"] == {}
    assert diag["n_comparado"] == diag["n_esperado"] > 0
    assert "FECHA" in _saida(diag["n_comparado"], diag["n_esperado"], 0)


def test_quarto_ofensor_aparece_nomeado():
    """CONTROLE POSITIVO da lane: stage que promete artefato e nao entrega."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    logs.append(("extract_statements", "completed", {"success": True}))
    diag = classificar(logs, por_stage)
    assert "extract_statements" in diag["ofensores"]
    assert "DIVERGE" in _saida(diag["n_comparado"], diag["n_esperado"], len(diag["ofensores"]))


def test_sem_carimbo_de_skip_o_mesmo_stage_reprova():
    """O ramo do skip e load-bearing: tirar o carimbo vira ofensor."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    logs[1] = ("extract_with_llm", "completed", {"success": True})
    assert "extract_with_llm" in classificar(logs, por_stage)["ofensores"]


def _ler_mutado(alvo: str, fonte: str):
    """Leitor que substitui a fonte de UM arquivo e delega o resto ao real."""
    from dev._unified_xchecks.execucao import _ler_fonte

    return lambda rel: fonte if alvo in rel else _ler_fonte(rel)


def test_read_only_com_write_na_fonte_vence_a_dispensa():
    """Se `validate_cross` ganhar writer, a dispensa deixa de valer."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    ler = _ler_mutado("validate_cross", "store.write('validate_cross', k, v)\n")
    assert "validate_cross" in classificar(logs, por_stage, ler=ler)["vencidas"]


def test_redirecao_para_outro_alvo_vence_a_dispensa():
    """A declaracao nomeia `analyze_finances`; fonte que escreve noutro lugar reprova."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    ler = _ler_mutado("generate_narratives", "store.write('outra_key', k, v)\n")
    assert "generate_narratives" in classificar(logs, por_stage, ler=ler)["vencidas"]


def test_redirecao_sem_artefato_no_alvo_vence_a_dispensa():
    """Fonte certa, run vazio: o merge nao aconteceu neste run."""
    from dev._unified_xchecks.execucao import classificar

    logs, _ = _cenario_saudavel()
    assert "generate_narratives" in classificar(logs, {})["vencidas"]


def test_dispensa_de_stage_que_produziu_artefato_proprio_esta_vencida():
    """Igualdade de conjunto no outro sentido: a dispensa deixou de ser necessaria."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    por_stage["validate_cross"] = 1
    assert "validate_cross" in classificar(logs, por_stage)["vencidas"]


def test_evidencia_ilegivel_nao_sai_verde():
    """Ausencia nao se prova com arquivo sumido — instrumento quebrado e INAPLICAVEL."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    diag = classificar(logs, por_stage, ler=lambda _rel: None)
    assert diag["n_comparado"] < diag["n_esperado"]
    assert "INAPLICAVEL" in _saida(diag["n_comparado"], diag["n_esperado"], 0)


def test_declaracao_bate_com_a_fonte_real():
    """`literal == sistema`: o ground truth e autorado, o cross-check e que mede."""
    from dev._unified_xchecks.execucao import DISPENSAS, _ler_fonte, _viola

    for stage, d in DISPENSAS.items():
        src = _ler_fonte(d.evidencia)
        assert src is not None, f"{stage}: evidencia sumiu ({d.evidencia})"
        alvo = {d.escreve_em: 1} if d.escreve_em else {}
        assert _viola(d, src, alvo) is None, f"{stage}: {_viola(d, src, alvo)}"


def test_fonte_sumida_le_None_e_nao_string_vazia():
    """A armadilha da dispensa READ-ONLY: ela afirma AUSENCIA de write, e ""
    tem zero writes. Arquivo sumido tem de virar `None` (⇒ INDETERMINADO),
    nunca fonte vazia que satisfaz a declaracao de graca."""
    from dev._unified_xchecks.execucao import _ler_fonte

    assert _ler_fonte("scripts/nao_existe_este_arquivo_xyz.py") is None
    assert _ler_fonte("scripts/validate_cross.py")


def test_zero_trabalho_na_outra_grafia_tambem_e_benigno():
    """5 dos 25 runs do dogfood saem por aqui: sem `skipped`, com `total_processed: 0`."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    logs[1] = ("extract_with_llm", "completed", {"success": True, "total_processed": 0})
    diag = classificar(logs, por_stage)
    assert diag["ofensores"] == {}
    assert _classes(diag)["extract_with_llm"] == "SEM-TRABALHO"


def test_zero_processado_com_erro_nao_e_zero_trabalho():
    """`total_processed: 0` com erros nao e "nada a fazer" — e nao entregar."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    logs[1] = ("extract_with_llm", "completed", {"total_processed": 0, "total_errors": 3})
    assert "extract_with_llm" in classificar(logs, por_stage)["ofensores"]
