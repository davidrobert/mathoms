#!/usr/bin/env bash
# Entrypoint do container `api-ops` em DEV (docker-compose.dev.yml · ADR-116).
# Processo dedicado ao /admin/*: sem alembic nem seed — o `api` migra, e o
# compose só sobe este depois do `api` healthy. Invocado via `bash` como o
# entrypoint.dev.sh, pelo mesmo motivo (x-bit do bind mount).
set -euo pipefail

# Fail-fast aqui, não `${VAR:?}` no compose: o Compose interpola todo service
# antes de filtrar o profile, e o `:?` quebraria o `up` de quem não usa ops.
# Antes do `exec` porque, sob --reload, startup que falha não derruba o reloader.
python - <<'PY'
import sys

from backend.app.core.internal_ops_auth import InternalOpsConfigError, validate_internal_ops_config

try:
    validate_internal_ops_config()
except InternalOpsConfigError as exc:
    sys.exit(f"api-ops não sobe: {exc} Ver docs/reference/RUNBOOK.md §7.2.")
PY

exec uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir backend/app
