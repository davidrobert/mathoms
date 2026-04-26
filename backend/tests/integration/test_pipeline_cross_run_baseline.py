"""ADR-132 T4 — Smoke test cross-run para baseline IRPF (`E1.5c`).

Regressão guardada: pipeline rodando 2× em sequência, segundo run sem
reprocessar IRPF. Antes do fix (DBArtifactStore com filtro só por
`pipeline_run_id`), o E4 do run B lia E1.5c=None, gravava placeholder
vazio em E4-patrimônio, e o E5 zerava composição patrimonial — usuário
via R$ 440k onde deveria ver R$ 5M.

Pós-ADR-132 (workspace fallback em stages de referência + omissão da
chave em build_patrimonio_artifact): run B vê o E1.5c persistente do
run A, E4 do run B produz patrimônio rico, E5 reflete IRPF completo.

Este teste é o single source para detectar essa classe de bug fim-a-fim
— se T1/T2/T3 falharem juntos por engano de cobertura, T4 ainda pega.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.services.db_artifact_store import DBArtifactStore
from backend.tests.factories import make_workspace
from pipeline.domain.services.baseline_normalizer import BaselineNormalizer
from pipeline.domain.services.e4_categorizer_adapter import E4CategorizerAdapter

_RICH_BASELINE = {
    "imoveis_consolidados": [
        {
            "descricao": "APARTAMENTO RESIDÊNCIA RUA TASSO",
            "proprietario": "david",
            "valores_31_12": {"2024": 800000.0},
            "tipo": "imovel",
        },
        {
            "descricao": "APARTAMENTO INVESTIMENTO PINHEIROS",
            "proprietario": "david",
            "valores_31_12": {"2024": 350000.0},
            "tipo": "imovel",
        },
        {
            "descricao": "APARTAMENTO MARIANA",
            "proprietario": "mariana",
            "valores_31_12": {"2024": 400000.0},
            "tipo": "imovel",
        },
    ],
    "veiculos_consolidados": [
        {
            "descricao": "FIAT TORO",
            "proprietario": "david",
            "valores_31_12": {"2024": 191354.0},
            "tipo": "veiculo",
        },
    ],
    "investimentos_consolidados": [
        {
            "descricao": "CDB ITAU",
            "proprietario": "david",
            "valores_31_12": {"2024": 100000.0},
            "tipo": "investimento",
        },
    ],
    "dividas": [],
    "patrimonio_por_ano": {"2024": {"total_bens": 1841354.0, "total_dividas": 0.0}},
}


@pytest.mark.asyncio
async def test_run_b_sees_baseline_from_run_a_via_workspace_fallback(db) -> None:
    """Núcleo do bug ADR-132: store no run B consegue ler E1.5c do run A."""
    ws = await make_workspace(db)

    run_a = PipelineRun(
        id=str(uuid4()),
        workspace_id=ws.id,
        status=PipelineRunStatus.completed,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run_a)
    await db.flush()

    db.add(
        PipelineArtifact(
            workspace_id=ws.id,
            pipeline_run_id=run_a.id,
            stage="E1.5c",
            artifact_key="baseline_patrimonial",
            content_json=_RICH_BASELINE,
        )
    )
    await db.commit()

    run_b = PipelineRun(
        id=str(uuid4()),
        workspace_id=ws.id,
        status=PipelineRunStatus.running,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run_b)
    await db.commit()

    run_b_id = run_b.id
    ws_id = ws.id
    with SyncSessionLocal() as session:
        store_b = DBArtifactStore(session, workspace_id=ws_id, pipeline_run_id=run_b_id)
        baseline = store_b.read("E1.5c", "baseline_patrimonial")

    assert baseline is not None, "fallback workspace-scoped deveria devolver baseline do run A"
    assert baseline["patrimonio_por_ano"]["2024"]["total_bens"] == 1841354.0
    assert len(baseline["imoveis_consolidados"]) == 3


@pytest.mark.asyncio
async def test_e4_load_baseline_in_run_b_reaches_run_a_baseline(db) -> None:
    """E4CategorizerAdapter.load_baseline é o consumidor real — confirma
    que a integração desse caminho casa com o fallback do store."""
    ws = await make_workspace(db)

    run_a = PipelineRun(
        id=str(uuid4()),
        workspace_id=ws.id,
        status=PipelineRunStatus.completed,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run_a)
    await db.flush()
    db.add(
        PipelineArtifact(
            workspace_id=ws.id,
            pipeline_run_id=run_a.id,
            stage="E1.5c",
            artifact_key="baseline_patrimonial",
            content_json=_RICH_BASELINE,
        )
    )
    await db.commit()

    run_b = PipelineRun(
        id=str(uuid4()),
        workspace_id=ws.id,
        status=PipelineRunStatus.running,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run_b)
    await db.commit()

    from pipeline.domain.services.cash_flow_builder import CashFlowBuilder
    from pipeline.domain.services.investments_consolidator import InvestmentsConsolidator
    from pipeline.domain.services.transaction_classifier import (
        ClassifierConfig,
        TransactionClassifier,
    )

    cfg = ClassifierConfig.from_configs(
        categorization={
            "expense_keywords": {},
            "income_keywords": {},
            "internal_transfer_patterns": [],
            "clt_source_mapping": {},
            "pj_source_mapping": {},
        },
    )
    adapter = E4CategorizerAdapter(
        classifier=TransactionClassifier(cfg),
        cash_flow_builder=CashFlowBuilder(),
        baseline_normalizer=BaselineNormalizer(),
        investments_consolidator=InvestmentsConsolidator(),
    )

    run_b_id = run_b.id
    ws_id = ws.id
    with SyncSessionLocal() as session:
        store_b = DBArtifactStore(session, workspace_id=ws_id, pipeline_run_id=run_b_id)
        baseline = adapter.load_baseline(store_b)

    assert baseline is not None
    assert baseline["patrimonio_por_ano"]["2024"]["total_bens"] == 1841354.0
