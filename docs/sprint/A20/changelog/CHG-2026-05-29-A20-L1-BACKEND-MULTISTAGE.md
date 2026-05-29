---
id: CHG-2026-05-29-A20-L1-BACKEND-MULTISTAGE
type: changelog-entry
date: "2026-05-29"
sprint: A20
lane: "[[A20.l1]]"
adrs: ["[[ADR-248]]"]
summary: |
  A20.L1 — Dockerfile backend multi-stage com dual target (runtime /
  playwright). Resolve P0.3 (build-essential fora do runtime) e o problema
  arquitetural P0.1-adjacente (worker/beat não carregam mais ~956MB de
  Chromium). ADR-248 flipada para Decidido; metas de tamanho do draft
  (<450MB/<950MB) corrigidas para a realidade empírica (impossíveis).
tags:
  - type/changelog-entry
  - sprint/a20
  - area/infra
  - area/docker
  - area/devops
---

# A20.L1 — Backend multi-stage + Playwright dual target

- **`Dockerfile` reescrito** ([[ADR-248]] Opção C): 3 stages
  `builder → runtime → playwright`, 2 targets publicáveis. `playwright` herda
  de `runtime` (`FROM runtime AS playwright`) — drift impossível por construção.
  Default target = `playwright` (superset seguro para dev local).
- **P0.3 resolvido**: `build-essential` vive só no `builder` descartado;
  runtime não tem `gcc`. Wheels compilados no builder, instalados no runtime
  via **BuildKit bind-mount** (`--mount=type=bind,from=builder,source=/wheels`)
  — não `COPY /wheels`, que deixaria ~157MB mortos (runtime mediu 1.4GB com
  COPY; 1.09GB com bind-mount).
- **Worker/beat sem Chromium**: target `runtime` não roda `playwright install
  chromium` — economia de ~956MB de browser cache em 2 dos 3 containers.
  Só o target `playwright` (api) carrega Chromium para PDF render server-side.
- **`docker-compose.dev.yml` dual-target**: `api → target playwright`,
  `worker/beat → target runtime` (beat reusa o build do worker).
- **`dev/audit_backend_image.sh`** fixa os dois invariantes do dual-target
  (runtime sem gcc; runtime sem cache `ms-playwright`) + smoke do target
  playwright (Playwright funcional, Chromium presente) + heredity check.
- **Runbook** `docs/reference/runbooks/docker_images.md`: quando trocar de
  target, como auditar enxutez, tamanhos reais, armadilhas (bind-mount vs
  COPY, lockfile único, `docker history --format`).
- **Metas de tamanho corrigidas**: o draft pedia `runtime <450MB` /
  `playwright <950MB` — fisicamente impossíveis (~652MB de site-packages
  irredutível). Reais arm64: runtime ~1.09GB, playwright ~2.72GB. Tamanho
  absoluto saiu dos critérios; os dois invariantes do audit são o deliverable.
- **`requirements.lock` único** (raiz, [[A20.l10]]) consumido via
  `--require-hashes --no-index`. `ARG PYTHON_BASE=python:3.12-slim` deixa o
  SHA pin de [[A20.l2]] entrar num único ponto.
- **Revisão `sre-devops`** (obrigatória) com dados empíricos: aprovou path de
  revisar critérios + adicionar invariantes de audit; confirmou apt-clean nos
  3 stages e non-root UID 1000; decidiu **não tocar** `docker-compose.prod.yml`
  (defere para [[A20.l4]]) e manter `chromium-headless-shell` como follow-up.
- **[[ADR-248]] flipada `Proposto → Decidido (A20.L1)`**. Deferido para
  [[A20.l4]]: GHCR matrix build, prod compose por target, hadolint (pós SHA
  pin de L2), CI matrix ≤6min, pre-flight smoke em staging.
