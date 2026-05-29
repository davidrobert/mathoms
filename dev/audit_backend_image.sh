#!/usr/bin/env bash
# Auditoria das imagens backend multi-stage (ADR-248 / A20.L1).
#
# Fixa os DOIS invariantes que são o deliverable real do dual-target — não o
# tamanho absoluto (que depende de arch e do dep set de 652MB; ver ADR-248
# §Validação para os alvos empíricos amd64):
#
#   1. runtime NÃO tem toolchain de build (gcc) — P0.3 resolvido.
#   2. runtime NÃO tem o browser Chromium (ms-playwright cache) — worker/beat
#      economizam ~956MB; só o target playwright carrega Chromium.
#
# Complementa com smoke do target playwright (Playwright funcional + Chromium
# presente) e checagem de heredity (FROM runtime AS playwright).
#
# Uso:
#   dev/audit_backend_image.sh [RUNTIME_TAG] [PLAYWRIGHT_TAG]
# Sem args, builda mathoms-backend:runtime-audit + :playwright-audit do Dockerfile
# local. Em CI (A20.L4 matrix) passe as tags já buildadas pelos targets.
set -euo pipefail

RUNTIME_TAG="${1:-mathoms-backend:runtime-audit}"
PLAYWRIGHT_TAG="${2:-mathoms-backend:playwright-audit}"
DOCKERFILE="${DOCKERFILE:-Dockerfile}"
fail=0

note() { printf '  %s\n' "$*"; }
ok()   { printf '\033[32m✓\033[0m %s\n' "$*"; }
bad()  { printf '\033[31m✗\033[0m %s\n' "$*"; fail=1; }

if [[ -z "${1:-}" ]]; then
  echo "==> build runtime + playwright (sem tags passadas)"
  DOCKER_BUILDKIT=1 docker build --target runtime    -t "$RUNTIME_TAG"    -f "$DOCKERFILE" .
  DOCKER_BUILDKIT=1 docker build --target playwright  -t "$PLAYWRIGHT_TAG" -f "$DOCKERFILE" .
fi

echo "==> Invariante 1: runtime sem gcc (build-essential fora do runtime)"
if docker run --rm --entrypoint sh "$RUNTIME_TAG" -c 'command -v gcc >/dev/null'; then
  bad "gcc presente no runtime — build-essential vazou (P0.3 regrediu)"
else
  ok "runtime sem gcc"
fi

echo "==> Invariante 2: runtime sem Chromium (ms-playwright cache ausente)"
if docker run --rm --entrypoint sh "$RUNTIME_TAG" -c 'test -d /home/mathoms/.cache/ms-playwright'; then
  bad "ms-playwright cache presente no runtime — worker carregaria Chromium morto"
else
  ok "runtime sem cache de browser (worker/beat economizam ~956MB)"
fi

echo "==> Smoke: playwright target tem Chromium + Playwright funcional"
if docker run --rm --entrypoint python "$PLAYWRIGHT_TAG" -m playwright --version >/dev/null 2>&1; then
  ok "playwright funcional ($(docker run --rm --entrypoint python "$PLAYWRIGHT_TAG" -m playwright --version))"
else
  bad "python -m playwright --version falhou no target playwright"
fi
if docker run --rm --entrypoint sh "$PLAYWRIGHT_TAG" -c 'test -d /home/mathoms/.cache/ms-playwright'; then
  ok "Chromium instalado no target playwright"
else
  bad "ms-playwright cache ausente no playwright — PDF render quebrado (P0.1)"
fi

echo "==> Heredity: FROM runtime AS playwright (camada runtime antes de Chromium)"
if docker history "$PLAYWRIGHT_TAG" --format '{{.CreatedBy}}' | grep -q 'playwright install'; then
  ok "layer 'playwright install chromium' presente no playwright"
else
  note "aviso: não achei a layer Chromium no history (cache squash?) — não-fatal"
fi

echo
if [[ "$fail" -ne 0 ]]; then
  echo "AUDITORIA FALHOU"; exit 1
fi
echo "AUDITORIA OK — invariantes do dual-target preservados"
