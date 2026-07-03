# Base pinada por digest do índice multi-arch (A20.L2 · ADR-249).
FROM python:3.12-slim@sha256:090ba77e2958f6af52a5341f788b50b032dd4ca28377d2893dcf1ecbdfdfe203 AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIPELINE_SERVICE_HOST=0.0.0.0 \
    PIPELINE_SERVICE_PORT=8001 \
    MATHOMS_LOG_FORMAT=json

# Paridade com o backend: user mathoms UID 1000 (não-root). Mesmo
# nome/UID facilita debugging e compartilhamento de volume entre os dois
# serviços (A20.L3 · resolve P0.4 — pipeline-service rodava como root).
RUN useradd --create-home --uid 1000 mathoms

WORKDIR /repo

# Deps do backend PRIMEIRO (camada cacheável — o lock muda raro): pós-ADR-303,
# executar stages exige `backend.*` importável (DBArtifactStore + hidratação
# via run_context_factory). Lock inteiro com hashes — paridade com CI/backend;
# subconjunto curado seria um segundo manifesto a driftar. Imagem cresce e é
# aceito: uso é smoke opt-in; produção segue InProcessPipelineClient.
COPY requirements.lock /repo/requirements.lock
RUN pip install --upgrade pip && pip install --require-hashes -r /repo/requirements.lock

# `pipeline/` e `backend/` são importados como libraries. Docker-compose monta
# o repo no dev (mounts :ro no overlay — manter em sync com os COPYs abaixo,
# senão edit no host roda cópia stale); o COPY abaixo é o que vale em
# build/prod. O source de pipeline-service é copiado ANTES do install: o build
# do wheel valida o pacote `app/` (setuptools falha com "package directory
# 'app' does not exist" se só o pyproject estiver presente).
COPY pipeline-service /repo/pipeline-service
COPY pipeline /repo/pipeline
COPY backend /repo/backend
# Stages delegam para scripts/eN_*.py e validam contra config/schemas/*.json.
COPY scripts /repo/scripts
COPY config /repo/config
RUN pip install /repo/pipeline-service[test]
RUN chown -R mathoms:mathoms /repo

WORKDIR /repo/pipeline-service
USER mathoms
EXPOSE 8001

# Single-modo (sempre uvicorn :8001) → HEALTHCHECK no Dockerfile é o lugar
# certo (paridade com k8s/ECS que leem a instrução). urllib evita instalar
# curl na base slim; timeout=5 impede o check de pendurar. Contraste com o
# backend multi-modo, cujo healthcheck vive no compose por service (A20.L3).
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health', timeout=5)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
