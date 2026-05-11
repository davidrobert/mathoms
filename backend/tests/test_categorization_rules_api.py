"""Integration tests dos endpoints learning loop (ADR-186/188 · A12 P3 PR2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import SyncSessionLocal
from backend.app.core.security import create_access_token
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    OVERRIDE_SOURCE_RULE,
    TransactionOverride,
)
from backend.app.services.feature_flags_service import set_flag
from backend.app.services.report_publication import publish_month
from backend.tests import factories

# ─── helpers ────────────────────────────────────────────────────────────


async def _enable_flag(db: AsyncSession, ws_id: str) -> None:
    """Liga ``learning_loop_enabled`` para o workspace."""
    await set_flag(ws_id, "learning_loop_enabled", True, db=db)
    await db.commit()


async def _auth(db: AsyncSession, client: AsyncClient) -> tuple[str, str]:
    """Cria user + workspace + liga flag + injeta token."""
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    await _enable_flag(db, ws.id)
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return user.id, ws.id


def _make_run(ws_id: str) -> PipelineRun:
    return PipelineRun(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        status=PipelineRunStatus.completed,
        started_at=datetime.now(timezone.utc),
        tier_at_run="premium",
        incremental=False,
        reprocess_all=False,
        total_documents=0,
    )


def _make_e4_artifact(*, ws_id: str, run_id: str, key: str, items: list[dict]) -> PipelineArtifact:
    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="categorize_transactions",
        artifact_key=key,
        content_json={"dados": {"Outros": items}},
    )


async def _seed_e4_artifact(
    db: AsyncSession,
    *,
    ws_id: str,
    despesas_items: list[dict],
    receitas_items: list[dict] | None = None,
) -> None:
    """Seeda PipelineArtifact ``stage='categorize_transactions'`` com items E4."""
    run = _make_run(ws_id)
    db.add(run)
    db.add(_make_e4_artifact(ws_id=ws_id, run_id=run.id, key="despesas", items=despesas_items))
    if receitas_items:
        db.add(_make_e4_artifact(ws_id=ws_id, run_id=run.id, key="receitas", items=receitas_items))
    await db.commit()


def _mk_tx(
    *,
    data: str,
    descricao: str,
    valor: str = "50.00",
    banco: str = "c6bank",
    categoria: str = "Outros",
    titular: str = "Test User",
) -> dict:
    """Item E4 cru (formato ``_flatten_e4_payload`` espera). ``valor`` em string decimal (ADR-090)."""
    return {
        "data": data,
        "descricao": descricao,
        "valor": valor,
        "banco": banco,
        "categoria": categoria,
        "titular": titular,
        "moeda": "BRL",
        "tipo_conta": "conta_corrente",
        "origem": None,
    }


async def _close_month(db: AsyncSession, ws_id: str, period: str) -> None:
    """Fecha o mês via ``publish_month``."""
    run = _make_run(ws_id)
    db.add(run)
    artifact = PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run.id,
        stage="analyze_finances",
        artifact_key="analise_financeira",
        content_json={"score": 78},
    )
    db.add(artifact)
    await db.flush()
    await publish_month(ws_id, period, artifact.id, actor="user:test", db=db)
    await db.commit()


def _api(ws_id: str) -> str:
    return f"/api/workspaces/{ws_id}/categorization/rules"


async def _post_create_rule(
    client: AsyncClient, ws_id: str, *, keyword: str = "ABCDE", target_category: str = "X"
) -> str:
    """POST / + retorna rule_id (assume sucesso)."""
    resp = await client.post(
        _api(ws_id), json={"keyword": keyword, "target_category": target_category}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _make_manual_override(
    *, ws_id: str, tx: dict, new_category: str = "Lazer Manual", override_id: str | None = None
) -> TransactionOverride:
    from backend.app.services.transaction_service import generate_transaction_hash

    return TransactionOverride(
        id=override_id or str(uuid.uuid4()),
        workspace_id=ws_id,
        transaction_hash=generate_transaction_hash(tx),
        original_category="Outros",
        new_category=new_category,
        source=OVERRIDE_SOURCE_MANUAL,
        rule_id=None,
        reviewed=True,
        created_at=datetime.now(timezone.utc),
    )


def _make_rule(
    *,
    ws_id: str,
    rule_id: str,
    keyword: str,
    target_category: str = "X",
    priority: int = 100,
    enabled: bool = True,
    **extra,
) -> CategorizationRule:
    return CategorizationRule(
        id=rule_id,
        workspace_id=ws_id,
        keyword=keyword,
        target_category=target_category,
        priority=priority,
        enabled=enabled,
        created_at=datetime.now(timezone.utc),
        **extra,
    )


# ─── preview ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_preview_shape_present_when_no_matches(db: AsyncSession, client: AsyncClient):
    """Sem matches → todos os campos do shape estão presentes (não-undefined)."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    resp = await client.post(
        _api(ws_id) + "/preview",
        json={"keyword": "NETFLIX", "target_category": "Lazer"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["matches_total"] == 0
    assert payload["matches_in_closed_months"] == 0
    assert payload["matches_with_manual_override"] == 0
    assert payload["matches_blocked_internal_transfers"] == 0
    assert payload["matches_amount_total_brl_cents"] == 0
    assert payload["matches_by_month"] == {}
    assert payload["conflicts"] == []
    assert payload["low_risk"] is True
    assert payload["requires_user_confirmation"] is False


@pytest.mark.asyncio
async def test_preview_closed_month_counts_in_closed_bucket(db: AsyncSession, client: AsyncClient):
    """tx em mês fechado conta em ``matches_in_closed_months`` E em ``matches_total``."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(
        db,
        ws_id=ws_id,
        despesas_items=[
            _mk_tx(data="2026-01-15", descricao="NETFLIX BR"),
            _mk_tx(data="2026-03-15", descricao="NETFLIX BR"),
        ],
    )
    await _close_month(db, ws_id, "202601")
    resp = await client.post(
        _api(ws_id) + "/preview",
        json={"keyword": "NETFLIX", "target_category": "Lazer"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["matches_total"] == 2
    assert payload["matches_in_closed_months"] == 1
    assert payload["low_risk"] is False  # closed_month presente


@pytest.mark.asyncio
async def test_preview_manual_override_counts_in_manual_bucket(
    db: AsyncSession, client: AsyncClient
):
    """Override manual prévio na mesma tx → ``matches_with_manual_override``."""
    _, ws_id = await _auth(db, client)
    tx = _mk_tx(data="2026-03-15", descricao="NETFLIX BR")
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[tx])
    db.add(_make_manual_override(ws_id=ws_id, tx=tx))
    await db.commit()
    resp = await client.post(
        _api(ws_id) + "/preview",
        json={"keyword": "NETFLIX", "target_category": "Lazer"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["matches_total"] == 1
    assert payload["matches_with_manual_override"] == 1


@pytest.mark.asyncio
async def test_preview_lists_conflict_with_existing_rule(db: AsyncSession, client: AsyncClient):
    """Rule ativa com mesma keyword → entra em ``conflicts``."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    db.add(
        _make_rule(
            ws_id=ws_id,
            rule_id="rule-existing-123",
            keyword="NETFLIX",
            target_category="Streaming",
            priority=200,
        )
    )
    await db.commit()
    resp = await client.post(
        _api(ws_id) + "/preview",
        json={"keyword": "NETFLIX", "target_category": "Lazer"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload["conflicts"]) == 1
    assert payload["conflicts"][0]["rule_id"] == "rule-existing-123"
    assert payload["conflicts"][0]["target_category"] == "Streaming"
    assert payload["low_risk"] is False  # conflito presente


@pytest.mark.asyncio
async def test_preview_short_keyword_emits_warning(db: AsyncSession, client: AsyncClient):
    """Keyword <4 chars → warning ``keyword_too_short``."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    resp = await client.post(
        _api(ws_id) + "/preview",
        json={"keyword": "PIX", "target_category": "Lazer"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    codes = {w["code"] for w in payload["warnings"]}
    assert "keyword_too_short" in codes


# ─── POST / (create) ────────────────────────────────────────────────────


def _count_rule_overrides(ws_id: str) -> int:
    with SyncSessionLocal() as sync_db:
        return len(
            sync_db.execute(
                select(TransactionOverride).where(
                    TransactionOverride.workspace_id == ws_id,
                    TransactionOverride.source == OVERRIDE_SOURCE_RULE,
                )
            )
            .scalars()
            .all()
        )


@pytest.mark.asyncio
async def test_create_rule_applies_retroactive_in_open_months(
    db: AsyncSession, client: AsyncClient
):
    """Cria regra → cria N overrides ``source='rule'`` em meses abertos."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(
        db,
        ws_id=ws_id,
        despesas_items=[
            _mk_tx(data="2026-03-15", descricao="NETFLIX BR"),
            _mk_tx(data="2026-04-15", descricao="NETFLIX BR"),
        ],
    )
    resp = await client.post(
        _api(ws_id), json={"keyword": "NETFLIX", "target_category": "Lazer", "priority": 100}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["applied_count"] == 2
    assert _count_rule_overrides(ws_id) == 2


@pytest.mark.asyncio
async def test_create_rule_skips_closed_months(db: AsyncSession, client: AsyncClient):
    """tx em mês fechado NÃO recebe override; rule.applied_count exclui ela."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(
        db,
        ws_id=ws_id,
        despesas_items=[
            _mk_tx(data="2026-01-15", descricao="NETFLIX BR"),
            _mk_tx(data="2026-03-15", descricao="NETFLIX BR"),
        ],
    )
    await _close_month(db, ws_id, "202601")
    resp = await client.post(
        _api(ws_id),
        json={"keyword": "NETFLIX", "target_category": "Lazer"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["applied_count"] == 1  # só 202603


@pytest.mark.asyncio
async def test_create_rule_preserves_manual_override_sticky(db: AsyncSession, client: AsyncClient):
    """Override manual prévio fica intacto (sticky)."""
    _, ws_id = await _auth(db, client)
    tx = _mk_tx(data="2026-03-15", descricao="NETFLIX BR")
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[tx])
    manual_id = str(uuid.uuid4())
    db.add(_make_manual_override(ws_id=ws_id, tx=tx, override_id=manual_id))
    await db.commit()
    resp = await client.post(_api(ws_id), json={"keyword": "NETFLIX", "target_category": "Lazer"})
    assert resp.status_code == 201

    with SyncSessionLocal() as sync_db:
        manual = sync_db.get(TransactionOverride, manual_id)
        assert manual.source == OVERRIDE_SOURCE_MANUAL
        assert manual.new_category == "Lazer Manual"


@pytest.mark.asyncio
async def test_create_rule_conflict_exact_triple_returns_409(db: AsyncSession, client: AsyncClient):
    """409 com ``existing_rule_id`` quando (ws, keyword, target) já existe."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    db.add(
        _make_rule(ws_id=ws_id, rule_id="rule-existing", keyword="NETFLIX", target_category="Lazer")
    )
    await db.commit()
    resp = await client.post(_api(ws_id), json={"keyword": "NETFLIX", "target_category": "Lazer"})
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["code"] == "rule_already_exists"
    assert detail["existing_rule_id"] == "rule-existing"


@pytest.mark.asyncio
async def test_create_rule_different_target_succeeds(db: AsyncSession, client: AsyncClient):
    """Outra regra com mesma keyword + target diferente → 201 (parcial uniq não bloqueia)."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    db.add(
        _make_rule(
            ws_id=ws_id, rule_id="rule-streaming", keyword="NETFLIX", target_category="Streaming"
        )
    )
    await db.commit()
    resp = await client.post(_api(ws_id), json={"keyword": "NETFLIX", "target_category": "Lazer"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_rule_hard_cap_returns_422(db: AsyncSession, client: AsyncClient):
    """422 ``hard_cap_exceeded`` quando workspace já tem ``rule_cap_override``."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    from backend.app.models.workspace import Workspace as Ws

    ws_row = (await db.execute(select(Ws).where(Ws.id == ws_id))).scalar_one()
    ws_row.rule_cap_override = 2
    db.add(_make_rule(ws_id=ws_id, rule_id="r1", keyword="A1"))
    db.add(_make_rule(ws_id=ws_id, rule_id="r2", keyword="A2"))
    await db.commit()
    resp = await client.post(_api(ws_id), json={"keyword": "TERCEIRA", "target_category": "X"})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "hard_cap_exceeded"
    assert detail["limit"] == 2


# ─── DELETE /{id} ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_rule_soft_deletes_rule_and_cascades_overrides(
    db: AsyncSession, client: AsyncClient
):
    """soft-delete: rule.deleted_at + overrides ``source='rule'`` ganham ``deleted_at``."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(
        db, ws_id=ws_id, despesas_items=[_mk_tx(data="2026-03-15", descricao="NETFLIX BR")]
    )
    rule_id = await _post_create_rule(client, ws_id, keyword="NETFLIX", target_category="Lazer")
    resp = await client.delete(f"{_api(ws_id)}/{rule_id}")
    assert resp.status_code == 204

    with SyncSessionLocal() as sync_db:
        rule = sync_db.get(CategorizationRule, rule_id)
        assert rule.deleted_at is not None
        overrides = (
            sync_db.execute(
                select(TransactionOverride).where(TransactionOverride.rule_id == rule_id)
            )
            .scalars()
            .all()
        )
        assert all(o.deleted_at is not None for o in overrides)


@pytest.mark.asyncio
async def test_delete_rule_does_not_touch_manual_overrides(db: AsyncSession, client: AsyncClient):
    """Manual override de outra txn fica intacto pós-delete."""
    _, ws_id = await _auth(db, client)
    tx_rule = _mk_tx(data="2026-03-15", descricao="NETFLIX BR")
    tx_manual = _mk_tx(data="2026-03-16", descricao="UBER EATS")
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[tx_rule, tx_manual])
    manual_id = str(uuid.uuid4())
    db.add(
        _make_manual_override(
            ws_id=ws_id, tx=tx_manual, new_category="Comida", override_id=manual_id
        )
    )
    await db.commit()

    resp = await client.post(_api(ws_id), json={"keyword": "NETFLIX", "target_category": "Lazer"})
    rule_id = resp.json()["id"]
    await client.delete(f"{_api(ws_id)}/{rule_id}")

    with SyncSessionLocal() as sync_db:
        manual = sync_db.get(TransactionOverride, manual_id)
        assert manual.deleted_at is None
        assert manual.source == OVERRIDE_SOURCE_MANUAL


@pytest.mark.asyncio
async def test_delete_rule_bumps_revert_count_rule_disabled(db: AsyncSession, client: AsyncClient):
    """``revert_count_rule_disabled`` incrementa pós-DELETE."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    resp = await client.post(
        _api(ws_id),
        json={"keyword": "ABCDE", "target_category": "X"},
    )
    rule_id = resp.json()["id"]

    resp = await client.delete(f"{_api(ws_id)}/{rule_id}")
    assert resp.status_code == 204

    with SyncSessionLocal() as sync_db:
        rule = sync_db.get(CategorizationRule, rule_id)
        assert rule.revert_count_rule_disabled == 1


@pytest.mark.asyncio
async def test_recreate_rule_after_delete_finds_no_active_conflict(
    db: AsyncSession, client: AsyncClient
):
    """Service não levanta ``RuleAlreadyExistsError`` pós-soft-delete (partial unique ADR-188)."""
    from backend.app.application.categorization.rule_management_service import (
        _find_existing_rule,
    )

    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    resp = await client.post(_api(ws_id), json={"keyword": "ABCDE", "target_category": "X"})
    await client.delete(f"{_api(ws_id)}/{resp.json()['id']}")
    with SyncSessionLocal() as sync_db:
        assert _find_existing_rule(sync_db, ws_id, "ABCDE", "X") is None


@pytest.mark.asyncio
async def test_delete_rule_idempotent_second_call_404(db: AsyncSession, client: AsyncClient):
    """2º DELETE → 404 (idempotência via ``deleted_at`` check)."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    resp = await client.post(
        _api(ws_id),
        json={"keyword": "ABCDE", "target_category": "X"},
    )
    rule_id = resp.json()["id"]

    r1 = await client.delete(f"{_api(ws_id)}/{rule_id}")
    r2 = await client.delete(f"{_api(ws_id)}/{rule_id}")
    assert r1.status_code == 204
    assert r2.status_code == 404


# ─── GET / ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_rules_default_pagination(db: AsyncSession, client: AsyncClient):
    """Lista paginada com meta carrega cap/warnings."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    # priority 100+i para verificar ordenação desc no list_rules
    for i in range(3):
        db.add(_make_rule(ws_id=ws_id, rule_id=f"r{i}", keyword=f"KW{i}", priority=100 + i))
    await db.commit()

    resp = await client.get(_api(ws_id))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["rules"]) == 3
    assert body["meta"]["count"] == 3
    assert body["meta"]["hard_cap"] == 200
    assert body["meta"]["soft_cap"] == 50


@pytest.mark.asyncio
async def test_list_rules_applied_count_visible(db: AsyncSession, client: AsyncClient):
    """``applied_count`` carrega valor histórico (pós-criação)."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(
        db,
        ws_id=ws_id,
        despesas_items=[_mk_tx(data="2026-03-15", descricao="NETFLIX BR")],
    )
    resp = await client.post(
        _api(ws_id),
        json={"keyword": "NETFLIX", "target_category": "Lazer"},
    )
    assert resp.status_code == 201

    listing = await client.get(_api(ws_id))
    rules = listing.json()["rules"]
    assert len(rules) == 1
    assert rules[0]["applied_count"] == 1


@pytest.mark.asyncio
async def test_list_rules_filter_by_enabled(db: AsyncSession, client: AsyncClient):
    """Query ``?enabled=true|false`` filtra."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    db.add(_make_rule(ws_id=ws_id, rule_id="r-on", keyword="ON", enabled=True))
    db.add(_make_rule(ws_id=ws_id, rule_id="r-off", keyword="OFF", enabled=False))
    await db.commit()

    r_on = await client.get(_api(ws_id) + "?enabled=true")
    r_off = await client.get(_api(ws_id) + "?enabled=false")
    assert {x["id"] for x in r_on.json()["rules"]} == {"r-on"}
    assert {x["id"] for x in r_off.json()["rules"]} == {"r-off"}


@pytest.mark.asyncio
async def test_list_rules_revert_counts_visible(db: AsyncSession, client: AsyncClient):
    """``revert_count_manual_edit`` + ``revert_count_rule_disabled`` ambos no payload."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    db.add(
        _make_rule(
            ws_id=ws_id,
            rule_id="r1",
            keyword="KW",
            revert_count_manual_edit=7,
            revert_count_rule_disabled=2,
        )
    )
    await db.commit()

    resp = await client.get(_api(ws_id))
    rule = resp.json()["rules"][0]
    assert rule["revert_count_manual_edit"] == 7
    assert rule["revert_count_rule_disabled"] == 2


# ─── POST /{id}/disable ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disable_rule_toggles_without_cascade(db: AsyncSession, client: AsyncClient):
    """``enabled=true→false`` sem mexer em overrides."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(
        db, ws_id=ws_id, despesas_items=[_mk_tx(data="2026-03-15", descricao="NETFLIX BR")]
    )
    rule_id = await _post_create_rule(client, ws_id, keyword="NETFLIX", target_category="Lazer")
    resp = await client.post(f"{_api(ws_id)}/{rule_id}/disable")
    assert resp.status_code == 204

    with SyncSessionLocal() as sync_db:
        rule = sync_db.get(CategorizationRule, rule_id)
        assert rule.enabled is False
        assert rule.deleted_at is None
        rows = (
            sync_db.execute(
                select(TransactionOverride).where(TransactionOverride.rule_id == rule_id)
            )
            .scalars()
            .all()
        )
        assert all(o.deleted_at is None for o in rows)


@pytest.mark.asyncio
async def test_disable_rule_idempotent(db: AsyncSession, client: AsyncClient):
    """Disable 2× → 204 + 204 (idempotente, sem error)."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    resp = await client.post(_api(ws_id), json={"keyword": "ABCDE", "target_category": "X"})
    rule_id = resp.json()["id"]

    r1 = await client.post(f"{_api(ws_id)}/{rule_id}/disable")
    r2 = await client.post(f"{_api(ws_id)}/{rule_id}/disable")
    assert r1.status_code == 204
    assert r2.status_code == 204


@pytest.mark.asyncio
async def test_disable_then_recreate_same_rule_does_not_reapply(
    db: AsyncSession, client: AsyncClient
):
    """Após disable + nova rule mesma keyword, override anterior fica como estava."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(
        db,
        ws_id=ws_id,
        despesas_items=[_mk_tx(data="2026-03-15", descricao="NETFLIX BR")],
    )
    resp1 = await client.post(_api(ws_id), json={"keyword": "NETFLIX", "target_category": "Lazer"})
    rule_id_1 = resp1.json()["id"]
    await client.post(f"{_api(ws_id)}/{rule_id_1}/disable")

    # Cria nova com mesma triple — ela apenas NÃO conflita pois enabled=False
    # mas deleted_at IS NULL, então parcial unique pega → 409.
    # Aceito: confirma comportamento documentado (disable mantém row ativa).
    resp2 = await client.post(_api(ws_id), json={"keyword": "NETFLIX", "target_category": "Lazer"})
    assert resp2.status_code == 409


# ─── feature flag ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_endpoints_return_403_when_flag_disabled(db: AsyncSession, client: AsyncClient):
    """403 ``learning_loop_disabled`` quando flag OFF (default)."""
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    # Não liga a flag.
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.get(_api(ws.id))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "learning_loop_disabled"


# ─── PR3: async apply (>SYNC_APPLY_THRESHOLD) ──────────────────────────


@pytest.mark.asyncio
async def test_create_rule_returns_202_when_estimate_exceeds_threshold(
    db: AsyncSession, client: AsyncClient
):
    """>``SYNC_APPLY_THRESHOLD`` matches → 202 + ``job_id`` + status pending.

    Não dispara Celery (mock ``delay``), apenas valida path do endpoint.
    """
    from unittest.mock import patch

    _, ws_id = await _auth(db, client)
    items = [_mk_tx(data="2026-04-15", descricao=f"UBER {i}", valor="10.00") for i in range(501)]
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=items)

    with (
        patch(
            "backend.app.tasks.categorization_apply.apply_rule_retroactive_task.delay"
        ) as m_delay,
        patch("backend.app.services.rule_apply_state.mark_pending") as m_mark,
    ):
        resp = await client.post(
            _api(ws_id),
            json={"keyword": "UBER", "target_category": "Transporte · App"},
        )
    assert resp.status_code == 202, resp.text
    payload = resp.json()
    assert payload["status"] == "pending"
    assert payload["rule_id"]
    assert payload["job_id"]
    assert "background" in payload["message"].lower()
    m_delay.assert_called_once()
    m_mark.assert_called_once()


@pytest.mark.asyncio
async def test_create_rule_returns_201_when_estimate_within_threshold(
    db: AsyncSession, client: AsyncClient
):
    """≤threshold matches → 201 (path sync continua funcional)."""
    _, ws_id = await _auth(db, client)
    items = [_mk_tx(data="2026-04-15", descricao=f"NETFLIX {i}") for i in range(3)]
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=items)

    resp = await client.post(
        _api(ws_id),
        json={"keyword": "NETFLIX", "target_category": "Lazer"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["keyword"] == "NETFLIX"


@pytest.mark.asyncio
async def test_get_apply_status_returns_unknown_when_never_dispatched(
    db: AsyncSession, client: AsyncClient
):
    """Rule criada via path sync nunca passou pelo Celery → status ``unknown``."""
    _, ws_id = await _auth(db, client)
    await _seed_e4_artifact(db, ws_id=ws_id, despesas_items=[])
    rule_id = await _post_create_rule(client, ws_id, keyword="NETFLIX")
    resp = await client.get(f"{_api(ws_id)}/{rule_id}/apply-status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "unknown"


@pytest.mark.asyncio
async def test_get_apply_status_reflects_pending_state(db: AsyncSession, client: AsyncClient):
    """``mark_pending`` + GET → status pending + job_id."""
    from unittest.mock import patch

    _, ws_id = await _auth(db, client)
    rule_id = "rule-x"
    with patch(
        "backend.app.services.rule_apply_state.get_status",
        return_value={
            "status": "pending",
            "job_id": "job-1",
            "started_at": "2026-05-11T00:00:00+00:00",
            "applied_count": 0,
            "failed_count": 0,
        },
    ):
        resp = await client.get(f"{_api(ws_id)}/{rule_id}/apply-status")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "pending"
    assert payload["job_id"] == "job-1"


@pytest.mark.asyncio
async def test_precondition_failed_returns_403_with_code(db: AsyncSession, client: AsyncClient):
    """ADR-188 PR3 senior-cto R2: 403 vem do handler ``PreconditionFailedError``."""
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.get(_api(ws.id))
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail.get("code") == "learning_loop_disabled"
    assert "learning_loop_disabled" not in detail["message"]  # message é descritivo
