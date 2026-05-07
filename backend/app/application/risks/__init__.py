"""Use cases do aggregate ``Risk`` (ADR-101 R15 · ADR-178).

CRUD com link semântico para Decision (mitigations). Não event-sourced —
ADR-178 §"Trade-offs" escopa para v1 sem log de eventos.
"""

from backend.app.application.risks.create_risk import create_risk
from backend.app.application.risks.delete_risk import delete_risk
from backend.app.application.risks.get_risk import get_risk
from backend.app.application.risks.link_mitigation import (
    link_mitigation,
    unlink_mitigation,
)
from backend.app.application.risks.list_risks import list_risks
from backend.app.application.risks.update_risk import update_risk

__all__ = [
    "create_risk",
    "delete_risk",
    "get_risk",
    "link_mitigation",
    "list_risks",
    "unlink_mitigation",
    "update_risk",
]
