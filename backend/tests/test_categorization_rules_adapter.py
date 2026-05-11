"""Tests do adapter ``CategorizationRulesV2`` + learning loop E4 (ADR-186 §D5 · A12.P2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.core.database import SyncSessionLocal
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    OVERRIDE_SOURCE_RULE,
    TransactionOverride,
)
from backend.app.services.categorization_learning_loop import apply_learning_loop
from backend.app.services.categorization_rules_adapter import (
    load_categorization_rules_v2,
)
from backend.app.services.report_publication import (
    is_month_closed_sync,
    publish_month,
)
from backend.app.services.transaction_service import generate_transaction_hash
from backend.tests import factories
from pipeline.domain.services.categorization_service import (
    CategorizationRulesV2,
    LearnedRule,
)
from pipeline.domain.services.transaction_classifier import (
    ClassifiedTransaction,
    ClassifierConfig,
    TransactionClassifier,
)

# ─── helpers ────────────────────────────────────────────────────────────


def _insert_rule(db, *, workspace_id: str, keyword: str, **kwargs) -> CategorizationRule:
    rule = CategorizationRule(
        id=kwargs.get("rule_id") or str(uuid.uuid4()),
        workspace_id=workspace_id,
        keyword=keyword,
        target_category=kwargs.get("target_category", "Alimentacao"),
        priority=kwargs.get("priority", 100),
        enabled=kwargs.get("enabled", True),
        created_at=kwargs.get("created_at") or datetime.now(timezone.utc),
    )
    db.add(rule)
    db.flush()
    return rule


def _make_classified(
    *,
    descricao: str,
    data: str = "2026-03-15",
    rule_id: str | None = None,
    categoria: str = "Alimentacao",
) -> ClassifiedTransaction:
    return ClassifiedTransaction(
        kind="despesa",
        data=data,
        descricao=descricao,
        valor=50.0,
        banco="c6bank",
        moeda="BRL",
        tipo_conta="conta_corrente",
        titular="Test User",
        tipo="debito",
        categoria=categoria,
        learned_rule_id=rule_id,
    )


def _make_lr(
    keyword: str,
    *,
    rule_id: str = "id",
    target_category: str = "Cat",
    priority: int = 100,
    created_at: datetime | None = None,
) -> LearnedRule:
    return LearnedRule(
        id=rule_id,
        keyword=keyword,
        target_category=target_category,
        priority=priority,
        created_at=created_at or datetime.now(timezone.utc),
    )


# ─── CategorizationRulesV2 sort estável (puro, sem DB) ──────────────────


class TestCategorizationRulesV2Sort:
    def test_priority_desc_wins(self):
        low = _make_lr("IFOOD", rule_id="b", priority=50)
        high = _make_lr("UBER", rule_id="a", priority=200)
        rules = CategorizationRulesV2.from_template_and_learned({}, [low, high])
        assert rules.learned_rules[0].priority == 200

    def test_len_keyword_desc_on_priority_tie(self):
        short = _make_lr("IFOOD", rule_id="a")
        long = _make_lr("MERCADO PAGO IFOOD", rule_id="b", target_category="Especifica")
        rules = CategorizationRulesV2.from_template_and_learned({}, [short, long])
        assert rules.learned_rules[0].keyword == "MERCADO PAGO IFOOD"
        assert rules.match("PIX MERCADO PAGO IFOOD") == ("Especifica", "b")

    def test_created_at_asc_on_double_tie(self):
        older = datetime(2026, 1, 1, tzinfo=timezone.utc)
        newer = datetime(2026, 5, 1, tzinfo=timezone.utc)
        old = _make_lr("IFOOD", rule_id="z", target_category="OLD", created_at=older)
        new = _make_lr("IFOOD", rule_id="a", target_category="NEW", created_at=newer)
        rules = CategorizationRulesV2.from_template_and_learned({}, [new, old])
        assert rules.learned_rules[0].target_category == "OLD"

    def test_id_asc_breaks_total_tie(self):
        same_dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rz = _make_lr("IFOOD", rule_id="zzz", target_category="Z", created_at=same_dt)
        ra = _make_lr("IFOOD", rule_id="aaa", target_category="A", created_at=same_dt)
        rules = CategorizationRulesV2.from_template_and_learned({}, [rz, ra])
        assert rules.learned_rules[0].id == "aaa"
        assert rules.learned_rules[0].target_category == "A"

    def test_match_returns_none_when_no_learned(self):
        rules = CategorizationRulesV2.from_template_and_learned({"X": ("Y",)}, [])
        assert rules.match("ANY") is None

    def test_match_returns_none_on_empty_narrative(self):
        rules = CategorizationRulesV2.from_template_and_learned({}, [_make_lr("X")])
        assert rules.match("") is None


# ─── Adapter + DB ───────────────────────────────────────────────────────


class TestAdapterLoadsFromDB:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_rules(self, db):
        ws = await factories.make_workspace(db)
        await db.commit()
        with SyncSessionLocal() as sync_db:
            rules = load_categorization_rules_v2(workspace_id=ws.id, db=sync_db)
            assert rules.learned_rules == ()

    @pytest.mark.asyncio
    async def test_returns_only_enabled(self, db):
        ws = await factories.make_workspace(db)
        await db.commit()
        with SyncSessionLocal() as sync_db:
            _insert_rule(sync_db, workspace_id=ws.id, keyword="IFOOD", enabled=True)
            _insert_rule(sync_db, workspace_id=ws.id, keyword="UBER", enabled=False)
            sync_db.commit()
            rules = load_categorization_rules_v2(workspace_id=ws.id, db=sync_db)
            assert len(rules.learned_rules) == 1
            assert rules.learned_rules[0].keyword == "IFOOD"

    @pytest.mark.asyncio
    async def test_isolates_workspaces(self, db):
        ws_a = await factories.make_workspace(db)
        ws_b = await factories.make_workspace(db)
        await db.commit()
        with SyncSessionLocal() as sync_db:
            _insert_rule(sync_db, workspace_id=ws_a.id, keyword="IFOOD")
            _insert_rule(sync_db, workspace_id=ws_b.id, keyword="UBER")
            sync_db.commit()
            rules_a = load_categorization_rules_v2(workspace_id=ws_a.id, db=sync_db)
            rules_b = load_categorization_rules_v2(workspace_id=ws_b.id, db=sync_db)
            assert {r.keyword for r in rules_a.learned_rules} == {"IFOOD"}
            assert {r.keyword for r in rules_b.learned_rules} == {"UBER"}

    @pytest.mark.asyncio
    async def test_hard_cap_at_200(self, db):
        ws = await factories.make_workspace(db)
        await db.commit()
        with SyncSessionLocal() as sync_db:
            for i in range(201):
                _insert_rule(sync_db, workspace_id=ws.id, keyword=f"KW{i:04d}")
            sync_db.commit()
            rules = load_categorization_rules_v2(workspace_id=ws.id, db=sync_db)
            assert len(rules.learned_rules) == 200

    @pytest.mark.asyncio
    async def test_keyword_uppercased_at_load(self, db):
        ws = await factories.make_workspace(db)
        await db.commit()
        with SyncSessionLocal() as sync_db:
            _insert_rule(sync_db, workspace_id=ws.id, keyword="ifood")
            sync_db.commit()
            rules = load_categorization_rules_v2(workspace_id=ws.id, db=sync_db)
            assert rules.learned_rules[0].keyword == "IFOOD"


# ─── TransactionClassifier consome learned_rules ────────────────────────


def _build_tx_account(desc: str, tipo: str) -> dict:
    return {
        "banco": "c6bank",
        "tipo_conta": "conta_corrente",
        "titular": "Test User",
        "moeda": "BRL",
        "transacoes": [
            {
                "data": "2026-03-15",
                "descricao": desc,
                "valor": -50.0 if tipo == "debito" else 50.0,
                "tipo": tipo,
            }
        ],
    }


def _classify_one_tx(desc: str, tipo: str, rules_v2: CategorizationRulesV2):
    cfg = ClassifierConfig(
        expense_keywords={"despesa_fallback": ["BOLETO"]},
        income_keywords={"renda_fallback": ["SALARIO"]},
        learned_rules_v2=rules_v2,
    )
    return TransactionClassifier(cfg).classify_account(_build_tx_account(desc, tipo))[0]


class TestClassifierConsumesLearnedRules:
    def test_learned_rule_wins_over_template_expense(self):
        rules = CategorizationRulesV2.from_template_and_learned(
            {}, [_make_lr("BOLETO", rule_id="r1", target_category="Aluguel")]
        )
        out = _classify_one_tx("PAGTO BOLETO XYZ", "debito", rules)
        assert out.categoria == "Aluguel"
        assert out.learned_rule_id == "r1"

    def test_no_learned_rule_falls_back_to_template(self):
        rules = CategorizationRulesV2.from_template_and_learned({}, [])
        out = _classify_one_tx("PAGTO BOLETO XYZ", "debito", rules)
        assert out.categoria == "despesa_fallback"
        assert out.learned_rule_id is None

    def test_learned_rule_on_receita(self):
        rules = CategorizationRulesV2.from_template_and_learned(
            {},
            [_make_lr("DIVIDENDO", rule_id="r2", target_category="Renda Passiva")],
        )
        out = _classify_one_tx("DIVIDENDO ITSA4", "credito", rules)
        assert out.categoria == "Renda Passiva"
        assert out.learned_rule_id == "r2"
        assert out.kind == "receita"


# ─── Learning loop helpers ──────────────────────────────────────────────


def _make_run(ws_id: str) -> PipelineRun:
    return PipelineRun(
        id=str(uuid4()),
        workspace_id=ws_id,
        status=PipelineRunStatus.completed,
        started_at=datetime.now(timezone.utc),
        tier_at_run="premium",
        incremental=False,
        reprocess_all=False,
        total_documents=0,
    )


async def _make_pipeline_artifact(db, ws) -> PipelineArtifact:
    run = _make_run(ws.id)
    db.add(run)
    artifact = PipelineArtifact(
        workspace_id=ws.id,
        pipeline_run_id=run.id,
        stage="analyze_finances",
        artifact_key="analise_financeira",
        content_json={"score": 78},
    )
    db.add(artifact)
    await db.flush()
    return artifact


async def _create_published_month(db, ws, period: str) -> None:
    """Cria artifact + publica para fechar o mês."""
    artifact = await _make_pipeline_artifact(db, ws)
    await publish_month(ws.id, period, artifact.id, actor="user:test", db=db)


def _count_overrides(sync_db, ws_id: str, source: str | None = None):
    stmt = select(TransactionOverride).where(
        TransactionOverride.workspace_id == ws_id,
    )
    if source is not None:
        stmt = stmt.where(TransactionOverride.source == source)
    return sync_db.execute(stmt).scalars().all()


def _hash_for(tx: ClassifiedTransaction) -> str:
    return generate_transaction_hash(
        {
            "data": tx.data,
            "descricao": tx.descricao,
            "valor": tx.valor,
            "banco": tx.banco,
            "titular": tx.titular,
        }
    )


def _assert_month_closed_outcome(sync_db, stats, rule, ws_id: str) -> None:
    """1 tx fechado + 1 tx aberto → counter=1, 1 override criado."""
    assert stats.to_dict() == {
        "matches_total": 2,
        "applied": 1,
        "skipped_sticky": 0,
        "skipped_closed_month": 1,
    }
    sync_db.refresh(rule)
    assert rule.applied_count == 1
    overrides = _count_overrides(sync_db, ws_id, OVERRIDE_SOURCE_RULE)
    assert len(overrides) == 1


def _insert_manual_override(
    sync_db, *, ws_id: str, tx: ClassifiedTransaction
) -> TransactionOverride:
    manual = TransactionOverride(
        workspace_id=ws_id,
        transaction_hash=_hash_for(tx),
        original_category="Diversos",
        new_category="Lazer",
        source=OVERRIDE_SOURCE_MANUAL,
    )
    sync_db.add(manual)
    sync_db.commit()
    return manual


# ─── Learning loop E2E ──────────────────────────────────────────────────


def _assert_sticky_outcome(sync_db, stats, manual, rule) -> None:
    """Sticky-manual: stats=skipped_sticky, manual intacto, counter zerado."""
    assert stats.to_dict() == {
        "matches_total": 1,
        "applied": 0,
        "skipped_sticky": 1,
        "skipped_closed_month": 0,
    }
    sync_db.refresh(manual)
    assert manual.source == OVERRIDE_SOURCE_MANUAL
    assert manual.new_category == "Lazer"
    sync_db.refresh(rule)
    assert rule.applied_count == 0


def _assert_applied_one(sync_db, stats, rule, ws_id: str) -> None:
    assert stats.to_dict() == {
        "matches_total": 1,
        "applied": 1,
        "skipped_sticky": 0,
        "skipped_closed_month": 0,
    }
    overrides = _count_overrides(sync_db, ws_id, OVERRIDE_SOURCE_RULE)
    assert len(overrides) == 1
    assert overrides[0].rule_id == rule.id
    sync_db.refresh(rule)
    assert rule.applied_count == 1


class TestLearningLoopE2E:
    @pytest.mark.asyncio
    async def test_creates_override_and_bumps_counter(self, db):
        ws = await factories.make_workspace(db)
        await db.commit()
        with SyncSessionLocal() as sync_db:
            rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="IFOOD")
            sync_db.commit()
            tx = _make_classified(descricao="PIX IFOOD", rule_id=rule.id)
            stats = apply_learning_loop(workspace_id=ws.id, classified=[tx], db=sync_db)
            sync_db.commit()
            _assert_applied_one(sync_db, stats, rule, ws.id)

    @pytest.mark.asyncio
    async def test_sticky_manual_skip(self, db):
        ws = await factories.make_workspace(db)
        await db.commit()
        with SyncSessionLocal() as sync_db:
            rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="IFOOD")
            sync_db.commit()
            tx = _make_classified(descricao="PIX IFOOD", rule_id=rule.id)
            manual = _insert_manual_override(sync_db, ws_id=ws.id, tx=tx)
            stats = apply_learning_loop(workspace_id=ws.id, classified=[tx], db=sync_db)
            sync_db.commit()
            _assert_sticky_outcome(sync_db, stats, manual, rule)

    @pytest.mark.asyncio
    async def test_month_closed_skip(self, db):
        ws = await factories.make_workspace(db)
        await _create_published_month(db, ws, "202603")
        await db.commit()
        with SyncSessionLocal() as sync_db:
            rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="IFOOD")
            sync_db.commit()
            tx_closed = _make_classified(
                descricao="PIX IFOOD CLOSED", data="2026-03-15", rule_id=rule.id
            )
            tx_open = _make_classified(
                descricao="PIX IFOOD OPEN", data="2026-04-15", rule_id=rule.id
            )
            stats = apply_learning_loop(
                workspace_id=ws.id, classified=[tx_closed, tx_open], db=sync_db
            )
            sync_db.commit()
            _assert_month_closed_outcome(sync_db, stats, rule, ws.id)

    @pytest.mark.asyncio
    async def test_idempotent_rerun(self, db):
        ws = await factories.make_workspace(db)
        await db.commit()
        with SyncSessionLocal() as sync_db:
            rule = _insert_rule(sync_db, workspace_id=ws.id, keyword="IFOOD")
            sync_db.commit()
            tx = _make_classified(descricao="PIX IFOOD", rule_id=rule.id)

            apply_learning_loop(workspace_id=ws.id, classified=[tx], db=sync_db)
            sync_db.commit()
            stats = apply_learning_loop(workspace_id=ws.id, classified=[tx], db=sync_db)
            sync_db.commit()

            overrides = _count_overrides(sync_db, ws.id, OVERRIDE_SOURCE_RULE)
            assert len(overrides) == 1
            assert stats.applied == 1


# ─── is_month_closed_sync ──────────────────────────────────────────────


class TestIsMonthClosedSync:
    @pytest.mark.asyncio
    async def test_returns_false_when_no_publication(self, db):
        ws = await factories.make_workspace(db)
        await db.commit()
        with SyncSessionLocal() as sync_db:
            assert is_month_closed_sync(ws.id, "202601", db=sync_db) is False

    @pytest.mark.asyncio
    async def test_returns_true_after_publish(self, db):
        ws = await factories.make_workspace(db)
        await _create_published_month(db, ws, "202601")
        await db.commit()
        with SyncSessionLocal() as sync_db:
            assert is_month_closed_sync(ws.id, "202601", db=sync_db) is True

    @pytest.mark.asyncio
    async def test_validates_period_format(self, db):
        from backend.app.application.base.errors import ValidationError

        ws = await factories.make_workspace(db)
        await db.commit()
        with SyncSessionLocal() as sync_db:
            with pytest.raises(ValidationError):
                is_month_closed_sync(ws.id, "2026-01", db=sync_db)
