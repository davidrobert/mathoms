"""Cobertura direta do stage runner E7 (`pipeline/stages/validate_cross.py`).

E7 é read-only por design (dead code de write desde ADR-199 — ver CLAUDE.md
§Convenções de naming): roda os checks CV sobre o E5 e **não** grava artifact.
Estes testes travam shape do retorno, a propriedade read-only, idempotência e
a falha limpa quando o E5 está ausente ou sem narrativas.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext
from pipeline.stages import validate_cross

_REQUIRED_CHARTS = (
    "score_gauge",
    "patrimonio_doughnut",
    "alocacao_atual_vs_alvo",
    "fluxo_mensal",
    "receita_bar",
    "receita_despesa_mensal",
    "despesas_doughnut",
)


class WriteRecordingArtifactStore(InMemoryArtifactStore):
    """Fake nomeado que registra cada write — prova que E7 não grava artifact."""

    def __init__(self) -> None:
        super().__init__()
        self.write_calls: list[tuple[str, str]] = []

    def write(self, stage: str, key: str, data: dict, *, document_id=None) -> None:
        self.write_calls.append((stage, key))
        super().write(stage, key, data, document_id=document_id)


def _minimal_e5() -> dict:
    """E5 sintético mínimo que passa os 6 checks always-on (CV9-CV14), zero PII."""
    return {
        "narrativas": {
            "summaries": {f"s{i}": "texto sintético" for i in range(1, 11)},
            "charts": {c: {"context": "ctx", "conclusion": "fim"} for c in _REQUIRED_CHARTS},
        },
        "tarefas": [{"t": "tarefa sintética", "p": "alta"}],
        "diagnostico_comportamental": [{"padrao": "sintético"}],
        "score": {"valor": 0, "classificacao": "Crítico"},
    }


def _seeded_ctx(tmp_path: Path, store: InMemoryArtifactStore) -> WorkspaceContext:
    (tmp_path / "config").mkdir(exist_ok=True)
    return WorkspaceContext(root=tmp_path, artifact_store=store)


def test_stage_run_shape_and_read_only(tmp_path: Path) -> None:
    """`run(ctx)` retorna shape crossval completo e não escreve row nova no store."""
    store = WriteRecordingArtifactStore()
    store.seed("analyze_finances", "analise_financeira", _minimal_e5())
    store.write_calls.clear()  # seed() delega a write(); só interessa o que o E7 fizer
    result = validate_cross.run(_seeded_ctx(tmp_path, store))
    assert result["success"] is True
    assert result["stage"] == "validate_cross"
    assert result["mode"] == "crossval"
    assert result["checks_total"] == 6  # só os always-on; opcionais skipam sem dados
    assert result["checks_failed"] == 0
    assert {r["check_id"] for r in result["results"]} == {f"CV{i}" for i in range(9, 15)}
    assert store.write_calls == [], "E7 é read-only — não pode gravar artifact"


def test_stage_run_is_idempotent(tmp_path: Path) -> None:
    """Segunda execução sobre o mesmo E5 produz resultado idêntico."""
    store = InMemoryArtifactStore()
    store.seed("analyze_finances", "analise_financeira", _minimal_e5())
    ctx = _seeded_ctx(tmp_path, store)
    assert validate_cross.run(ctx) == validate_cross.run(ctx)


def test_stage_run_fails_cleanly_without_e5(tmp_path: Path) -> None:
    """E5 ausente → retorno estruturado (não raise), reason `e5_not_found`."""
    result = validate_cross.run(_seeded_ctx(tmp_path, InMemoryArtifactStore()))
    assert result == {"success": False, "reason": "e5_not_found", "stage": "validate_cross"}


def test_stage_run_fails_cleanly_without_narrativas(tmp_path: Path) -> None:
    """E5 sem narrativas (E5.N não rodou) → reason `missing_narrativas`."""
    store = InMemoryArtifactStore()
    store.seed("analyze_finances", "analise_financeira", {"score": {"valor": 0}})
    result = validate_cross.run(_seeded_ctx(tmp_path, store))
    assert result == {"success": False, "reason": "missing_narrativas", "stage": "validate_cross"}
