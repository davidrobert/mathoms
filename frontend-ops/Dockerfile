# Mathoms frontend-ops — console interno (IA-0).
# Multi-stage, Next standalone. Dentro do container o server escuta em
# 0.0.0.0:3100: o port-forward do Docker entrega na eth0 do container, e um bind
# em 127.0.0.1 responde "Empty reply" ao host. O isolamento é o prefixo
# `127.0.0.1:` no `ports:` do compose — NUNCA publique sem ele.

# node:<major>-alpine pinado por digest do índice multi-arch (A20.L2 · ADR-249).
# O major é o de frontend-ops/.nvmrc — o gate node-version-parity reprova divergência.
FROM node:26-alpine@sha256:2d984a15c9b54fd0aeb608b8e0d0d83529eb34d2966db27a1fb4f1edc3d298a3 AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:26-alpine@sha256:2d984a15c9b54fd0aeb608b8e0d0d83529eb34d2966db27a1fb4f1edc3d298a3 AS builder
WORKDIR /app
# O rewrite `/admin/*` do next.config.ts é resolvido no `next build` e fica no
# routes-manifest; env de runtime não o altera. Default = api da rede do compose
# (127.0.0.1:8001, o default do next.config, não existe dentro de um container).
ARG INTERNAL_OPS_API_BASE=http://api:8000
ENV INTERNAL_OPS_API_BASE=$INTERNAL_OPS_API_BASE
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:26-alpine@sha256:2d984a15c9b54fd0aeb608b8e0d0d83529eb34d2966db27a1fb4f1edc3d298a3 AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3100
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3100
# /login renderiza sem backend; `/` redireciona para /users.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:3100/login || exit 1
CMD ["node", "server.js"]
