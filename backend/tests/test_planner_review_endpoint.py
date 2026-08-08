"""Endpoint GET/POST .../planner-review — Ato 5 (ADR-199 / ADR-208).

Cobre 404 ausente, tier filter (premium full vs free teaser), publish idempotente,
sigilo §13.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.planner_review import PlannerReview
from backend.app.models.report import Report
from backend.tests import factories

PERSONA_HASH = "a" * 64

# fmt: off
_PONTOS_FORTES = [
    {"titulo": "Reserva sólida", "descricao": "Cobertura de 12 meses",
     "ancora_metodologica": "perini", "tema_canonico": "Saúde de balanço",
     "section_id": "S1"},
    {"titulo": "Alocação coerente", "descricao": "Adequada ao perfil",
     "ancora_metodologica": "perini", "tema_canonico": "Alocação",
     "section_id": "S3"},
    {"titulo": "Disciplina de aporte", "descricao": "Aporte mensal estável",
     "ancora_metodologica": "cerbasi", "tema_canonico": "Equilíbrio presente-futuro",
     "section_id": "S2"},
]
_RISCOS = [
    {"severidade": "Crítica", "titulo": "Concentração imobiliária alta",
     "descricao": "70% do patrimônio em imóveis", "ancora_metodologica": "perini",
     "tema_canonico": "Alocação", "evidencia": None, "evidencia_path": None,
     "section_id": "S4", "confianca": "alta"},
    {"severidade": "Alta", "titulo": "Sem seguro de vida",
     "descricao": "Proteção patrimonial ausente", "ancora_metodologica": "cerbasi",
     "tema_canonico": "Proteção", "evidencia": None, "evidencia_path": None,
     "section_id": "S9", "confianca": "alta"},
]
_EXECUCAO = [
    {"prioridade": "P0", "acao": "Contratar seguro de vida ASAP",
     "impacto_qualitativo": "Reduz exposição patrimonial em caso de morte",
     "ancora_metodologica": "cerbasi", "tema_canonico": "Proteção",
     "confianca": "alta", "section_id": "S9",
     "suggestion_dedup_key": "d" * 64},
]
_METADATA = {
    "persona_hash": PERSONA_HASH, "manifest_version": "1.0",
    "schema_version": "1.0", "model_id": "anthropic/claude-sonnet-4-20250514",
    "tier_at_generation": "premium", "generated_at": "2026-05-13T16:00:00+00:00",
}
# fmt: on


def make_full_artifact() -> dict:
    """Output canônico do stage parecer_planejador (ADR-202)."""
    return {
        "version": "1.0",
        "metadata": dict(_METADATA),
        "diagnostico_geral": (
            "diagnostico de teste com tamanho minimo aceito pelo schema validator"
        ),
        "pontos_fortes": [dict(p) for p in _PONTOS_FORTES],
        "riscos": [dict(r) for r in _RISCOS],
        "sugestoes_execucao": [dict(s) for s in _EXECUCAO],
        "sugestoes_taticas": [],
        "sugestoes_estrategicas": [],
        "metricas": [],
        "notas_metodologicas": [],
    }


# fmt: off
_REVIEW_DEFAULTS = dict(
    persona_hash=PERSONA_HASH, manifest_version="1.0", schema_version="1.0",
    model_id="anthropic/claude-sonnet-4-20250514", tier_at_generation="premium",
    items_shown_count=6, items_gated_count=0, cost_usd_cents=15,
    tokens_in=5000, tokens_out=1000, tool_iterations=1, latency_ms=8000,
)
# fmt: on


def make_review_row(*, workspace_id, run_id, parecer_id, e5_id, status="Gerado", **overrides):
    """Row factory para PlannerReview com defaults sensatos."""
    fields = {**_REVIEW_DEFAULTS, **overrides}
    return PlannerReview(
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        pipeline_artifact_id=parecer_id,
        e5_artifact_id=e5_id,
        status=status,
        **fields,
    )


def _make_artifact_row(workspace, run, stage: str, key: str, content_json: dict):
    return PipelineArtifact(
        workspace_id=workspace.id,
        pipeline_run_id=run.id,
        stage=stage,
        artifact_key=key,
        content_json=content_json,
    )


async def make_run_artifacts(db, workspace, run):
    """Cria E5 + parecer artifacts; flush to materialize IDs."""
    e5 = _make_artifact_row(workspace, run, "E5", "analise_financeira", {"narrativas": {}})
    db.add(e5)
    await db.flush()
    parecer = _make_artifact_row(
        workspace, run, "E6-parecer", "parecer_planejador", make_full_artifact()
    )
    db.add(parecer)
    await db.flush()
    return e5, parecer


async def make_planner_review(db, *, workspace, status="Gerado", **overrides):
    """Cria run + 2 artifacts (E5 + parecer) + Report + PlannerReview."""
    run = await factories.make_run(db, workspace=workspace)
    e5, parecer = await make_run_artifacts(db, workspace, run)
    report = await factories.make_report(db, workspace=workspace, pipeline_run=run)
    review = make_review_row(
        workspace_id=workspace.id,
        run_id=run.id,
        parecer_id=parecer.id,
        e5_id=e5.id,
        status=status,
        **overrides,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review, report


# ─── tests ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_returns_404_when_review_missing(auth_client, db):
    """Endpoint retorna 404 com code=not_generated_yet quando não há parecer."""
    from backend.app.models.workspace import Workspace

    ws = (await db.execute(select(Workspace))).scalar_one()
    # `tier_at_run` explícito: a factory default para `free`, que agora é OUTRO
    # código. Deixar implícito faria este teste medir o tier sem dizer que mede.
    run = await factories.make_run(db, workspace=ws, tier_at_run="premium")
    report = await factories.make_report(db, workspace=ws, pipeline_run=run)
    await db.commit()
    resp = await auth_client.get(f"/api/workspaces/{ws.id}/reports/{report.id}/planner-review")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "not_generated_yet"


@pytest.mark.asyncio
async def test_get_404_tier_gated_quando_o_run_foi_free(auth_client, db):
    """Free sem artifact deixa de ser `not_generated_yet` — são ações opostas (ADR-366 §D6)."""
    from backend.app.models.workspace import Workspace

    ws = (await db.execute(select(Workspace))).scalar_one()
    run = await factories.make_run(db, workspace=ws, tier_at_run="free")
    report = await factories.make_report(db, workspace=ws, pipeline_run=run)
    await db.commit()

    resp = await auth_client.get(f"/api/workspaces/{ws.id}/reports/{report.id}/planner-review")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "tier_gated"
    # Mesma guarda do `generation_unavailable`: nada de vocabulário de operador.
    assert "LLM" not in resp.text and "error" not in resp.text


@pytest.mark.asyncio
async def test_get_404_distingue_run_que_tentou_de_run_que_nao_rodou(auth_client, db):
    """`generation_unavailable`: houve artifact e não há row — o run tentou (ADR-366 §D6)."""
    from backend.app.models.workspace import Workspace

    ws = (await db.execute(select(Workspace))).scalar_one()
    run = await factories.make_run(db, workspace=ws)
    report = await factories.make_report(db, workspace=ws, pipeline_run=run)
    await _seed_parecer_artifact(db, workspace=ws, run=run)
    await db.commit()

    resp = await auth_client.get(f"/api/workspaces/{ws.id}/reports/{report.id}/planner-review")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "generation_unavailable"
    # A copy do 404 não pode carregar vocabulário de operador nem "LLM".
    assert "LLM" not in resp.text and "error" not in resp.text


async def _seed_parecer_artifact(db, *, workspace, run):
    """Artifact do desfecho indisponível — o que `_needs_review_return` grava."""
    from backend.app.models.pipeline_artifact import PipelineArtifact

    db.add(
        PipelineArtifact(
            workspace_id=workspace.id,
            pipeline_run_id=run.id,
            stage="review_finances_holistic",
            artifact_key="parecer_planejador",
            content_json={"_meta": {"status": "needs_review"}},
        )
    )


@pytest.mark.asyncio
async def test_get_returns_404_when_report_missing(auth_client):
    """Endpoint retorna 404 quando report_id não existe no workspace."""
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    resp = await auth_client.get(
        f"/api/workspaces/{ws_id}/reports/00000000-0000-0000-0000-000000000000/planner-review"
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "report_not_found"


async def _seed_premium_llm_config(db, workspace_id):
    """Cria LLMConfig encriptada — marca workspace como premium."""
    from backend.app.models.llm_config import LLMConfig
    from backend.app.services.security.vault import get_vault

    db.add(
        LLMConfig(
            workspace_id=workspace_id,
            provider="anthropic",
            model_name="claude-sonnet-4",
            api_key_encrypted=get_vault().encrypt("sk-test-not-real"),
        )
    )
    await db.commit()


def _assert_premium_content(body, review_id):
    assert body["id"] == review_id
    assert body["status"] == "Gerado"
    assert len(body["content"]["pontos_fortes"]) == 3
    assert len(body["content"]["riscos"]) == 2
    assert len(body["content"]["sugestoes_execucao"]) == 1
    assert body["content"]["meta"]["tier_at_generation"] == "premium"


@pytest.mark.asyncio
async def test_get_returns_full_content_for_premium(auth_client, db):
    """Premium (LLMConfig + api_key) recebe content completo."""
    from backend.app.models.workspace import Workspace

    ws = (await db.execute(select(Workspace))).scalar_one()
    await _seed_premium_llm_config(db, ws.id)
    review, report = await make_planner_review(db, workspace=ws)
    resp = await auth_client.get(f"/api/workspaces/{ws.id}/reports/{report.id}/planner-review")
    assert resp.status_code == 200, resp.text
    _assert_premium_content(resp.json(), review.id)


def _assert_free_teaser(body):
    """Free vê 3 pontos, 1 risco (Crítica), 0 sugestões + gated_counts >0."""
    content = body["content"]
    assert len(content["pontos_fortes"]) == 3
    assert len(content["riscos"]) == 1
    assert content["riscos"][0]["severidade"] == "Crítica"
    assert content["sugestoes_execucao"] == []
    assert content["meta"]["tier_at_generation"] == "free"
    assert content["meta"]["gated_counts"]["riscos"] == 1
    assert content["meta"]["gated_counts"]["sugestoes_execucao"] == 1


@pytest.mark.asyncio
async def test_get_returns_teaser_for_free(auth_client, db):
    """Free (sem LLMConfig) recebe teaser: 3 pontos + 1 risco + 0 sugestões."""
    from backend.app.models.workspace import Workspace

    ws = (await db.execute(select(Workspace))).scalar_one()
    _review, report = await make_planner_review(db, workspace=ws)
    resp = await auth_client.get(f"/api/workspaces/{ws.id}/reports/{report.id}/planner-review")
    assert resp.status_code == 200, resp.text
    _assert_free_teaser(resp.json())


@pytest.mark.asyncio
async def test_response_strips_ancora_metodologica(auth_client, db):
    """Sigilo §13 (ADR-207): JSON jamais contém `ancora_metodologica`."""
    from backend.app.models.workspace import Workspace

    ws = (await db.execute(select(Workspace))).scalar_one()
    _review, report = await make_planner_review(db, workspace=ws)
    resp = await auth_client.get(f"/api/workspaces/{ws.id}/reports/{report.id}/planner-review")
    assert resp.status_code == 200
    raw = json.dumps(resp.json()).lower()
    assert "ancora_metodologica" not in raw
    assert "perini" not in raw
    assert "cerbasi" not in raw


async def _post_publish(auth_client, ws_id, report_id):
    return await auth_client.post(
        f"/api/workspaces/{ws_id}/reports/{report_id}/planner-review/publish"
    )


@pytest.mark.asyncio
async def test_publish_flips_status_to_publicado(auth_client, db):
    """POST /publish transiciona Gerado → Publicado + grava immutable_hash (idempotente)."""
    from backend.app.models.workspace import Workspace

    ws = (await db.execute(select(Workspace))).scalar_one()
    _review, report = await make_planner_review(db, workspace=ws)
    resp = await _post_publish(auth_client, ws.id, report.id)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "Publicado"
    assert body["immutable_hash"] is not None
    assert len(body["immutable_hash"]) == 64
    resp2 = await _post_publish(auth_client, ws.id, report.id)
    assert resp2.status_code == 200
    assert resp2.json()["immutable_hash"] == body["immutable_hash"]


@pytest.mark.asyncio
async def test_publish_rejects_invalid_status(auth_client, db):
    """Publish em Superseded → 409."""
    from backend.app.models.workspace import Workspace

    ws = (await db.execute(select(Workspace))).scalar_one()
    _review, report = await make_planner_review(db, workspace=ws, status="Superseded")
    resp = await _post_publish(auth_client, ws.id, report.id)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "invalid_status_for_publish"


# ─── desfecho retido (ADR-366) ──────────────────────────────────────────


_RETIDO = {
    "outcome": "retido",
    "retention_reason": "parecer.sigilo",
    "items_shown_count": 0,
    "items_dropped_count": 0,
}


async def _get_retido(auth_client, db):
    """Semeia um review retido premium e devolve a resposta do GET."""
    from backend.app.models.workspace import Workspace

    workspace = (await db.execute(select(Workspace))).scalars().first()
    _, report = await make_planner_review(db, workspace=workspace, **_RETIDO)
    await _seed_premium_llm_config(db, workspace.id)
    return await auth_client.get(
        f"/api/workspaces/{workspace.id}/reports/{report.id}/planner-review"
    )


@pytest.mark.asyncio
async def test_get_retido_devolve_200_sem_conteudo(auth_client, db):
    """Retido é 200 com `content: null` — 404 diria "não gerado", que é mentira."""
    resp = await _get_retido(auth_client, db)

    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome"] == "retido"
    assert body["content"] is None
    assert body["items_shown_count"] == 0
    assert body["retention"] == {
        "reason": "parecer.sigilo",
        "items_dropped_count": 0,
    }


@pytest.mark.asyncio
async def test_get_retido_nao_vaza_vocabulario_de_operador(auth_client, db):
    """Nem o placeholder nem a prosa de operador cruzam o boundary (ADR-366 §D3/§D5)."""
    raw = (await _get_retido(auth_client, db)).text
    for leak in (
        "placeholder",
        "error_detail",
        "_meta",
        "needs_review",
        "whitelist_miss",
        "resolve_null",
        "pairing_mismatch",
        "Inspecione",
    ):
        assert leak not in raw, leak


@pytest.mark.asyncio
async def test_publish_rejeita_parecer_retido(auth_client, db):
    """Publicar congelaria `immutable_hash` sobre o placeholder (ADR-366 §D2)."""
    from backend.app.models.workspace import Workspace

    workspace = (await db.execute(select(Workspace))).scalars().first()
    _, report = await make_planner_review(db, workspace=workspace, **_RETIDO)

    resp = await _post_publish(auth_client, workspace.id, report.id)

    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "retained_cannot_publish"


@pytest.mark.asyncio
async def test_publish_permite_entregue_com_retencao(auth_client, db):
    """Parecer entregue com itens removidos é PUBLICÁVEL — foi o que decidiu o eixo próprio."""
    from backend.app.models.workspace import Workspace

    workspace = (await db.execute(select(Workspace))).scalars().first()
    _, report = await make_planner_review(
        db,
        workspace=workspace,
        outcome="entregue_com_retencao",
        retention_reason="parecer.citacao_nao_confirmada",
        items_dropped_count=2,
    )
    await _seed_premium_llm_config(db, workspace.id)

    resp = await _post_publish(auth_client, workspace.id, report.id)

    assert resp.status_code == 200
    assert resp.json()["outcome"] == "entregue_com_retencao"
    assert resp.json()["retention"]["items_dropped_count"] == 2
