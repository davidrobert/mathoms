"""Base do PGBL da S8 sai do ano-base fiscal eleito, não do `created_at` (A40.l65 §Escopo 1).

Antes desta lane `_load_irpf_renda_tributavel` lia a row mais recentemente criada.
Com dois declarantes — ou com o mesmo declarante re-extraído — o ano publicado
passava a depender de quem foi processado por último, enquanto o Card B publicava
o ano que `resolve_ano_base_fiscal` elege (ADR-305 D1/D2). Dois resolvedores do
mesmo corpus no mesmo documento.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.services.tributario_input_builder import build_cascata_input_sync
from backend.tests import factories

_HOJE = datetime.now(timezone.utc)


def _contribuinte(*, ano_base: int, cpf_final: str) -> dict:
    return {
        "cpf_masked": f"***.***.***-{cpf_final}",
        "nome": f"Declarante {cpf_final}",
        "ano_base": ano_base,
        "exercicio": ano_base + 1,
        "modelo": "completo",
        "natureza": "titular",
    }


def _fonte_pj(tributavel: str) -> dict:
    return {
        "cnpj": "12.345.678/0001-90",
        "nome": "Fonte",
        "rendimentos_tributaveis_brl": tributavel,
        "contrib_previdenciaria_brl": "0",
        "ir_retido_brl": "0",
        "decimo_terceiro_bruto_brl": "0",
        "decimo_terceiro_ir_retido_brl": "0",
    }


def _declaracao(*, ano_base: int, cpf_final: str, tributavel: str) -> dict:
    return {
        "contribuinte": _contribuinte(ano_base=ano_base, cpf_final=cpf_final),
        "rendimentos_pj": [_fonte_pj(tributavel)],
        "rendimentos_pf": [],
        "imposto_apurado": {
            "base_calculo_brl": tributavel,
            "ir_devido_brl": "0",
            "deducoes_totais_brl": "0",
            "ir_pago_brl": "0",
        },
        "confidence": 0.95,
    }


# ADR-371: `pipeline_run_id` é NOT NULL — a fixture materializa o pai da FK em vez
# de fabricar id sintético.
async def _run_do_workspace(db, ws_id: str) -> str:
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus

    run = PipelineRun(
        id=str(uuid4()),
        workspace_id=ws_id,
        status=PipelineRunStatus.completed,
        started_at=_HOJE - timedelta(days=1),
    )
    db.add(run)
    await db.flush()
    return run.id


def _artifact(ws_id: str, run_id: str, content: dict, *, created_at: datetime):
    from backend.app.models.pipeline_artifact import PipelineArtifact

    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="extract_irpf_full",
        artifact_key=f"irpfdeclaracao_{content['contribuinte']['ano_base']}_{uuid4().hex[:6]}",
        content_json=content,
        created_at=created_at,
    )


async def _ws_com_perfil(db):
    from backend.app.models.workspace import Workspace

    ws = await factories.make_workspace(db)
    row = await db.get(Workspace, ws.id)
    row.business_profile_json = {"regime": "simples", "anexo_simples": "III"}
    await db.commit()
    return ws


def _base_pgbl(ws_id: str) -> Decimal:
    from backend.app.core.database import SyncSessionLocal

    with SyncSessionLocal() as sync_db:
        return build_cascata_input_sync(ws_id, db=sync_db).renda_tributavel_pf_irpf_anual.amount


#: (ano_base, tributável) das duas declarações; 2024 é o ano completo eleito.
_DE_2024 = (2024, "200000")
_DE_2023 = (2023, "90000")


async def _seed(db, ws_id: str, *, primeiro, segundo):
    """Semeia as duas declarações; `primeiro` é o criado há mais tempo."""
    run_id = await _run_do_workspace(db, ws_id)
    for (ano, valor), quando in ((primeiro, _HOJE - timedelta(hours=2)), (segundo, _HOJE)):
        payload = _declaracao(ano_base=ano, cpf_final="11", tributavel=valor)
        db.add(_artifact(ws_id, run_id, payload, created_at=quando))
    await db.commit()


@pytest.mark.asyncio
async def test_ano_base_nao_segue_a_ordem_de_processamento(db):
    """A row de 2023 foi criada DEPOIS e não vence: o ano eleito é 2024."""
    ws = await _ws_com_perfil(db)
    await _seed(db, ws.id, primeiro=_DE_2024, segundo=_DE_2023)

    assert _base_pgbl(ws.id) == Decimal("200000")


@pytest.mark.asyncio
async def test_falsificavel_a_ordem_inversa_devolve_o_mesmo_ano(db):
    """Braço de controle: invertidos os `created_at`, o resultado NÃO muda — sem
    este par o teste acima passaria por coincidência de ordenação, que é
    exatamente a leitura por `created_at` que ele existe para falsificar."""
    ws = await _ws_com_perfil(db)
    await _seed(db, ws.id, primeiro=_DE_2023, segundo=_DE_2024)

    assert _base_pgbl(ws.id) == Decimal("200000")


@pytest.mark.asyncio
async def test_sem_irpf_a_base_e_zero(db):
    """Workspace sem declaração: o caminho não estoura e a base não é inventada."""
    ws = await _ws_com_perfil(db)

    assert _base_pgbl(ws.id) == Decimal("0")
