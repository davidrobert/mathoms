"""Paridade de contrato do shell GO (F1 Fase 4, decisão 10 do track).

Roda o MESMO fuzz schemathesis do serviço Python contra o binário Go —
ambas as implementações validadas contra o snapshot OpenAPI congelado
(#747) = paridade de contrato provada sem subir as duas juntas.

Guarded (`MATHOMS_GO_CONTRACT=1`): exige toolchain Go — roda local e no
gate de cutover; o job pipeline-tests do CI não tem Go (registrado no
track como limitação consciente da F1).
O executor de stage é FAKE (`MATHOMS_PYTHON` → script que ecoa um
StageResult): o alvo é o contrato HTTP, não a execução (coberta pela
integração real da Fase 2).
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest
import schemathesis
from hypothesis import HealthCheck, settings

_REPO = Path(__file__).resolve().parent.parent.parent
_SNAPSHOT = _REPO / "docs" / "reference" / "api" / "v1" / "pipeline-service.openapi.json"

pytestmark = pytest.mark.skipif(
    not os.environ.get("MATHOMS_GO_CONTRACT"),
    reason="defina MATHOMS_GO_CONTRACT=1 (exige toolchain Go)",
)

schemathesis.experimental.OPEN_API_3_1.enable()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def go_service_url(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("go-contract")
    binary = tmp / "pipeline-service"
    subprocess.run(
        ["go", "build", "-o", str(binary), "./cmd/pipeline-service"],
        cwd=_REPO / "services" / "pipeline-service-go",
        check=True,
    )
    fake = tmp / "fake-python"
    fake.write_text(
        '#!/bin/sh\necho \'{"stage":"reconcile_transactions","success":true,'
        '"duration_ms":1.0,"detail":null,"error":null}\'\n'
    )
    fake.chmod(0o755)
    port = _free_port()
    proc = subprocess.Popen(
        [str(binary)],
        env={
            **os.environ,
            "PIPELINE_SERVICE_PORT": str(port),
            "MATHOMS_PYTHON": str(fake),
            "MATHOMS_REPO_ROOT": str(tmp),
            "REDIS_URL": "redis://127.0.0.1:6390/0",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(url + "/health", timeout=0.2)
            break
        except Exception:
            time.sleep(0.05)
    else:
        proc.kill()
        pytest.fail("binário Go não subiu")
    yield url
    proc.terminate()
    proc.wait(timeout=10)


schema = schemathesis.from_path(str(_SNAPSHOT))


@schema.parametrize()
@settings(
    max_examples=12,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)
def test_go_service_matches_frozen_contract(case, go_service_url):
    response = case.call(base_url=go_service_url)
    case.validate_response(response)
