# Mathoms AI — Planejamento Financeiro Inteligente

> Envie extratos e documentos financeiros. Obtenha um retrato consolidado da família em minutos — não em semanas de planilha.

**Status:** Dogfood interno · **Roadmap:** [docs/reference/PHASES.md](docs/reference/PHASES.md) · **Sprint atual:** [docs/_MOC/_generated/SPRINT_CURRENT.md](docs/_MOC/_generated/SPRINT_CURRENT.md) (auto) · narrativa em [docs/_MOC/SPRINTS-active.md](docs/_MOC/SPRINTS-active.md).

**Começar em <5min:** `make dev-up-docker` sobe a stack inteira em containers (Docker · ADR-252) em **API 8010 / Frontend 3010 / Postgres 5433** — banda distinta da nativa, então **coexiste** com o fallback uvicorn-local (8000/3000/8001/3100). Detalhes em [docs/reference/SETUP.md](docs/reference/SETUP.md).

**Produção (pré-launch · hosting ainda não provisionado):** `app.mathoms.ai` · API: `api.mathoms.ai/v1/` · Console interno: `ops.mathoms.ai` · Docs: `docs.mathoms.ai` · Status: `status.mathoms.ai` · Landing: `mathoms.ai`. Subdomínios canônicos em [ADR-108](docs/adr/108-estrategia-de-subdominios-mathomsai-cloudflare-dns.md); o cutover para produção é gated pelo plano [LAUNCH_TRUST](docs/plan/LAUNCH_TRUST/_README.md).

---

## O que é

Mathoms AI consolida extratos, faturas, investimentos e IRPFs de múltiplas instituições e gera um relatório com score financeiro, visão patrimonial, fluxo de caixa e recomendações.

**Recursos**

- **Relatório nativo** em React (rota `/reports/[id]`) com exportação **PDF** server-side via Playwright ([ADR-129](docs/adr/129-descontinuacao-completa-do-renderer-html-server.md)).
- **Parecer do Planejador** — revisão holística por LLM ([ADR-199](docs/adr/199-parecer-planejador-supersede-review-finances.md)).
- **Metas e Plano de Ação** versionados + **compartilhamento de workspace** (3 papéis, convites com TTL).
- **Multi-tenant** com isolamento por workspace.

**Como funciona (arquitetura)**

- **11 parsers de instituição** (`scripts/e2/banks/`), majoritariamente determinísticos (regex/tabela): C6, Itaú (2 layouts, incl. o de 2026), Santander, Bradesco, Caixa, BTG, Rico, PicPay, Wise, Bank of America e QuintoAndar (fatura de aluguel). A Caixa recorre a LLM de visão para PDFs somente-imagem. Fontes sem parser fixo (ex.: cripto/exchanges) caem no fallback **E2-llm** ou entram por extensão futura do E2.
- **LLM opcional (BYOK)** nas etapas sem parser fixo (E1, E1.5, E2-llm, E6-parecer, etc.).
- **Contratos type-safe** na API (FastAPI / OpenAPI) e tipagem forte no frontend (TypeScript, tipos gerados em `frontend/src/generated/`).
- **Camada de domínio isolada de I/O** ([ADR-089](docs/adr/089-pipelinedomain-camada-de-dominio-isolada-de-io.md)) — `Money` com `Decimal` ([ADR-090](docs/adr/090-decimal-money.md)), services de domínio puros testáveis em memória; artefatos do pipeline no banco via `ArtifactStore` (ADR-082/083, DB-only desde [ADR-212](docs/adr/212-sunset-mathoms-use-db-artifacts-disk-store-cli.md)). O reconciliador E3 foi decomposto por **extract-then-refactor** ([ADR-097](docs/adr/097-extract-then-refactor-estrategia-de-decomposicao.md)): 7 validators/preprocessors extraídos (`BankCanonicalizer`, `SaldoContinuityValidator`, `TemporalGapDetector`, `BaselineValidator`, etc.) sem tocar o `main()` legado.

---

## Documentação

### Produto e arquitetura

| Documento | Conteúdo |
| --------- | --------- |
| [docs/reference/PRODUCT.md](docs/reference/PRODUCT.md) | Visão, proposta de valor, público-alvo |
| [docs/reference/ARCHITECTURE.md](docs/reference/ARCHITECTURE.md) | Stack, modelo de dados, fluxos, pastas |
| [docs/reference/tenancy.md](docs/reference/tenancy.md) | Workspaces, isolamento, convites |
| [docs/reference/SETUP.md](docs/reference/SETUP.md) | Setup local, env, Redis, Celery, LLM |

### Execução e decisões

| Documento | Conteúdo |
| --------- | --------- |
| [docs/reference/PHASES.md](docs/reference/PHASES.md) | Fases macro, milestones, status |
| [docs/_MOC/_generated/SPRINT_CURRENT.md](docs/_MOC/_generated/SPRINT_CURRENT.md) | Sprint corrente + lanes ready (auto-gerado) |
| [docs/_MOC/SPRINTS-active.md](docs/_MOC/SPRINTS-active.md) | Narrativa editorial da sprint (vault atomizado, ADR-182) |
| [docs/_MOC/_generated/ADR_INDEX.md](docs/_MOC/_generated/ADR_INDEX.md) | ADRs por categoria + status (auto-gerado) |
| [docs/_MOC/_generated/CHANGELOG_RECENT.md](docs/_MOC/_generated/CHANGELOG_RECENT.md) | Entregas na janela de 14 dias desde a última entrega registrada (auto-gerado) |

### Contribuição e qualidade

| Documento | Conteúdo |
| --------- | --------- |
| [docs/reference/TESTING.md](docs/reference/TESTING.md) | Como rodar testes, CI, mocks |
| [CLAUDE.md](CLAUDE.md) | Instruções para assistentes de código / convenções do repo |
| [docs/reference/SKILLS.md](docs/reference/SKILLS.md) | Skills de projeto (audit-vault, parse-certify, ledger-certify, pipeline-review) — o quê / quando usar |

---

## Quick start

Pré-requisitos: **Python 3.11+**, **Node 20+** (Next 16 exige Node ≥20.9), **Redis** (ex.: `brew install redis`). `make help` lista todos os targets.

### Opção A — Docker (recomendado · 1 comando)

```bash
make dev-up-docker   # containers: API 8010 / Frontend 3010 / Postgres 5433 (coexiste com a stack nativa)
```

Sobe a stack inteira e **roda migrations + seed automaticamente** — não precisa de `.env` nem virtualenv (o compose traz defaults de dev). Boot leva ~60s.

- Abrir **http://localhost:3010** · API: **http://localhost:8010/docs** · login `admin@mathoms.ai` / `admin`.
- Parar (preserva volumes): `make docker-down` · logs: `make docker-logs` (`SVC=api` para um só) · reset destrutivo: `make docker-reset`.

### Opção B — Nativo (uvicorn local)

```bash
make onboard   # setup do zero: venv, deps, .env, migra o DB e cria o usuário dev
make up        # sobe os 6 serviços em background
```

Sobe 6 serviços: Redis, API 8000, worker Celery, frontend 3000, ops API 8001, frontend-ops 3100. Logs em `_dev_pids/<svc>.log`.

- Abrir **http://localhost:3000** · API: **http://localhost:8000/docs** · login `admin@mathoms.ai` / `admin`.
- Operar: `make status` (o que roda) · `make logs SVC=api` · `make down` (para tudo, preserva `.env` e `mathoms.db`) · `make recover` (destrava o clone).

Passo a passo (o que o `onboard` faz): `make dev-bootstrap` → `make seed` (que roda `make migrate` antes de semear, criando o schema via Alembic — não via `create_all`). Demais targets, fallback manual e troubleshooting (Alembic, Playwright/PDF): **[docs/reference/SETUP.md §4](docs/reference/SETUP.md)** · `make help`.

### Console interno local (operador dev/staging)

Ferramenta para o operador executar anonimização de conta, purge de documentos,
reset de senha, toggle `is_developer` e leitura de métricas/relatórios em
**dev/staging** — app Next separada em `frontend-ops/`, bind `127.0.0.1:3100`. As
rotas `/admin/*` no backend só respondem com a flag ligada (sem ela, retornam
404). Contexto de fase e detalhes em [docs/reference/RUNBOOK.md §7](docs/reference/RUNBOOK.md)
e no plano [INTERNAL_ADMIN](docs/plan/INTERNAL_ADMIN/_README.md).

Setup inicial do operador:

```bash
# 1. Gerar hash da senha (≥6 chars em dev; use ≥12 fora de localhost)
python3 scripts/hash_ops_pw.py   # cole o hash no próximo passo

# 2. Criar config/internal_operators.yaml a partir do exemplo (gitignored por design)
cp config/internal_operators.example.yaml config/internal_operators.yaml
# edite o arquivo e cole o hash do passo 1 em hashed_password
```

Depois disso, `make up` já sobe a Ops API (8001) e o frontend-ops (3100) com
as envs corretas (`MATHOMS_INTERNAL_OPS_UI_ENABLED=1` + session secret efêmero ou
o que estiver no `.env`). Login em **http://127.0.0.1:3100/login**.

Não rodar em produção: o console remoto (`ops.mathoms.ai`, OAuth staff) é lane
separada; o console local é bloqueado por flag + bind local + guard de
`ENVIRONMENT=production`.

---

## Contribuindo

Antes de abrir um PR, leia [docs/reference/ARCHITECTURE.md](docs/reference/ARCHITECTURE.md) e [docs/_MOC/_generated/ADR_INDEX.md](docs/_MOC/_generated/ADR_INDEX.md) (wrappers do pipeline, multi-tenant). Rode os gates locais antes do push: `make test` (pipeline + backend), `make precommit` (hooks de lint/PII/paths) e `make format` (ruff). Detalhes de testes e CI em [docs/reference/TESTING.md](docs/reference/TESTING.md); fluxo de PR completo em [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md). Convenções de commit, paths sensíveis e hooks: [CLAUDE.md](CLAUDE.md). Política de segurança e divulgação de vulnerabilidades: [SECURITY.md](SECURITY.md).
