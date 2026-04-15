#!/usr/bin/env bash
# test_backend_down.sh — F6.5 (sub-fase 6.5F.3)
#
# Derruba a stack de teste. Por padrão preserva o volume do Postgres
# (re-up reusa estado para iterações rápidas). Use --volumes para limpar.

set -euo pipefail

cd "$(dirname "$0")/.."

WIPE=0
for arg in "$@"; do
  case "$arg" in
    --volumes|-v) WIPE=1 ;;
  esac
done

if [[ $WIPE -eq 1 ]]; then
  echo "→ Derrubando stack + volumes..."
  docker compose -f docker-compose.test.yml down -v
else
  echo "→ Derrubando stack (volumes preservados)..."
  docker compose -f docker-compose.test.yml down
fi

if [[ -f .env.test ]]; then
  rm .env.test
  echo "→ .env.test removido."
fi

echo "✓ Stack de teste parada."
