"""``InstitutionCatalog`` — catálogo global de instituições (ADR-137 · A7.3).

Workspace não customiza catálogo; banco fora da lista é ticket de produto.
``BankAccount`` rows continuam workspace-scoped — esta tabela define apenas
a taxonomia global de bancos/corretoras suportadas.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class InstitutionCatalog(Base):
    """Catálogo global de instituições financeiras."""

    __tablename__ = "institution_catalog"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    default_parser: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="bank")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
