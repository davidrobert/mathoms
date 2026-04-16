# Fin — Planejamento Financeiro Inteligente

> Envie extratos e documentos financeiros. Obtenha um retrato consolidado da família em minutos — não em semanas de planilha.

**Status:** Dogfood interno · **F9 concluída** (relatório nativo React, design tokens, workspace sharing) · Próxima fase planejada: **F7** (produção, LGPD, ops) — ver [docs/ROADMAP.md](docs/ROADMAP.md).

---

## O que é

Fin consolida extratos, faturas, investimentos e IRPFs de múltiplas instituições, gerando análise com score financeiro, visão patrimonial, fluxo de caixa e recomendações.

- **10 parsers bancários determinísticos** (`scripts/e2/banks/`): C6, Itaú, Santander, Bradesco, BTG, Rico, PicPay, Wise, Bank of America, QuintoAndar. Outras fontes (ex.: cripto/exchanges) entram via **E2-LLM** ou extensão futura do E2.
- **LLM opcional (BYOK)** para etapas que não têm parser fixo (E1, E1.5, E2-llm, E7-review, etc.).
- **Multi-tenant** com isolamento por workspace.
- **Contratos type-safe** na API (FastAPI / OpenAPI) e tipagem forte no frontend (TypeScript).

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

cd frontend && npm install && cd ..

# Variáveis de ambiente (na raiz): ./scripts/gen-secrets.sh --init-env
# (requer cryptography — ex.: pip install -r backend/requirements.txt)

# Primeira vez / após mudanças em layout ou tokens:
python3 design-tokens/build.py
python3 dev/codegen_report_layout.py

# Banco e usuário dev (SQLite em ./fin.db por padrão)
cd backend && python seed_db.py && cd ..
```

**Subir a aplicação** — são necessários **4 terminais** (Redis, API, worker Celery, Next.js):

```bash
# Terminal 1
redis-server

# Terminal 2 (com venv ativado, na raiz)
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 3 (com venv ativado, na raiz — mesmo nível que contém backend/)
celery -A backend.app.worker worker -l info -c 2

# Terminal 4
cd frontend && npm run dev
```

Abrir **http://localhost:3000** · API: **http://localhost:8000/docs** · Login após `seed_db.py`: `admin@fin.app` / `admin123`.

Detalhes (Fernet, migrations Alembic, Playwright/PDF, troubleshooting): **[docs/SETUP.md](docs/SETUP.md)**.

---

## Contribuindo

Antes de abrir um PR, leia [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/DECISIONS.md](docs/DECISIONS.md) (wrappers do pipeline, multi-tenant). Para testes e CI, [docs/TESTING.md](docs/TESTING.md). Commits e paths sensíveis: [CLAUDE.md](CLAUDE.md) e hooks em `dev/`.
