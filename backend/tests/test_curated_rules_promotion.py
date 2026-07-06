"""Promoção em lote do ruleset curado A28.l5 — invariantes do learning loop (ADR-186/188)."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from backend.app.application.categorization import _apply_engine
from backend.app.application.categorization.curated_rules import (
    CURATED_RULES_A28_L5,
    VALID_EXPENSE_CATEGORIES,
    CuratedRule,
    promote_curated_rules,
)
from backend.app.application.categorization.rule_preview_service import empty_detector
from backend.app.core.database import SyncSessionLocal
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    TransactionOverride,
)
from backend.app.models.workspace import Workspace
from backend.app.schemas.transactions import TransactionItem
from backend.app.services.transaction_service import generate_transaction_hash
from backend.tests import factories

# ─── hygiene estática do ruleset (PII-zero + template v1) ───────────────


def test_curated_targets_are_valid_template_categories():
    targets = {r.target_category for r in CURATED_RULES_A28_L5}
    assert targets <= VALID_EXPENSE_CATEGORIES


def test_curated_keywords_are_uppercase_and_generic():
    """Keyword de estabelecimento/segmento: uppercase, sem dígitos (CPF/valor), >=4 chars."""
    for rule in CURATED_RULES_A28_L5:
        assert rule.keyword == rule.keyword.upper(), rule.keyword
        assert not re.search(r"\d", rule.keyword), f"dígito em keyword: {rule.keyword!r}"
        assert len(rule.keyword) >= 4, rule.keyword


def test_curated_ruleset_has_no_duplicate_triples():
    triples = [(r.keyword, r.target_category) for r in CURATED_RULES_A28_L5]
    assert len(triples) == len(set(triples))


# ─── helpers ─────────────────────────────────────────────────────────────


def _item_fields(descricao: str, data: str, valor: str, categoria: str) -> dict:
    return {
        "data": data,
        "descricao": descricao,
        "valor": Decimal(valor),
        "banco": "c6bank",
        "categoria": categoria,
        "origem": None,
        "tipo_conta": "conta_corrente",
        "titular": "Test User",
        "moeda": "BRL",
        "tipo": "debito",
        "is_overridden": False,
    }


def _mk_item(
    *,
    descricao: str,
    data: str = "2026-03-15",
    valor: str = "50.00",
    categoria: str = "nao_identificado",
) -> TransactionItem:
    raw = {
        "data": data,
        "descricao": descricao,
        "valor": valor,
        "banco": "c6bank",
        "titular": "Test User",
    }
    tx_hash = generate_transaction_hash(raw)
    fields = _item_fields(descricao, data, valor, categoria)
    return TransactionItem(transaction_hash=tx_hash, row_id=f"{tx_hash}:0", **fields)


def _promote(ws_id: str, transactions: list, rules: tuple[CuratedRule, ...]):
    with SyncSessionLocal() as sync_db:
        workspace = sync_db.get(Workspace, ws_id)
        return promote_curated_rules(
            workspace=workspace,
            detector=empty_detector(),
            transactions=transactions,
            db=sync_db,
            rules=rules,
        )


def _list_overrides(ws_id: str) -> list[TransactionOverride]:
    from sqlalchemy import select

    with SyncSessionLocal() as sync_db:
        return list(
            sync_db.execute(
                select(TransactionOverride).where(TransactionOverride.workspace_id == ws_id)
            ).scalars()
        )


def _count_active_rules(ws_id: str) -> int:
    from sqlalchemy import func, select

    with SyncSessionLocal() as sync_db:
        return int(
            sync_db.execute(
                select(func.count(CategorizationRule.id)).where(
                    CategorizationRule.workspace_id == ws_id,
                    CategorizationRule.deleted_at.is_(None),
                )
            ).scalar_one()
        )


_PADARIA_RULES = (CuratedRule("PADARIA", "alimentacao"),)


# ─── comportamento da promoção ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_promotion_creates_rule_and_applies_retroactive(db):
    ws = await factories.make_workspace(db)
    await db.commit()
    txs = [_mk_item(descricao="PADARIA DO BAIRRO")]

    results = _promote(ws.id, txs, _PADARIA_RULES)

    assert [(r.status, r.applied_count) for r in results] == [("created", 1)]
    overrides = _list_overrides(ws.id)
    assert len(overrides) == 1
    assert overrides[0].new_category == "alimentacao"
    assert overrides[0].source == "rule"


@pytest.mark.asyncio
async def test_promotion_is_idempotent_second_run_skips(db):
    ws = await factories.make_workspace(db)
    await db.commit()
    txs = [_mk_item(descricao="PADARIA DO BAIRRO")]

    first = _promote(ws.id, txs, _PADARIA_RULES)
    second = _promote(ws.id, txs, _PADARIA_RULES)

    assert first[0].status == "created"
    assert second[0].status == "skipped_exists"
    assert second[0].applied_count == 1
    assert _count_active_rules(ws.id) == 1


def _seed_manual_override(ws_id: str, tx: TransactionItem, *, new_category: str) -> None:
    with SyncSessionLocal() as sync_db:
        sync_db.add(
            TransactionOverride(
                id=str(uuid.uuid4()),
                workspace_id=ws_id,
                transaction_hash=tx.transaction_hash,
                original_category="nao_identificado",
                new_category=new_category,
                source=OVERRIDE_SOURCE_MANUAL,
                rule_id=None,
                reviewed=True,
                created_at=datetime.now(timezone.utc),
            )
        )
        sync_db.commit()


@pytest.mark.asyncio
async def test_promotion_does_not_overwrite_manual_override(db):
    """Invariante ADR-186 §D2: override manual é sticky — regra nova não sobrescreve."""
    ws = await factories.make_workspace(db)
    await db.commit()
    tx = _mk_item(descricao="PADARIA DO BAIRRO")
    _seed_manual_override(ws.id, tx, new_category="lazer_viagens")

    results = _promote(ws.id, [tx], _PADARIA_RULES)

    assert results[0].status == "created"
    assert results[0].applied_count == 0
    overrides = _list_overrides(ws.id)
    assert len(overrides) == 1
    assert overrides[0].source == OVERRIDE_SOURCE_MANUAL
    assert overrides[0].new_category == "lazer_viagens"


@pytest.mark.asyncio
async def test_promotion_skips_closed_month(db, monkeypatch):
    """Invariante ADR-186: mês fechado é imutável — tx no período fechado fica intocada."""
    ws = await factories.make_workspace(db)
    await db.commit()
    closed_tx = _mk_item(descricao="PADARIA CENTRAL", data="2026-01-10")
    open_tx = _mk_item(descricao="PADARIA DO BAIRRO", data="2026-03-15")
    monkeypatch.setattr(
        _apply_engine,
        "is_month_closed_sync",
        lambda ws_id, period, db: period == "202601",
    )

    results = _promote(ws.id, [closed_tx, open_tx], _PADARIA_RULES)

    assert results[0].applied_count == 1
    overrides = _list_overrides(ws.id)
    assert len(overrides) == 1
    assert overrides[0].transaction_hash == open_tx.transaction_hash


@pytest.mark.asyncio
async def test_promotion_rejects_target_outside_template(db):
    ws = await factories.make_workspace(db)
    await db.commit()

    with pytest.raises(ValueError, match="fora do category_template"):
        _promote(ws.id, [], (CuratedRule("PADARIA", "categoria_inexistente"),))
