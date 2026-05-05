"""LGPD email notifications — stub backend (logger-only) até provider real entrar (A8+)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def send_export_ready_email(
    *,
    to_email: str,
    request_id: str,
    download_url: str,
) -> None:
    """Notifica titular que o export está pronto. Stub — apenas log."""
    logger.info(
        "lgpd.email.export_ready to=%s request_id=%s download_url=%s",
        to_email,
        request_id,
        download_url,
    )


def send_deletion_scheduled_email(
    *,
    to_email: str,
    hard_delete_after_iso: str,
) -> None:
    """Notifica titular que a conta foi marcada para exclusão (grace 30d)."""
    logger.info(
        "lgpd.email.deletion_scheduled to=%s hard_delete_after=%s",
        to_email,
        hard_delete_after_iso,
    )
