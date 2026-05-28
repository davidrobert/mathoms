# Backend container — Mathoms (lane 7A-dev, dev.3+dev.7)
# Single-stage, alvo "boota" (não otimizado pra tamanho).
# 3 modos via entrypoint: api / worker / beat.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    MATHOMS_LOG_FORMAT=json

# Apt deps mínimas:
# - build-essential + libpq-dev: psycopg2-binary já vem wheel, mas asyncpg/cryptography
#   podem precisar build em arch sem wheel pré-built. libpq-dev sustenta psycopg fallback.
# - curl: usado pelo HEALTHCHECK no modo api.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# User não-root (UID 1000 default; Coolify roda como root host, mas processo cai pra mathoms).
RUN useradd --create-home --shell /bin/bash --uid 1000 mathoms

WORKDIR /app

# Requirements: lock combinado (raiz + backend) com hashes — build determinístico
# bit-a-bit (ADR-254). `--require-hashes` recusa qualquer dep cujo hash sha256 não
# bata com o lock. requirements.in/backend/requirements.in são as sources human-edited;
# requirements.lock é gerado via pip-compile --generate-hashes em container amd64
# (runbook docs/reference/runbooks/python_dependencies.md). Regenerar em arm64
# quebra o build (hashes de wheels nativos divergem por plataforma).
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r /app/requirements.lock

# Código: backend e pipeline são pacotes peer; config tem schemas + layout YAML
# carregados em runtime; pyproject.toml fica pra metadata (não instalado em editable).
COPY backend/ /app/backend/
COPY pipeline/ /app/pipeline/
COPY config/ /app/config/
COPY pyproject.toml /app/pyproject.toml

# Storage volume — diretório criado pra montar volume persistente em prod.
RUN mkdir -p /app/storage \
    && chmod +x /app/backend/scripts/entrypoint.sh \
    && chown -R mathoms:mathoms /app

USER mathoms

EXPOSE 8000

# Healthcheck só faz sentido no modo api; em worker/beat o curl falha mas o
# start-period de 30s + retries=3 dá margem. Modos não-api podem ser configurados
# no compose pra desabilitar healthcheck (override).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/backend/scripts/entrypoint.sh"]
CMD ["api"]
