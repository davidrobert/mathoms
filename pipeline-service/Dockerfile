FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIPELINE_SERVICE_HOST=0.0.0.0 \
    PIPELINE_SERVICE_PORT=8001 \
    MATHOMS_LOG_FORMAT=json

WORKDIR /repo

# `pipeline/` is imported as a library. Docker-compose mounts the repo so
# dev iterations don't require rebuilds; for production a COPY is needed.
COPY pipeline-service/pyproject.toml /repo/pipeline-service/pyproject.toml
RUN pip install --upgrade pip && pip install /repo/pipeline-service[test]

COPY pipeline-service /repo/pipeline-service
COPY pipeline /repo/pipeline

WORKDIR /repo/pipeline-service
EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
