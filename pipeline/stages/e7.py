"""Stage wrapper for E7 Review & Cross-validation (ADR-097).

Chama ``scripts.e7_review.main_with_store(ctx, mode=...)`` direto. Dois
modos determinísticos:

- ``run_crossval(ctx)`` — 14 checks CV1-CV14 + gera template para LLM em
  ``processed/E7_review/e7_review_template.json``.
- ``run_apply(ctx, review_path)`` — aplica review LLM ao E5 (grava E5
  atualizado via ``ArtifactStore``); skip gracioso se ``review_path``
  ausente + sem template no workspace (free tier, sem LLM).

O modo ``E7-review`` (LLM) **não migra** — é passo humano/externo, não
determinístico.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run_crossval(ctx: "WorkspaceContext") -> dict:
    from scripts.e7_review import main_with_store

    result = main_with_store(ctx, mode="crossval")
    result["stage"] = "E7-crossval"
    return result


def run_apply(ctx: "WorkspaceContext", review_path: str = None) -> dict:
    """Aplica review LLM ao E5.

    Skip gracioso quando:
    - `review_path` não fornecido, E
    - não existe template E7-review no workspace (free tier, sem LLM).
    """
    from pipeline.artifact_store import DiskArtifactStore

    store = ctx.get_artifact_store()
    if not review_path:
        if isinstance(store, DiskArtifactStore):
            review_dir = ctx.root / "processed" / "E7_review"
            if not review_dir.exists() or not list(review_dir.glob("*.json")):
                return {
                    "success": True,
                    "skipped": True,
                    "reason": "No E7-review output — E7-review not run (free tier)",
                    "stage": "E7-apply",
                }
        else:
            if not store.list_keys("E7-review"):
                return {
                    "success": True,
                    "skipped": True,
                    "reason": "No E7-review artifact — E7-review not run (free tier)",
                    "stage": "E7-apply",
                }

    from scripts.e7_review import main_with_store

    result = main_with_store(ctx, mode="apply", review_path=review_path)
    result["stage"] = "E7-apply"
    return result
