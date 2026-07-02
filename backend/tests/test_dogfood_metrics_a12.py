"""``dev/dogfood_metrics_a12.py`` — critérios quantitativos §9.3 (ADR-186 §D6)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models import CategorizationRule, User, Workspace
from dev.dogfood_metrics_a12 import compute_metrics

_WINDOW_START = datetime.now(timezone.utc) - timedelta(days=7)


@pytest.fixture()
def db_factory():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


def _seed_workspace(session) -> str:
    user = User(email="dogfood@test.com", hashed_password=hash_password("p"), full_name="U")
    session.add(user)
    session.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    session.add(ws)
    session.flush()
    return ws.id


def _rule(ws_id: str, keyword: str, *, applied: int = 0, reverts: int = 0, **kw):
    return CategorizationRule(
        workspace_id=ws_id,
        keyword=keyword,
        target_category=kw.pop("target", "Alimentação"),
        applied_count=applied,
        revert_count_manual_edit=reverts,
        **kw,
    )


def test_gate_pass_com_5_regras_e_revert_baixo(db_factory) -> None:
    session = db_factory()
    ws_id = _seed_workspace(session)
    for i in range(5):
        session.add(_rule(ws_id, f"KW{i}", applied=10, reverts=1, target=f"Cat{i}"))
    session.commit()

    m = compute_metrics(session, ws_id, _WINDOW_START)

    assert m.verdict == "PASS"
    assert m.rules_persistent == 5
    assert m.revert_rate_pct == 10.0
    assert m.rules_with_min_matches == 5


def test_gate_partial_com_revert_alto(db_factory) -> None:
    """revert_rate > 30% derruba só o critério 2 — verdict PARTIAL."""
    session = db_factory()
    ws_id = _seed_workspace(session)
    for i in range(5):
        session.add(_rule(ws_id, f"KW{i}", applied=10, reverts=4, target=f"Cat{i}"))
    session.commit()

    m = compute_metrics(session, ws_id, _WINDOW_START)

    assert m.verdict == "PARTIAL"
    assert m.revert_rate_pct == 40.0
    assert m.criteria["revert_rate <= 30.0%"] is False


def test_gate_ignora_regra_deletada_e_fora_da_janela(db_factory) -> None:
    session = db_factory()
    ws_id = _seed_workspace(session)
    session.add(_rule(ws_id, "DELETADA", applied=10, deleted_at=datetime.now(timezone.utc)))
    session.add(
        _rule(
            ws_id,
            "ANTIGA",
            applied=10,
            target="Cat2",
            created_at=_WINDOW_START - timedelta(days=30),
        )
    )
    session.commit()

    m = compute_metrics(session, ws_id, _WINDOW_START)

    assert m.rules_persistent == 0
    assert m.verdict == "FAIL"


def test_revert_rate_none_sem_applied(db_factory) -> None:
    """0 applied → rate N/D; critério 2 falha explicitamente (sem divisão por zero)."""
    session = db_factory()
    ws_id = _seed_workspace(session)
    for i in range(5):
        session.add(_rule(ws_id, f"KW{i}", target=f"Cat{i}"))
    session.commit()

    m = compute_metrics(session, ws_id, _WINDOW_START)

    assert m.revert_rate_pct is None
    assert m.criteria["revert_rate <= 30.0%"] is False
    assert m.verdict == "PARTIAL"


def test_disable_nao_polui_revert_rate(db_factory) -> None:
    """ADR-188 §D3: revert_count_rule_disabled é sinal fraco — fora do KPI."""
    session = db_factory()
    ws_id = _seed_workspace(session)
    session.add(_rule(ws_id, "KW", applied=10, reverts=0, revert_count_rule_disabled=9))
    session.commit()

    m = compute_metrics(session, ws_id, _WINDOW_START)

    assert m.revert_rate_pct == 0.0
