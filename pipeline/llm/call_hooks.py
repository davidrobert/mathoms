"""Hooks de FinOps no choke-point LLM — budget hard-stop + call log (ADR-173).

O ``LLMService`` (pipeline) não pode importar sqlalchemy/redis (boundary
``check_pipeline_boundaries``); o backend injeta a implementação concreta
(``LLMBudgetService``) via ``WorkspaceContext.llm_call_hooks``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from pipeline.llm.litellm_client import LLMCallResult


class LLMBudgetExceededError(Exception):
    """Hard-stop pré-call: gasto mensal do workspace cruzou 110% do budget."""

    def __init__(self, workspace_id: str, spent_usd: Decimal, budget_usd: Decimal):
        super().__init__(
            f"LLM budget exceeded for workspace {workspace_id}: "
            f"spent=${spent_usd} >= 110% of budget=${budget_usd}"
        )
        self.workspace_id = workspace_id
        self.spent_usd = spent_usd
        self.budget_usd = budget_usd


class LLMCallHooks(Protocol):
    """Contrato injetado no ``LLMService`` — implementado pelo backend."""

    def check_budget(self) -> None:
        """Pré-call: raise ``LLMBudgetExceededError`` se gasto ≥110% do budget."""
        ...

    def record_call(
        self,
        result: "LLMCallResult",
        *,
        stage: Optional[str],
        prompt_version: Optional[str],
    ) -> None:
        """Pós-call: persiste 1 row de telemetria (``LLMCallLog``)."""
        ...
