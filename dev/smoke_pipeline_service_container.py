#!/usr/bin/env python3
"""Gate ADR-303 do container do pipeline-service (smoke sequencial).

Prova que o container executa stage real via HTTP e persiste em
``pipeline_artifacts`` — o "path não quebra em silêncio" da ADR-303, agora
também no Docker. O workspace vem do host (bind de ``_smoke_storage``); o
seed e o readback do DB rodam VIA ``docker exec`` no próprio container.

**Por quê docker exec e não sessão do host:** o SQLite do smoke roda em WAL,
e WAL usa mmap compartilhado (-shm) que NÃO é coerente entre host e container
(virtioFS) — escritas de um lado ficam invisíveis do outro até checkpoint.
Acesso simultâneo host↔container ao mesmo arquivo não é suportado; o gate
mantém todo acesso a DB num único namespace. O arquivo (``mathoms-smoke.db``)
segue persistido no host via bind mount.

Pré-requisitos: ``make smoke-up`` (fernet key + DB migrado) e o container do
overlay no ar (o target ``make smoke-pipeline-service`` orquestra tudo).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_FERNET_KEY_FILE = REPO_ROOT / "_smoke_pids" / "fernet.key"
_E2_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "pipeline_golden" / "e2" / "minimal-extrato-2_extract.json"
)
_SERVICE_URL = os.environ.get("PIPELINE_SERVICE_SMOKE_URL", "http://localhost:8001")
_CONTAINER = os.environ.get("PIPELINE_SERVICE_SMOKE_CONTAINER", "mathoms-pipeline-service")
_WS_ID = "ws-container-smoke"

_SEED_SNIPPET = """
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.services.db_artifact_store import DBArtifactStore
payload = json.loads({payload_json!r})
engine = create_engine("sqlite:////repo/mathoms-smoke.db")
session = sessionmaker(bind=engine, expire_on_commit=False)()
DBArtifactStore(session, workspace_id="{ws}", pipeline_run_id="{run}").write(
    "E2-extratos", "golden-minimal", payload
)
session.commit(); session.close()
print("seed-ok")
"""

_READBACK_SNIPPET = """
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.services.db_artifact_store import DBArtifactStore
engine = create_engine("sqlite:////repo/mathoms-smoke.db")
session = sessionmaker(bind=engine, expire_on_commit=False)()
store = DBArtifactStore(session, workspace_id="{ws}", pipeline_run_id="{run}")
keys = store.list_keys("E3")
assert len(keys) == 1, f"esperava 1 key E3, veio {{keys}}"
persisted = store.read("E3", keys[0])
assert persisted["banco"] == "itau", persisted
print(f"readback-ok {{keys[0]}}")
"""


def _docker_exec_python(snippet: str) -> str:
    proc = subprocess.run(
        ["docker", "exec", "-i", "-e", "PYTHONPATH=/repo", _CONTAINER, "python", "-"],
        input=snippet,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise SystemExit(f"❌ docker exec falhou: {proc.stderr[:800]}")
    return proc.stdout.strip()


def _docker_exec_seed(run_id: str) -> None:
    payload = json.loads(_E2_FIXTURE.read_text(encoding="utf-8"))
    payload.update(saldo_inicial=0.0, saldo_final=100.0)
    snippet = _SEED_SNIPPET.format(ws=_WS_ID, run=run_id, payload_json=json.dumps(payload))
    out = _docker_exec_python(snippet)
    assert "seed-ok" in out, out
    print(f"✓ seed E2 gravado via container (run {run_id})")


def _make_workspace(run_id: str) -> Path:
    ws = REPO_ROOT / "_smoke_storage" / f"ps-smoke-{run_id}"
    cfg = ws / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "pipeline.json").write_text(
        '{"reconciliation": {"skip_types": [], "skip_files": []}}', encoding="utf-8"
    )
    (cfg / "family_members.json").write_text("{}", encoding="utf-8")
    (cfg / "institutions.json").write_text('{"banco_canonical": {}}', encoding="utf-8")
    return ws


def _post_execute(run_id: str, ws_container_path: str) -> dict:
    body = json.dumps(
        {"run_id": run_id, "workspace_id": _WS_ID, "workspace_root": ws_container_path}
    ).encode()
    req = urllib.request.Request(
        f"{_SERVICE_URL}/api/v1/pipeline/stages/reconcile_transactions/execute",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def main() -> int:
    if not _FERNET_KEY_FILE.exists():
        raise SystemExit("❌ _smoke_pids/fernet.key ausente — rode 'make smoke-up' antes.")
    run_id = f"container-{int(time.time())}"
    ws = _make_workspace(run_id)
    _docker_exec_seed(run_id)
    result = _post_execute(run_id, f"/repo/_smoke_storage/{ws.name}")
    assert result.get("success") is True, f"stage falhou via container: {result}"
    print(f"✓ HTTP 200 success=true (duration {result.get('duration_ms', 0):.0f}ms)")
    out = _docker_exec_python(_READBACK_SNIPPET.format(ws=_WS_ID, run=run_id))
    print(f"✓ artefato E3 persistido: {out}")
    print(
        "\nGATE ADR-303 (container): PASSA — stage real via HTTP persistido em pipeline_artifacts."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
