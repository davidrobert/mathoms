# Mathoms frontend-ops — console interno (IA-0).
# Multi-stage, Next standalone, bind 127.0.0.1:3100 dentro do container.
# Expor para o host apenas via `-p 127.0.0.1:3100:3100` no compose (NUNCA 0.0.0.0).

# node:22-alpine pinado por digest do índice multi-arch (A20.L2 · ADR-249).
FROM node:26-alpine@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019 AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

FROM node:26-alpine@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019 AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:26-alpine@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019 AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=127.0.0.1
ENV PORT=3100
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3100
CMD ["node", "server.js"]
