"""ADR-362 — frase de escopo derivada dos stage logs, nunca escrita à mão."""

from __future__ import annotations

from dev.run_scope import (
    executed_stages,
    mixed_execution,
    reentered_stages,
    revisions_in,
    scope_sentence,
)


def _row(stage: str, *, status: str = "completed", rev: str | None = "aaaaaaaaaaaa") -> dict:
    return {"stage": stage, "status": status, "executor_revision": rev}


def test_full_quando_nada_foi_herdado() -> None:
    frase = scope_sentence(
        incremental=False, base_run_id=None, stage_rows=[_row("reconcile"), _row("analyze")]
    )
    assert frase.startswith("escopo: full")
    assert "2 stage(s)" in frase


def test_herdado_nomeia_o_run_de_origem() -> None:
    """Mutação que mata: hardcodar `full` ⇒ a frase mente sob base_run_id."""
    frase = scope_sentence(
        incremental=False, base_run_id="4b2c8e01-dead-beef", stage_rows=[_row("analyze")]
    )
    assert "herdado do run 4b2c8e01" in frase
    assert "full" not in frase


def test_resume_nomeia_os_stages_que_reentraram() -> None:
    rows = [_row("reconcile"), _row("reconcile"), _row("analyze")]
    frase = scope_sentence(incremental=False, base_run_id=None, stage_rows=rows)
    assert "resume" in frase and "reconcile" in frase


def test_incremental_avisa_que_nao_recomputou_tudo() -> None:
    frase = scope_sentence(incremental=True, base_run_id=None, stage_rows=[_row("analyze")])
    assert "incremental" in frase
    assert "não foram recomputados" in frase


def test_resume_tem_precedencia_sobre_herdado() -> None:
    """Reentrada é o fato mais forte: descreve o loop, não a origem do dado."""
    rows = [_row("reconcile"), _row("reconcile")]
    frase = scope_sentence(incremental=True, base_run_id="abc", stage_rows=rows)
    assert frase.startswith("escopo: resume")


def test_stage_sem_terminal_nao_conta_como_computado() -> None:
    """Row `running` é crash: não afirmar que computou."""
    rows = [_row("reconcile", status="running"), _row("analyze")]
    assert executed_stages(rows) == ["analyze"]


def test_skipped_conta_como_terminal() -> None:
    rows = [_row("parecer", status="skipped_free_tier")]
    assert executed_stages(rows) == ["parecer"]


def test_execucao_mista_detecta_duas_revisoes() -> None:
    rows = [_row("reconcile", rev="aaaaaaaaaaaa"), _row("analyze", rev="bbbbbbbbbbbb")]
    assert mixed_execution(rows) is True
    assert revisions_in(rows) == ["aaaaaaaaaaaa", "bbbbbbbbbbbb"]


def test_revisao_ausente_nao_inventa_execucao_mista() -> None:
    rows = [_row("reconcile", rev=None), _row("analyze", rev=None)]
    assert mixed_execution(rows) is False
    assert revisions_in(rows) == []


def test_reentrada_ignora_stage_sem_nome() -> None:
    assert reentered_stages([{"stage": None}, {"stage": None}]) == []


def test_sem_stage_algum_nao_afirma_computo() -> None:
    frase = scope_sentence(incremental=False, base_run_id=None, stage_rows=[])
    assert "nenhum stage terminal" in frase
