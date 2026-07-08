"""Regressão P3: todos os readers user-facing devem preferir DB a disco.

Cenário comum pós-cutover MATHOMS_USE_DB_ARTIFACTS=True: artefatos em
``pipeline_artifacts`` (DB), disco ``processed/`` vazio. Se algum reader
cair no disco por engano, retorna dados stale ou nada.

Este teste monta workspace com artefatos só no DB e verifica que todos
os pontos de leitura retornam os dados frescos:
  - dashboard_service.load_e5_analysis (E5)
  - transaction_service.load_transactions (E4: receitas + despesas)
  - document_pipeline_sync.has_e15a_artifact_in_db (E1.5a — IRPF)
  - document_pipeline_sync.has_e2_artifact_in_db (E2 — extratos/faturas)
  - document_extract_json_service.read_document_extract_json (IRPF + E2)

Complementa os unit tests de cada serviço — aqui o objetivo é bater no
DB real (TestSyncSession) e ver todos trabalhando juntos.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.services.dashboard_service import load_e5_analysis
from backend.app.services.documents.document_extract_json_service import read_document_extract_json
from backend.app.services.pipeline.document_pipeline_sync import (
    has_e2_artifact_in_db,
    has_e15a_artifact_in_db,
)
from backend.app.services.storage import StorageService
from backend.app.services.transaction_service import load_transactions
from backend.tests import factories


@pytest.mark.asyncio
async def test_all_user_facing_readers_prefer_db_when_disk_empty(db, tmp_path: Path) -> None:
    ws = await factories.make_workspace(db)
    tenant_root = tmp_path / ws.id
    (tenant_root / "processed").mkdir(parents=True)

    irpf_doc = await factories.make_document(
        db,
        workspace=ws,
        original_name="receitafederal_irpfdeclaracao_2024.pdf",
        stored_path="data/income_tax_br/receitafederal_irpfdeclaracao_2024-0_original.pdf",
        doc_type="irpf",
        status="processed",
    )
    extrato_doc = await factories.make_document(
        db,
        workspace=ws,
        original_name="c6bank_extratoconta_202604.pdf",
        stored_path="data/c6bank/c6bank_extratoconta_202604-0_original.pdf",
        doc_type="bank_statement",
        bank_code="c6bank",
        period="2026-04",
        status="processed",
    )

    run = PipelineRun(
        id=str(uuid4()),
        workspace_id=ws.id,
        status=PipelineRunStatus.completed,
        started_at=datetime.now(timezone.utc),
        tier_at_run="premium",
        incremental=False,
        reprocess_all=False,
        total_documents=1,
    )
    db.add(run)
    await db.flush()

    artifacts = [
        (
            "analyze_finances",
            "analise_financeira",
            {"patrimonio": {"bruto": 4_308_452.40, "liquido": 3_084_154.94}},
        ),
        (
            "categorize_transactions",
            "receitas",
            {"dados": {"salarios": [{"data": "2026-04-01", "descricao": "Folha", "valor": 10000}]}},
        ),
        (
            "categorize_transactions",
            "despesas",
            {
                "dados": {
                    "moradia": [{"data": "2026-04-05", "descricao": "Aluguel", "valor": -3000}]
                }
            },
        ),
        (
            "E1.5a",
            "receitafederal_irpfdeclaracao_2024",
            {"itens": [{"codigo": "11", "descricao": "Imóvel Casa", "valor_brl": 1_000_000}]},
        ),
        (
            "E2-extratos",
            "c6bank_extratoconta_202604",
            {"transacoes": [{"data": "2026-04-10", "descricao": "Pix recebido", "valor": 500.00}]},
        ),
    ]
    for stage, key, payload in artifacts:
        db.add(
            PipelineArtifact(
                workspace_id=ws.id,
                pipeline_run_id=run.id,
                stage=stage,
                artifact_key=key,
                content_json=payload,
            )
        )
    await db.commit()

    # Dashboard
    e5 = load_e5_analysis(ws.id, str(tenant_root))
    assert e5 is not None and e5["patrimonio"]["bruto"] == 4_308_452.40

    # Transactions
    txs = load_transactions(ws.id, str(tenant_root))
    assert len(txs) == 2
    assert {t.descricao for t in txs} == {"Folha", "Aluguel"}

    # IRPF sync flag
    with SyncSessionLocal() as session:
        assert (
            has_e15a_artifact_in_db(
                session,
                ws.id,
                "receitafederal_irpfdeclaracao_2024-0_original.pdf",
            )
            is True
        )
        # E2 sync flag — botão "ver JSON" depende disso para extratos/faturas.
        assert (
            has_e2_artifact_in_db(
                session,
                ws.id,
                "c6bank_extratoconta_202604-0_original.pdf",
            )
            is True
        )

    # IRPF extract JSON endpoint — StorageService aceita storage_root no construtor
    storage = StorageService(storage_root=tmp_path)
    result = read_document_extract_json(irpf_doc, workspace_id=ws.id, storage=storage)
    assert result.data["itens"][0]["descricao"] == "Imóvel Casa"
    assert result.filename == "receitafederal_irpfdeclaracao_2024-1.5a_extract.json"

    # E2 extract JSON endpoint — mesmo fluxo, sem disco
    e2_result = read_document_extract_json(extrato_doc, workspace_id=ws.id, storage=storage)
    assert e2_result.data["transacoes"][0]["descricao"] == "Pix recebido"
    assert e2_result.filename == "c6bank_extratoconta_202604-2_extract.json"

    # Disco permanece vazio — prova de que veio tudo do DB
    assert not any((tenant_root / "processed").rglob("*.json"))
