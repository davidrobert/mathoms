# Mathoms AI — Planejamento Financeiro Inteligente

> Envie extratos e documentos financeiros. Obtenha um retrato consolidado da família em minutos — não em semanas de planilha.

**Status:** Dogfood interno · **F9 concluída** (relatório nativo React, design tokens, workspace sharing) · **Sprint transversal A6** em curso (Ondas 1-2 ✅; A6g.3 final + lane `adr-129-e6-kill` em andamento — ver [docs/BACKLOG.md §Sprint A6](docs/BACKLOG.md#sprint-a6--migração-infradomínio-plano-transversal)) · Próxima fase: **F7** (produção, LGPD, ops) — ver [docs/ROADMAP.md](docs/ROADMAP.md).

**Produção (em configuração):** `app.mathoms.ai` · API: `api.mathoms.ai/v1/` · Console interno: `ops.mathoms.ai` · Docs: `docs.mathoms.ai` · Status: `status.mathoms.ai` · Landing: `mathoms.ai`. Ver [ADR-108](docs/DECISIONS.md#adr-108--estratégia-de-subdomínios-mathomsai--cloudflare-dns).

---

## O que é

Mathoms AI consolida extratos, faturas, investimentos e IRPFs de múltiplas instituições, gerando análise com score financeiro, visão patrimonial, fluxo de caixa e recomendações.

- **11 parsers bancários determinísticos** (`scripts/e2/banks/`): C6, Itaú, Santander, Bradesco, Caixa, BTG, Rico, PicPay, Wise, Bank of America, QuintoAndar. Outras fontes (ex.: cripto/exchanges) entram via **E2-LLM** ou extensão futura do E2.
- **LLM opcional (BYOK)** para etapas que não têm parser fixo (E1, E1.5, E2-llm, E7-review, etc.).
- **Multi-tenant** com isolamento por workspace.
- **Contratos type-safe** na API (FastAPI / OpenAPI) e tipagem forte no frontend (TypeScript).
- **Camada de domínio isolada de I/O** (ADR-089) — `Money` com `Decimal` (ADR-090), services puros testáveis em memória; artefatos do pipeline no banco via `ArtifactStore` (ADR-082, ADR-083). Decomposição de E3 (1193 linhas) via **extract-then-refactor** (ADR-097): 7 validators/preprocessors extraídos (`BankCanonicalizer`, `SaldoContinuityValidator`, `TemporalGapDetector`, `BaselineValidator`, etc.) sem tocar o `main()` legado.

---

## Documentação

### Produto e arquitetura

| Documento | Conteúdo |
| --------- | --------- |
| [docs/PRODUCT.md](docs/PRODUCT.md) | Visão, proposta de valor, público-alvo |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Stack, modelo de dados, fluxos, pastas |
| [docs/tenancy.md](docs/tenancy.md) | Workspaces, isolamento, convites |
| [docs/SETUP.md](docs/SETUP.md) | Setup local, env, Redis, Celery, LLM |

### Execução e decisões

| Documento | Conteúdo |
| --------- | --------- |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Fases, milestones, status |
| [docs/BACKLOG.md](docs/BACKLOG.md) | Tasks (P0/P1/P2) |
| [docs/DECISIONS.md](docs/DECISIONS.md) | ADRs |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Entregas por data |

### Contribuição e qualidade

| Documento | Conteúdo |
| --------- | --------- |
| [docs/TESTING.md](docs/TESTING.md) | Como rodar testes, CI, mocks |
| [CLAUDE.md](CLAUDE.md) | Instruções para assistentes de código / convenções do repo |

---

## Quick start

Pré-requisitos: **Python 3.11+**, **Node 18+**, **Redis** (ex.: `brew install redis`). Recomenda-se um virtualenv na raiz do repositório.

```bash
# Na raiz do repositório
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
pip install -r backend/requirements.txt   # FastAPI, SQLAlchemy, Celery, cryptography…

cd frontend && npm install && cd ..

# Variáveis de ambiente (gera .env com MATHOMS_FERNET_KEY e demais secrets)
./scripts/gen-secrets.sh --init-env

# Primeira vez / após mudanças em layout ou tokens:
python3 design-tokens/build.py
python3 dev/codegen_report_layout.py

# Banco e usuário dev (SQLite em ./mathoms.db por padrão)
cd backend && python seed_db.py && cd ..
```

**Subir a aplicação** — são necessários **4 terminais** (Redis, API, worker Celery, Next.js):

```bash
# Terminal 1
redis-server

# Terminal 2 (com venv ativado, na raiz — NÃO fazer `cd backend`)
uvicorn backend.app.main:app --reload --port 8000

# Terminal 3 (com venv ativado, na raiz — mesmo nível que contém backend/)
celery -A backend.app.worker worker -l info -c 2

# Terminal 4
cd frontend && npm run dev
```

Abrir **http://localhost:3000** · API: **http://localhost:8000/docs** · Login após `seed_db.py`: `admin@mathoms.ai` / `admin123`.

Detalhes (Fernet, migrations Alembic, Playwright/PDF, troubleshooting): **[docs/SETUP.md](docs/SETUP.md)**.

### Console interno local (F7F-Local · IA-0)

Ferramenta para operador executar anonimização de conta, purge de documentos,
reset de senha, toggle `is_developer` e leitura de métricas/relatórios em
**dev/staging** — app Next separada em `frontend-ops/`, bind `127.0.0.1:3100`,
rotas `/admin/*` no backend só sobem com flag explícita.

Passos rápidos (ver **[docs/RUNBOOK.md §7](docs/RUNBOOK.md)** para detalhes):

```bash
# 1. Gerar hash do operador (senha ≥6 chars em dev; use ≥12 fora de localhost)
python3 scripts/hash_ops_pw.py   # cole o hash no próximo passo

# 2. Criar config/internal_operators.yaml (gitignored por design)
cat > config/internal_operators.yaml <<EOF
operators:
  - username: superadmin
    hashed_password: "$2b$12$..."
    role: superadmin
EOF

# 3. Backend com flag + session secret isolado (NÃO reusar SECRET_KEY do cliente)
# Porta 8001 para não colidir com o backend principal do dev (8000)
export MATHOMS_INTERNAL_OPS_UI_ENABLED=1
export MATHOMS_INTERNAL_OPS_SESSION_SECRET="<secret distinto>"
uvicorn backend.app.main:app --host 127.0.0.1 --port 8001

# 4. Frontend-ops em terminal separado (default rewrite já aponta p/ :8001)
cd frontend-ops && npm install && npm run dev
# http://127.0.0.1:3100/login
```

Não rodar em produção — F7F-Remote (`ops.mathoms.ai` com OAuth staff) é lane
separada; console local é bloqueado por flag + bind + guard de `ENVIRONMENT=production`.

---

## Contribuindo

Antes de abrir um PR, leia [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/DECISIONS.md](docs/DECISIONS.md) (wrappers do pipeline, multi-tenant). Para testes e CI, [docs/TESTING.md](docs/TESTING.md). Commits e paths sensíveis: [CLAUDE.md](CLAUDE.md) e hooks em `dev/`.
