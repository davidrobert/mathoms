# syntax=docker/dockerfile:1.7
# ADR-248 — multi-stage backend com dual target (runtime / playwright).
# Build:
#   docker build --target runtime    -t mathoms-backend:runtime-<sha>    .
#   docker build --target playwright -t mathoms-backend:playwright-<sha> .
# Default target = playwright (superset seguro pra dev local rodar tudo, incl. PDF).
#
# Lockfile único combinado `requirements.lock` (ADR-254 / A20.L10): pip-compile
# --generate-hashes sobre requirements.in + backend/requirements.in. backend/
# requirements.in NÃO é instalado direto — o lock da raiz já é o superset.

# PYTHON_BASE pinado por digest do índice multi-arch (A20.L2 · ADR-249).
# tag@sha256 preserva legibilidade + reprodutibilidade; o digest é do manifest
# list (não platform-specific), então resolve amd64/arm64. Dependabot
# (ecosystem docker, dir `/`) re-pina quando sai versão nova. Único ponto de
# pin para os 3 FROM (builder/runtime/playwright).
ARG PYTHON_BASE=python:3.12-slim@sha256:090ba77e2958f6af52a5341f788b50b032dd4ca28377d2893dcf1ecbdfdfe203

# ──────────────────────────────────────────────────────────────────────────
# Stage 1: builder — compila wheels nativos (cryptography, asyncpg, etc.).
# Descartado no resultado final; só produz wheels em /wheels/.
# ──────────────────────────────────────────────────────────────────────────
FROM ${PYTHON_BASE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Lockfile primeiro pra maximizar cache da layer de wheels.
COPY requirements.lock /build/requirements.lock

# Constroi wheels em /wheels/ — instala depois no runtime stage (zero compile lá).
RUN pip wheel --require-hashes --wheel-dir /wheels -r /build/requirements.lock

# ──────────────────────────────────────────────────────────────────────────
# Stage 2: runtime — base enxuta (api fora-de-Playwright, worker, beat).
# Target publicado: mathoms-backend:runtime-<sha>. Tamanho alvo: <450MB.
# ──────────────────────────────────────────────────────────────────────────
FROM ${PYTHON_BASE} AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    MATHOMS_LOG_FORMAT=json

# Runtime libs (sem build-essential): libpq5 pro psycopg fallback, curl pro healthcheck.
# L8/ADR-253 consolida driver — quando entregue, libpq5 pode sair se asyncpg-only.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# User não-root (UID 1000) — mesmo padrão do legado single-stage.
RUN useradd --create-home --shell /bin/bash --uid 1000 mathoms

WORKDIR /app

# Instala wheels do builder — zero compile, fast, determinístico.
# Bind-mount transitório (não COPY): os wheels nunca viram layer persistente.
# COPY /wheels deixaria ~150MB mortos na imagem mesmo após `rm -rf` (a layer
# anterior não é reclamada por um RUN posterior).
COPY requirements.lock /app/requirements.lock
RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    pip install --require-hashes --no-index --find-links /wheels -r /app/requirements.lock

# Código — ordenado pra cache (config muda menos que código da API).
COPY config/ /app/config/
COPY pipeline/ /app/pipeline/
COPY backend/ /app/backend/
COPY pyproject.toml /app/pyproject.toml

RUN mkdir -p /app/storage \
    && chmod +x /app/backend/scripts/entrypoint.sh \
    && chown -R mathoms:mathoms /app

USER mathoms
EXPOSE 8000

# Sem instrução de health-check aqui: a imagem é multi-modo (api/worker/beat
# via entrypoint) e `curl /health` só vale para o api. worker/beat não expõem
# HTTP e ficariam unhealthy permanentemente. Cada service declara o seu no
# compose por service (A20.L3 · ADR-252 D4).

ENTRYPOINT ["/app/backend/scripts/entrypoint.sh"]
CMD ["api"]

# ──────────────────────────────────────────────────────────────────────────
# Stage 3: playwright — runtime + Chromium + libs de sistema.
# Herda 100% de runtime (FROM runtime AS playwright); só adiciona Chromium.
# Target publicado: mathoms-backend:playwright-<sha>. Tamanho alvo: <950MB.
# DEFAULT TARGET (superset seguro pra dev local).
# ──────────────────────────────────────────────────────────────────────────
FROM runtime AS playwright

USER root

# Libs Chromium em Debian bookworm (slim). Lista enxugada de
# `playwright install-deps chromium` — só o necessário pro PDF headless
# server-side em backend/app/services/pdf_renderer.py.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libnss3 \
        libnspr4 \
        libdbus-1-3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpango-1.0-0 \
        libcairo2 \
        libatspi2.0-0 \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

USER mathoms

# Apenas Chromium (não webkit/firefox) — única engine usada pelo pdf_renderer.
# Browsers ficam em /home/mathoms/.cache/ms-playwright/ (já owned pelo user).
RUN python -m playwright install chromium
