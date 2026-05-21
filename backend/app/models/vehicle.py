"""Vehicle — tabela canônica de veículos (ADR-239 D1; padrão ADR-225 identidade imutável)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

# RFB codes para bens (ADR-225 invariante imutável). 21=veículo terrestre,
# 22=aeronave, 23=embarcação. L1 cobre 21; demais entram em V2.
CODIGO_RFB_VEICULO_TERRESTRE = "21"
CODIGO_RFB_AERONAVE = "22"
CODIGO_RFB_EMBARCACAO = "23"

VALID_CODIGOS_RFB_VEHICLE = (
    CODIGO_RFB_VEICULO_TERRESTRE,
    CODIGO_RFB_AERONAVE,
    CODIGO_RFB_EMBARCACAO,
)


class Vehicle(Base):
    """Identidade canônica de veículo cross-IRPFs (ADR-239 D1; identidade imutável)."""

    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("workspace_id", "placa", name="uq_workspace_placa"),
        # ANSI SQL portátil — Pydantic (P2) valida regex `^[0-9]{9,11}$` no boundary.
        CheckConstraint(
            "length(renavam) BETWEEN 9 AND 11",
            name="chk_vehicles_renavam_length",
        ),
        CheckConstraint(
            "codigo_rfb IN ('21', '22', '23')",
            name="chk_vehicles_codigo_rfb",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    placa: Mapped[str] = mapped_column(String(10), nullable=False)
    renavam: Mapped[str] = mapped_column(String(11), nullable=False)
    marca: Mapped[str] = mapped_column(String(60), nullable=False)
    modelo: Mapped[str] = mapped_column(String(120), nullable=False)
    ano_modelo: Mapped[int] = mapped_column(Integer, nullable=False)
    ano_fabricacao: Mapped[int] = mapped_column(Integer, nullable=False)
    fipe_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    cor: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    combustivel: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    codigo_rfb: Mapped[str] = mapped_column(
        String(4), nullable=False, default=CODIGO_RFB_VEICULO_TERRESTRE, server_default="21"
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


__all__ = [
    "Vehicle",
    "VALID_CODIGOS_RFB_VEHICLE",
    "CODIGO_RFB_VEICULO_TERRESTRE",
    "CODIGO_RFB_AERONAVE",
    "CODIGO_RFB_EMBARCACAO",
]
