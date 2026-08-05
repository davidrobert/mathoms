#!/usr/bin/env python3
"""Escopo de um run, DERIVADO dos stage logs — nunca escrito à mão (ADR-362).

Afirmar "este run computou E3→E5 neste código" é **falso** sob `base_run_id`, e
afirmar escopo errado com autoridade é pior que não afirmar. Aqui tudo sai de
colunas que existem: os stage logs do run (com `executor_revision`), mais
`base_run_id`/`incremental` do próprio run.

O que este módulo NÃO pode dizer: `from_stage` **não é persistido** (vive só em
log estruturado), então o ponto de partida não é nomeável a partir do DB.
"""

from __future__ import annotations

_DONE = frozenset({"completed", "skipped", "skipped_free_tier"})


def _status_of(row: dict) -> str:
    status = row.get("status")
    return getattr(status, "value", status) or ""


def executed_stages(stage_rows: list[dict]) -> list[str]:
    """Stages que de fato atingiram estado terminal de sucesso neste run."""
    seen: list[str] = []
    for row in stage_rows:
        if _status_of(row) in _DONE and row.get("stage") not in seen:
            seen.append(row["stage"])
    return seen


def revisions_in(stage_rows: list[dict]) -> list[str]:
    """Revisões distintas que executaram stages deste run, em ordem de aparição."""
    out: list[str] = []
    for row in stage_rows:
        rev = row.get("executor_revision")
        if rev and rev not in out:
            out.append(rev)
    return out


def reentered_stages(stage_rows: list[dict]) -> list[str]:
    """Stages com mais de uma execução — resume ou redelivery do Celery."""
    counts: dict[str, int] = {}
    for row in stage_rows:
        stage = row.get("stage")
        if stage:
            counts[stage] = counts.get(stage, 0) + 1
    return sorted(s for s, n in counts.items() if n > 1)


def mixed_execution(stage_rows: list[dict]) -> bool:
    """Derivado, nunca armazenado: o run atravessou mais de uma revisão."""
    return len(revisions_in(stage_rows)) > 1


def scope_kind(*, incremental: object, base_run_id: object, stage_rows: list[dict]) -> str:
    if reentered_stages(stage_rows):
        return "resume"
    if base_run_id:
        return "herdado"
    if incremental:
        return "incremental"
    return "full"


def scope_sentence(*, incremental: object, base_run_id: object, stage_rows: list[dict]) -> str:
    """Uma linha honesta sobre o que este run computou de fato."""
    kind = scope_kind(incremental=incremental, base_run_id=base_run_id, stage_rows=stage_rows)
    stages = executed_stages(stage_rows)
    corpo = f"{len(stages)} stage(s) computado(s) neste run" if stages else "nenhum stage terminal"
    if kind == "resume":
        alvo = ", ".join(reentered_stages(stage_rows))
        return f"escopo: resume — o loop reentrou em [{alvo}]; {corpo}"
    if kind == "herdado":
        return f"escopo: herdado do run {str(base_run_id)[:8]} — {corpo}; upstream veio de lá"
    if kind == "incremental":
        return f"escopo: incremental — {corpo}; stages não listados não foram recomputados"
    return f"escopo: full — {corpo}"
