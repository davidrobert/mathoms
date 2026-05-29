# Mathoms AI — Planejamento Financeiro Inteligente

> Envie extratos e documentos financeiros. Obtenha um retrato consolidado da família em minutos — não em semanas de planilha.

**Status:** Dogfood interno · **Roadmap:** [docs/reference/PHASES.md](docs/reference/PHASES.md) · **Sprint atual:** [docs/_MOC/SPRINTS-active.md](docs/_MOC/SPRINTS-active.md).

**Começar em <5min:** `make dev-up-docker` sobe a stack inteira em containers (Docker · ADR-252) em **API 8010 / Frontend 3010 / Postgres 5433** — banda distinta da nativa, então **coexiste** com o fallback uvicorn-local (8000/3000/8001/3100). Detalhes em [docs/reference/SETUP.md](docs/reference/SETUP.md).

**Produção (em configuração):** `app.mathoms.ai` · API: `api.mathoms.ai/v1/` · Console interno: `ops.mathoms.ai` · Docs: `docs.mathoms.ai` · Status: `status.mathoms.ai` · Landing: `mathoms.ai`. Ver [ADR-108](docs/adr/108-estrategia-de-subdominios-mathomsai-cloudflare-dns.md).

---

## O que é

Mathoms AI consolida extratos, faturas, investimentos e IRPFs de múltiplas instituições, gerando análise com score financeiro, visão patrimonial, fluxo de caixa e recomendações.

- **11 parsers bancários determinísticos** (`scripts/e2/banks/`): C6, Itaú, Santander, Bradesco, Caixa, BTG, Rico, PicPay, Wise, Bank of America, QuintoAndar. Outras fontes (ex.: cripto/exchanges) entram via **E2-LLM** ou extensão futura do E2.
- **LLM opcional (BYOK)** para etapas que não têm parser fixo (E1, E1.5, E2-llm, E6-parecer, etc.).
- **Multi-tenant** com isolamento por workspace.
- **Contratos type-safe** na API (FastAPI / OpenAPI) e tipagem forte no frontend (TypeScript).
- **Camada de domínio isolada de I/O** (ADR-089) — `Money` com `Decimal` (ADR-090), services puros testáveis em memória; artefatos do pipeline no banco via `ArtifactStore` (ADR-082, ADR-083). Decomposição de E3 (1193 linhas) via **extract-then-refactor** (ADR-097): 7 validators/preprocessors extraídos (`BankCanonicalizer`, `SaldoContinuityValidator`, `TemporalGapDetector`, `BaselineValidator`, etc.) sem tocar o `main()` legado.

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
| [docs/_MOC/SPRINTS-active.md](docs/_MOC/SPRINTS-active.md) | Sprint atual + lanes ready (vault atomizado, ADR-182) |
| [docs/_MOC/_generated/ADR_INDEX.md](docs/_MOC/_generated/ADR_INDEX.md) | ADRs por categoria + status (auto-gerado) |
| [docs/_MOC/_generated/CHANGELOG_RECENT.md](docs/_MOC/_generated/CHANGELOG_RECENT.md) | Entregas últimos 14 dias (auto-gerado) |

### Contribuição e qualidade

| Documento | Conteúdo |
| --------- | --------- |
| [docs/reference/TESTING.md](docs/reference/TESTING.md) | Como rodar testes, CI, mocks |
| [CLAUDE.md](CLAUDE.md) | Instruções para assistentes de código / convenções do repo |

---

## Quick start

Pré-requisitos: **Python 3.11+**, **Node 18+**, **Redis** (ex.: `brew install redis`). Recomenda-se um virtualenv na raiz do repositório.

```bash
# Na raiz do repositório
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e . -r requirements-dev.txt  # pipeline editable + backend + pytest plugins + reportlab

cd frontend && npm install && cd ..

# Variáveis de ambiente (gera .env com MATHOMS_FERNET_KEY e demais secrets)
./scripts/gen-secrets.sh --init-env

# Primeira vez / após mudanças em layout ou tokens:
python3 design-tokens/build.py
python3 dev/codegen_report_layout.py

# Banco e usuário dev (SQLite em ./mathoms.db por padrão)
cd backend && python seed_db.py && cd ..
```

**Subir a aplicação** — uma aba sobe os 6 serviços (Redis, API 8000, worker Celery, frontend 3000, ops API 8001, frontend-ops 3100):

```bash
make dev-bootstrap   # primeira vez: venv, deps, .env, codegen
make dev-up          # sobe tudo em background; logs em _dev_pids/<svc>.log
make dev-status      # ✅/❌ por serviço (PID + porta)
make dev-logs        # tail -f (use SVC=api para um só)
make dev-down        # mata tudo (preserva .env e mathoms.db)
```

Abrir **http://localhost:3000** · API: **http://localhost:8000/docs** · Login após `make dev-bootstrap`: `admin@mathoms.ai` / `admin123`.

Detalhes dos targets, `dev-pull`, `dev-restart-worker`, `dev-reset-env` e fallback manual de 4 terminais: **[docs/reference/SETUP.md §4](docs/reference/SETUP.md)**. Migrations Alembic, Playwright/PDF, troubleshooting: idem.

### Console interno local (F7F-Local · IA-0)

Ferramenta para operador executar anonimização de conta, purge de documentos,
reset de senha, toggle `is_developer` e leitura de métricas/relatórios em
**dev/staging** — app Next separada em `frontend-ops/`, bind `127.0.0.1:3100`,
rotas `/admin/*` no backend só sobem com flag explícita.

Setup inicial do operador (ver **[docs/reference/RUNBOOK.md §7](docs/reference/RUNBOOK.md)** para detalhes):

```bash
# 1. Gerar hash da senha (≥6 chars em dev; use ≥12 fora de localhost)
python3 scripts/hash_ops_pw.py   # cole o hash no próximo passo

# 2. Criar config/internal_operators.yaml (gitignored por design)
cat > config/internal_operators.yaml <<EOF
operators:
  - username: superadmin
    hashed_password: "$2b$12$..."
    role: superadmin
EOF
```

Depois disso, `make dev-up` já sobe a Ops API (8001) e o frontend-ops (3100) com
as envs corretas (`MATHOMS_INTERNAL_OPS_UI_ENABLED=1` + session secret efêmero ou
o que estiver no `.env`). Login em **http://127.0.0.1:3100/login**.

Não rodar em produção — F7F-Remote (`ops.mathoms.ai` com OAuth staff) é lane
separada; console local é bloqueado por flag + bind + guard de `ENVIRONMENT=production`.

---

## Contribuindo

Antes de abrir um PR, leia [docs/reference/ARCHITECTURE.md](docs/reference/ARCHITECTURE.md) e [docs/_MOC/_generated/ADR_INDEX.md](docs/_MOC/_generated/ADR_INDEX.md) (wrappers do pipeline, multi-tenant). Para testes e CI, [docs/reference/TESTING.md](docs/reference/TESTING.md). Fluxo de PR completo em [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md). Commits e paths sensíveis: [CLAUDE.md](CLAUDE.md) e hooks em `dev/`.
