#!/usr/bin/env bash
# test_backend_up.sh — F6.5 (sub-fase 6.5F.3)
#
# Sobe stack de teste (Postgres 5433 + Redis 6380), aguarda health,
# exporta vars de ambiente em arquivo `.env.test` para o test runner.
#
# Uso:
#   ./scripts/test_backend_up.sh             # sobe e aguarda
#   ./scripts/test_backend_up.sh --reset     # derruba volumes antes (DB limpo)
#   ./scripts/test_backend_up.sh --no-wait   # sobe sem bloquear no health
#
# Saída:
#   `.env.test` na raiz com FIN_DATABASE_URL, REDIS_URL apontando para portas
#   isoladas. Test runner carrega via `dotenv` ou export manual.

set -euo pipefail

cd "$(dirname "$0")/.."

RESET=0
WAIT=1
for arg in "$@"; do
  case "$arg" in
    --reset) RESET=1 ;;
    --no-wait) WAIT=0 ;;
    *) echo "Arg desconhecido: $arg"; exit 1 ;;
  esac
done

if [[ $RESET -eq 1 ]]; then
  echo "→ Derrubando stack + volumes (reset completo)..."
  docker compose -f docker-compose.test.yml down -v
fi

echo "→ Subindo postgres-test (5433) + redis-test (6380)..."
docker compose -f docker-compose.test.yml up -d

if [[ $WAIT -eq 1 ]]; then
  echo "→ Aguardando health checks (timeout 60s)..."
  TIMEOUT=60
  ELAPSED=0
  while true; do
    PG_OK=$(docker inspect --format='{{.State.Health.Status}}' fin-postgres-test 2>/dev/null || echo "starting")
    REDIS_OK=$(docker inspect --format='{{.State.Health.Status}}' fin-redis-test 2>/dev/null || echo "starting")
    if [[ "$PG_OK" == "healthy" && "$REDIS_OK" == "healthy" ]]; then
      echo "✓ Postgres + Redis healthy."
      break
    fi
    if [[ $ELAPSED -ge $TIMEOUT ]]; then
      echo "✗ Timeout aguardando health (pg=$PG_OK, redis=$REDIS_OK)."
      docker compose -f docker-compose.test.yml logs --tail=30
      exit 1
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
  done
fi

cat > .env.test <<'EOF'
# Gerado por scripts/test_backend_up.sh — F6.5F.3
# NÃO COMITAR. Adicionado ao .gitignore.
FIN_DATABASE_URL=postgresql+asyncpg://fin_test:fin_test@127.0.0.1:5433/fin_test
FIN_DATABASE_URL_SYNC=postgresql+psycopg2://fin_test:fin_test@127.0.0.1:5433/fin_test
REDIS_URL=redis://127.0.0.1:6380/0
CELERY_BROKER_URL=redis://127.0.0.1:6380/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6380/2
EOF

echo ""
echo "✓ Stack pronta. Vars exportadas em .env.test:"
cat .env.test
echo ""
echo "Para usar com pytest/uvicorn:"
echo "  set -a; source .env.test; set +a"
echo ""
echo "Para derrubar:"
echo "  ./scripts/test_backend_down.sh"
