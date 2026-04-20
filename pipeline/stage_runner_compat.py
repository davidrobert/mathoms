"""Helper para "Caminho A" durante a Fase 3: rodar script legado com o bridge.

Uso pelos wrappers de stage:

    def run(ctx: WorkspaceContext) -> dict:
        from pipeline.stage_runner_compat import run_legacy_with_bridge_if_db
        return run_legacy_with_bridge_if_db(
            ctx, stage="E3",
            legacy_runner=lambda root: e3_main(root_dir=root),
            collect=lambda root: {"files": [...]},
        )

Se o ``ArtifactStore`` ativo é um :class:`DiskArtifactStore`, o script roda com
``root_dir=ctx.root`` direto (comportamento legado). Se é DB-backed (detectado
pela presença da pipeline_run_id e da absence do DiskArtifactStore), o bridge
hidrata inputs, roda o script em ``tmp_dir`` e persiste outputs.

Remoção prevista: Fase 9 (``MaterializationBridge`` eliminado).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from pipeline.artifact_store import DiskArtifactStore

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


LegacyRunner = Callable[[Path], None]
DetailCollector = Callable[[Path], dict]


def run_legacy_with_bridge_if_db(
    ctx: "WorkspaceContext",
    *,
    stage: str,
    legacy_runner: LegacyRunner,
    collect: Optional[DetailCollector] = None,
) -> dict:
    """Executa ``legacy_runner(root_dir)`` via bridge quando o store é DB-backed.

    Args:
        ctx: contexto do pipeline (provê ``get_artifact_store`` e
             ``pipeline_run_id``).
        stage: identificador legado do stage (ex: ``"E3"``, ``"E4"``).
        legacy_runner: função que roda o script legado. Recebe o ``root_dir``
            a usar — o script deve ler/escrever em ``root_dir/processed/...``.
        collect: callback opcional para montar o dict de ``detail`` após a run.
            Recebe o mesmo ``root_dir`` usado no ``legacy_runner``. Se ``None``,
            retorna apenas ``{"success": True}``.

    Returns:
        Dict com resultado (``success``, ``detail`` customizado).
    """
    store = ctx.get_artifact_store()
    if isinstance(store, DiskArtifactStore):
        legacy_runner(ctx.root)
        detail = collect(ctx.root) if collect else {}
        return {"success": True, **detail}

    # DB-backed path: usa o bridge
    from pipeline.materialization_bridge import MaterializationBridge

    run_id = ctx.pipeline_run_id
    if not run_id:
        raise RuntimeError(
            f"Stage '{stage}' com ArtifactStore não-disco requer "
            f"ctx.pipeline_run_id para instanciar MaterializationBridge"
        )

    with MaterializationBridge(store, pipeline_run_id=run_id) as bridge:
        root_dir = bridge.hydrate_for_stage(stage)
        legacy_runner(root_dir)
        persisted = bridge.persist_from_stage(stage)
        detail: dict = {"bridge_persisted": persisted}
        if collect:
            detail.update(collect(root_dir))
        return {"success": True, **detail}
