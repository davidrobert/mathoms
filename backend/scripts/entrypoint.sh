#!/usr/bin/env bash
# Entrypoint do container backend (modos: api/worker/beat). Lane 7A-dev. Migration roda só em api.
set -euo pipefail

ROLE="${1:-api}"

case "$ROLE" in
  api)
    # Alembic upgrade head é idempotente; em DB já atualizado é no-op.
    # Limitação aceita 7A-dev: race em multi-replica (1 réplica em dev minimal).
    alembic -c backend/alembic.ini upgrade head
    # --no-proxy-headers: o trust do XFF é do app (MATHOMS_FORWARDED_ALLOW_IPS,
    # ADR-232 §Emenda 2026-10-09). Com o CLI ligado, `*` trocaria o cliente pelo
    # hop forjado antes do middleware do app.
    exec uvicorn backend.app.main:app \
      --host 0.0.0.0 \
      --port 8000 \
      --no-proxy-headers
    ;;
  worker)
    exec celery -A backend.app.worker worker --loglevel=info --concurrency=2
    ;;
  beat)
    exec celery -A backend.app.worker beat --loglevel=info
    ;;
  *)
    echo "Usage: entrypoint.sh {api|worker|beat}" >&2
    echo "Got: '$ROLE'" >&2
    exit 1
    ;;
esac
