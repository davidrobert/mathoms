---
id: MOC-sprint-a20
type: moc
title: "Sprint A20 — Docker dev↔prod parity + P0 production gates"
aliases: ["A20", "Sprint A20"]
sprint_status: paused
date: "2026-05-22"
theme: "infra"
---

# Sprint A20 — Docker dev↔prod parity

> **Status:** `paused` — pausada pelo owner em 2026-05-29. O objetivo de DX
> (Docker como caminho opt-in de dev local) está **entregue e em uso**:
> `make dev-up-docker` sobe a stack completa numa banda de porta que coexiste
> com a nativa, com docs atualizadas (SETUP/README/`make help`). As lanes
> restantes **dependem de confirmação externa do owner** e ficam represadas até
> a retomada. Promovida `candidate → current` em 2026-05-29 (priorização do
> owner; A17 movida a `paused`). Criada 2026-05-22 após review independente
> `sre-devops` (maturidade Docker 2.5/5). Sprint de infra dedicada, **10 lanes em
> 2 ondas + gate final**, **7 ADRs Proposto** (ADR-248 a ADR-254). **Subsume W4-T02**
> do [PLATFORM_REVIEW](../../plan/PLATFORM_REVIEW/_README.md) (que estava `blocked`).
>
> **Entregue antes da pausa (2026-05-29):** Onda A (L10→L2, L3∥L6) → Gate A →
> Onda B (L1, L7, L8), **mais** o ajuste de coexistência de porta da stack dev
> ([[A20.l6]]/[[A20.l7]], PR #513). **Represado para a retomada** (requer
> confirmação externa do owner): **L4** (GHCR — token + Coolify webhook),
> **L5** (Trivy — depende de L4 publicar imagem) e **L9** (smoke gate — depende
> de tudo).

## Resumo

Resolver os **5 blockers P0** de produção identificados em review independente do
`sre-devops` e, no mesmo bundle, **eliminar o gap dev↔prod** transformando Docker
em caminho opt-in viável para onboarding (`make dev-up-docker`). As mesmas imagens
que sobem no dev local sobem em staging/prod, com hash determinístico, scan de
vulnerabilidade blocking, e renderização de PDF funcionando end-to-end (hoje cai
em fallback silencioso).

**Decisões macro consolidadas via review `senior-cto`:**

- **Sem ADR guarda-chuva** — sprint MOC é a costura natural; 6 ADRs específicas
  são auto-suficientes (precedente do repo: A18/[[ADR-239]], A19/[[ADR-240]]).
- **L1 (multi-stage) e L4 (GHCR) em paralelo** — image size não é breaking
  change pro registry; sequenciar atrasaria caminho crítico em ~3d sem ganho.
- **Opção C para Playwright em L1** — dual target no mesmo Dockerfile (`FROM
  runtime AS playwright`). Compose prod: `api → playwright`, `worker/beat →
  runtime`. Poupa ~450MB RAM em CX32 + drift impossível por construção.
- **L8 (driver Postgres) é obrigatória**, não opcional — coexistência psycopg2
  + asyncpg é dívida ativa que bloqueia enxugar imagem `runtime`.
- **+ L10 (Python lockfile com hashes)** — SHA pin de imagem base ([[A20.l2]])
  é placebo parcial sem isso; `pip install` resolve transitivamente.

## Objetivo

Materializar **paridade dev↔prod via Docker** com imagens determinísticas,
auditáveis e enxutas. North star: novo dev clona repo + roda `make dev-up-docker`
+ tem stack completa healthy em **<120s wall-clock**, com a **mesma imagem**
publicada no GHCR que vai subir em staging/prod.

## Por que agora (não-óbvio)

- W4-T02 do [PLATFORM_REVIEW](../../plan/PLATFORM_REVIEW/_README.md) está `blocked` há semanas (GHCR + SHA pin)
  e bloqueia indiretamente outras tasks `operational_gate`. A20 destrava.
- Os 5 P0s se beneficiam de resolver juntos: L1 (Playwright multi-stage) e L2
  (SHA pin) compartilham `Dockerfile`; L4 (GHCR) só faz sentido com imagem
  enxuta e pinada; L5 (Trivy blocking) depende de L4 publicar imagem para escanear.
- Fazer em lanes isoladas espalhadas em sprints custaria 3× mais context-switch.
- TTFR atual de ~25min (instalar Python+Postgres+Redis+Alembic+seed manualmente)
  é fricção real de onboarding pré-launch.

## Critérios de sucesso (mensuráveis)

1. **`make dev-up-docker`** parte de `git clone` limpo e sobe API + worker + beat
   + frontend + postgres + redis em **<120s wall-clock** numa máquina dev típica
   (≥8GB RAM, SSD). Comando único, sem editar `.env` manualmente além de uma vez.
2. **Backend image build time** <3min (warm cache) / <7min (cold) em GH Actions.
   Imagem `runtime` final <450MB; imagem `playwright` final <950MB.
3. **PDF export server-side via Playwright** funciona dentro do container
   (`image: playwright`) em integration test. Smoke
   `tests/integration/test_pdf_render_docker.py` verde — não cai mais em
   fallback `return None`.
4. **GHCR publica** `ghcr.io/davidrobert/mathoms-backend:{runtime,playwright}-<sha>`
   e `:{runtime,playwright}-latest` em todo push em `main`.
   `docker-compose.prod.yml` referencia tags SHA, não `:latest`.
5. **Trivy bloqueia merge** se imagem tem CVE `HIGH` ou `CRITICAL` com fix
   disponível em base ou layer próprio. SBOM CycloneDX publicado como artefato.
6. **Todos os containers rodam como UID não-root**; nenhum container tem
   `build-essential` em runtime; bases (python, node, postgres, redis) pinadas
   por `@sha256:`.
7. **Lockfile Python com hashes** (`requirements.lock`) consumido por `pip
   install --require-hashes` no Dockerfile. PR com diff em `requirements.in`
   sem `.lock` correspondente é bloqueado.
8. **5 P0s resolvidos** (P0.1 Playwright + P0.2 GHCR + P0.3 multi-stage + P0.4
   non-root pipeline-service + P0.5 SHA pin), cada um com ADR `Decidido`.
   W4-T02 do PLATFORM_REVIEW flippado `blocked → shipped`.
9. **KPI norte-mágico — TTFR (Time-To-First-Request)** para novo dev cai de
   ~25min (baseline) para **<5min** (`make dev-up-docker && curl localhost:8000/health`).

## Non-goals (explícitos)

- **Kubernetes / Helm.** Coolify continua orquestrador prod. Migração k8s é
  débito separado.
- **IaC do host CX32 (Terraform/Pulumi/Ansible).** Hetzner provisionado manual
  continua; IaC é ADR futura.
- **CI rodando os testes dentro de Docker.** Test suite continua em runner
  nativo do GH Actions; só o *build* da imagem entra em CI. Migrar testes
  para Docker dobra wall-clock sem ganho proporcional.
- **Deprecar `uvicorn` local / `npm run dev`.** Continuam suportados durante
  A20; deprecação é decisão pós-dogfood da paridade.
- **Refactor do `pipeline-service` container** além de não-root + healthcheck.
- **`docker-compose.ci.yml` dedicado para L9** — usa estensão do `smoke.yml`
  existente (gap 4 do review do `senior-cto` adiado).
- **TTFR <2min como meta hard.** Postgres + 2× Redis + Alembic `start_period:
  60s` é ~90-120s só de cold start. <5min é viável; sub-2min exige seed pré-built
  (gap 5 adiado).
- **Multi-arch builds (`linux/arm64`).** Coolify roda x86_64; arm64 só vira
  escopo se Apple Silicon dev local virar problema mensurável.
- **Trocar PostgreSQL ou Redis por managed (RDS/ElastiCache).** Build-vs-buy
  separado.

## Ondas

```
Onda A — quick wins, paralelo, baixo risco           (~3-5d)
├─ L2  SHA pinning + Dependabot Docker                [P0.5]
├─ L3  pipeline-service non-root + healthcheck        [P0.4 + P1.1]
├─ L6  docker-compose.dev.yml unificado               [P1.6 — DX]
└─ L10 Python lockfile com hashes (pip-tools/uv)      [NOVO — destrava L1]
        │
        ▼ Gate A: lockfile + SHA pin mergeados; compose dev sobe local

Onda B — núcleo, paralela, depende de A              (~5-8d)
├─ L1  Backend multi-stage + Playwright dual target   [P0.1 + P0.3]
├─ L4  GHCR push + tagging strategy                   [P0.2 — destrava W4-T02]
├─ L7  Makefile + SETUP.md revisado                   [DX]
└─ L8  Postgres driver consolidation (asyncpg-only)   [P1.2 — obrigatória]
        │
        ▼ Gate B: imagens publicadas em GHCR; PDF render funciona em container

Onda C — scan + gate final                           (~3d)
├─ L5  Trivy image blocking HIGH+ + SBOM CycloneDX    (depende de L4)
└─ L9  Smoke E2E em compose (login + relatório + PDF) [GATE de fechamento]
```

**Caminho crítico:** L10 → L1 → L4 → L5 → L9 (~10-13d wall-clock).
**Paralelismo máximo:** 4 agentes na onda A, 4 na onda B, 2 na onda C.

## ADRs Proposto (range ADR-248 a ADR-254)

| ID | Lane | Título |
|---|---|---|
| [[ADR-248]] | L1 | Multi-stage backend + Playwright dual target |
| [[ADR-249]] | L2 | SHA pinning de bases + Dependabot Docker |
| [[ADR-250]] | L4 | GHCR como registry + tagging strategy |
| [[ADR-251]] | L5 | Trivy image scan blocking HIGH+ + SBOM CycloneDX |
| [[ADR-252]] | L6+L7 | Compose dev unificado + Makefile targets opt-in |
| [[ADR-253]] | L8 | Postgres driver consolidation (asyncpg-only) |
| [[ADR-254]] | L10 | Python lockfile com hashes (pip-tools vs uv) |

Cada ADR é auto-suficiente. Sprint MOC (este arquivo) consolida a visão.
**Sem ADR guarda-chuva** — precedente do repo (A18/[[ADR-239]], A19/[[ADR-240]],
A11/ADRs 170-175) é "1 ADR por decisão técnica, sprint MOC coordena".

## Lanes

- [[A20.l1]] (`ready`) — Backend multi-stage + Playwright dual target. **L** · P0. Onda B. [[ADR-248]].
- [[A20.l2]] (`ready`) — SHA pinning + Dependabot Docker. **S** · P0. Onda A. [[ADR-249]].
- [[A20.l3]] (`ready`) — pipeline-service non-root + healthcheck por service. **XS** · P0. Onda A. [[ADR-252]].
- [[A20.l4]] (`ready`) — GHCR push + tagging strategy. **M** · P0. Onda B. [[ADR-250]].
- [[A20.l5]] (`ready`) — Trivy blocking + SBOM CycloneDX. **M** · P0. Onda C. Depende de L4. [[ADR-251]].
- [[A20.l6]] (`ready`) — `docker-compose.dev.yml` unificado + cleanup de composes legados. **M** · P1. Onda A. [[ADR-252]].
- [[A20.l7]] (`ready`) — Makefile targets `dev-up-docker` + `SETUP.md` revisado. **S** · P1. Onda B. [[ADR-252]].
- [[A20.l8]] (`ready`) — Postgres driver consolidation (asyncpg-only). **S** · P1. Onda B. [[ADR-253]].
- [[A20.l9]] (`blocked`) — Smoke E2E em compose (login + relatório + PDF). **S** · P0. Gate final. Bloqueia fechamento.
- [[A20.l10]] (`ready`) — Python lockfile com hashes. **S** · P0. Onda A. [[ADR-254]].

## Pré-requisitos

- A17 ([PLATFORM_REVIEW](../../plan/PLATFORM_REVIEW/_README.md) sub-lanes) e A18 (CRLV/apólices) não bloqueiam
  A20 — paralelizável.
- W4-T02 do [PLATFORM_REVIEW](../../plan/PLATFORM_REVIEW/_README.md) flippa `blocked → shipped` ao fechar L4+L5.
- Conta GHCR (`ghcr.io/davidrobert`) já existe — confirmar quota e `packages:
  write` no `GITHUB_TOKEN` antes de L4.
- Secret `MATHOMS_FERNET_KEY` em GH Actions já existe (usado em `ci.yml`).
- Coolify webhook precisa atualizar pra puxar tag SHA em vez de buildar localmente
  (passo manual de L4).

## Bloqueios externos

Nenhum. GHCR é gratuito no plano pessoal. Trivy é open-source (Aqua). pip-tools
e uv são open-source.

## Não-objetivos

Ver §Non-goals acima.

## Follow-ups potenciais (post-A20)

- **FU-1 · `docker-compose.ci.yml` dedicado** (gap 4 do `senior-cto`) — quando
  L9 evoluir além de smoke local. Sprint A21+.
- **FU-2 · Seed pré-built em compose dev** para sub-30s TTFR (gap 5). Dataset
  sintético versionado fora do git.
- **FU-3 · Multi-arch arm64** se Apple Silicon dev nativo virar bottleneck.
- **FU-4 · Migração `pyproject.toml` `[project]` formal** — substituir `.in`
  human-edited por `[project.dependencies]`.
- **FU-5 · `uv pip sync` em runtime** se velocidade install em CI virar
  gargalo crítico (decisão preservada em [[ADR-254]]).
- **FU-6 · Testes em Docker (CI)** quando deriva dev↔CI virar problema mensurável.
- **FU-7 · IaC para Hetzner CX32** (Terraform módulo único + state em S3).
- **FU-8 · Sunset uvicorn local** após 1 sprint de dogfood positivo do Docker.

## Métricas de saúde do sprint

| Métrica | Como medir | Baseline | Alvo |
|---|---|---|---|
| **TTFR** (novo dev) | `time make dev-up-docker && time curl --fail localhost:8000/health` (clone fresh) | ~25min | **<5min** |
| Backend image size `runtime` | `docker image inspect ghcr.io/.../backend:runtime-<sha> --format '{{.Size}}'` | ~1.1GB | **<450MB** |
| Backend image size `playwright` | idem | n/a | **<950MB** |
| Build time `runtime` (cold/warm) | GH Actions job duration | n/a | <7min / <3min |
| Build time `playwright` (cold/warm) | idem | n/a | <8min / <3min |
| Trivy CVE block rate | % PRs bloqueados por CVE HIGH+ com fix | 0% | 100% (gate hard) |
| P0s resolvidas | ADRs `Proposto → Decidido` | 0/5 | **5/5** |
| Lanes shipped | Frontmatter `status: shipped` | 0/10 | **≥9/10** |
| Workers sem Chromium | `docker exec worker ps -ef \| grep chromium` em `runtime` target | n/a | **vazio (audit)** |

## Riscos

| Risco | Prob | Mitigação |
|---|---|---|
| Playwright + Chromium ultrapassa 950MB no target `playwright` | P1 | Pre-flight em L1 mede tamanho ANTES de mergear; se >950MB, [[ADR-248]] documenta novo target com justificativa |
| Coolify quebra ao puxar de GHCR (auth/network) | P0 | L4 inclui smoke deploy em staging contra GHCR antes de cutover prod; runbook de rollback em `docs/reference/runbooks/coolify_ghcr_rollback.md` |
| Trivy blocking trava merges legítimos (CVE sem fix em base) | P1 | [[ADR-251]] define escape hatch documentado: `.trivyignore` por CVE com justificativa + data de revisão + dono; revisado mensalmente |
| Hot-reload em compose dev fica frágil (volumes NFS em macOS) | P1 | L6 testa em macOS + Linux explicitamente; fallback `cached`; alternativa final: rebuild rápido (`make dev-rebuild`) via cache de layers |
| L8 (driver consolidation) quebra migration Alembic | P0 | [[ADR-253]] avalia pre-flight; se sinal de risco, mantém `psycopg[binary]` v3 como fallback estrito; L8 nunca é "deferred" — vira gate de Onda B |
| Lockfile (L10) revela conflito transitivo escondido | P1 | Plano de execução em fases preserva install legado em paralelo até F3; conflito vira pin explícito em `.in` + regenerar |
| Coolify cobrança/quota inesperada com 2 imagens/release | P2 | GHCR é gratuito até 50GB no plano pessoal; com retention de 30d em PR-SHA, uso esperado <10GB |

## Dependências externas

- **W4-T02 (PLATFORM_REVIEW):** A20 **subsume**; ao fechar L4+L5, flippar
  `blocked → shipped` em [PLATFORM_REVIEW](../../plan/PLATFORM_REVIEW/_README.md) + atualizar [[ADR-228]] §G3.
- **GHCR (`ghcr.io/davidrobert`):** account já existe; confirmar `packages:
  write` no token e quota free tier (50GB).
- **Coolify webhook:** atualização manual em L4; runbook obrigatório
  (`docs/reference/runbooks/coolify_ghcr_deploy.md`).
- **Dependabot config:** atualizada em L2 (Docker) e L10 (pip).

## Pré-requisitos de pickup (cada lane)

Antes de qualquer lane:

1. `git fetch origin && git worktree list` — confirmar nenhum agente em lane A20.
2. ADR Proposto da lane **mergeada em `main`** (não basta aberta).
3. Pré-flight da lane (cada uma especifica) executado e documentado no PR como
   comentário inicial.
4. `pre-commit run --all-files` verde antes do PR.

## Definition of Done do sprint

- [ ] **5 P0 resolvidos** (P0.1 a P0.5), cada um com ADR `Decidido (Sprint A20.<lane>)`.
- [ ] **7 ADRs Proposto** (ADR-248 a ADR-254) flippadas para `Decidido`.
- [ ] **Lanes L1, L2, L3, L4, L5, L6, L7, L9, L10 `shipped`**. L8 `shipped`
      (obrigatória).
- [ ] **W4-T02** do PLATFORM_REVIEW flippado `blocked → shipped`.
- [ ] **`make dev-up-docker`** documentado em [SETUP](../../reference/SETUP.md) como caminho
      recomendado; uvicorn local mantido como fallback.
- [ ] **Métrica TTFR** medida pós-sprint por 1 dev real (PM ou CEO faz onboarding
      from-scratch e registra `time` em PR comment de L9).
- [ ] **[CHANGELOG](../../CHANGELOG.md) entry** no merge da última lane.
- [ ] Sprint flippa `current → done` em [[SPRINTS-active]].
- [ ] Atualizar [[ADR-228]] §G3 (operational gates) com referência a A20.

## Detalhe operacional

Track prompts dedicados (pós-F3/ADR-182 em `docs/sprint/A20/tracks/`, **não**
mais `docs/agent_prompts/`) para lanes complexas — criados 2026-05-29:
- [`tracks/a20-l1-backend-multistage.md`](tracks/a20-l1-backend-multistage.md) — L1
- [`tracks/a20-l4-ghcr-push.md`](tracks/a20-l4-ghcr-push.md) — L4
- [`tracks/a20-l5-trivy-sbom.md`](tracks/a20-l5-trivy-sbom.md) — L5
- [`tracks/a20-l6-compose-dev.md`](tracks/a20-l6-compose-dev.md) — L6
- [`tracks/a20-l9-smoke-e2e.md`](tracks/a20-l9-smoke-e2e.md) — L9
- [`tracks/a20-l10-python-lockfile.md`](tracks/a20-l10-python-lockfile.md) — L10

Lanes restantes (L2, L3, L7, L8) ficam só com `lanes/A20-lN-*.md` — escopo
mecânico não exige prompt operacional.
