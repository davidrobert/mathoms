# Fin — Planejamento Financeiro Inteligente

> Envie seus PDFs bancários. Receba um retrato financeiro completo da sua família em minutos — não em semanas de planilha.

**Status:** Dogfood interno • Premium E2E funcional • Dashboard + Transaction Explorer + Report React prontos

---

## O que é

Fin consolida automaticamente extratos, faturas, investimentos e IRPFs de múltiplos bancos brasileiros, gerando um relatório unificado com score financeiro, análise patrimonial, fluxo de caixa e recomendações.

- **11 parsers bancários nativos** (C6, Itaú, Santander, Bradesco, BTG, Rico, PicPay, Wise, BoA, QuintoAndar, Binance)
- **LLM opcional** (BYOK — Bring Your Own Key) para extração de docs sem parser determinístico
- **Multi-tenant** com isolamento por workspace
- **Type-safe end-to-end** (FastAPI OpenAPI → TypeScript)

---

## Documentação

### Para entender o produto
- **[docs/PRODUCT.md](docs/PRODUCT.md)** — Visão, proposta de valor, público-alvo, modelo de negócio
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Stack, modelo de dados, fluxos, estrutura de pastas
- **[docs/SETUP.md](docs/SETUP.md)** — Setup local, dependências, variáveis de ambiente

### Para acompanhar a execução
- **[docs/ROADMAP.md](docs/ROADMAP.md)** — Fases do projeto, milestones, status atual, timeline
- **[docs/BACKLOG.md](docs/BACKLOG.md)** — Tasks detalhadas com status (P0/P1/P2)
- **[docs/DECISIONS.md](docs/DECISIONS.md)** — Architecture Decision Records (ADRs)
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)** — Log cronológico do que foi entregue

---

## Quick Start

```bash
# 1. Pré-requisitos: Python 3.11+, Node 18+, Redis

# 2. Instalar pipeline + backend deps
pip install -e ".[dev]"

# 3. Instalar frontend
cd frontend && npm install && cd ..

# 4. Configurar env
cp .env.example .env   # ajustar FIN_FERNET_KEY se necessário

# 5. Inicializar DB (SQLite por default)
cd backend && python seed_db.py && cd ..

# 6. Rodar os 3 serviços (cada um em um terminal)
redis-server
cd backend && uvicorn app.main:app --reload --port 8000
cd backend && celery -A app.worker worker -l info -c 2
cd frontend && npm run dev

# 7. Abrir http://localhost:3000
#    Login: admin@fin.app / admin123
```

Para setup detalhado, troubleshooting e configuração de LLM: **[docs/SETUP.md](docs/SETUP.md)**

---

## Fase atual

**F6 completa** (Transaction Explorer + Dashboard + Report React + UX polish) • **F6.5** (testes frontend) e **F7** (produção + LGPD) em planejamento. Ver [docs/ROADMAP.md](docs/ROADMAP.md).

---

## Contribuindo

Antes de abrir um PR, leia [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/DECISIONS.md](docs/DECISIONS.md) para entender o padrão de wrappers e a estrutura multi-tenant.
