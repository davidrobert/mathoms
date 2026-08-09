"""Bloco de proveniência do `run_meta.md`, em prosa — o entregável da ADR-362.

Morava em `.claude/skills/pipeline-review/scripts/collect_review_inputs.py`, onde
nenhuma suíte alcança: três critérios de aceite da A40.l32 falam do que o
**entregável** afirma ("reporta as duas revisões", "diz `desconhecido` em
destaque", "nomeia o run de origem") e as três mutações correspondentes
sobreviviam verdes. Mesmo movimento que o helper de duração fez para `dev/`.

Derivação pura fica em `run_scope`; aqui é só redação.
"""

from __future__ import annotations

from dev.build_info import ancestry, commits_ahead_of
from dev.run_scope import (
    mixed_execution,
    partial_attribution,
    revisions_in,
    scope_sentence,
    unknown_revision_count,
)

UNKNOWN_EXECUTOR = (
    "- executor: **desconhecido** — nenhum stage declarou revisão. Causa provável: "
    "run anterior a 2026-08-05 (a coluna não existia e não há backfill, por decisão "
    "da ADR-362), ou processo subiu sem `MATHOMS_BUILD_SHA`."
)
MIXED_EXECUTION = (
    "- ⚠️ **execução mista**: o run atravessou mais de uma revisão — "
    "stages diferentes rodaram códigos diferentes"
)
NO_REPRODUCIBILITY = (
    "- reprodutibilidade: **NÃO garantida**. Mesmo executor pode produzir output "
    "diferente — o parecer roda com temperature 0,1 e cache de 7 dias; câmbio, "
    "parâmetros fiscais e regras de categorização vivem em DB e mudam sem commit."
)


def executor_line(revs: list[str]) -> str:
    """Ausência é linha em destaque, nunca linha faltando; mista lista TODAS."""
    if not revs:
        return UNKNOWN_EXECUTOR
    return f"- executor: `{revs[0] if len(revs) == 1 else ', '.join(revs)}`"


def ancestry_line(revs: list[str]) -> str:
    """Responde "a main andou desde o run?" — ausência nunca colapsa em zero."""
    rev = revs[0] if revs else None
    ahead = commits_ahead_of(rev) if rev else None
    sufixo = f" ({ahead} commit(s) à frente)" if ahead else ""
    return f"- relação com o HEAD atual: **{ancestry(rev)}**{sufixo}"


def partial_attribution_line(stage_rows: list[dict]) -> str:
    return (
        f"- ⚠️ **atribuição parcial**: {unknown_revision_count(stage_rows)} stage(s) "
        "sem revisão declarada — a revisão acima não cobre o run inteiro"
    )


def provenance_lines(run: dict, stage_rows: list[dict]) -> list[str]:
    """Bloco de proveniência do `run_meta.md` — em prosa, não `repr()` de dict."""
    revs = revisions_in(stage_rows)
    escopo = scope_sentence(
        incremental=run.get("incremental"),
        base_run_id=run.get("base_run_id"),
        stage_rows=stage_rows,
    )
    lines = [executor_line(revs), f"- {escopo}", ancestry_line(revs)]
    if mixed_execution(stage_rows):
        lines.append(MIXED_EXECUTION)
    if partial_attribution(stage_rows):
        lines.append(partial_attribution_line(stage_rows))
    return lines + [NO_REPRODUCIBILITY]


def provenance_context(run: dict, stage_rows: list[dict]) -> dict:
    """Contexto top-level do snapshot — nunca supressor, nunca perna de regressão."""
    revs = revisions_in(stage_rows)
    return {
        "executor_revision": revs[0] if len(revs) == 1 else None,
        "executor_revisions": revs,
        "execucao_mista": mixed_execution(stage_rows),
        "atribuicao_parcial": partial_attribution(stage_rows),
        "ancestry": ancestry(revs[0] if revs else None),
        "commits_ahead": commits_ahead_of(revs[0]) if revs else None,
        "escopo": {
            "base_run_id": run.get("base_run_id"),
            "incremental": bool(run.get("incremental")),
            "stages_terminais": len({r.get("stage") for r in stage_rows if r.get("stage")}),
        },
    }
