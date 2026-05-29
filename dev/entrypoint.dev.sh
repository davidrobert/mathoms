#!/usr/bin/env bash
# Entrypoint do container `api` em DEV (docker-compose.dev.yml · A20.L6).
# Diferenças vs entrypoint.sh de prod: roda seed mínimo se DB vazio e sobe
# uvicorn com --reload (hot-reload do bind mount ./backend:ro). Invocado via
# `bash /app/dev/entrypoint.dev.sh` no compose para não depender do x-bit do
# bind mount. dev/ chega no container por bind mount (Dockerfile não copia dev/).
set -euo pipefail

alembic -c backend/alembic.ini upgrade head

# Seed idempotente: o próprio script faz short-circuit se já há workspace.
python /app/dev/seed_minimal_workspace.py

# --reload-dir restringe o watcher a backend/app — watchar /app inteiro
# (pipeline/ + config/ + site-packages) satura CPU em macOS.
exec uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir backend/app
