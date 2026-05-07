"""Protocol do RiskRepository — DIP (ADR-101).

Use cases dependem do protocol; testes injetam fake (``FakeRiskRepository``)
sem montar SQLAlchemy. Implementação concreta: ``RiskRepository``.
"""

from __future__ import annotations

from typing import Optional, Protocol

from backend.app.models.risk import Risk


class RiskRepositoryProtocol(Protocol):
    async def get_by_id(self, workspace_id: str, risk_id: str) -> Optional[Risk]: ...

    async def get_by_code(self, workspace_id: str, code: str) -> Optional[Risk]: ...

    async def list_by_workspace(self, workspace_id: str) -> list[Risk]: ...

    async def add(self, risk: Risk) -> Risk: ...

    async def delete(self, risk: Risk) -> None: ...
