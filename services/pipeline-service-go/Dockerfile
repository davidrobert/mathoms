# Imagem do shell Go (Caminho 1, ADR-150 §5 — F1 Fase 4, track f1-go-service).
#
# Multi-stage: binário Go + a MESMA base do pipeline-service Python (digest
# idêntico — manter os dois FROMs em sync; drift de base = drift de runtime
# do subprocess). O container carrega Go (shell HTTP) E Python (o CLI
# run-stage que executa os stages — ADR-150 §Consequências: Caminho 1 não
# elimina Python). Convive com a imagem Python até o decommission (F3);
# NÃO substitui — a coexistência é o mecanismo de rollback (§8).
#
# Build (context = raiz do repo):
#   docker build -f services/pipeline-service-go/Dockerfile -t mathoms-pipeline-service-go .

FROM golang:1.27@sha256:e432b43af23a9328d56a7c499be0476810aa344acbcf65fc7c455d4ff5a40602 AS gobuild
WORKDIR /src
COPY go.work go.work.sum ./
COPY services/pipeline-service-go ./services/pipeline-service-go
RUN cd services/pipeline-service-go && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" \
    -o /out/pipeline-service ./cmd/pipeline-service

FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIPELINE_SERVICE_HOST=0.0.0.0 \
    PIPELINE_SERVICE_PORT=8001 \
    MATHOMS_LOG_FORMAT=json \
    MATHOMS_PYTHON=python3 \
    MATHOMS_REPO_ROOT=/repo

RUN useradd --create-home --uid 1000 mathoms

WORKDIR /repo

# Runtime do subprocess: mesmas deps/sources da imagem Python (ADR-303 —
# o CLI precisa de backend.* importável). Manter em sync com
# pipeline-service/Dockerfile e com os mounts do overlay.
COPY requirements.lock /repo/requirements.lock
RUN pip install --upgrade pip && pip install --require-hashes -r /repo/requirements.lock
COPY pipeline /repo/pipeline
COPY backend /repo/backend
COPY scripts /repo/scripts
COPY config /repo/config
COPY --from=gobuild /out/pipeline-service /usr/local/bin/pipeline-service
RUN chown -R mathoms:mathoms /repo

USER mathoms
EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health', timeout=5)" || exit 1

ENTRYPOINT ["/usr/local/bin/pipeline-service"]
