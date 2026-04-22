#!/usr/bin/env bash
# A6g.6 slice 2 · ADR-114 — wrapper para pre-commit hook eslint-frontend.
#
# Pula quando frontend/node_modules não existe (dev local pode não ter
# instalado). CI sempre tem, então o gate efetivamente bloqueia lá.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
FRONT_DIR="$REPO_ROOT/frontend"

if [ ! -d "$FRONT_DIR/node_modules" ]; then
  echo "skip: frontend/node_modules ausente — rode 'cd frontend && npm install' para ativar o gate local" >&2
  exit 0
fi

cd "$FRONT_DIR"
exec npx --no-install eslint src/
