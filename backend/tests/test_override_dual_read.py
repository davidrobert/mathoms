"""ADR-282 slice 4 — cutover de LEITURA: match de override em ``natural_key_hash``
v2 com fallback v1 durante a janela, gated por ``override_natural_key_v2_enabled``.
Flag-OFF = comportamento legado byte-idêntico; flag-ON corrige drift de sufixo PIX
e não cruza fatura-estorno com a gêmea débito. Fallback v1 emite log estruturado
``mathoms.categorization.dualread`` (gate empírico da M2)."""

from __future__ import annotations

import importlib
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.application.categorization._apply_engine import apply_retroactive_sync
from backend.app.application.categorization.rule_preview_service import (
    empty_detector,
    preview_rule,
)
from backend.app.application.transaction.create_override import create_override
from backend.app.application.transaction.delete_override import delete_override
from backend.app.core.database import SyncSessionLocal
from backend.app.models.audit_log import AuditLog
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    OVERRIDE_SOURCE_RULE,
    TransactionOverride,
)
from backend.app.schemas.transactions import TransactionItem, TransactionOverrideRequest
from backend.app.services.audit import AuditAction
from backend.app.services.categorization_learning_loop import apply_learning_loop
from backend.app.services.feature_flags_service import set_flag
from backend.app.services.override_dual_read import (
    OVERRIDE_NATURAL_KEY_V2_FLAG,
    OverrideMatchIndex,
    persist_dualread_snapshot,
)
from backend.app.services.override_identity import (
    identity_from_classified_tx,
    identity_from_transaction_item,
)
from backend.app.services.transaction_service import apply_overrides
from backend.tests import factories
from pipeline.domain.services.transaction_classifier import ClassifiedTransaction

PIX_PLAIN = "PAGAMENTO LOJA"
PIX_DRIFTED = "PAGAMENTO LOJA — TRANSF ENVIADA PIX"


def _item(**over) -> TransactionItem:
    base = dict(
        data="2026-03-15",
        descricao=PIX_PLAIN,
        valor=Decimal("50.0"),
        banco="c6bank",
        categoria="Lazer",
        tipo_conta="conta_corrente",
        titular="Test User",
        moeda="BRL",
        tipo="debito",
        transaction_hash="v1-atual",
        row_id="v1-atual:0",
    )
    base.update(over)
    return TransactionItem(**base)


def _override(**over) -> TransactionOverride:
    base = dict(
        id=str(uuid.uuid4()),
        transaction_hash="v1-antigo",
        original_category="Lazer",
        new_category="Alimentacao",
        source=OVERRIDE_SOURCE_MANUAL,
        reviewed=True,
        created_at=datetime.now(timezone.utc),
        deleted_at=None,
    )
    base.update(over)
    return TransactionOverride(**base)


def _v2_of(item: TransactionItem) -> str:
    return identity_from_transaction_item(item).natural_key_hash


# -- janela dual-read (unit, sem DB) --


def test_dual_read_window() -> None:
    """Backfillado v2 (v1 drifted) + legado v1-only coexistem: ambos casam flag-ON."""
    drifted = _item(descricao=PIX_DRIFTED, transaction_hash="v1-drifted")
    backfilled = _override(transaction_hash="v1-antigo", natural_key_hash=_v2_of(drifted))
    legacy_item = _item(descricao="OUTRA COMPRA", transaction_hash="v1-legado")
    legacy = _override(transaction_hash="v1-legado", natural_key_hash=None)
    index = OverrideMatchIndex.from_overrides(
        [backfilled, legacy], workspace_id="ws", v2_enabled=True
    )

    assert index.match(natural_key_hash=_v2_of(drifted), legacy_hash="v1-drifted") is backfilled
    assert index.match(natural_key_hash=_v2_of(legacy_item), legacy_hash="v1-legado") is legacy
    assert index.v1_fallback_count == 1  # só o legado caiu para v1


def test_flag_off_match_is_v1_only() -> None:
    """Flag-OFF = comportamento atual: v2 é ignorado; só v1 idêntico casa."""
    drifted = _item(descricao=PIX_DRIFTED, transaction_hash="v1-drifted")
    backfilled = _override(transaction_hash="v1-antigo", natural_key_hash=_v2_of(drifted))
    index = OverrideMatchIndex.from_overrides([backfilled], workspace_id="ws", v2_enabled=False)

    assert index.match(natural_key_hash=_v2_of(drifted), legacy_hash="v1-drifted") is None
    assert index.match(natural_key_hash=None, legacy_hash="v1-antigo") is backfilled
    assert index.v1_fallback_count == 0  # flag-OFF não é fallback


class _CapturingHandler(logging.Handler):
    """Handler anexado direto ao logger do módulo — imune a propagate/root config."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@contextmanager
def _dualread_log_capture():
    from backend.app.services import override_dual_read

    handler = _CapturingHandler()
    logger = override_dual_read.logger
    previous_level = logger.level
    logger.disabled = False  # fileConfig do Alembic (guardrails) desativa loggers existentes
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


def test_v1_fallback_emits_structured_log_without_pii() -> None:
    legacy = _override(transaction_hash="v1-legado", natural_key_hash=None)
    index = OverrideMatchIndex.from_overrides([legacy], workspace_id="ws-log", v2_enabled=True)
    with _dualread_log_capture() as handler:
        index.match(natural_key_hash="ffffffffffffffff", legacy_hash="v1-legado")
        index.match(natural_key_hash="ffffffffffffffff", legacy_hash="nao-existe")
    records = [r for r in handler.records if getattr(r, "event", "") == "v1_fallback"]
    assert len(records) == 1  # miss total não loga; só match que caiu para v1
    assert records[0].workspace_id == "ws-log"
    assert records[0].v1_fallback_count == 1
    for pii_attr in ("descricao", "valor", "titular"):
        assert not hasattr(records[0], pii_attr)


# -- casos de domínio no read-path do match (ADR-282 critério de aceite) --


def test_pix_suffix_drift_matches_via_v2_flag_on() -> None:
    """Drift de sufixo PIX (ADR-255): re-extração muda o v1; flag-ON reata via v2."""
    original = _item(descricao=PIX_PLAIN, transaction_hash="v1-original")
    reextracted = _item(descricao=PIX_DRIFTED, transaction_hash="v1-reextraido")
    override = _override(transaction_hash="v1-original", natural_key_hash=_v2_of(original))

    flag_on = OverrideMatchIndex.from_overrides([override], workspace_id="ws", v2_enabled=True)
    applied = apply_overrides([reextracted], flag_on)
    assert applied[0].categoria == "Alimentacao"
    assert applied[0].is_overridden is True

    flag_off = OverrideMatchIndex.from_overrides([override], workspace_id="ws", v2_enabled=False)
    orphaned = apply_overrides([reextracted], flag_off)
    assert orphaned[0].categoria == "Lazer"  # o bug vivo que o cutover corrige


def test_fatura_estorno_does_not_cross_match_debit_twin() -> None:
    """Estorno de fatura (credit) e a gêmea débito têm v2 distintos — sem cross-match."""
    estorno = _item(
        tipo="credito",
        valor=Decimal("-120.0"),
        tipo_conta="fatura_cartao",
        transaction_hash="v1-estorno",
    )
    debito = _item(
        tipo="debito",
        valor=Decimal("120.0"),
        tipo_conta="fatura_cartao",
        transaction_hash="v1-debito",
    )
    override = _override(transaction_hash="v1-estorno", natural_key_hash=_v2_of(estorno))
    index = OverrideMatchIndex.from_overrides([override], workspace_id="ws", v2_enabled=True)

    assert index.match(natural_key_hash=_v2_of(estorno), legacy_hash="v1-estorno") is override
    assert index.match(natural_key_hash=_v2_of(debito), legacy_hash="v1-debito") is None


# -- integração: call-sites com flag por workspace --


async def _ws_with_flag(db, *, enabled: bool):
    ws = await factories.make_workspace(db)
    if enabled:
        await set_flag(ws.id, OVERRIDE_NATURAL_KEY_V2_FLAG, True, db=db)
    await db.commit()
    return ws


def _persisted_override(ws_id: str, **over) -> TransactionOverride:
    return _override(workspace_id=ws_id, **over)


async def _arrange_drifted(db, monkeypatch, *, enabled: bool, module: str):
    """Workspace + override com v1 drifted/mesmo v2 + stub de ``load_transactions``."""
    ws = await _ws_with_flag(db, enabled=enabled)
    item = _item(transaction_hash="v1-atual")
    db.add(_persisted_override(ws.id, transaction_hash="v1-drifted", natural_key_hash=_v2_of(item)))
    await db.commit()
    monkeypatch.setattr(
        importlib.import_module(module), "load_transactions", lambda *a, **k: [item]
    )
    return ws, item


async def _ws_rows(db, ws_id: str) -> list[TransactionOverride]:
    result = await db.execute(
        select(TransactionOverride).where(TransactionOverride.workspace_id == ws_id)
    )
    return list(result.scalars().all())


def _sync_rows(sync_db, ws_id: str) -> list[TransactionOverride]:
    stmt = select(TransactionOverride).where(TransactionOverride.workspace_id == ws_id)
    return list(sync_db.execute(stmt).scalars().all())


@pytest.mark.asyncio
async def test_create_override_flag_on_updates_via_v2_without_duplicate(db, monkeypatch):
    """FE manda hash v1 atual; linha existente tem v1 drifted + mesmo v2 → update, não duplica."""
    ws, item = await _arrange_drifted(
        db, monkeypatch, enabled=True, module="backend.app.application.transaction.create_override"
    )
    await create_override(
        ws.id, "v1-atual", TransactionOverrideRequest(new_category="Restaurantes"), db=db
    )
    rows = await _ws_rows(db, ws.id)
    assert len(rows) == 1
    assert rows[0].new_category == "Restaurantes"
    assert rows[0].natural_key_hash == _v2_of(item)


@pytest.mark.asyncio
async def test_create_override_flag_off_keeps_legacy_insert(db, monkeypatch):
    """Zero-behavior-change: flag-OFF ignora o v2 igual e insere por v1 (comportamento atual)."""
    ws, _ = await _arrange_drifted(
        db, monkeypatch, enabled=False, module="backend.app.application.transaction.create_override"
    )
    await create_override(
        ws.id, "v1-atual", TransactionOverrideRequest(new_category="Restaurantes"), db=db
    )
    assert len(await _ws_rows(db, ws.id)) == 2  # documenta o comportamento legado preservado


@pytest.mark.asyncio
async def test_delete_override_flag_on_matches_via_v2(db, monkeypatch):
    ws, _ = await _arrange_drifted(
        db, monkeypatch, enabled=True, module="backend.app.application.transaction.delete_override"
    )
    await delete_override(ws.id, "v1-atual", db=db)
    assert await _ws_rows(db, ws.id) == []


def _classified(*, rule_id: str | None = None, **over) -> ClassifiedTransaction:
    base = dict(
        kind="despesa",
        data="2026-03-15",
        descricao=PIX_PLAIN,
        valor=50.0,
        banco="c6bank",
        moeda="BRL",
        tipo_conta="conta_corrente",
        titular="Test User",
        tipo="debito",
        categoria="Lazer",
        learned_rule_id=rule_id,
    )
    base.update(over)
    return ClassifiedTransaction(**base)


def _insert_rule(sync_db, *, workspace_id: str, keyword: str, target: str) -> CategorizationRule:
    rule = CategorizationRule(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        keyword=keyword,
        target_category=target,
        priority=100,
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )
    sync_db.add(rule)
    sync_db.flush()
    return rule


def _apply_rule_sync(sync_db, *, ws_id: str, rule, item) -> int:
    return apply_retroactive_sync(
        workspace_id=ws_id,
        rule=rule,
        detector=empty_detector(),
        transactions=[item],
        db=sync_db,
    )


def _add_same_rule_override(sync_db, ws_id: str, rule, item) -> None:
    sync_db.add(
        _persisted_override(
            ws_id,
            transaction_hash="v1-drifted",
            natural_key_hash=_v2_of(item),
            source=OVERRIDE_SOURCE_RULE,
            rule_id=rule.id,
            new_category="Compras",
        )
    )


@pytest.mark.asyncio
async def test_learning_loop_flag_on_manual_sticky_via_v2(db):
    """Override manual com v1 drifted + mesmo v2 → sticky via v2 (não orfaniza, não duplica)."""
    ws = await _ws_with_flag(db, enabled=True)
    v2 = identity_from_classified_tx(_classified()).natural_key_hash
    db.add(_persisted_override(ws.id, transaction_hash="v1-drifted", natural_key_hash=v2))
    await db.commit()
    with SyncSessionLocal() as sync_db:
        rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="PAGAMENTO", target="Compras")
        sync_db.commit()
        stats = apply_learning_loop(
            workspace_id=ws.id, classified=[_classified(rule_id=rule.id)], db=sync_db
        )
        sync_db.commit()
        assert stats.skipped_sticky == 1
        assert stats.applied == 0
        assert len(_sync_rows(sync_db, ws.id)) == 1


@pytest.mark.asyncio
async def test_apply_engine_flag_on_skips_manual_via_v2(db):
    ws = await _ws_with_flag(db, enabled=True)
    item = _item(transaction_hash="v1-atual")
    db.add(_persisted_override(ws.id, transaction_hash="v1-drifted", natural_key_hash=_v2_of(item)))
    await db.commit()
    with SyncSessionLocal() as sync_db:
        rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="PAGAMENTO", target="Compras")
        sync_db.commit()
        applied = _apply_rule_sync(sync_db, ws_id=ws.id, rule=rule, item=item)
        sync_db.commit()
        assert applied == 0  # manual sticky casado via v2, apesar do v1 drifted


@pytest.mark.asyncio
async def test_apply_engine_flag_on_updates_same_rule_in_place(db):
    """Existing da MESMA regra com v1 drifted: update in-place — sem duplicata de v2."""
    ws = await _ws_with_flag(db, enabled=True)
    item = _item(transaction_hash="v1-atual")
    with SyncSessionLocal() as sync_db:
        rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="PAGAMENTO", target="Compras")
        _add_same_rule_override(sync_db, ws.id, rule, item)
        sync_db.commit()
        applied = _apply_rule_sync(sync_db, ws_id=ws.id, rule=rule, item=item)
        sync_db.commit()
        rows = _sync_rows(sync_db, ws.id)
        assert applied == 1
        assert len(rows) == 1  # ON CONFLICT é no v1; in-place evita a duplicata
        assert rows[0].original_category == item.categoria


@pytest.mark.asyncio
async def test_preview_counts_manual_override_via_v2(db):
    ws = await _ws_with_flag(db, enabled=True)
    item = _item(transaction_hash="v1-atual")
    db.add(_persisted_override(ws.id, transaction_hash="v1-drifted", natural_key_hash=_v2_of(item)))
    await db.commit()

    with SyncSessionLocal() as sync_db:
        response = preview_rule(
            workspace_id=ws.id,
            keyword="PAGAMENTO",
            target_category="Compras",
            period_window=None,
            transactions=[item],
            db=sync_db,
            detector=empty_detector(),
        )
    assert response.matches_total == 1
    assert response.matches_with_manual_override == 1


# -- instrumentação do gate da M2 (ADR-282 §Emenda / A26.l4) --


def test_v2_match_increments_and_snapshot() -> None:
    """Hit via v2 incrementa v2_match_count; snapshot reflete cobertura + zero divergência."""
    item = _item(transaction_hash="v1-atual")
    ov = _override(transaction_hash="v1-drifted", natural_key_hash=_v2_of(item))
    index = OverrideMatchIndex.from_overrides([ov], workspace_id="ws", v2_enabled=True)

    assert index.match(natural_key_hash=_v2_of(item), legacy_hash="v1-atual") is ov
    assert index.snapshot() == {"v1_fallback": 0, "v2_match": 1, "divergence": 0}


def test_shadow_compare_off_never_diverges() -> None:
    """shadow_compare=False (default): v2 hit não computa v1 → divergence sempre 0."""
    item = _item(transaction_hash="v1-atual")
    a = _override(transaction_hash="hash-a", natural_key_hash=_v2_of(item))
    b = _override(transaction_hash="v1-atual", natural_key_hash=None)  # v1 casaria outro
    index = OverrideMatchIndex.from_overrides([a, b], workspace_id="ws", v2_enabled=True)

    assert index.match(natural_key_hash=_v2_of(item), legacy_hash="v1-atual") is a
    assert index.divergence_count == 0  # sem shadow, não olha o v1


def test_shadow_compare_same_row_no_divergence() -> None:
    """shadow ON + v2 e v1 casam a MESMA linha → divergence 0 (caso saudável)."""
    item = _item(transaction_hash="v1-atual")
    ov = _override(transaction_hash="v1-atual", natural_key_hash=_v2_of(item))
    index = OverrideMatchIndex.from_overrides(
        [ov], workspace_id="ws", v2_enabled=True, shadow_compare=True
    )

    assert index.match(natural_key_hash=_v2_of(item), legacy_hash="v1-atual") is ov
    assert index.divergence_count == 0


def test_shadow_compare_divergent_row_counts_and_warns() -> None:
    """shadow ON + v2 casa A mas v1 casaria B → divergence+warning (o modo de falha 'sticky' cego ao gate de cobertura)."""
    item = _item(transaction_hash="v1-atual")
    a = _override(transaction_hash="hash-a", natural_key_hash=_v2_of(item))
    b = _override(transaction_hash="v1-atual", natural_key_hash="outra-nk")
    index = OverrideMatchIndex.from_overrides(
        [a, b], workspace_id="ws-div", v2_enabled=True, shadow_compare=True
    )

    with _dualread_log_capture() as handler:
        matched = index.match(natural_key_hash=_v2_of(item), legacy_hash="v1-atual")
    assert matched is a  # v2 é a verdade em prod; shadow não altera o retorno
    assert index.snapshot() == {"v1_fallback": 0, "v2_match": 1, "divergence": 1}
    div = [r for r in handler.records if getattr(r, "event", "") == "divergence"]
    assert len(div) == 1 and div[0].workspace_id == "ws-div"
    for pii_attr in ("descricao", "valor", "titular"):
        assert not hasattr(div[0], pii_attr)


def test_persist_snapshot_noop_when_v2_disabled() -> None:
    """Flag-OFF: nada a auditar (v2 nem rodou)."""
    index = OverrideMatchIndex(workspace_id="ws", v2_enabled=False)
    with SyncSessionLocal() as sync_db:
        persist_dualread_snapshot(sync_db, index)
        sync_db.commit()
        rows = (
            sync_db.execute(
                select(AuditLog).where(
                    AuditLog.action == AuditAction.override_v2_dualread_snapshot.value
                )
            )
            .scalars()
            .all()
        )
    assert rows == []


@pytest.mark.asyncio
async def test_persist_snapshot_writes_audit_row_when_v2_ran(db) -> None:
    """Após exercício real do v2, o dreno grava 1 linha de AuditLog com as contagens (PII-zero)."""
    ws = await _ws_with_flag(db, enabled=True)
    item = _item(transaction_hash="v1-atual")
    ov = _persisted_override(ws.id, transaction_hash="v1-drifted", natural_key_hash=_v2_of(item))
    index = OverrideMatchIndex.from_overrides([ov], workspace_id=ws.id, v2_enabled=True)
    index.match(natural_key_hash=_v2_of(item), legacy_hash="v1-atual")

    with SyncSessionLocal() as sync_db:
        persist_dualread_snapshot(sync_db, index)
        sync_db.commit()
        rows = (
            sync_db.execute(select(AuditLog).where(AuditLog.workspace_id == ws.id)).scalars().all()
        )
    snapshots = [r for r in rows if r.action == AuditAction.override_v2_dualread_snapshot.value]
    assert len(snapshots) == 1
    assert snapshots[0].details == {"v1_fallback": 0, "v2_match": 1, "divergence": 0}
