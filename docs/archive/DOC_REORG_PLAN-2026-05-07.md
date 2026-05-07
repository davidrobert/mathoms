---
id: PLAN-doc-reorg
type: plan
title: Reorganização da documentação operacional como vault Obsidian-friendly
status: in_progress
created_at: 2026-05-07
last_review: 2026-05-07
sprint_origem: A11
sprint_atual: A11
sprints_envolvidas: [A11]
paused_at: null
pause_reason: null
adrs_canonical: ["[[ADR-182]]"]
tags:
  - type/plan
  - status/in-progress
---

# Plano executivo — Reorganização da documentação operacional como vault Obsidian-friendly

> **Status:** Proposto · **ADR canônica:** [ADR-182](DECISIONS.md#adr-182--vault-de-documentação-operacional-obsidian-friendly-em-docs) · **Owner:** senior-cto + data-engineer
>
> **Origem:** brainstorm em [`_scratch/doc-reorg-brainstorm-cto.md`](../_scratch/doc-reorg-brainstorm-cto.md) (lente estrutural) e brainstorm data-engineer (lente de consumo por LLM, retornado inline na sessão de 2026-05-07).
>
> **Audiência primária:** LLMs operando o repositório (busca, atualização, inclusão cirúrgica). **Audiência secundária:** humanos navegando no Obsidian (graph view, backlinks, tags).

---

## 1. Resumo

Migrar `~24k linhas distribuídas em 70+ arquivos` para vault Obsidian-friendly em `docs/`, com notas atômicas + frontmatter YAML + índices materializados (gerados + editoriais). Preservar `CLAUDE.md` na raiz fora da vault. Migração em 5 fases sequenciais (~26-28h em ~3 dias calendário).

### Direcionais (ordem de prioridade)

1. **Diminuição do uso de tokens por LLM** em queries de leitura/atualização típicas — meta ≥90% em queries comuns.
2. **Aumento de velocidade de execução por LLM** — leitura cirúrgica (1-3k tokens) em vez de varredura (50-130k tokens).
3. **Enabler para humanos navegarem documentação** — vault abre no Obsidian out-of-the-box (graph view, backlinks, tags, busca sem plugin obrigatório; Dataview opcional).

### Ganho de tokens estimado por operação típica

| Operação | Hoje | Pós-reorg | Ganho |
|---|---|---|---|
| Adicionar lane no BACKLOG | ~50k | ~3k | **~94%** |
| Atualizar status de lane | ~80k | ~1k | **~99%** |
| Adicionar entrada changelog | ~130k | ~1k | **~99%** |
| Atualizar entrada changelog | ~130k | ~0.5k | **~99.6%** |
| Descobrir lanes prontas | ~56k | ~1k | **~98%** |
| Listar planos não finalizados | ~5k + drift | ~1k + drift zero | **~80% + correctness** |

Token-cost-benchmark é entregável da Fase 1 (`tests/benchmarks/doc_token_cost.json` com baseline + meta) e gate de promoção `Proposto` → `Decidido`.

---

## 2. Topologia alvo

```
docs/                                      # vault-root, raiz preservada
├── _MOC/                                   # Maps of Content
│   ├── 00-INDEX.md                         # editorial — entrypoint humano + agente
│   ├── SPRINTS-active.md                   # editorial — overview narrativo da sprint corrente + curating de prioridade
│   ├── PLANS-active.md                     # editorial — declaração explícita de paused/in_progress
│   └── _generated/                         # auto, snapshot test bloqueia drift
│       ├── INDEX.md                        # 1 linha por nota (id | type | status | sprint | título | path)
│       ├── ADR_INDEX.md                    # ADRs agrupadas por categoria + status
│       ├── SPRINT_CURRENT.md               # lanes da sprint ativa (status, priority, branch slug, dependências)
│       ├── CHANGELOG_RECENT.md             # últimos 14 dias agregados por dia
│       ├── ROADMAP.md                      # tabela F0-F11 (substitui ROADMAP.md raiz; gerado de reference/PHASES.md)
│       └── PLAN_PROGRESS.md                # plano X: N/M lanes done · K in_progress · L open
│
├── _schemas/                               # JSON Schemas para frontmatter
│   ├── note-adr.schema.json
│   ├── note-lane.schema.json
│   ├── note-plan.schema.json
│   ├── note-changelog-entry.schema.json
│   ├── note-track.schema.json
│   └── note-domain-rule.schema.json
│
├── adr/                                    # 175 ADRs atomizadas
│   ├── 001-sqlalchemy-orm.md
│   ├── 002-filesystem-storage.md
│   └── ...
│
├── sprint/
│   ├── A6/                                 # sprint encerrada
│   │   ├── _README.md                      # overview, status: done, gate de fechamento
│   │   ├── lanes.md                        # tabela histórica (estática)
│   │   ├── waves.md                        # diagrama de ondas (estático)
│   │   ├── changelog.md                    # cortado do CHANGELOG.md original
│   │   ├── lanes/                          # 1 arquivo por lane
│   │   │   ├── A6.1-onda-1.md
│   │   │   └── ...
│   │   └── tracks/                         # prompts consumidos
│   │       └── ...
│   ├── A7/
│   ├── A10/                                # sprint atual
│   └── _backlog-future.md                  # F11/F12/ideias não-sprintadas
│
├── plan/                                   # 1 folder por plano multi-fase
│   ├── REPORT_PREMIUM/
│   │   ├── _README.md                      # status editorial, owner, sprints envolvidas
│   │   ├── v1.md                           # plano v1 (encerrado)
│   │   ├── v2.md                           # plano v2 (em ondas)
│   │   └── tracks/                         # tracks ligados ao plano (não à sprint)
│   ├── PLATFORM_REVIEW/
│   ├── DOC_REORG/                          # ESTE plano vira folder pós-aprovação
│   │   └── _README.md
│   └── ...
│
├── reference/                              # docs estáveis, baixa cadência de update
│   ├── PRODUCT.md                          # (movido de docs/PRODUCT.md)
│   ├── PHASES.md                           # tabela F0-F11 (extraída de ROADMAP.md)
│   ├── ARCHITECTURE.md                     # (mantido)
│   ├── TESTING.md
│   ├── RUNBOOK.md
│   ├── SETUP.md
│   ├── DB_SCHEMA_REFERENCE.md
│   ├── PIPELINE_ARTIFACTS.md
│   ├── CANONICAL_ENGINE_P0.md
│   ├── tenancy.md
│   └── SLO.md
│
├── archive/                                # mantido (planos arquivados, manual histórico)
│
├── DECISIONS.md                            # SHIM ~50 linhas → adr/ + _MOC/_generated/ADR_INDEX.md
├── BACKLOG.md                              # SHIM ~30 linhas → _MOC/SPRINTS-active.md
├── CHANGELOG.md                            # SHIM ~80 linhas → cronologia top-level + sprint/<X>/changelog.md
├── ROADMAP.md                              # DELETADO (cabeçalho deadcode)
├── PRODUCT.md                              # MOVIDO para reference/PRODUCT.md (path raiz vira shim 5 linhas)
└── DOC_REORG_PLAN.md                       # ESTE arquivo — após Fase 1 vira plan/DOC_REORG/_README.md

CLAUDE.md                                   # PERMANECE NA RAIZ, fora da vault
README.md                                   # PERMANECE NA RAIZ, ajustado (remove status duplicado)
```

---

## 3. Schemas de frontmatter

### 3.1 ADR (`docs/adr/NNN-slug.md`)

```yaml
---
id: ADR-090                              # regex: ^ADR-\d{3}(-[A-Z]+)?$
type: adr                                 # const
title: Decimal para valores monetários
status: Decidido                          # enum: Decidido | Proposto | Roadmap
phase: A5b                                # opcional, livre
date: 2026-04-19                          # ISO date
domain: [pipeline, backend, money]        # tags livres
supersedes: []                            # lista de wikilinks ADR-XXX
superseded_by: []
relates_to: [[[ADR-097]], [[ADR-111]]]   # FKs simbólicas via wikilinks
aliases: ["ADR 090", "Decimal money"]    # aliases Obsidian
tags:
  - type/adr
  - area/money
  - area/pipeline
  - status/decidido
size_lines: 62                            # gerado; gate alerta >150
---
```

### 3.2 Lane (`docs/sprint/<sprint>/lanes/<id>.md`)

```yaml
---
id: A10.2                                 # regex: ^[A-Z]\d+(\.\d+[a-z]?)*$
type: lane
title: Rules-as-code consolidation goals.json
sprint: A10                               # FK ← uma sprint apenas
plan: PLAN-goals-cutover                  # FK opcional ← um plano apenas (pode ser null)
status: shipped                           # enum: planned | open | in_progress | blocked | shipped | cancelled
priority: P1                              # enum: P0 | P1 | P2
branch_slug: a10-2-rules-as-code
ship_date: 2026-05-07
ship_pr: 107
adrs: [[[ADR-177]]]
prompt: [[track-a10-2-rules-as-code]]    # opcional, FK para sprint/<X>/tracks/
depends_on: [[[A10.0]]]
parallel_with: [[[A10.1]]]
tags:
  - type/lane
  - sprint/a10
  - status/shipped
  - priority/p1
---
```

### 3.3 Plan (`docs/plan/<SLUG>/_README.md`)

```yaml
---
id: PLAN-doc-reorg                        # regex: ^PLAN-[a-z0-9-]+$
type: plan
title: Reorganização da documentação operacional
status: in_progress                       # enum: draft | in_progress | paused | done | cancelled
sprint_origem: A11                        # opcional
sprint_atual: A11                         # editorial — atualizado quando sprint mover
sprints_envolvidas: [A11, A12]            # auto-derivado das lanes; gate avisa se diverge
created_at: 2026-05-07
last_review: 2026-05-07                   # editorial — última revisão de status
paused_at: null
pause_reason: null
adrs_canonical: [[[ADR-182]]]
tags:
  - type/plan
  - status/in-progress
---
```

### 3.4 Changelog entry (`docs/sprint/<X>/changelog/YYYY-MM-DD-<scope>.md`)

```yaml
---
id: CHG-2026-05-07-A10-2                  # regex: ^CHG-\d{4}-\d{2}-\d{2}-[A-Z0-9-]+$
type: changelog-entry
date: 2026-05-07
sprint: A10
lane: [[A10.2]]
adrs: [[[ADR-177]]]
prs: [107]
commits: [1125ba5]
breaking: false
files_touched: 8
summary: |
  Rules-as-code consolidation goals.json (ADR-177).
  5 chaves U/M/O migradas para constantes em
  pipeline/domain/services/methodology_constants.py.
tags:
  - type/changelog-entry
  - area/pipeline
  - sprint/a10
---
```

### 3.5 Track (`docs/sprint/<X>/tracks/<slug>.md` ou `docs/plan/<X>/tracks/<slug>.md`)

```yaml
---
id: TRACK-a10-2-rules-as-code             # regex: ^TRACK-[a-z0-9-]+$
type: track
title: A10.2 — Rules-as-code consolidation
lane: [[A10.2]]
sprint: A10
plan: PLAN-goals-cutover
status: consumed                          # enum: ready | consumed | cancelled
created_at: 2026-05-06
consumed_at: 2026-05-07
agent_role: senior-cto
tags:
  - type/track
  - sprint/a10
  - status/consumed
---
```

### 3.6 Domain rule (`docs/reference/rules/<slug>.md`) — opcional, fase contínua

```yaml
---
id: RULE-trs-efetiva
type: domain-rule
concept: TRS efetiva
methodology: [perini, auvp]
canonical_adr: [[ADR-164]]
enforcer_modules:
  - pipeline/domain/services/passive_income_calculator.py
  - pipeline/domain/services/ratios_calculator.py
formula_ref: FORMULAS.md#trs-efetiva
tags:
  - type/domain-rule
  - methodology/perini
  - methodology/auvp
---
```

---

## 4. Convenções

### 4.1 IDs estáveis

| Tipo | Convenção | Regex | Filename |
|---|---|---|---|
| ADR | `ADR-NNN` | `^ADR-\d{3}(-[A-Z]+)?$` | `adr/NNN-slug.md` |
| Lane | `<sprint>.<num>[<letra>]` | `^[A-Z]\d+(\.\d+[a-z]?)*$` | `sprint/<X>/lanes/<id>.md` |
| Plan | `PLAN-<slug>` | `^PLAN-[a-z0-9-]+$` | `plan/<SLUG>/_README.md` |
| Changelog entry | `CHG-YYYY-MM-DD-<scope>` | `^CHG-\d{4}-\d{2}-\d{2}-[A-Z0-9-]+$` | `sprint/<X>/changelog/<id>.md` |
| Track | `TRACK-<slug>` | `^TRACK-[a-z0-9-]+$` | `sprint/<X>/tracks/<slug>.md` ou `plan/<SLUG>/tracks/<slug>.md` |
| Domain rule | `RULE-<slug>` | `^RULE-[a-z0-9-]+$` | `reference/rules/<slug>.md` |

**Filename = ID (com `lowercase` para `<slug>` e `<scope>`).** Renomear arquivo = renomear ID, gate alerta se `id` no frontmatter diverge do filename.

### 4.2 Tags hierárquicas

```
type/        adr | lane | plan | changelog-entry | track | domain-rule | runbook
area/        auth | pipeline | persistence | frontend | mlops | observability | security | money | report | docs
sprint/      a6 | a7 | a8 | a9 | a10 | a11 | f7 | f9 | direcao-e | report-premium-v2
status/      decidido | proposto | roadmap | open | in-progress | blocked | shipped | done | cancelled | paused
priority/    p0 | p1 | p2
methodology/ perini | cerbasi | auvp
phase/       wave-0 | wave-1 | onda-a | ...
breaking/    yes | no
```

Filtragem: `tag:#area/auth AND tag:#status/decidido` no Obsidian (out-of-the-box, sem plugin).

### 4.3 Links

- **Wikilinks `[[X]]`** dentro da vault (`docs/**`) — ativa graph view + backlinks.
- **Markdown links** em `CLAUDE.md`, `README.md`, PR descriptions, comentários de código (consumo externo).
- **Aliases** populados no frontmatter para autocomplete Obsidian (`aliases: ["ADR 090", "Decimal money"]`).

### 4.4 Princípio de single-source

| Fato | Fonte única | Derivações geradas |
|---|---|---|
| Status de sprint corrente | `docs/sprint/<current>/_README.md` `status:` | `_MOC/_generated/ROADMAP.md`, `_MOC/_generated/SPRINT_CURRENT.md` |
| Status de lane | `docs/sprint/<X>/lanes/<id>.md` `status:` | `_MOC/_generated/SPRINT_CURRENT.md`, `_MOC/_generated/PLAN_PROGRESS.md` |
| Status de plano | `docs/plan/<SLUG>/_README.md` `status:` (editorial) | `_MOC/_generated/PLAN_PROGRESS.md` (cruzando lanes) |
| Decisões arquiteturais | `docs/adr/NNN-*.md` `status:` | `_MOC/_generated/ADR_INDEX.md` |
| Changelog | `docs/sprint/<X>/changelog/<id>.md` (1 entrada por PR) | `_MOC/_generated/CHANGELOG_RECENT.md` (14 dias) |

Drift impossível dentro da vault: snapshot test bloqueia inconsistência entre fonte e gerado.

---

## 5. Gates novos

| Gate | Etapa | Substitui/estende | Função |
|---|---|---|---|
| `dev/build_doc_index.py` | pre-commit + CI | estende `dev/build_adr_toc.py` | Regenera os 6 arquivos em `_MOC/_generated/`. Modo `--check` falha se `git diff` em `_MOC/_generated/` |
| `dev/validate_frontmatter.py` | pre-commit + CI | estende `dev/validate_adr_format.py` | Carrega schema por `type` da nota e valida via `jsonschema` (já dependência) |
| `dev/check_doc_links.py` | pre-commit + CI | novo | Wikilinks `[[X]]` resolvem para arquivo existente; orphan detector (notas sem nenhum backlink, exceto MOCs) |
| `dev/check_doc_supersedure.py` | pre-commit | estende `dev/validate_adr_format.py` | Bidirecionalidade ADR `supersedes` ↔ `superseded_by`; estende para outros tipos no futuro |
| `dev/check_doc_stale.py` | CI semanal (warning) | novo | Notas com `status: in_progress` há >30 dias, `proposto` há >60 dias, `paused` há >60 dias |
| `dev/check_doc_filename_id.py` | pre-commit | novo | Filename casa com `id:` no frontmatter (case-insensitive para slug) |
| `dev/benchmark_doc_token_cost.py` | CI por PR | novo | Roda 6 queries-benchmark, compara com baseline em `tests/benchmarks/doc_token_cost.json`. Falha se regressão >5% |
| `dev/check_forbidden_paths.py` | pre-commit | **estendido** | Bloqueia recriação de `docs/methodology/`, `goals.json`, etc. Permanece. |

**Snapshot test** em `tests/test_doc_indexes_snapshot.py` (mesmo padrão de `tests/test_openapi_snapshot.py`):

```python
def test_INDEX_md_matches_source():
    """build_doc_index.py é idempotente — INDEX.md regenerado bate byte-a-byte."""
    expected = (DOCS / "_MOC" / "_generated" / "INDEX.md").read_text()
    actual = build_index_inline()
    assert expected == actual, "INDEX.md fora de sync — rode dev/build_doc_index.py"
```

---

## 6. Plano em 5 fases

### Fase 1 — Foundation (1 dia · ~6h ativo)

**Escopo:**
- Criar `docs/_MOC/` com 6 arquivos placeholder (manuais iniciais).
- Criar `docs/_schemas/note-{adr,lane,plan,changelog-entry,track,domain-rule}.schema.json`.
- `dev/build_doc_index.py` v1 (gera só `INDEX.md` mínimo a partir de notas existentes).
- `dev/validate_frontmatter.py` (carrega schema por type).
- `dev/check_doc_links.py` (wikilink + orphan detector).
- `dev/check_doc_filename_id.py`.
- `dev/benchmark_doc_token_cost.py` com 6 queries-benchmark + baseline em `tests/benchmarks/doc_token_cost.json`.
- 1 ADR migrada manualmente como exemplo (ADR-090 ou similar P0): cria `docs/adr/090-decimal-money.md` com frontmatter completo, valida gates.
- Pre-commit + CI hooks ativos.

**Critério de aceite:**
- Todos os gates passam em ADR exemplo.
- `dev/build_doc_index.py --check` verde.
- `tests/test_doc_indexes_snapshot.py` verde.
- Baseline de tokens registrado.

**Gate de rollback:** `git revert` da fase. Sem efeito em arquivos legados.

**Agentes em voo:** zero impacto.

**Estimativa:** 6h.

---

### Fase 2 — Split DECISIONS.md (1 dia · ~6h ativo + 24h janela de pausa)

**Escopo:**
- `dev/split_adrs.py`: lê `docs/DECISIONS.md`, gera 175 arquivos `docs/adr/NNN-slug.md` com frontmatter populado a partir do regex existente.
- `dev/build_doc_index.py` v2: adiciona `_MOC/_generated/ADR_INDEX.md` (substitui ToC inline atual) agrupado por categoria + status.
- `docs/DECISIONS.md` vira shim ~50 linhas: aponta para `adr/` + `_MOC/_generated/ADR_INDEX.md` + preserva âncoras históricas via `<a id="adr-NNN-slug"></a>` para PRs antigos.
- `dev/check_adr_anchors.py` adapta para validar paths em `adr/`.
- `dev/build_adr_toc.py` removido (substituído).
- ADR-182 promovida de `Proposto` → `Decidido (Sprint XX.Y)` apenas no final da Fase 5.

**Critério de aceite:**
- `ls docs/adr/ | wc -l == 175`.
- Todo arquivo passa `dev/validate_frontmatter.py`.
- Diff de conteúdo: script `dev/diff_adrs.py docs/adr/ /tmp/old_DECISIONS.md` retorna byte-a-byte por ADR.
- `dev/check_doc_links.py` retorna 0 broken.
- Anchors históricos resolvem (smoke test: `gh pr view <antigo> --json body | grep "DECISIONS.md#adr-090"` continua clicável via shim).

**Gate de rollback:** `git revert` + script `dev/rebuild_decisions_md.py` reconstitui `DECISIONS.md` a partir de `adr/` byte-a-byte.

**Agentes em voo:** **janela de pausa obrigatória 24h** — anunciar em CLAUDE.md hotspot warning + Slack 24h antes. Nenhum PR pode tocar `DECISIONS.md` durante a janela.

**Estimativa:** 6h ativo + 24h janela.

---

### Fase 3 — Migrate tracks + plans (meio dia · ~4h ativo)

**Escopo:**
- `git mv docs/agent_prompts/track_a*.md docs/sprint/<X>/tracks/` por sprint.
- `dev/add_track_frontmatter.py` adiciona frontmatter (extrai lane/sprint/status do nome do arquivo + grep no BACKLOG legado).
- `docs/agent_prompts/README.md` vira shim para `_MOC/SPRINTS-active.md`.
- `docs/agent_prompts/archive/` move para `docs/sprint/<X>/tracks/archive/` ou agrega por sprint.
- `docs/<TOPIC>_PLAN.md` (7 arquivos) → `docs/plan/<SLUG>/_README.md` + `v1.md`/`v2.md` quando aplicável.
- `_MOC/PLANS-active.md` (editorial) populado.
- `_MOC/_generated/PLAN_PROGRESS.md` adicionado a `dev/build_doc_index.py` v3.

**Critério de aceite:**
- `find docs/agent_prompts -name 'track_*.md' | wc -l == 0`.
- `find docs/sprint -name 'track_*.md' | wc -l == 57+`.
- Cada track tem frontmatter válido.
- 7 plans migrados; cada `plan/<X>/_README.md` tem `status:` editorial.
- `_MOC/PLANS-active.md` lista planos `in_progress` e `paused` corretamente (humano valida).
- Snapshot test verde.

**Gate de rollback:** `git revert`.

**Agentes em voo:** **moderado**. Anunciar 12h antes. Agentes com lane aberta atualizam path do track no prompt de sessão.

**Estimativa:** 4h.

---

### Fase 4 — Split BACKLOG.md em sprint folders (1 dia · ~6h ativo + 24-48h janela)

**Escopo:**
- Por sprint A6/A7/A8/A9/A10/A11(?): criar `docs/sprint/<X>/_README.md`, `lanes.md`, `waves.md`.
- Quebrar lanes em arquivos atômicos `docs/sprint/<X>/lanes/<id>.md` com frontmatter completo (~70 lanes hoje).
- Sprint atual (A11+ ou continuação A10) ganha `lanes.md` que vira **única** fonte de pickup.
- `_MOC/SPRINTS-active.md` (editorial, ~50 linhas) overview narrativo + curating de prioridade.
- `_MOC/_generated/SPRINT_CURRENT.md` gerado de lanes da sprint atual filtradas por `status: open | in_progress`.
- `docs/BACKLOG.md` vira shim ~30 linhas.
- Atualizar `CLAUDE.md` §"Onde procurar contexto adicional": "Sprint atual + roadmap → `docs/_MOC/SPRINTS-active.md`".
- Atualizar `CLAUDE.md` §"Antes de pegar uma task" para referenciar `docs/sprint/<X>/lanes/`.

**Critério de aceite:**
- `BACKLOG.md` ≤ 50 linhas.
- Agente real consegue fazer pickup completo lendo só `_MOC/SPRINTS-active.md` + 1 track (validar com 1 sessão de teste).
- Status atual da sprint mora em **um único lugar** (`docs/sprint/<current>/_README.md`).
- `_MOC/_generated/SPRINT_CURRENT.md` reflete frontmatter byte-a-byte.
- Token-cost-benchmark Q2/Q3/Q7 atinge meta ≥90%.
- Backup completo do BACKLOG antes: `cp docs/BACKLOG.md _scratch/BACKLOG-pre-reorg.md` (commit em `_scratch/` é gitignored — backup local apenas).

**Gate de rollback:** `git revert`. Mais arriscado que Fase 2 (BACKLOG é editorial-rich); idealmente preserve `_scratch/BACKLOG-pre-reorg.md` localmente como referência.

**Agentes em voo:** **alto impacto**. Janela de pausa 24-48h. Anunciar em CLAUDE.md hotspot warning 48h antes. **Pausar pickup novo durante a fase.**

**Estimativa:** 6h ativo + 24-48h janela.

---

### Fase 5 — Split CHANGELOG + cleanup raiz (meio dia · ~4h)

**Escopo:**
- Mover seções de `docs/CHANGELOG.md` para `docs/sprint/<X>/changelog/` por entrega (1 entry por PR mergeado, granularidade por dia agregada via `_MOC/_generated/CHANGELOG_RECENT.md`).
- `docs/CHANGELOG.md` vira shim ~80 linhas: cronologia top-level apontando para `sprint/<X>/changelog/`.
- **Deletar `docs/ROADMAP.md`** (cabeçalho deadcode).
- Mover tabela "Visão geral das fases F0-F11" para `docs/reference/PHASES.md` (evergreen, sem status).
- **Mover `docs/PRODUCT.md` → `docs/reference/PRODUCT.md`**; deixar shim 5 linhas em `docs/PRODUCT.md`.
- Atualizar `README.md` linha 5: remover "Status: ... Sprint A7 entregue ... Próxima fase: F7"; substituir por `Status: Dogfood interno · Roadmap: docs/reference/PHASES.md`.
- Atualizar `CLAUDE.md` §"Onde procurar contexto adicional" completamente.
- Reduzir `CLAUDE.md` §"Hotspots de documentação" (não há mais hotspots de 6k linhas).
- ADR-182 status: `Proposto` → `Decidido (Sprint XX.5)`.
- Critério de aceite ADR-182 todos checados.
- Move `docs/DOC_REORG_PLAN.md` para `docs/plan/DOC_REORG/_README.md` ou arquivar em `docs/archive/DOC_REORG_PLAN-YYYY-MM-DD.md`.

**Critério de aceite:**
- `CHANGELOG.md` ≤ 80 linhas.
- Cada `sprint/<X>/changelog/<id>.md` é internamente coerente (mover não quebrou cross-refs).
- `ROADMAP.md` deletado; `reference/PHASES.md` criado.
- `README.md` linha 5 ajustada; smoke test: `grep "Sprint A" README.md` retorna 0 linhas.
- `CLAUDE.md` atualizado; gates verdes.
- Token-cost-benchmark final supera baseline em ≥90% nas queries comuns; deep-dive ADR-cross em ≥40%.
- Vault abre no Obsidian out-of-the-box: smoke test manual.

**Gate de rollback:** `git revert`.

**Agentes em voo:** **baixo impacto**. CHANGELOG é menos consultado durante pickup.

**Estimativa:** 4h.

---

### 6.6 Resumo das fases

| Fase | Escopo | Horas ativas | Janela de pausa | Risco |
|---|---|---|---|---|
| 1 | Foundation MOC + scripts + schemas + benchmark | 6h | nenhuma | baixo |
| 2 | Split DECISIONS.md | 6h | 24h sem PR em ADR | alto |
| 3 | Migrate tracks + plans | 4h | 12h aviso | moderado |
| 4 | Split BACKLOG.md | 6h | 24-48h sem pickup novo | alto |
| 5 | Split CHANGELOG + cleanup raiz | 4h | nenhuma | baixo |
| **Total** | — | **26h** | **~3 dias calendário** | **moderado** |

---

## 7. Após aprovação — antes da Fase 1

1. Aprovar este plano (revisão final do usuário; opcionalmente review do `product-designer` ou `product-manager` para UX da vault).
2. ADR-182 permanece `Proposto`. Promoção para `Decidido (Sprint XX.Y)` ocorre **apenas** no final da Fase 5, após critério de aceite todos checados.
3. Criar lane única `<SX>.docreorg` no BACKLOG (último uso do BACKLOG legado), referenciando este plano.
4. Anunciar janelas de pausa Fase 2 e Fase 4 com 24-48h de antecedência em CLAUDE.md `§Hotspots de documentação`.
5. Smoke test inicial: clonar repo limpo, abrir Obsidian apontando para `docs/`, validar que estado pré-Fase 1 já não quebra (Obsidian abre `*.md` mesmo sem frontmatter).

---

## 8. Lacunas e decisões adiadas

- **SQLite layer (M4 do data-engineer)** — adiada. Avaliar quando query grafo (cross-ADR, supersedure chains, agregação por método) virar dor concreta.
- **`.obsidian/` config compartilhada** — gitignored por default. Reabrir se time crescer e workspace settings consistentes virarem útil.
- **Domain rules em `docs/reference/rules/`** — migração contínua. Rules novas vão direto; rules existentes em `docs/ARCHITECTURE.md §4.1` migram quando ADR canônica for editada.
- **Categoria nova "Documentação & Vault" em `dev/build_adr_toc.py`** — bug atual: categorias criadas só via `OVERRIDES` são silenciosamente descartadas. ADR-182 fica em "Outras" temporariamente. Quando cluster sobre tema crescer (≥3 ADRs), corrigir o script (lane separada).
- **Bug check para `paused_at` sem `pause_reason`** — adicionar em fase de hardening pós-Fase 5.
- **Product-manager review da UX final da vault** — depois da Fase 1, antes da Fase 4. Lente: graph view, taxonomia de tags, onboarding de humano novo.

---

## 9. Critério de aceite global (gate ADR-182 `Proposto` → `Decidido`)

Todos os checks abaixo devem estar verdes ao final da Fase 5:

- [ ] Plano executivo aprovado pelo usuário.
- [ ] Fases 1-5 entregues com critério de aceite por fase verde.
- [ ] Snapshot test `tests/test_doc_indexes_snapshot.py` verde.
- [ ] `tests/benchmarks/doc_token_cost.json` mostra redução ≥90% em Q2/Q3/Q7.
- [ ] Vault abre no Obsidian out-of-the-box (graph + backlinks + tags + busca sem plugin obrigatório).
- [ ] CLAUDE.md §"Onde procurar contexto adicional" atualizado; §Hotspots reduzido.
- [ ] README.md, PRODUCT.md, ROADMAP.md ajustados.
- [ ] Drift zero entre status de sprint (única fonte é `docs/sprint/<current>/_README.md`).
- [ ] (Opcional) Product-manager review da UX final.

---

## 10. Ligações

- ADR canônica: [ADR-182](DECISIONS.md#adr-182--vault-de-documentação-operacional-obsidian-friendly-em-docs)
- Brainstorm estrutural: [`_scratch/doc-reorg-brainstorm-cto.md`](../_scratch/doc-reorg-brainstorm-cto.md) (gitignored, referência)
- Brainstorm dados/LLM: retornado inline pelo data-engineer em sessão de 2026-05-07 (não materializado em arquivo)
- Padrão de codegen: [ADR-076](DECISIONS.md#adr-076--design-tokens-unificados-site--relatório), [ADR-109](DECISIONS.md#adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a)
- Doutrina rules-as-code: [ADR-143](DECISIONS.md#adr-143--docsmethodology-é-rules-as-code-sprint-a76)
