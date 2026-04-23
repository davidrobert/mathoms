"""Stage wrapper for E6 Report Rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


# Stages que `scripts.e6_render.render_report` lê de disco. Mantido aqui
# (não em stage_spec.reads) porque E6 lê muito mais do que a spec declara —
# a spec cobre dependências lógicas; isto cobre I/O real do script legado.
_E6_DISK_INPUTS = (
    "E1.5",
    "E1.5c",
    "E2-extratos",
    "E2-faturas",
    "E2-llm",
    "E3",
    "E4",
    "E5",
    "E5-revised",
    "E5.N",
)


def run(ctx: WorkspaceContext) -> dict:
    """Executa E6 rendering com contexto injetado."""
    from pipeline.stage_materialization import materialize_stages_to_root
    from scripts.e6_render import render_report

    # DBArtifactStore não escreve em disco; render_report lê disco → precisamos
    # espelhar artefatos antes de renderizar, senão HTML usa dados stale.
    materialize_stages_to_root(ctx.get_artifact_store(), ctx.root, _E6_DISK_INPUTS)

    output_path = render_report(root_dir=ctx.root)

    return {
        "success": True,
        "output_path": str(output_path) if output_path else None,
    }
