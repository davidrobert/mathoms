"""ADR-363 — `/health` declara a revisão do executor sem sobrecarregar `version`."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.core import config as core_config
from backend.app.schemas.health import HealthResponse

_BASE = {
    "api": "ok",
    "version": "1.0.0",
    "redis": "ok",
    "celery": "ok",
    "database": "ok",
    "artifact_store_mode": "db",
    "status": "ok",
}


def test_executor_revision_e_opcional_e_nao_derruba_o_healthcheck() -> None:
    """O healthcheck de prod é `curl -fsS`: 500 aqui marcaria o container unhealthy."""
    assert HealthResponse(**_BASE).executor_revision is None
    assert HealthResponse(**_BASE, executor_revision=None).executor_revision is None
    assert HealthResponse(**_BASE, executor_revision="aaaaaaaaaaaa").executor_revision == (
        "aaaaaaaaaaaa"
    )


def test_version_continua_required_non_nullable() -> None:
    """É por isso que a revisão é campo NOVO, não o valor de `version` trocado."""
    # Mutação que mata: tornar `version` opcional "para reusar o campo" — passaria
    # a devolver null quando a env faltasse, e o `curl -fsS` derrubaria o container.
    with pytest.raises(ValidationError):
        HealthResponse(**{**_BASE, "version": None})


@pytest.mark.asyncio
async def test_endpoint_serve_api_version_e_nao_literal_stale(monkeypatch) -> None:
    """`/health` servia `"0.6.0"` hardcoded enquanto a app declarava `API_VERSION`."""
    from backend.app.main import health

    monkeypatch.setattr(core_config.settings, "BUILD_SHA", "aaaaaaaaaaaa", raising=False)
    payload = await health()

    assert payload["version"] == core_config.settings.API_VERSION
    assert payload["version"] != "0.6.0"
    assert payload["executor_revision"] == "aaaaaaaaaaaa"


@pytest.mark.asyncio
async def test_endpoint_sem_env_reporta_none_e_responde(monkeypatch) -> None:
    from backend.app.main import health

    monkeypatch.setattr(core_config.settings, "BUILD_SHA", "", raising=False)
    payload = await health()

    assert payload["executor_revision"] is None
    assert payload["api"] == "ok"
