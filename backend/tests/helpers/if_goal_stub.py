"""Seed helper for the IF goal gate added to ``trigger_pipeline``.

Pipeline run trigger agora exige uma meta IF (``Goal`` com
``type="INDEPENDENCIA_FINANCEIRA"`` e ``effective_to=None``). Testes que
só mockam ``start_pipeline_run`` usam este stub minimal para destravar o
gate — sem passar por ``compute_if_derived``.
"""

from __future__ import annotations

from datetime import date

from backend.app.models.goal import Goal


def build_if_goal_stub(workspace_id: str) -> Goal:
    return Goal(
        workspace_id=workspace_id,
        type="INDEPENDENCIA_FINANCEIRA",
        params_json={"inputs": {}, "meta_version": 1},
        derived_json={},
        effective_from=date.today(),
        effective_to=None,
    )
