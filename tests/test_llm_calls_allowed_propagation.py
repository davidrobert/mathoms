"""``skip_llm`` alcança a chamada LLM condicional dentro do stage (ADR-355).

Filtrar a lista de stages por ``is_llm`` não impede stage determinístico de
chamar LLM. Cada teste de "não chamou" vem com a perna de controle que **prova
que a fixture dispararia a chamada** — sem ela, o gate passa vazio no dia em que
o classificador melhorar e o documento deixar de cair abaixo do threshold.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.context import WorkspaceContext
from pipeline.orchestrator import run_stages
from pipeline.stages import route_documents
from tests.fakes.anthropic_sdk import RecordingAnthropicSDK

# Sem marcador de nenhum TypeRule → confidence 0.0 → abaixo do threshold de 0,8
# que arma o fallback (ADR-081 camada 2).
_SEM_MARCADOR = "conteudo generico sem marcador de tipo reconhecivel\n" * 5

_RESPOSTA_LLM = {
    "institution": "itau",
    "doc_type": "extratocontabrl",
    "dest_group": "financial_statements",
    "period": "202602",
    "final_name": "extrato.txt",
    "confidence": 0.95,
}


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> WorkspaceContext:
    """Workspace com 1 documento que só roteia se o LLM for consultado."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-de-teste")
    cfg = tmp_path / "config"
    cfg.mkdir()
    for name in ("pipeline.json", "institutions.json", "family_members.json"):
        (cfg / name).write_text("{}")
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "generico.txt").write_text(_SEM_MARCADOR, encoding="utf-8")
    return WorkspaceContext(root=tmp_path, artifact_store=None)


@pytest.fixture()
def sdk(monkeypatch: pytest.MonkeyPatch) -> RecordingAnthropicSDK:
    return RecordingAnthropicSDK(payload=_RESPOSTA_LLM).install(monkeypatch)


def _no_inbox(ctx: WorkspaceContext) -> list[str]:
    return sorted(p.name for p in (ctx.root / "inbox").iterdir())


def test_run_sem_llm_nao_chama_o_fallback_de_classificacao(workspace, sdk):
    workspace.llm_calls_allowed = False

    detail = route_documents.run(workspace)

    assert sdk.calls == [], "run determinístico gastou LLM no E0"
    assert detail["llm_calls_allowed"] is False
    assert detail["inbox_review"] == 1
    assert detail["llm_classified"] == 0
    assert _no_inbox(workspace) == ["generico.txt"], "doc sem classificação sai do inbox"
    assert "corpus" in detail["warning"], "encolhimento de corpus tem que ser declarado"


def test_run_com_llm_chama_o_fallback(workspace, sdk):
    """Perna de controle: sem ela o teste acima passaria com fixture inerte."""
    detail = route_documents.run(workspace)

    assert len(sdk.calls) == 1
    assert detail["llm_calls_allowed"] is True
    assert detail["llm_classified"] == 1
    assert detail["inbox_review"] == 0
    assert _no_inbox(workspace) == []


@pytest.mark.parametrize("skip_llm, esperado", [(True, False), (False, True)])
def test_run_stages_anota_a_politica_no_contexto(tmp_path, skip_llm, esperado):
    """Caminho puro (testes, dev/) recebe ctx pronto — a política é anotada nele."""
    ctx = WorkspaceContext(root=tmp_path, artifact_store=None)

    run_stages(ctx, [], skip_llm=skip_llm)

    assert ctx.llm_calls_allowed is esperado


def test_narrativas_nao_consultam_llm_sem_politica(monkeypatch, tmp_path):
    """``generate_narratives`` não é ``is_llm``: o env var não pode vencer o run."""
    from scripts import generate_narratives as gn

    monkeypatch.setenv("MATHOMS_LLM_SECTION_SUMMARIES", "1")
    chamadas: list[object] = []
    monkeypatch.setattr(gn, "_resolve_workspace_id", lambda ctx: chamadas.append(ctx))
    ctx = WorkspaceContext(root=tmp_path, artifact_store=None)
    ctx.llm_calls_allowed = False

    assert gn._e5n_generate_section_summaries(ctx, {}) == {}
    assert chamadas == [], "retornou antes de montar a chamada"


@pytest.mark.parametrize("argv_extra, esperado", [([], False), (["--skip-llm"], True)])
def test_cli_run_stage_propaga_a_flag(argv_extra, esperado):
    from pipeline.cli_run_stage import _hydration_kwargs, build_parser

    args = build_parser().parse_args(
        [
            "run-stage",
            "route_documents",
            "--workspace",
            "/tmp/ws",
            "--run-id",
            "run-1",
            "--workspace-id",
            "ws-1",
            *argv_extra,
        ]
    )

    assert _hydration_kwargs(args)["skip_llm"] is esperado
