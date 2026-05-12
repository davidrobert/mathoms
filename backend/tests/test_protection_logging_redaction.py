"""ADR-110 · ADR-192 · S9-T05 — gate empírico de PII redaction no POST /protections."""

from __future__ import annotations

import io
import json
import logging
from contextlib import contextmanager

import pytest
from httpx import AsyncClient

from backend.app.core.logging import MathomsJsonFormatter

_RAW_POLICY = "POL-SECRET-9999-X9Q"


def _install_buffer_handler(logger: logging.Logger) -> io.StringIO:
    """Substitui handlers do logger por um StreamHandler em StringIO (JSON formatter)."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(MathomsJsonFormatter())
    handler.setLevel(logging.INFO)
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.disabled = False
    return buf


@contextmanager
def _capture_protection_logs():
    """Captura INFO do `mathoms.protection`, resilient a Manager.disable global."""
    logger = logging.getLogger("mathoms.protection")
    saved = (logger.handlers, logger.level, logger.propagate, logger.disabled)
    saved_manager_disable = logging.root.manager.disable
    buf = _install_buffer_handler(logger)
    logging.root.manager.disable = logging.NOTSET  # restaura no finally
    try:
        yield buf
    finally:
        logger.handlers, logger.level, logger.propagate, logger.disabled = saved
        logging.root.manager.disable = saved_manager_disable


def _make_payload() -> dict:
    return {
        "category": "vida",
        "coverage_brl": "500000.00",
        "premium_monthly_brl": "350.00",
        "starts_at": "2026-01-01",
        "policy_ref": _RAW_POLICY,
        "insurer": "Seguradora Teste",
    }


def _assert_response_redacted(body: dict) -> None:
    assert _RAW_POLICY not in json.dumps(body)
    assert body["policy_ref_masked"].startswith("****")


def _assert_logs_redacted(log_text: str) -> None:
    assert (
        "protection_created" in log_text
    ), f"esperava log estruturado 'protection_created' do POST /protections; got: {log_text!r}"
    assert _RAW_POLICY not in log_text, f"policy_ref raw vazou em log INFO: {log_text!r}"


@pytest.mark.asyncio
async def test_create_protection_does_not_leak_policy_ref_in_logs(
    auth_client: AsyncClient,
):
    """POST /protections com `policy_ref` raw — log INFO não pode conter o valor."""
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    with _capture_protection_logs() as buf:
        resp = await auth_client.post(
            f"/api/workspaces/{ws_id}/protections",
            json=_make_payload(),
        )
        assert resp.status_code == 201, resp.text
        _assert_response_redacted(resp.json())
    _assert_logs_redacted(buf.getvalue())
