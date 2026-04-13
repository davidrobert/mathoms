# PRODUCT PLAN — Fin: Planejamento Financeiro Inteligente

> **Documento vivo.** Atualizado a cada sprint. Fonte de verdade para visão, arquitetura, fases e backlog.
>
> **Última atualização:** 2026-04-13
> **Status global:** Fase 0 — Planejamento

---

## Índice

1. [Visão do Produto](#1-visão-do-produto)
2. [Decisões Estratégicas](#2-decisões-estratégicas)
3. [Arquitetura Alvo](#3-arquitetura-alvo)
4. [Estado Atual do Projeto](#4-estado-atual-do-projeto)
5. [Fases de Migração](#5-fases-de-migração)
   - [Fase 0 — Desacoplar Core](#fase-0--desacoplar-core-em-package-python)
   - [Fase 1 — Backend API + Auth](#fase-1--backend-fastapi--auth--db)
   - [Fase 2 — Upload + Pipeline Web](#fase-2--upload-de-arquivos--pipeline-trigger)
   - [Fase 3 — Configuração via UI](#fase-3--configuração-via-ui)
   - [Fase 4 — Automação LLM](#fase-4--automação-llm-premium)
   - [Fase 5 — Task Queue + Async](#fase-5--task-queue--real-time-progress)
   - [Fase 6 — Frontend Polished](#fase-6--frontend-completo--polish)
   - [Fase 7 — Produção + LGPD](#fase-7--infraestrutura-de-produção--lgpd)
6. [Backlog Priorizado](#6-backlog-priorizado)
7. [Sprints](#7-sprints)
8. [Decisões Técnicas Pendentes](#8-decisões-técnicas-pendentes)
9. [Métricas de Sucesso](#9-métricas-de-sucesso)
10. [Riscos e Mitigações](#10-riscos-e-mitigações)
11. [Log de Progresso](#11-log-de-progresso)

---

## 1. Visão do Produto

### O que é

**Fin** é um planejador financeiro pessoal inteligente que consolida automaticamente extratos, faturas, investimentos e declarações de IRPF de múltiplos bancos brasileiros, gerando um relatório profissional unificado com score financeiro, análise patrimonial, fluxo de caixa e recomendações.

### Proposta de valor

> "Envie seus PDFs bancários. Receba um retrato financeiro completo da sua família em minutos — não em semanas de planilha."

### Diferenciais competitivos

1. **Parsers nativos para bancos BR** — não depende de Open Banking (ainda limitado no Brasil)
2. **Consolidação multi-banco, multi-membro** — visão família, não indivíduo
3. **IRPF-aware** — cruza dados fiscais com patrimoniais
4. **LLM-augmented** — extrai documentos sem parser determinístico via fallback inteligente
5. **Relatório com narrativa** — não é só número, é contexto e recomendação

### Público-alvo

| Segmento | Perfil | Dor |
|----------|--------|-----|
| **Primário** | Profissionais PJ/CLT alta renda, múltiplas contas | Não conseguem ver o retrato completo das finanças |
| **Secundário** | Famílias com patrimônio diversificado (imóveis + investimentos) | Consolidação manual em planilha demora dias |
| **Futuro (B2B2C)** | Planejadores financeiros independentes | Ferramenta white-label para atender clientes |

---

## 2. Decisões Estratégicas

| Decisão | Escolha | Data | Rationale |
|---------|---------|------|-----------|
| Modelo de negócio | **Freemium** | 2026-04-13 | Free = pipeline determinístico. Premium = LLM + features avançadas |
| Primeiro cliente | **Dogfood (David)** | 2026-04-13 | Refinar até estar perfeito antes de abrir |
| LLM strategy | **Híbrido** | 2026-04-13 | Free sem LLM. Premium: BYOK ou incluso na assinatura |
| Frontend | **Next.js + TypeScript** | 2026-04-13 | Performático, tipagem estática, ecossistema maduro |
| Backend | **FastAPI (Python)** | 2026-04-13 | Mesma linguagem dos scripts, async, Pydantic nativo |
| Banco de dados | **PostgreSQL** (prod) / **SQLite** (dev) | 2026-04-13 | Robusto, JSON support, full-text search |
| Type safety end-to-end | **openapi-typescript** | 2026-04-13 | FastAPI OpenAPI → TS types auto-gerados |

---

## 3. Arquitetura Alvo

### Diagrama de componentes

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (SPA)                         │
│  Next.js 15 + TypeScript + shadcn/ui + Tailwind          │
│  Upload, Config, Dashboard, Reports, Onboarding          │
└────────────────────────┬────────────────────────────────┘
                         │ REST API (OpenAPI)
                         │ + WebSocket (progress)
┌────────────────────────┴────────────────────────────────┐
│                  BACKEND (API Server)                      │
│  FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2         │
│                                                           │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │ Auth Module   │  │ Pipeline      │  │ LLM Service   │  │
│  │ JWT + bcrypt  │  │ Orchestrator  │  │ Anthropic/OAI │  │
│  └──────────────┘  └───────────────┘  └───────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         Pipeline Core (package Python)               │  │
│  │   e0/ e2/ e3/ e4/ e5/ e5n/ e6/ e7/ models/          │  │
│  │   Refatorados como módulos importáveis               │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────┬────────────────┬────────────────┬────────────┘
           │                │                │
      ┌────┴─────┐   ┌─────┴──────┐   ┌─────┴──────┐
      │PostgreSQL │   │File Storage│   │Task Queue  │
      │users,     │   │uploads,    │   │Celery/ARQ  │
      │configs,   │   │processed,  │   │+ Redis     │
      │results    │   │reports     │   │            │
      └──────────┘   └────────────┘   └────────────┘
```

### Type safety ponta-a-ponta

```
FastAPI (Pydantic models)
    → auto-generate OpenAPI schema (JSON)
        → openapi-typescript (build step)
            → TypeScript types (.d.ts)
                → Next.js consome com fetch type-safe
```

### Modelo de dados (inicial)

```
User
  id, email, hashed_password, name, tier, created_at
  llm_api_key (encrypted)

Workspace
  id, user_id, name, created_at

FamilyMember
  id, workspace_id, name, cpf (encrypted), birth_date, role

BankAccount
  id, family_member_id, institution, account_type, agency, account_number

Document
  id, workspace_id, original_name, stored_path, doc_type
  status (uploaded|routed|processed|error), uploaded_at

Category
  id, workspace_id, code, name, monthly_cap, keywords[]

PipelineRun
  id, workspace_id, status, current_stage
  started_at, completed_at, config_snapshot (JSON)
  tier_at_run (free|premium)

PipelineStageLog
  id, pipeline_run_id, stage, status, started_at, completed_at
  output_summary, errors

Report
  id, pipeline_run_id, html_path, period_start, period_end
  created_at, score, patrimonio_liquido
```

### Estrutura de pastas alvo (pós-migração completa)

```
fin/
├── backend/
│   ├── alembic/                  # DB migrations
│   ├── app/
│   │   ├── api/                  # FastAPI routers
│   │   │   ├── auth.py
│   │   │   ├── documents.py
│   │   │   ├── pipeline.py
│   │   │   ├── reports.py
│   │   │   └── config.py
│   │   ├── core/                 # Auth, security, settings
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic request/response
│   │   ├── services/             # Business logic
│   │   └── main.py
│   ├── pipeline/                 # Pipeline core (refatorado)
│   │   ├── core/                 # E0-E7 como módulos
│   │   │   ├── e0_unlock.py
│   │   │   ├── e0_audit.py
│   │   │   ├── e0_route.py
│   │   │   ├── e2/              # Parsers (já modular)
│   │   │   │   ├── banks/
│   │   │   │   ├── common.py
│   │   │   │   ├── registry.py
│   │   │   │   └── validation.py
│   │   │   ├── e3_reconcile.py
│   │   │   ├── e4_categorize.py
│   │   │   ├── e5_analyze.py
│   │   │   ├── e5n_narrativas.py
│   │   │   ├── e6_render.py
│   │   │   └── e7_review.py
│   │   ├── llm/                  # LLM service (Fase 4)
│   │   │   ├── service.py
│   │   │   ├── prompts/
│   │   │   └── validators/
│   │   ├── models/               # Pydantic models dos artefatos
│   │   │   ├── e2_result.py
│   │   │   ├── e3_result.py
│   │   │   ├── e4_result.py
│   │   │   ├── e5_result.py
│   │   │   └── config.py
│   │   └── orchestrator.py       # Substitui e_reset.py
│   ├── scripts/                  # CLIs thin wrappers (retrocompat)
│   │   ├── e_reset.py
│   │   ├── e_save.py
│   │   └── ...
│   ├── storage/                  # File storage por tenant
│   │   └── {workspace_id}/
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router
│   │   │   ├── (auth)/           # Login, Register
│   │   │   ├── (dashboard)/      # Dashboard, Reports
│   │   │   ├── (config)/         # Settings, Categories
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ui/               # shadcn/ui components
│   │   │   └── ...
│   │   ├── lib/
│   │   │   ├── api.ts            # Type-safe API client
│   │   │   └── auth.ts
│   │   └── types/
│   │       └── api.d.ts          # Auto-generated from OpenAPI
│   ├── package.json
│   └── tsconfig.json
│
├── docker-compose.yml
├── docs/
│   └── PRODUCT_PLAN.md           # ← este documento
└── README.md
```

---

## 4. Estado Atual do Projeto

### O que já existe e funciona

| Asset | Detalhes | Valor |
|-------|----------|-------|
| **11 parsers bancários** | C6, Itaú, Santander, Bradesco, BTG, Rico, PicPay, Wise, BoA, QuintoAndar, Binance | Alto — difícil de replicar |
| **Pipeline E0→E7** | 14 etapas, 31 scripts Python, ~860KB de código | Alto — lógica de domínio refinada |
| **Categorização** | 300+ keywords em 16 categorias | Médio — expansível |
| **Relatório HTML** | ~411KB, Chart.js, dark mode, narrativas | Médio — precisa virar componente |
| **Reconciliação** | Deduplicação cross-banco, transferências internas | Alto — lógica complexa |
| **Cross-validation** | 14 checks automáticos no E7 | Médio — qualidade do output |
| **Config estruturada** | 22 arquivos em config/ (JSON, YAML, MD) | Médio — precisa virar DB |
| **Testes** | ~7 arquivos em tests/ | Baixo — precisa expandir |

### O que NÃO existe ainda

- Nenhum web framework (sem Flask, FastAPI, Django)
- Nenhum banco de dados
- Nenhuma autenticação
- Nenhuma UI (output é HTML estático)
- LLM calls são manuais (via chat, não API)
- Sem multi-tenancy
- Sem task queue / processamento assíncrono

---

## 5. Fases de Migração

> **Regra de ouro:** Após cada fase, o pipeline continua funcionando e gerando relatórios corretos.

### Visão geral

| Fase | Nome | Duração est. | Pré-requisito | Entrega principal |
|------|------|-------------|---------------|-------------------|
| **0** | Desacoplar Core | 3-4 sem | — | Pipeline como package Python importável + contexto injetável |
| **1** | Backend API + Auth | 2-3 sem | Fase 0 | Login/registro + API de relatórios |
| **2** | Upload + Pipeline Web | 2-3 sem | Fase 1 | Upload via browser + trigger de pipeline |
| **3** | Configuração via UI | 3-4 sem | Fase 2 | CRUD de membros, categorias, parâmetros |
| **4** | Automação LLM | 3-4 sem | Fase 3 | Pipeline end-to-end sem intervenção |
| **5** | Task Queue + Async | 2-3 sem | Fase 4 | Execução em background + progresso real-time |
| **6** | Frontend Polished | 4-6 sem | Fase 5 | Dashboard, onboarding, landing page |
| **7** | Produção + LGPD | 2-3 sem | Fase 6 | Deploy seguro, criptografia, compliance |

**Timeline total estimada: ~7 meses** (com entregas funcionais a cada 2-3 semanas).

---

### FASE 0 — Desacoplar Core em Package Python

**Objetivo:** Tornar os scripts chamáveis programaticamente com paths e configs injetáveis, sem reescrever a lógica interna.

**Estratégia: "Wrap, Don't Rewrite"**

Os scripts são grandes (E6=197KB, E5=107KB) e têm lógica de domínio refinada. Reescrevê-los é arriscado. Em vez disso:

1. Criar uma camada de **contexto** (`WorkspaceContext`) que fornece paths e configs
2. **Envolver** cada script com uma função que aceita esse contexto
3. O código interno dos scripts permanece **inalterado** inicialmente
4. CLIs continuam funcionando exatamente como antes

**Duração estimada:** 3-4 semanas (4 sub-fases)

#### Diagnóstico técnico dos acoplamentos atuais

| Acoplamento | Onde ocorre | Impacto |
|-------------|-------------|---------|
| Paths via `__file__` | Todos os 14 scripts | Impede rodar com root diferente (multi-tenant) |
| Config no module-level | e2/common, e3, e4, e5, e5n | Importar módulo = ler disco. Impede injetar config do DB |
| `_load_json_config` duplicado | 6 implementações diferentes | Dificulta trocar source de config |
| `print()` para progresso | Todos os scripts | Impede capturar progresso para WebSocket |
| I/O direto no filesystem | Todos os scripts | OK para Fase 0, abstrair em Fase 2 |

#### Scripts por tamanho e risco

| Script | KB | Linhas | Entry point existente | Risco |
|--------|-----|--------|----------------------|-------|
| `e6_render.py` | 197 | ~3968 | `render_report()` ✓ | Alto — refatorar por ÚLTIMO |
| `e5_analyze.py` | 107 | ~2572 | `main()` ✓ | Alto — muitas configs |
| `e5n_narrativas.py` | 61 | ~1198 | `main()` ✓ | Médio |
| `e_reset.py` | 55 | ~1314 | Orchestration complexo | Médio — postergar para 0D |
| `e3_reconcile.py` | 44 | ~1131 | `main()` ✓ | Médio — bom candidato inicial |
| `e4_categorize.py` | 41 | ~1018 | `main()` ✓ | Médio — bom candidato inicial |
| `e7_review.py` | 36 | ~900 | `main()` ✓ | Baixo |
| `e0_audit.py` | 36 | ~900 | `main()` ✓ | Baixo |
| `e0_route.py` | 31 | ~750 | `main()` ✓ | Baixo |
| `e2_extract.py` | 10 | ~300 | `main()` ✓ | Baixo — E2 já é modular |
| `e2/` (banks+common) | ~130 | ~3000 | Registry pattern ✓ | Baixo — já bem estruturado |

---

#### Sub-fase 0A: Foundation Layer (Semana 1)

**Objetivo:** Criar as abstrações base sem tocar nos scripts existentes.

| # | Tarefa | Prioridade | Estimativa | Status |
|---|--------|-----------|-----------|--------|
| 0A.1 | Criar `pipeline/` package com `__init__.py` na raiz do projeto | P0 | 1h | ☐ |
| 0A.2 | Criar `pipeline/context.py` com classe `WorkspaceContext` | P0 | 4h | ☐ |
| 0A.3 | Criar `pipeline/config_loader.py` — loader unificado (disco ou dict) | P0 | 4h | ☐ |
| 0A.4 | Criar `pipeline/logging.py` — adapter que captura print + logging | P1 | 3h | ☐ |
| 0A.5 | Snapshot de golden files: salvar outputs atuais do E2→E6 para regressão | P0 | 2h | ☐ |
| 0A.6 | Criar script `tests/test_regression.py` que compara outputs | P0 | 3h | ☐ |

**`WorkspaceContext`** — o conceito central:

```python
# pipeline/context.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class WorkspaceContext:
    """Fornece paths e configs para o pipeline. Injeta dependências em vez de
    ler do disco via __file__. Default = layout atual do projeto."""

    root: Path  # raiz do workspace (= PROJECT_DIR atual)

    # Paths derivados (calculados no __post_init__)
    config_dir: Path = field(init=False)
    data_dir: Path = field(init=False)
    processed_dir: Path = field(init=False)
    e2_dir: Path = field(init=False)
    e3_dir: Path = field(init=False)
    e4_dir: Path = field(init=False)
    e5_dir: Path = field(init=False)
    output_dir: Path = field(init=False)
    logs_dir: Path = field(init=False)

    # Config overrides (se None, carrega do disco via config_dir)
    config_overrides: Optional[dict] = None

    def __post_init__(self):
        self.config_dir = self.root / "config"
        self.data_dir = self.root / "data"
        self.processed_dir = self.root / "processed"
        self.e2_dir = self.processed_dir / "E2_extracts"
        self.e3_dir = self.processed_dir / "E3_reconciled"
        self.e4_dir = self.processed_dir / "E4_unified"
        self.e5_dir = self.processed_dir / "E5_analysis"
        self.output_dir = self.root / "output"
        self.logs_dir = self.root / "logs"

    def load_config(self, name: str) -> dict:
        """Carrega config do override (DB/dict) ou do disco."""
        if self.config_overrides and name in self.config_overrides:
            return self.config_overrides[name]
        path = self.config_dir / name
        if path.exists():
            import json
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    @classmethod
    def default(cls) -> "WorkspaceContext":
        """Contexto padrão: raiz do projeto atual (retrocompatível)."""
        project_dir = Path(__file__).resolve().parent.parent
        return cls(root=project_dir)

    @classmethod
    def for_tenant(cls, tenant_root: Path, config: dict) -> "WorkspaceContext":
        """Contexto para tenant web com config do banco de dados."""
        return cls(root=tenant_root, config_overrides=config)
```

**Por que isso é poderoso:**
- Scripts CLI: `ctx = WorkspaceContext.default()` → funciona igual a antes
- Web API: `ctx = WorkspaceContext.for_tenant(Path(f"storage/{workspace_id}"), db_config)` → multi-tenant
- Testes: `ctx = WorkspaceContext(root=tmp_dir, config_overrides={...})` → isolado

---

#### Sub-fase 0B: Wrap dos módulos menores (Semana 1-2)

**Objetivo:** Criar wrappers para E3 e E4 (os mais "funcionais" — input claro → output claro).

| # | Tarefa | Prioridade | Estimativa | Status |
|---|--------|-----------|-----------|--------|
| 0B.1 | Wrap `e3_reconcile.py`: criar `run_e3(ctx: WorkspaceContext)` | P0 | 4h | ☐ |
| 0B.2 | Wrap `e4_categorize.py`: criar `run_e4(ctx: WorkspaceContext)` | P0 | 4h | ☐ |
| 0B.3 | Wrap `e2_extract.py`: criar `run_e2(ctx: WorkspaceContext, mode)` | P0 | 3h | ☐ |
| 0B.4 | Wrap `e7_review.py`: criar `run_e7_crossval(ctx)` e `run_e7_apply(ctx)` | P1 | 3h | ☐ |
| 0B.5 | Criar `pipeline/stages.py` — registry de stages com suas funções | P0 | 2h | ☐ |
| 0B.6 | Testes de regressão E3: output idêntico via wrapper vs CLI direto | P0 | 2h | ☐ |
| 0B.7 | Testes de regressão E4: output idêntico via wrapper vs CLI direto | P0 | 2h | ☐ |

**Pattern do wrapper — Opção B com `_init_config()` (Decidido)**

Cada script ganha uma função `_init_config(base_dir)` que (re)carrega todos os globals
de configuração. É chamada no module level com o default (retrocompat), e re-chamada
por `main(root_dir=...)` quando um root diferente é injetado.

**Passo 1 — Mudança cirúrgica no script (exemplo E3):**

```python
# scripts/e3_reconcile.py

_DEFAULT_BASE = Path(__file__).resolve().parent.parent

def _init_config(base_dir: Path):
    """(Re)carrega paths e configs a partir de um root_dir.
    Chamado no module level com default, e por main() com root injetado."""
    global _BASE_DIR, _CONFIG_DIR, PIPE_CONFIG, ACCOUNT_TYPE_EQUIVALENCES
    global _BANCO_CANONICAL_REVERSE
    _BASE_DIR = base_dir
    _CONFIG_DIR = base_dir / "config"
    PIPE_CONFIG = _load_json(_CONFIG_DIR / "pipeline.json")
    ACCOUNT_TYPE_EQUIVALENCES = _load_equivalences(_CONFIG_DIR / "family_members.json")
    _BANCO_CANONICAL_REVERSE = _load_banco_canonical_reverse()

# Module level: carrega defaults (retrocompat com import e CLI direto)
_init_config(_DEFAULT_BASE)

def main(root_dir: Path = None):
    if root_dir:
        _init_config(root_dir)
    # ... resto do main() 100% inalterado ...

if __name__ == "__main__":
    main()  # sem argumento = default = igual a antes
```

**Esforço real por script (refinado):**

| Script | Globals a re-inicializar | Linhas extras | Complexidade |
|--------|--------------------------|---------------|-------------|
| `e3_reconcile.py` | ~5 | ~15 | Baixa |
| `e4_categorize.py` | ~10 (3 configs + 7 derivados) | ~25 | Média |
| `e2/common.py` | ~8 (FAMILY, LOCALE, INST, PIPE + derivados) | ~20 | Média |
| `e5_analyze.py` | ~5 (paths + DOBs) | ~15 | Baixa |
| `e5n_narrativas.py` | ~15 (FAMILY + 12 keys + FISCAL) | ~35 | Média-alta |
| `e6_render.py` | ~3 (paths + template) | ~10 | Baixa |

**Passo 2 — Wrapper fino no package pipeline:**

```python
# pipeline/stages/e3.py
from pipeline.context import WorkspaceContext

def run(ctx: WorkspaceContext) -> dict:
    """Executa E3 reconciliation com contexto injetado."""
    from scripts.e3_reconcile import main as e3_main
    e3_main(root_dir=ctx.root)
    files = list(ctx.e3_dir.glob("*-3_reconciled.json"))
    return {"success": True, "files_created": [f.name for f in files]}
```

**Vantagens:**
- Thread-safe (cada call re-inicializa seus globals com o root recebido)
- CLI funciona idêntico (`main()` sem argumento)
- Wrappers são triviais (3-5 linhas cada)
- Testável com `main(root_dir=Path("/tmp/test_workspace"))`
- Lógica interna dos scripts permanece 100% inalterada

**Regras da Fase 0:**
- Scripts permanecem em `scripts/` (sem reorganização de arquivos)
- `pipeline/` importa de `scripts/` (reorganização de pastas é Fase 2+)
- Config sempre vem de `root_dir/config/` (injeção via DB é Fase 3)
- `e_reset.py` roda scripts via subprocess hoje — orchestrator (0D) substitui por chamadas diretas

---

#### Sub-fase 0C: Wrap dos módulos grandes + Config injection (Semana 2-3)

**Objetivo:** E5, E5.N, E6 e E0s ganham wrappers. Config passa a ser injetável.

| # | Tarefa | Prioridade | Estimativa | Status |
|---|--------|-----------|-----------|--------|
| 0C.1 | Wrap `e5_analyze.py`: criar `run_e5(ctx)` | P0 | 6h | ☐ |
| 0C.2 | Wrap `e5n_narrativas.py`: criar `run_e5n(ctx)` | P0 | 4h | ☐ |
| 0C.3 | Wrap `e6_render.py`: criar `run_e6(ctx)` | P0 | 6h | ☐ |
| 0C.4 | Wrap `e0_audit.py`: criar `run_e0_audit(ctx)` | P1 | 3h | ☐ |
| 0C.5 | Wrap `e0_route.py`: criar `run_e0_route(ctx)` | P1 | 3h | ☐ |
| 0C.6 | Wrap `e0_unlock.py`: criar `run_e0_unlock(ctx)` | P1 | 2h | ☐ |
| 0C.7 | Wrap `e15_consolidate.py`: criar `run_e15c(ctx)` | P1 | 2h | ☐ |
| 0C.8 | Refatorar `pipeline_common.py` para usar `WorkspaceContext` | P0 | 3h | ☐ |
| 0C.9 | Refatorar `e2/common.py` — config lazy-loaded em vez de module-level | P0 | 4h | ☐ |
| 0C.10 | Testes de regressão completos: E0→E6 via wrappers | P0 | 3h | ☐ |

**O desafio do E5 (107KB):**
- Carrega **10 arquivos de config** diferentes (`goals.json`, `scoring.json`, `parametros_fiscais.json`, etc.)
- Muitos desses loads são em `_load_*()` functions chamadas no module level
- Solução: Mover loads para dentro de `main()`, guardar em dict, passar para subfunções
- Mudança cirúrgica: renomear `main()` para `_main_impl(ctx=None)`, criar novo `main()` que chama `_main_impl(WorkspaceContext.default())`

**O desafio do E6 (197KB):**
- Já tem `render_report()` como entry point limpo
- A maioria dos helpers não lê config — recebe dados como parâmetro
- Path de output e template são os principais acoplamentos
- Solução: `render_report(ctx=None)` — se None, usa default. Mudança de ~10 linhas.

---

#### Sub-fase 0D: Orchestrator + Package final (Semana 3-4)

**Objetivo:** Pipeline chamável end-to-end via Python. CLIs viram thin wrappers.

| # | Tarefa | Prioridade | Estimativa | Status |
|---|--------|-----------|-----------|--------|
| 0D.1 | Criar `pipeline/orchestrator.py` — sequencia stages usando wrappers | P0 | 8h | ☐ |
| 0D.2 | Adaptar `e_reset.py` para usar orchestrator (manter CLI interface) | P1 | 6h | ☐ |
| 0D.3 | Criar `pipeline/__init__.py` com API pública limpa | P0 | 2h | ☐ |
| 0D.4 | Criar `pyproject.toml` com dependências | P1 | 2h | ☐ |
| 0D.5 | Consolidar `_load_json_config` — uma implementação, em `pipeline/config_loader.py` | P1 | 3h | ☐ |
| 0D.6 | Testes de integração: `pipeline.run(ctx)` produz relatório correto | P0 | 4h | ☐ |
| 0D.7 | Documentar API do package em docstrings | P2 | 2h | ☐ |

**Orchestrator — interface alvo:**

```python
# pipeline/orchestrator.py
from pipeline.context import WorkspaceContext
from pipeline.stages import e0, e2, e3, e4, e5, e5n, e6, e7

DETERMINISTIC_STAGES = [
    ("E0-audit", e0.run_audit),
    ("E2-extratos", e2.run_extratos),
    ("E2-faturas", e2.run_faturas),
    ("E3", e3.run),
    ("E4", e4.run),
    ("E5", e5.run),
    ("E5.N", e5n.run),
    ("E6", e6.run),
    ("E7-crossval", e7.run_crossval),
]

LLM_STAGES = ["E1", "E1.5", "E2-llm", "E7-review"]

def run_pipeline(
    ctx: WorkspaceContext,
    from_stage: str = "E0",
    skip_llm: bool = True,      # Free tier = skip. Premium = False.
    on_progress=None,            # callback(stage, status, message)
) -> PipelineResult:
    """Executa pipeline completo ou parcial."""
    ...
```

**Como `e_reset.py` fica:**

```python
# scripts/e_reset.py (thin wrapper — mantém toda a interface CLI)
if __name__ == "__main__":
    args = parse_args()
    if args.new_orchestrator:
        # Nova path via pipeline package
        from pipeline.orchestrator import run_pipeline
        from pipeline.context import WorkspaceContext
        ctx = WorkspaceContext.default()
        run_pipeline(ctx, from_stage=args.from_stage, ...)
    else:
        # Path legado (código original) — safety net
        main(args)
```

---

#### Critérios de aceite da Fase 0 completa

| Critério | Verificação |
|----------|-------------|
| CLI funciona igual | `python scripts/e_reset.py` → output idêntico ao pré-Fase-0 |
| Pipeline importável | `from pipeline import run_pipeline` funciona |
| Contexto injetável | `run_pipeline(WorkspaceContext(root=Path("/tmp/test")))` funciona |
| Config injetável | `WorkspaceContext(root=..., config_overrides={"family_members.json": {...}})` funciona |
| Regressão zero | Golden files do E2→E6 match byte-a-byte |
| Testes passam | `pytest tests/` verde |
| Scripts inalterados | Lógica interna dos scripts E2-E7 não muda (apenas wrappers adicionados) |

#### O que a Fase 0 NÃO faz (fica para fases posteriores)

| Escopo excluído | Por quê | Fase destino |
|----------------|---------|-------------|
| Pydantic models dos artefatos | Útil mas não bloqueante. Scripts leem/escrevem dicts. | Fase 1-2 |
| Abstrair storage (S3/MinIO) | Filesystem funciona até ter web | Fase 2 |
| Substituir print por logging | Funciona sem isso para CLI | Fase 5 (WebSocket) |
| Refatorar lógica interna dos scripts | Risco alto, valor baixo nesta fase | Futuro (gradual) |
| Migrar E2 registry para auto-discovery | O sistema de BANK_MODULES funciona bem | Futuro |

---

### FASE 1 — Backend FastAPI + Auth + DB

**Objetivo:** API server rodando com autenticação, servindo relatórios existentes.

**Duração estimada:** 2-3 semanas

#### Tarefas

| # | Tarefa | Prioridade | Complexidade | Status |
|---|--------|-----------|-------------|--------|
| 1.1 | Setup FastAPI project (`backend/app/`) | P0 | Baixa | ☐ |
| 1.2 | Setup SQLAlchemy 2.0 + Alembic | P0 | Média | ☐ |
| 1.3 | Modelo `User` + migration | P0 | Baixa | ☐ |
| 1.4 | Auth: register, login, JWT tokens | P0 | Média | ☐ |
| 1.5 | Middleware de autenticação (dependency injection) | P0 | Baixa | ☐ |
| 1.6 | Modelo `Workspace` + migration | P0 | Baixa | ☐ |
| 1.7 | Modelo `Report` + migration | P0 | Baixa | ☐ |
| 1.8 | Endpoint `GET /api/reports` (lista relatórios) | P0 | Baixa | ☐ |
| 1.9 | Endpoint `GET /api/reports/{id}/html` (serve HTML) | P0 | Baixa | ☐ |
| 1.10 | Seed: importar relatório existente para o banco | P1 | Baixa | ☐ |
| 1.11 | CORS configurado para frontend Next.js | P0 | Baixa | ☐ |
| 1.12 | Script de setup dev (`docker-compose.dev.yml` com PostgreSQL) | P1 | Média | ☐ |
| 1.13 | Testes dos endpoints de auth | P1 | Média | ☐ |
| 1.14 | Setup Next.js project (`frontend/`) | P0 | Baixa | ☐ |
| 1.15 | Página de login/registro (Next.js) | P0 | Média | ☐ |
| 1.16 | Página de lista de relatórios | P1 | Média | ☐ |
| 1.17 | Visualização de relatório HTML em iframe/embed | P1 | Baixa | ☐ |
| 1.18 | Auto-geração de types TS via `openapi-typescript` | P1 | Média | ☐ |

#### Critério de aceite

- `POST /api/auth/register` + `POST /api/auth/login` funcionam
- Usuário autenticado vê lista de relatórios via browser
- Relatório HTML é exibido corretamente na UI
- Pipeline CLI continua funcionando independentemente

#### Dependências externas

```
# Backend
fastapi>=0.115
uvicorn>=0.30
sqlalchemy>=2.0
alembic>=1.13
python-jose>=3.3
passlib[bcrypt]>=1.7
python-multipart>=0.0.7
psycopg2-binary>=2.9

# Frontend
next@15
react@19
typescript@5
@shadcn/ui
tailwindcss@4
openapi-typescript
```

---

### FASE 2 — Upload de Arquivos + Pipeline Trigger

**Objetivo:** Usuário faz upload via browser e dispara pipeline (ainda síncrono).

**Duração estimada:** 2-3 semanas

#### Tarefas

| # | Tarefa | Prioridade | Complexidade | Status |
|---|--------|-----------|-------------|--------|
| 2.1 | Modelo `Document` + migration | P0 | Baixa | ☐ |
| 2.2 | File storage organizado por tenant (`storage/{workspace_id}/`) | P0 | Média | ☐ |
| 2.3 | Endpoint `POST /api/documents/upload` (multipart, batch) | P0 | Média | ☐ |
| 2.4 | Endpoint `GET /api/documents` (lista por workspace) | P0 | Baixa | ☐ |
| 2.5 | Endpoint `DELETE /api/documents/{id}` | P1 | Baixa | ☐ |
| 2.6 | Adaptar E0-route para processar a partir do storage do tenant | P0 | Alta | ☐ |
| 2.7 | Modelo `PipelineRun` + `PipelineStageLog` + migration | P0 | Média | ☐ |
| 2.8 | Endpoint `POST /api/pipeline/run` (trigger síncrono) | P0 | Alta | ☐ |
| 2.9 | Endpoint `GET /api/pipeline/runs/{id}` (status) | P0 | Baixa | ☐ |
| 2.10 | Adaptar orchestrator para trabalhar com paths do tenant | P0 | Alta | ☐ |
| 2.11 | UI: página de upload com drag-and-drop | P0 | Média | ☐ |
| 2.12 | UI: lista de documentos com status | P0 | Média | ☐ |
| 2.13 | UI: botão "Gerar Relatório" + feedback | P0 | Média | ☐ |
| 2.14 | Validação de tipos de arquivo no upload (PDF, XLSX, CSV, JPG) | P1 | Baixa | ☐ |
| 2.15 | Limite de tamanho de upload (50MB por arquivo) | P1 | Baixa | ☐ |
| 2.16 | Testes de integração: upload → pipeline → relatório | P0 | Alta | ☐ |

#### Critério de aceite

- Upload via browser substitui completamente o fluxo `inbox/`
- Pipeline roda via API e gera relatório acessível na UI
- Dados isolados por workspace (multi-tenant no filesystem)

---

### FASE 3 — Configuração via UI

**Objetivo:** O que hoje está em `config/*.json` vira configurável por usuário via interface.

**Duração estimada:** 3-4 semanas

#### Tarefas

| # | Tarefa | Prioridade | Complexidade | Status |
|---|--------|-----------|-------------|--------|
| 3.1 | Modelos `FamilyMember`, `BankAccount` + migrations | P0 | Média | ☐ |
| 3.2 | Modelos `Category`, `CategoryKeyword` + migrations | P0 | Média | ☐ |
| 3.3 | Modelo `Institution` + migration | P1 | Baixa | ☐ |
| 3.4 | Modelo `PipelineConfig` (tolerâncias, thresholds) + migration | P1 | Média | ☐ |
| 3.5 | Modelo `ReportLayout` (seções, ordem, visibilidade) + migration | P2 | Média | ☐ |
| 3.6 | CRUD API: `/api/config/members` | P0 | Média | ☐ |
| 3.7 | CRUD API: `/api/config/accounts` | P0 | Média | ☐ |
| 3.8 | CRUD API: `/api/config/categories` | P0 | Média | ☐ |
| 3.9 | CRUD API: `/api/config/institutions` | P1 | Baixa | ☐ |
| 3.10 | CRUD API: `/api/config/pipeline` | P1 | Baixa | ☐ |
| 3.11 | CRUD API: `/api/config/report-layout` | P2 | Média | ☐ |
| 3.12 | Serializar config do banco → `PipelineConfig` Pydantic para pipeline | P0 | Alta | ☐ |
| 3.13 | Adaptar pipeline para receber config como parâmetro (não ler disco) | P0 | Alta | ☐ |
| 3.14 | Default values = valores atuais do `config/*.json` | P0 | Média | ☐ |
| 3.15 | UI: tela de membros da família | P0 | Média | ☐ |
| 3.16 | UI: tela de contas bancárias (vinculadas a membros) | P0 | Média | ☐ |
| 3.17 | UI: tela de categorias (keywords, tetos, drag-and-drop reorder) | P0 | Alta | ☐ |
| 3.18 | UI: tela de parâmetros do pipeline | P1 | Média | ☐ |
| 3.19 | UI: tela de layout do relatório (toggle seções, reordenar) | P2 | Alta | ☐ |
| 3.20 | Seed de defaults na criação de novo workspace | P0 | Média | ☐ |
| 3.21 | Testes: config via UI gera mesmo relatório que config em arquivo | P0 | Alta | ☐ |

#### Critério de aceite

- Todas as configurações que hoje estão em JSON podem ser editadas via UI
- Pipeline usa config do banco quando disponível, fallback para defaults
- Relatório gerado via config-UI é idêntico ao gerado via config-arquivo

---

### FASE 4 — Automação LLM (Premium)

**Objetivo:** Etapas E1, E1.5, E2-llm e E7-review rodam automaticamente via API.

**Duração estimada:** 3-4 semanas

#### Tarefas

| # | Tarefa | Prioridade | Complexidade | Status |
|---|--------|-----------|-------------|--------|
| 4.1 | Modelo `LLMConfig` (api_key encrypted, model, limits) + migration | P0 | Média | ☐ |
| 4.2 | UI: tela para configurar API key (com teste de conectividade) | P0 | Média | ☐ |
| 4.3 | Módulo `pipeline/llm/service.py` — wrapper para Anthropic API | P0 | Alta | ☐ |
| 4.4 | `pipeline/llm/prompts/` — templates versionados por etapa | P0 | Alta | ☐ |
| 4.5 | Implementar E1 via API: extração de dados pessoais | P0 | Alta | ☐ |
| 4.6 | Implementar E1.5 via API: consolidação baseline patrimonial | P0 | Alta | ☐ |
| 4.7 | Implementar E2-llm via API: extração sem parser determinístico | P0 | Alta | ☐ |
| 4.8 | Implementar E7-review via API: review holístico com persona | P1 | Alta | ☐ |
| 4.9 | `pipeline/llm/validators/` — validação de output LLM contra schemas | P0 | Alta | ☐ |
| 4.10 | Retry com exponential backoff para LLM calls | P0 | Média | ☐ |
| 4.11 | Fallback para revisão manual se confidence < threshold | P1 | Média | ☐ |
| 4.12 | Orchestrator: detectar tier → skip LLM no free, executar no premium | P0 | Média | ☐ |
| 4.13 | Token usage tracking por run (para billing futuro) | P2 | Média | ☐ |
| 4.14 | UI: indicador de quais etapas são premium (lock icon) | P1 | Baixa | ☐ |
| 4.15 | Testes: comparar output LLM automático vs manual anterior | P0 | Alta | ☐ |

#### Critério de aceite

- Pipeline premium roda end-to-end sem intervenção humana
- Pipeline free roda determinístico, marcando etapas LLM como "skipped"
- Output LLM é validado contra schemas antes de prosseguir
- API key é armazenada com criptografia at-rest

---

### FASE 5 — Task Queue + Real-time Progress

**Objetivo:** Pipeline roda em background com status em tempo real.

**Duração estimada:** 2-3 semanas

#### Tarefas

| # | Tarefa | Prioridade | Complexidade | Status |
|---|--------|-----------|-------------|--------|
| 5.1 | Setup Celery + Redis (ou ARQ) | P0 | Média | ☐ |
| 5.2 | Mover pipeline execution para task assíncrona | P0 | Alta | ☐ |
| 5.3 | `POST /api/pipeline/run` retorna imediatamente com `run_id` | P0 | Média | ☐ |
| 5.4 | Task atualiza `PipelineStageLog` a cada etapa | P0 | Média | ☐ |
| 5.5 | WebSocket endpoint para push de progresso | P0 | Alta | ☐ |
| 5.6 | UI: barra de progresso com etapas (E0→E6) | P0 | Alta | ☐ |
| 5.7 | UI: notificação quando relatório está pronto | P1 | Média | ☐ |
| 5.8 | Cancelamento de pipeline em execução | P2 | Média | ☐ |
| 5.9 | Retry automático de etapa falhada | P2 | Média | ☐ |
| 5.10 | Limite de concorrência (1 run por workspace) | P1 | Baixa | ☐ |
| 5.11 | Docker Compose com Redis | P0 | Baixa | ☐ |
| 5.12 | Testes de integração assíncronos | P1 | Alta | ☐ |

#### Critério de aceite

- Pipeline roda em background sem bloquear a UI
- Progresso atualiza em tempo real via WebSocket
- Usuário pode navegar pela UI enquanto pipeline processa

---

### FASE 6 — Frontend Completo + Polish

**Objetivo:** Produto com cara profissional, pronto para mostrar.

**Duração estimada:** 4-6 semanas

#### Tarefas

| # | Tarefa | Prioridade | Complexidade | Status |
|---|--------|-----------|-------------|--------|
| 6.1 | Dashboard com KPIs (score, patrimônio, taxa poupança) | P0 | Alta | ☐ |
| 6.2 | Relatório renderizado in-app (não só iframe/download) | P0 | Alta | ☐ |
| 6.3 | Histórico de relatórios com comparação entre períodos | P1 | Alta | ☐ |
| 6.4 | Onboarding wizard (3 passos: dados → upload → gerar) | P0 | Alta | ☐ |
| 6.5 | Landing page com proposta de valor | P1 | Alta | ☐ |
| 6.6 | Dark mode nativo (toda a UI) | P1 | Média | ☐ |
| 6.7 | Design responsivo (mobile-first) | P1 | Alta | ☐ |
| 6.8 | Export PDF do relatório | P2 | Média | ☐ |
| 6.9 | Tela de billing/planos (free vs premium) | P2 | Média | ☐ |
| 6.10 | Documentação/FAQ | P2 | Média | ☐ |
| 6.11 | Loading states e error handling polished | P0 | Média | ☐ |
| 6.12 | Animações sutis (gráficos, transições) | P2 | Baixa | ☐ |
| 6.13 | SEO da landing page | P2 | Média | ☐ |
| 6.14 | Accessibility (WCAG 2.1 AA) | P2 | Média | ☐ |

#### Critério de aceite

- Produto visualmente profissional
- Fluxo completo: landing → registro → onboarding → upload → relatório → dashboard
- Funciona bem em desktop e mobile

---

### FASE 7 — Infraestrutura de Produção + LGPD

**Objetivo:** Deploy real, seguro, compliance.

**Duração estimada:** 2-3 semanas

#### Tarefas

| # | Tarefa | Prioridade | Complexidade | Status |
|---|--------|-----------|-------------|--------|
| 7.1 | Dockerfile backend (FastAPI + Celery) | P0 | Média | ☐ |
| 7.2 | Dockerfile frontend (Next.js) | P0 | Baixa | ☐ |
| 7.3 | `docker-compose.prod.yml` (API + DB + Redis + Frontend) | P0 | Média | ☐ |
| 7.4 | Deploy em cloud (Railway, Fly.io, ou AWS) | P0 | Alta | ☐ |
| 7.5 | HTTPS + domínio próprio | P0 | Baixa | ☐ |
| 7.6 | Criptografia de CPFs e dados sensíveis at-rest (Fernet/AES) | P0 | Alta | ☐ |
| 7.7 | Rate limiting | P0 | Baixa | ☐ |
| 7.8 | Backup automático diário do banco | P0 | Média | ☐ |
| 7.9 | Sentry para error tracking | P1 | Baixa | ☐ |
| 7.10 | Uptime monitoring | P1 | Baixa | ☐ |
| 7.11 | Termos de uso + política de privacidade | P0 | Média | ☐ |
| 7.12 | Endpoint `DELETE /api/account` (direito ao esquecimento) | P0 | Média | ☐ |
| 7.13 | Endpoint `GET /api/account/export` (portabilidade LGPD) | P1 | Média | ☐ |
| 7.14 | Log de auditoria (quem acessou o quê) | P2 | Média | ☐ |
| 7.15 | CI/CD pipeline (GitHub Actions) | P1 | Média | ☐ |

#### Critério de aceite

- Produto acessível via URL pública com HTTPS
- Dados sensíveis criptografados at-rest
- Backup diário funcionando
- Termos de uso aceitos no registro

---

## 6. Backlog Priorizado

### Legenda de prioridades

- **P0** — Bloqueante. Sem isso a fase não entrega valor.
- **P1** — Importante. Sem isso funciona, mas falta qualidade/completude.
- **P2** — Nice-to-have. Pode postergar para a próxima fase ou sprint.

### Backlog completo (todas as fases)

Total de tarefas: **122**

| Fase | Sub-fases | P0 | P1 | P2 | Total |
|------|-----------|----|----|----|----|
| 0 — Core | 0A, 0B, 0C, 0D | 16 | 10 | 1 | 27 |
| 1 — API + Auth | — | 11 | 5 | 0 | 16 |
| 2 — Upload | — | 10 | 3 | 0 | 13 |
| 3 — Config UI | — | 10 | 5 | 3 | 18 |
| 4 — LLM | — | 9 | 3 | 2 | 14 |
| 5 — Task Queue | — | 5 | 3 | 3 | 11 |
| 6 — Frontend | — | 4 | 4 | 6 | 14 |
| 7 — Produção | — | 7 | 4 | 1 | 12 |

---

## 7. Sprints

### Planejamento por sprint (2 semanas cada)

> Sprints são estimativas. Ajustar conforme velocidade real.

#### Sprint 1-2: Fase 0 — Foundation

**Objetivo:** Pipeline como package Python importável com contexto injetável.

| Sprint | Foco | Sub-fase | Tarefas |
|--------|------|----------|---------|
| S1 (sem 1) | Foundation layer + wrap módulos menores | 0A + 0B | 0A.1–0A.6, 0B.1–0B.7 |
| S2 (sem 2-3) | Wrap módulos grandes + orchestrator | 0C + 0D | 0C.1–0C.10, 0D.1–0D.7 |

**Checkpoint S1:** E3 e E4 chamáveis via `run_e3(ctx)` / `run_e4(ctx)`. Golden files match.
**Checkpoint S2:** Pipeline completo chamável via `pipeline.run_pipeline(ctx)`. Regressão zero.

---

#### Sprint 3-4: Fase 1 — API + Auth

| Sprint | Foco | Tarefas |
|--------|------|---------|
| S3 | Backend: FastAPI + DB + Auth + endpoints | 1.1–1.13 |
| S4 | Frontend: Next.js + login + relatórios | 1.14–1.18 |

**Checkpoint S4:** Login via browser. Relatório visível na UI.

---

#### Sprint 5-6: Fase 2 — Upload + Pipeline Web

| Sprint | Foco | Tarefas |
|--------|------|---------|
| S5 | Backend: upload, storage, pipeline trigger | 2.1–2.10 |
| S6 | Frontend: upload UI + pipeline feedback | 2.11–2.16 |

**Checkpoint S6:** Upload via browser → pipeline → relatório. CLI pode ser aposentado.

---

#### Sprint 7-8: Fase 3 — Config UI

| Sprint | Foco | Tarefas |
|--------|------|---------|
| S7 | Backend: modelos de config + CRUD APIs | 3.1–3.14 |
| S8 | Frontend: telas de configuração | 3.15–3.21 |

**Checkpoint S8:** Configuração via UI. Novo usuário consegue configurar e gerar relatório.

---

#### Sprint 9-10: Fase 4 — LLM Automation

| Sprint | Foco | Tarefas |
|--------|------|---------|
| S9 | LLM service + E1/E1.5/E2-llm | 4.1–4.7, 4.9–4.10 |
| S10 | E7-review + tier detection + UI | 4.8, 4.11–4.15 |

**Checkpoint S10:** Pipeline premium roda end-to-end sem intervenção.

---

#### Sprint 11: Fase 5 — Task Queue

| Sprint | Foco | Tarefas |
|--------|------|---------|
| S11 | Queue + async + WebSocket + progress UI | 5.1–5.12 |

**Checkpoint S11:** Pipeline roda em background com progresso real-time.

---

#### Sprint 12-14: Fase 6 — Frontend Polish

| Sprint | Foco | Tarefas |
|--------|------|---------|
| S12 | Dashboard + relatório in-app + onboarding | 6.1–6.4, 6.11 |
| S13 | Landing page + dark mode + responsive | 6.5–6.7 |
| S14 | Export PDF + billing + docs + polish | 6.8–6.14 |

**Checkpoint S14:** Produto profissional completo.

---

#### Sprint 15: Fase 7 — Produção

| Sprint | Foco | Tarefas |
|--------|------|---------|
| S15 | Docker + deploy + crypto + LGPD + CI/CD | 7.1–7.15 |

**Checkpoint S15:** Produto em produção. Acessível via URL pública.

---

## 8. Decisões Técnicas Pendentes

> Decisões que precisam ser tomadas antes ou durante a execução.

| # | Decisão | Fase | Opções | Status |
|---|---------|------|--------|--------|
| D1 | ORM vs Raw SQL | F1 | SQLAlchemy 2.0 (recomendado) / Tortoise / raw | **Decidido: SQLAlchemy 2.0** |
| D2 | File storage | F2 | Filesystem local / S3 / MinIO | Pendente |
| D3 | Auth provider | F1 | Custom JWT / Auth.js / Clerk | Pendente |
| D4 | Task queue | F5 | Celery+Redis / ARQ / Dramatiq | Pendente |
| D5 | Cloud provider | F7 | Railway / Fly.io / AWS / Vercel+Railway | Pendente |
| D6 | Monorepo vs repos separados | F0 | Monorepo (recomendado) / backend+frontend separados | Pendente |
| D13 | Wrapper pattern na Fase 0 | F0 | Monkey-patch globals / **Parâmetro `root_dir=None` no main()** / Ambos | **Decidido: Opção B** |
| D7 | Criptografia de dados sensíveis | F7 | Fernet (symmetric) / pgcrypto / app-level AES | Pendente |
| D8 | Pricing do premium | F6 | R$29/mês / R$49/mês / R$99/mês | Pendente |
| D9 | Nome do produto | F6 | Fin / FinPlan / outro | Pendente |
| D10 | Prioridade de novos bancos | F3+ | Nubank / Inter / Mercado Pago / Open Finance | Pendente |
| D11 | Relatório in-app: como renderizar | F6 | iframe / React components / server-side render | Pendente |
| D12 | Multi-language support | F6+ | pt-BR only / pt-BR + en | Pendente |

---

## 9. Métricas de Sucesso

### Por fase

| Fase | Métrica | Meta |
|------|---------|------|
| F0 | Output diff pré/pós refactoring | 0 diff |
| F1 | Login → ver relatório funciona | <3s load |
| F2 | Upload → relatório gerado | <5min end-to-end |
| F3 | Config UI → relatório correto | 100% paridade |
| F4 | Pipeline premium sem intervenção | >95% runs sem erro |
| F5 | Progresso real-time funciona | <1s latency |
| F6 | NPS de beta testers | >8/10 |
| F7 | Uptime | >99.5% |

### De produto (longo prazo)

| Métrica | Meta 3 meses | Meta 6 meses | Meta 12 meses |
|---------|-------------|-------------|---------------|
| Usuários registrados | 1 (dogfood) | 10 (beta) | 100 |
| Relatórios gerados/mês | 2 | 20 | 200 |
| Bancos suportados | 11 | 15 | 20+ |
| MRR | R$0 | R$0 | R$2.000+ |

---

## 10. Riscos e Mitigações

| # | Risco | Impacto | Probabilidade | Mitigação |
|---|-------|---------|---------------|-----------|
| R1 | Refactoring quebra pipeline | Alto | Média | Testes de regressão antes/depois (F0) |
| R2 | LLM output inconsistente | Alto | Alta | Schema validation + retry + fallback manual (F4) |
| R3 | Custo de LLM por run inviável | Médio | Baixa | BYOK + cache de prompts + modelo menor para tasks simples |
| R4 | Dados sensíveis vazam | Crítico | Baixa | Criptografia at-rest, HTTPS, audit log, LGPD compliance |
| R5 | Parsers quebram com mudança de layout do banco | Alto | Alta | Testes com golden files, alertas de parsing error, LLM fallback |
| R6 | Escopo cresce demais | Alto | Alta | Stick to P0 tasks por sprint, cortar P2 se atrasar |
| R7 | Complexidade do E5/E6 dificulta refactoring | Médio | Alta | Estratégia "Wrap Don't Rewrite": wrappers finos, lógica interna inalterada. E5 (107KB) e E6 (197KB) por último |
| R8 | Mudanças no Open Banking BR | Baixo | Média | Arquitetura de parsers já suporta novos sources |

---

## 11. Log de Progresso

> Atualizar a cada sprint ou milestone significativo.

| Data | Evento | Notas |
|------|--------|-------|
| 2026-04-13 | Brainstorm inicial | Decisões: Freemium, Next.js, FastAPI, Hybrid LLM |
| 2026-04-13 | Documento de plano criado | `docs/PRODUCT_PLAN.md` — este arquivo |
| 2026-04-13 | Fase 0 refinada | Diagnóstico técnico detalhado. Estratégia "Wrap Don't Rewrite". 4 sub-fases (0A-0D), 27 tarefas |
| 2026-04-13 | D13 decidido: Opção B | Parâmetro `root_dir` + `_init_config()` pattern. Refinado com análise de module-level globals por script |
| | | |
| | | |

---

## Apêndice A: Tiers Freemium

### Free — "Consolidação Determinística"

| Funcionalidade | Etapa |
|----------------|-------|
| Upload de documentos | Web UI |
| Desbloqueio de PDFs | E0-unlock |
| Auditoria de integridade | E0-audit |
| Roteamento automático (determinístico) | E0-route |
| Extração de extratos e faturas (11 bancos) | E2 |
| Reconciliação e deduplicação | E3 |
| Categorização automática (300+ keywords) | E4 |
| Análise financeira (patrimônio, score, fluxo) | E5 |
| Narrativas determinísticas | E5.N |
| Relatório HTML completo | E6 |
| Cross-validation (14 checks) | E7-crossval |

**Limitações:** 1 relatório/mês. Sem LLM. Sem histórico.

### Premium — "Inteligência Financeira Completa"

Tudo do free, mais:

| Funcionalidade | Etapa |
|----------------|-------|
| Extração LLM de dados pessoais | E1, E1.5 |
| Extração LLM de investimentos/IRPF | E2-llm |
| Review holístico com persona | E7-review |
| Refinamentos automáticos | E7-apply |
| Relatórios ilimitados | — |
| Histórico + comparação temporal | — |
| Export PDF | — |

**LLM:** BYOK (chave própria) ou incluso na assinatura.

---

## Apêndice B: Custo Estimado de Infraestrutura

### Dev (local)

- SQLite + filesystem: R$0
- Docker Desktop: R$0

### Staging / MVP

| Serviço | Estimativa | Provider |
|---------|-----------|----------|
| PostgreSQL | $0–7/mês | Railway / Neon free tier |
| Backend (FastAPI) | $5–10/mês | Railway / Fly.io |
| Frontend (Next.js) | $0/mês | Vercel free tier |
| Redis | $0–5/mês | Upstash free tier |
| Storage (uploads) | $1–5/mês | S3 / R2 |
| **Total MVP** | **~$10–25/mês** | |

### Produção (100 usuários)

| Serviço | Estimativa | Provider |
|---------|-----------|----------|
| PostgreSQL | $15–30/mês | Railway / RDS |
| Backend | $20–40/mês | Railway / Fly.io |
| Frontend | $0–20/mês | Vercel |
| Redis | $5–10/mês | Upstash / ElastiCache |
| Storage | $5–20/mês | S3 |
| Domínio + SSL | $10/mês | Cloudflare |
| Sentry | $0–26/mês | Free tier |
| **Total Produção** | **~$55–160/mês** | |

---

*Fim do documento. Atualizar conforme o projeto evolui.*
