"""Use cases do aggregate ``Decision`` (ADR-101 R15 · ADR-136).

Cada comando emite um ``DecisionEvent`` append-only — invariante do
aggregate. Status é projeção do log.
"""

from backend.app.application.decisions.create_decision import create_decision
from backend.app.application.decisions.get_decision import get_decision
from backend.app.application.decisions.list_decisions import list_decisions
from backend.app.application.decisions.mark_executed import mark_decision_executed
from backend.app.application.decisions.supersede_decision import supersede_decision
from backend.app.application.decisions.update_decision import update_decision

__all__ = [
    "create_decision",
    "get_decision",
    "list_decisions",
    "mark_decision_executed",
    "supersede_decision",
    "update_decision",
]
