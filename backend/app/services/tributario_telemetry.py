"""Telemetria estruturada da cascata fiscal PJ — ADR-236 §D6 + P6 (Sprint A16)."""

from __future__ import annotations

from typing import Iterable, Optional

from backend.app.core.logging import get_logger

_logger = get_logger("mathoms.tributario")


def compute_profile_completeness(
    regime: Optional[str] = None,
    anexo_simples: Optional[str] = None,
    tipo_declaracao_ir: Optional[str] = None,
) -> tuple[bool, list[str]]:
    """Retorna ``(is_complete, missing_fields)`` para o card S8 V1 ([[ADR-236]] §D1)."""
    missing: list[str] = []
    if regime is None:
        missing.append("regime")
    if tipo_declaracao_ir is None:
        missing.append("tipo_declaracao_ir")
    if regime == "simples" and anexo_simples is None:
        missing.append("anexo_simples")
    return (not missing, missing)


def emit_cascata_rendered(
    *,
    regime: Optional[str],
    has_complete_profile: bool,
    triggers_count: int,
) -> None:
    _logger.info(
        "cascata_rendered",
        extra={
            "event_type": "mathoms.tributario.cascata_rendered",
            "regime": regime,
            "has_complete_profile": has_complete_profile,
            "triggers_count": triggers_count,
        },
    )


def emit_trigger_shown(*, trigger_code: str, regime: Optional[str]) -> None:
    _logger.info(
        "trigger_shown",
        extra={
            "event_type": "mathoms.tributario.trigger_shown",
            "trigger_code": trigger_code,
            "regime": regime,
        },
    )


def emit_profile_incomplete(*, missing_fields: list[str]) -> None:
    _logger.info(
        "profile_incomplete",
        extra={
            "event_type": "mathoms.tributario.profile_incomplete",
            "missing_fields": list(missing_fields),
        },
    )


def emit_telemetry_for_section(
    *,
    regime: Optional[str],
    has_complete_profile: bool,
    missing_fields: list[str],
    trigger_codes: Iterable[str],
) -> None:
    """Pipeline completo: 1 cascata_rendered + N trigger_shown + 0/1 profile_incomplete."""
    codes = [c for c in trigger_codes if c]
    emit_cascata_rendered(
        regime=regime,
        has_complete_profile=has_complete_profile,
        triggers_count=len(codes),
    )
    for code in codes:
        emit_trigger_shown(trigger_code=code, regime=regime)
    if not has_complete_profile:
        emit_profile_incomplete(missing_fields=missing_fields)


__all__ = [
    "compute_profile_completeness",
    "emit_cascata_rendered",
    "emit_profile_incomplete",
    "emit_telemetry_for_section",
    "emit_trigger_shown",
]
