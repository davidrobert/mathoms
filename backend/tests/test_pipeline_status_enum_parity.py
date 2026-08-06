"""Paridade dos enums de status de pipeline entre Python e o cliente TS.

`frontend/src/lib/api/pipeline.ts` declara `PipelineStageStatus` e
`PipelineRunStatus` **à mão** — não sai do codegen de `frontend/src/generated/`,
que cobre só o report layout. Nada ligava as duas cópias, e o comentário em
`frontend/src/lib/pipelinePhases.ts` já nomeava o risco: *"com duas cópias, o
próximo status novo entra pela metade"*.

Foi exatamente o que aconteceu na janela reader-first da A40.l21 → A40.l18: o TS
ganhou `degraded` em #1232 e o Python só agora. Substitui o tripwire negativo
`test_degraded_stage_status_ainda_nao_existe`, que era one-shot — cobrava a
conferência **uma vez**, no PR que criasse o membro, e mandava se deletar.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.app.models.pipeline_run import PipelineRunStatus, PipelineStageStatus

_TS_CLIENT = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "api" / "pipeline.ts"
)


def _ts_union_members(type_name: str) -> set[str]:
    """Extrai os literais de `export type <type_name> = "a" | "b";` (multilinha)."""
    # Comentários saem antes do match: uma linha `// … (A40.l21 …);` termina em
    # `;` e truncaria a união no meio.
    source = re.sub(r"//[^\n]*", "", _TS_CLIENT.read_text(encoding="utf-8"))
    match = re.search(rf"export type {type_name} =(.*?);", source, re.DOTALL)
    if match is None:
        pytest.fail(f"union {type_name} não encontrada em {_TS_CLIENT}")
    return set(re.findall(r'"([a-z_]+)"', match.group(1)))


@pytest.mark.parametrize(
    ("enum_cls", "ts_type"),
    [
        (PipelineStageStatus, "PipelineStageStatus"),
        (PipelineRunStatus, "PipelineRunStatus"),
    ],
)
def test_python_enum_matches_ts_union(enum_cls, ts_type):
    assert {m.value for m in enum_cls} == _ts_union_members(ts_type)


def test_degraded_existe_dos_dois_lados():
    """A40.l18 fecha o handoff que a A40.l21 abriu — asserção nomeada para o bisect."""
    assert PipelineStageStatus.degraded.value == "degraded"
    assert "degraded" in _ts_union_members("PipelineStageStatus")
