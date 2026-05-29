# Mathoms frontend (cliente) — Next.js standalone (7A-dev).
# Multi-stage; build context = raiz do repo (precisa de design-tokens/, config/, dev/
# para o prebuild rodar codegen).
#
# Uso:
#   docker build -t mathoms-frontend -f frontend/Dockerfile .
#   docker run --rm -p 3000:3000 -e BACKEND_INTERNAL_URL=http://backend:8000 mathoms-frontend

# ---------------------------------------------------------------------------
# Stage 1: deps — instala node_modules a partir do package-lock.json
# ---------------------------------------------------------------------------
# node:22-alpine pinado por digest do índice multi-arch (A20.L2 · ADR-249).
FROM node:22-alpine@sha256:968df39aedcea65eeb078fb336ed7191baf48f972b4479711397108be0966920 AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

# ---------------------------------------------------------------------------
# Stage 2: builder — roda codegen (Python) + next build (gera .next/standalone)
# ---------------------------------------------------------------------------
FROM node:22-alpine@sha256:968df39aedcea65eeb078fb336ed7191baf48f972b4479711397108be0966920 AS builder
# Python necessário pelo prebuild: design-tokens/build.py + dev/codegen_report_layout.py.
# pyyaml + jsonschema são deps do codegen do report_layout.
RUN apk add --no-cache python3 py3-pip py3-yaml py3-jsonschema libc6-compat
WORKDIR /app

# node_modules vem da stage deps
COPY --from=deps /app/node_modules ./frontend/node_modules

# Inputs de codegen + frontend. Mantém a estrutura de pastas para que os scripts
# Python resolvam ROOT como /app (e gravem em frontend/src/{styles,generated}/).
COPY design-tokens ./design-tokens
COPY config ./config
COPY dev/codegen_report_layout.py ./dev/codegen_report_layout.py
COPY frontend ./frontend

# Codegen escreve também em frontend-ops/src/styles/ e backend/app/generated/;
# os scripts usam mkdir(parents=True) e essas pastas são descartadas com o builder.
WORKDIR /app/frontend
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 3: runner — imagem final mínima, só com o standalone server
# ---------------------------------------------------------------------------
FROM node:22-alpine@sha256:968df39aedcea65eeb078fb336ed7191baf48f972b4479711397108be0966920 AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Standalone copia server.js (root) + node_modules mínimo + .next/ minimal manifests.
# Next standalone preserva o layout do monorepo: server.js fica em /app/server.js
# (dir = __dirname), mas o build em si vive em /app/frontend/.next/. Por isso o
# `static/` precisa ser copiado para /app/frontend/.next/static (e não /app/.next).
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/static ./frontend/.next/static

# @swc/helpers: o tracer do Next standalone só copia o subset `cjs/`, mas o
# `package.json` aponta `module-sync` exports para `esm/` — quebra com
# "Cannot find module '@swc/helpers'" em runtime. Sobrescreve com a cópia
# completa da stage `deps` (cjs + esm).
COPY --from=deps --chown=nextjs:nodejs /app/node_modules/@swc/helpers ./node_modules/@swc/helpers

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
