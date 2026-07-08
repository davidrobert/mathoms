---
id: CHG-2026-05-29-A20-L7-MAKEFILE-ONBOARDING
type: changelog-entry
date: "2026-05-29"
sprint: A20
lane: "[[A20.l7]]"
adrs: ["[[ADR-252]]"]
summary: |
  A20.L7 — Makefile dev-*-docker + SETUP.md "Onboarding em <5min" (D3+D5).
  6 targets `make` para a stack Docker do L6 (sufixo `-docker` para não
  colidir com a stack uvicorn-local legada), SETUP/README/runbook reescritos
  posicionando Docker como caminho recomendado e uvicorn como fallback.
tags:
  - type/changelog-entry
  - sprint/a20
  - area/dx
  - area/docs
---

# A20.L7 — Makefile targets + onboarding revisado

> **Nota (2026-07-08, #847):** os targets desta entrega foram renomeados para a
> taxonomia env-first — `dev-up-docker`→`docker-up`, `dev-down-docker`→`docker-down`,
> `dev-reset-docker`→`docker-reset`, `dev-shell-docker`→`docker-shell`,
> `dev-rebuild-docker`→`docker-build`, `dev-logs-docker`→`docker-logs`; nativa
> `dev-up`→`native-up`, `dev-down`→`native-down`. Os nomes abaixo são o que foi
> entregue em 2026-05-29 e seguem como aliases com aviso; use os canônicos (ver
> [[ADR-252]] §Emenda).

- **6 targets `make` para a stack Docker** ([[ADR-252]] D3) sobre o
  `docker-compose.dev.yml` do [[A20.l6]]:
  - `dev-up-docker` — sobe a stack (`up -d --build`) com guard de porta
    (`check_port_free` em 8000 + 3000) e echo das URLs.
  - `dev-down-docker` — `down` (preserva volumes).
  - `dev-reset-docker` — `down -v` (wipe DB/Redis/storage → re-seed).
  - `dev-shell-docker` — `exec api bash`.
  - `dev-rebuild-docker` — `build` (sem subir).
  - `dev-logs-docker` — `logs -f` (`SVC=<nome>` filtra um service).
  - Todos com linha `## target: desc` → aparecem em `make help`.
- **Desvio de naming vs lane (intencional)**: a lane previa
  `dev-down`/`dev-reset`/`dev-shell`/`dev-rebuild`/`dev-logs` sem sufixo,
  mas `dev-up`/`dev-down`/`dev-logs` **já existem** como a stack uvicorn-local
  legada (Makefile linhas 429/501/631). Sufixo `-docker` uniforme nos 6
  evita colisão parcial e deixa explícito qual stack se está operando.
- **SETUP.md** ([[ADR-252]] D5): nova seção topo "Onboarding em <5min"
  com `make dev-up-docker` como comando único; bloco de operação diária;
  setup uvicorn-local rebaixado a fallback documentado.
- **README**: linha "Começar em <5min" apontando `make dev-up-docker`.
- **Runbook `dev_environment.md` §3**: atalhos `make` adicionados antes dos
  equivalentes `docker compose` crus; troubleshooting de porta 8000 cita
  `make dev-up`/`dev-down` (legado).
- **Gates human-only adiados** (registrados como follow-up, não bloqueiam o
  artefato): TTFR medido por dev real em clone fresh (critério 2 e 6) e
  cross-test macOS+Linux — exigem clone limpo e host sem uvicorn na 8000.
  A validação autônoma cobriu: `make help` lista os 6 targets,
  `docker compose -f docker-compose.dev.yml config --quiet` passa.
- **ADR-252 permanece `Proposto`** até [[A20.l3]] (D4 — healthcheck Celery)
  entrar; L7 (D3/D5) e L6 (D1/D2) já mergeados.
