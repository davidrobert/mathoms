---
id: TRACK-a6g3-backend-style-sweep
type: track
title: "Track A6g.3 — Backend Python code style sweep"
sprint: A6
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a6
  - status/consumed
---

# Track A6g.3 — Backend Python code style sweep

> **Lane ID:** A6g.3
> **Branch prefix:** `agent/a6g3-backend-style/*`
> **Depende de:** A6e.4 (routers finos, atualmente 9/14 fase 4a) — ideal **mergear completo** antes; este sweep roda em `backend/app/` **fora de** `api/*` e `application/*` (que são escopo da A6e.4 ou já limpos pela A6e.3/.3b). A6g.6 ✅ (gates ativos — Ruff, ESLint, audit regression).
> **Paralelo com:** A6e.4 (só se disciplinar escopo — **nunca tocar `backend/app/api/*.py` nem `backend/app/application/*`**). A6g.6b, A6g.2c (pequenas follow-ups), A6e.3c (tipar DTOs — toca `schemas/dto/`, potencial overlap cuidar).
> **Conflita com:** commits simultâneos em `backend/app/services/*.py`, `backend/app/repositories/*.py`, `backend/app/models/*.py`, `backend/app/schemas/*.py`, `backend/app/tasks/*.py`, `backend/app/core/*.py`. Se A6e.3c estiver ativa, coordenar por arquivo.
> **Onda:** 3
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [CLAUDE.md §Code style](../../CLAUDE.md#code-style) · [docs/archive/audits/](../audits/) · ADR-114 (enforcement)

> **Objetivo:** aplicar §Code style em `backend/app/` **fora do escopo
> de outras lanes** — services, repositories, models, schemas (não-DTO
> novo), tasks, core, middleware. Alvos principais: (a) P1 long
> functions (134 ofensores), (b) P5 float money (12), (c) P9 deep
> nesting (28), (d) P4 optional-no-default (5), (e) P8 what-comments
> (2). Deixa audit baseline (A6g.6) com drift significativamente menor
> sem tocar routers (A6e.4) nem use cases limpos (A6e.3/.3b).

---

## Por que esta lane agora

1. **3 sweeps fecharam** (A6g.2 r1, A6g.4 r1+r2+r3, A6g.5) + **enforcement ativo** (A6g.6 ✅, ADR-114) + **Go prep** (A6g.7 ✅). Backend Python é o último território não varrido do trilho A6g.
2. **Baseline decrescente em CI:** A6g.6 instalou `check_code_style_regression.py` comparando audit atual vs `dev/code_style_baseline.json`. Sweep agora **decresce** baseline; sem sweep, baseline vira gate estático.
3. **Destrava F7:** produção precisa CI sem débito visível em services/repositories. F7B.5 (audit log completo) vai **modificar** services — melhor varrer antes.
4. **Application layer (A6e.3/.3b)** é código novo e limpo — ótimo modelo a replicar em services legados que sobreviveram.

---

## Regras inegociáveis

Do CLAUDE.md §Code style + ADR-090 + ADR-114 baseline:

1. **Funções 4-20 linhas.** Audit categoria P1_long_functions (≥40 linhas = high severity). Extrai helpers privados com nome específico.
2. **Arquivos ≤500 linhas** (P2). Split por responsabilidade quando quebrar (ex.: `services/pipeline_adapter.py` → `pipeline_event_translator.py` + `pipeline_run_mapper.py`).
3. **`Dict[str, Any]` só em código interno dinâmico** (P3). Boundary (HTTP, JSON, config) usa Pydantic `BaseModel`. **Não** tocar DTOs de `application/*` (A6e.3/.3b já fez).
4. **Dinheiro nunca é `float`** (ADR-090 / P5): campos com nome `amount|valor|brl|saldo|money|total|price|cost|fee|tax` usam `Decimal` (Python) ou string decimal (JSON wire). 12 ofensores em `schemas/dto/goal/{if_goal,aporte,dolar}.py` + `schemas/dto/config_blob/response.py` + `schemas/transactions.py`. **Overlap potencial com A6e.3c** — coordenar.
5. **Optional com default explícito** (P4): `foo: str | None = None`, nunca `foo: str | None` sem default.
6. **Early returns > ifs aninhados** (P9 deep_nesting). Max 2 níveis em lógica; 3 aceitável só em parsing.
7. **Nomes específicos** (P6). A6g.6 ativou hook `check_forbidden_names.py` — qualquer arquivo novo com nome `utils.py`/`helpers.py`/`manager.py`/`handler.py`/`service.py` (sozinho) é bloqueado em pre-commit.
8. **Comentários** (P8): só **por quê**, não **o quê**. `# increment counter`, `# used by X`, `# added for Y flow` → apagar. Preservar comentários históricos/invariantes.
9. **Docstrings** (P7 — baixa severidade): uma linha de intent. Multi-parágrafo só em API pública complexa. **Não é gate bloqueante** — limpar por osmose quando tocar arquivo.
10. **Preserve comentários existentes em refactor.** Especialmente invariantes de domínio / workarounds de bug citando ADR.
11. **Dinheiro:** se encontrar `float` em DTO monetário novo (não só em legado), reporte em commit separado — pode ter entrado pós-A6g.6 e escapado do hook (gate analisa linhas adicionadas do staged).

---

## Estado atual — baseline mapeado (2026-04-22)

### Estrutura `backend/app/` — escopo

| Diretório | Arquivos | Linhas | Ofensores | Em escopo? |
|---|---|---|---|---|
| `services/` | 37 | 6 601 | **180** | ✅ alvo principal |
| `schemas/` | 49 | 3 175 | 104 | ✅ alvo (exceto DTOs A6e.3c) |
| `tasks/` | 3 | 836 | 29 | ✅ alvo (ponta grande em `pipeline_task.py` já foi tratada em A6g.2 T2.b) |
| `repositories/` | 11 | 1 548 | 53 | ✅ alvo |
| `models/` | 21 | 1 759 | 15 | ✅ alvo (baixo drift) |
| `core/` | 8 | 656 | 15 | ✅ alvo (baixo drift) |
| `middleware/` | 3 | 131 | 2 | ✅ alvo trivial |
| `scripts/` | 13 | 2 134 | 65 | ⚠️ **opcional** — 98% P7 low; deferir (não é código produção) |
| `api/` | — | — | — | 🚫 A6e.4 escopo |
| `application/` | — | — | — | 🚫 A6e.3/.3b limpos |
| `generated/` | — | — | — | 🚫 codegen |

**Total alvo:** ~14k linhas em 132 arquivos, **~400 ofensores** no audit.

### Top 10 arquivos mais longos (candidatos diretos)

| Rank | Arquivo | Linhas | Categorias |
|---|---|---|---|
| 1 | `tasks/pipeline_task.py` | **753** | P1×13 (mas `run_pipeline_task` já refatorado por A6g.2 T2.b → 58 linhas; outros métodos ainda grandes) |
| 2 | `services/content_classifier.py` | 621 | P1×3, P7×2 |
| 3 | `services/pipeline_adapter.py` | 442 | P1×6, P7×5 |
| 4 | `services/goal_service.py` | 412 | P1×3, P5×2, P7×7 |
| 5 | `services/task_service.py` | 334 | P1×3, P7×4 |
| 6 | `services/invitation_service.py` | 329 | P1×3, P7×6 |
| 7 | `models/task.py` | 308 | P1×2, P7×6 |
| 8 | `repositories/family_member_repository.py` | 274 | P1×2, P7×4 |
| 9 | `repositories/category_repository.py` | 264 | P1×3, P7×9 |
| 10 | `services/document_processor.py` | 257 | P1×3, P7×5 |

### Drift por categoria (só escopo A6g.3)

| Categoria | Ofensores | Severidade | Estratégia |
|---|---|---|---|
| **P1 long_functions** | **134** | high | extract helpers privados com nomes específicos |
| **P5 float_money** | **12** | high | `float` → `Decimal` (Python) / string (JSON wire) — **overlap A6e.3c** |
| **P3 dict_str_any_boundary** | ~15 (excluindo DTOs application/) | med | tipar com Pydantic `BaseModel` |
| **P9 deep_nesting** | 28 | med | early returns + guard clauses |
| **P4 optional_no_default** | 5 | med | adicionar `= None` / `= Literal[...]` |
| **P8 what_comments** | 2 | med | apagar ou converter para "why" |
| **P7 multiparagraph_docstring** | 254 | low | collapse single-line ou deixar por osmose |

**HIGH/MED total:** ~196 ofensores. **LOW (P7) 254:** opcional.

### Coordenação com A6e.3c (se estiver ativa ou pendente)

A6e.3c toca **4 arquivos DTO** (`schemas/dto/family_member/{command,mapper,response}.py` + `schemas/dto/category/mapper.py`) para tipar `dict[str, Any]`. Esse escopo é **adjacente ao seu P5 em `schemas/dto/goal/*`**. Se A6e.3c ainda não rodou:
- **Pegue** os 4 arquivos junto com P5 (mesmo agente = sem conflito).
- Ou **não tocar** esses 4 arquivos (deixa para A6e.3c) e focar em goal/transactions/config_blob.

Se A6e.3c já rodou, verifique `test_no_any_in_boundary.py` ALLOWLIST para evitar regressão.

---

## Alvo estrutural — estratégia de 2 slices

### Slice 1 — P5 (float money) + P9 (deep nesting) + P4 (optional-no-default)

**Objetivo:** cleanup de impacto bloqueante HIGH/MED que não exige decomposição estrutural.

**Arquivos alvo:**
- `backend/app/schemas/dto/goal/if_goal.py` (4 float→Decimal)
- `backend/app/schemas/dto/goal/aporte.py` (2)
- `backend/app/schemas/dto/goal/dolar.py` (1)
- `backend/app/schemas/dto/config_blob/response.py` (1)
- `backend/app/schemas/transactions.py` (4)
- Qualquer arquivo em `scripts/backfill_*.py` com deep nesting >3 níveis (28 ofensores total — alvo se encontrar ganho claro)
- Signatures `Optional[T]` sem default em `services/`, `repositories/` — 5 ocorrências

**Gate:**
- `pytest backend/tests -q` zero regressão
- `mypy backend/app/ --strict` (se disponível) — sem new errors
- `make update-openapi-snapshot` — `float` → `string` em DTOs monetários muda wire format; **verificar se frontend precisa sync**. Se sim, commit separado com update de `frontend/src/lib/api/*` + regerar `frontend/src/generated/`.

**Commit 1:** `refactor(schemas): float → Decimal em DTOs monetários (A6g.3 slice 1 · ADR-090)`
**Commit 2 (opcional):** `refactor(scripts): early returns em backfill_*.py (A6g.3 slice 1b)`
**Commit 3 (opcional):** `refactor(backend): optional signatures com default explícito (A6g.3 slice 1c)`

### Slice 2 — P1 (long functions) decomposição

**Objetivo:** quebrar 134 funções >40 linhas em helpers privados.

**Prioridade por arquivo (ordem sugerida):**

1. `services/pipeline_adapter.py` (442 l, P1×6) — maior concentração; padrão: extrair `_translate_stage_event(...)`, `_map_run_status(...)`, `_build_artifact_payload(...)`.
2. `services/goal_service.py` (412 l, P1×3) — refactor cirúrgico; use cases já existem em `application/goal/`, sobrou factory + glue.
3. `services/task_service.py` (334 l, P1×3) — similar; composites (upload attachment, scan deadlines) ficaram no service.
4. `services/invitation_service.py` (329 l, P1×3).
5. `services/content_classifier.py` (621 l, P1×3) — cuidado: ADR-081 cita; não alterar algoritmo, só decompor métodos.
6. `services/document_processor.py` (257 l, P1×3).
7. `services/task_progress_service.py` (P1×10 — maior densidade) — extract state machine.
8. `repositories/category_repository.py` (264 l, P1×3) — mapper + filter queries.
9. `repositories/family_member_repository.py` (274 l, P1×2).
10. `models/task.py` (308 l, P1×2) — métodos de entidade.

**Padrão:**
- Extrair helper `_<nome-específico>_<verb>_<noun>` (privado; underscore prefix).
- Cada helper 4-15 linhas.
- **Não** mudar assinatura pública — só reorganização interna.
- Teste: se serviço tem teste (provável após A6e.3), rodar `pytest backend/tests/test_<service>.py -q` antes/depois; mesma contagem de passes.

**Gate:**
- `pytest backend/tests -q` baseline mantido (>1054 passing)
- `dev/check_code_style_regression.py` verde — audit decresceu em P1
- `mypy` sem new errors

**Commit 4+:** 1 commit por arquivo grande. `refactor(services): extract helpers em pipeline_adapter (A6g.3 slice 2.a · P1 -6)`.

### Commit N+1 (docs hotspot, ≤5min)

- `docs/CHANGELOG.md [Unreleased]`: A6g.3 com deltas (X arquivos tocados, P1 Y→Z, P5 12→0).
- `docs/BACKLOG.md`: linha A6g.3 ☐ → ✅ + data; `dev/code_style_baseline.json` regenerado + committed.
- Atualizar linha A6g.3 em `BACKLOG §A6g` sub-fases.

### Fora de escopo (explicitar no CHANGELOG)

- **Routers `api/*.py`** — A6e.4.
- **Use cases `application/*`** — A6e.3/.3b limpos.
- **Scripts `backend/app/scripts/`** — 65 ofensores 98% P7 low; deferido. Entry em `per-file-ignores` se necessário.
- **P7 multiparagraph_docstring** — 254 ofensores low; osmose OK quando tocar arquivo, não commit dedicado.
- **Decomposição arquitetural profunda** (ex.: split `pipeline_task.py` 753 linhas em 3 módulos) — escopo é style sweep, não refactor arquitetural. Se encontrar necessidade, abrir ADR + lane dedicada.
- **Migração `Dict[str, Any]` em código interno dinâmico** (dispatchers de events, config merge) — `Dict[str, Any]` é legítimo em código **interno** (§Code style). Gate P3 só bloqueia em boundary HTTP.

---

## Sequência de execução

### 1. Setup

```bash
git fetch origin
git worktree list                           # confirma zero worktree a6g3
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' \
  refs/remotes/origin/agent/ | head -15
git checkout -b agent/a6g3-backend-style/$(date +%Y%m%d-%H%M)
```

### 2. Baseline

```bash
pytest backend/tests -q 2>&1 | tail -3      # anotar N passed (baseline >1054)
python dev/audit_code_style.py --format json --output-dir _scratch/a6g3_baseline/
# anotar contagens por categoria em backend/app/ (excluindo api/ application/)
python dev/check_code_style_regression.py    # deve passar contra baseline atual
```

### 3. Slices 1 → 2 na ordem acima

Cada slice = 1 ou mais commits atômicos + gate verde antes do próximo. Nunca misture slice 1 (tipos) com slice 2 (decomposição).

### 4. Gates de push final

```bash
pre-commit run --all-files                   # tudo verde (hooks ruff, grep, AST)
pytest backend/tests -q                      # zero regressão
python dev/check_code_style_regression.py    # baseline decresceu ou igual
make update-openapi-snapshot                 # só se P5 mudou DTOs monetários

git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest backend/tests -q

git push origin HEAD:main
```

---

## Critérios de aceite (binários)

- [ ] P5 `float_money` em `backend/app/schemas/` = **0** (12 eliminados ou migrados para A6e.3c).
- [ ] P1 `long_functions` em `backend/app/services/` + `repositories/` + `models/` **decresceu ≥50%** (de ~134 para ≤67).
- [ ] P9 `deep_nesting` em `backend/app/` (excluindo `scripts/`) = **0**.
- [ ] P4 `optional_no_default` em `backend/app/` = **0** (5 eliminados).
- [ ] P8 `what_comments` em `backend/app/` (excluindo `scripts/`) = **0** (2 eliminados).
- [ ] `dev/code_style_baseline.json` regenerado + committed; baseline decresceu em P1+P5+P4+P8+P9.
- [ ] `pytest backend/tests -q` zero regressão (mesmo N passed ou maior, com testes novos possíveis).
- [ ] `make update-openapi-snapshot` aplicado; se DTOs monetários mudaram, **frontend sync** em commit paralelo.
- [ ] `dev/check_code_style_regression.py` verde contra baseline anterior.
- [ ] `pre-commit run --all-files` passa (especialmente Ruff + AST tests novos da A6g.6).
- [ ] CHANGELOG + BACKLOG atualizados; linha A6g.3 → ✅.

---

## Rollback criteria — ABORTE se

- `pytest backend/tests -q` regredir em ≥3 tests (decomposição quebrou contract interno de algum service).
- `make update-openapi-snapshot` mostra mudança não-esperada de endpoint (schemas monetários devem mudar; tudo mais zero — rollback se router ou response shape não-monetário mudou).
- `mypy` ou `ruff check` acusa novos erros em arquivos não-tocados (indica refactor acidental de dependência).
- `dev/check_code_style_regression.py` acusa que alguma categoria **piorou** (ex.: extrair helper gerou nova long_function por engano).
- Conflict real com A6e.3c em `schemas/dto/family_member/*` ou `category/mapper.py` — coordenar por anúncio.

Em rollback: `git reset --hard origin/main` na branch; anunciar no chat (`A6g.3 rollback — categoria X regrediu em Y tests`); issue com diagnóstico.

---

## Anti-patterns a evitar

- **Tocar `backend/app/api/*.py`.** A6e.4 escopo; mesmo arquivo pequeno — fora.
- **Tocar `backend/app/application/*`.** A6e.3/.3b limpos; sweep agora só arrisca regressão sem ganho.
- **Mover lógica para `services/utils.py`** — filename proibido. Se extraindo helper compartilhado genuinamente, use nome específico (`services/money_formatting.py`, não `services/utils.py`).
- **Collapse agressivo de docstrings multi-parágrafo** em API pública de domínio. P7 é low; sacrifique por osmose, não como commit dedicado.
- **Split de arquivo grande "porque CLAUDE.md diz ≤500 linhas"** sem decomposição natural clara. Melhor deixar 753 linhas com helpers privados do que forçar split que não melhora leitura. Essa decisão entra no commit com justificativa.
- **Mudar assinatura pública de service** durante extract helper. Helpers são privados (`_` prefix); public API intacta.
- **Introduzir type `Any` "porque é mais simples"** em campo que era `Dict[str, Any]` — o pedido é tipar com Pydantic `BaseModel`. Se impossível, documentar em `test_no_any_in_boundary.py` ALLOWLIST com track de futuro sweep.
- **Modificar `pipeline_task.py::run_pipeline_task`** — já refatorado por A6g.2 T2.b. Outros métodos da classe/módulo pode sim refatorar.
- **`# noqa: <RULE>` sem motivo citável.** Cada noqa deve citar ADR ou track. Exemplo: `# noqa: PLR0915 — bank parser invariant; CLAUDE.md exceção ADR-097`.

---

## Coordenação com outros agentes

| Lane | Status | Overlap |
|---|---|---|
| **A6e.4** thin routers | 🚧 9/14 parcial | **Zero** — você não toca `api/*`. Se A6e.4 agente ainda está ativo com rebases, comunique via commit pequeno em hotspot (CHANGELOG/BACKLOG). |
| **A6e.3c** tipar DTOs | ☐ aberta | **Overlap real** em 4 arquivos (`schemas/dto/family_member/*` + `category/mapper.py`). **Pegar ambos** (incluir no seu slice 1) OR **evitar** esses 4 arquivos (deixa para quem pegar A6e.3c). |
| **A6g.6b** ruff auto-fix + format | ☐ aberta | **Overlap pesado** — `ruff format .` reformata ~422 arquivos incluindo backend/. Se A6g.6b mergear **antes** de A6g.3, você só precisa rebasear e trabalhar sobre código já formatado (bom). Se A6g.6b mergear **durante** seu slice, rebase vai ser grande — coordene sequencial. |
| **A6g.2c** rename `pipeline/llm/service.py` → `litellm_client.py` | ✅ 2026-04-22 | **Zero overlap** — mergeada em `main` (commit `8e115ec`); nenhuma ação necessária. |
| **A6e.events-migration** | ☐ aberta | **Overlap moderado** em `services/audit.py` + use cases. Se a migration rodar antes, você trabalha sobre código pós-evento. Coordene via commit order. |

**Recomendação de ordem:** A6g.6b **primeiro** (ruff format reformata tudo) → A6g.3 trabalha em código já formatado. Se impossível coordenar, rode `ruff format .` você mesmo em slice inicial como "sync".

**Hotspots compartilhados:**

```bash
git fetch origin
git log -5 --oneline origin/main -- \
  backend/app/services/ \
  backend/app/repositories/ \
  backend/app/schemas/ \
  docs/CHANGELOG.md \
  docs/BACKLOG.md
```

Se agente mergeou hotspot <30min, espere 2min, anuncie, commite docs no **mesmo turno** (≤5min).

**Sync periódico (sessão >1h):**

```bash
git fetch origin && git log --oneline HEAD..origin/main
# A6e.4 slice N+ merge → rebase e revisar; seu escopo não colide
# A6g.6b merge → rebase é grande (format aplicado em tudo); revisar com calma
```

---

## O que esta lane NÃO entrega

- **Routers finos** — A6e.4.
- **Use cases** — A6e.3/.3b ✅.
- **DTOs `family_member/*` + `category/mapper`** — A6e.3c (pode sobrepor; ver coordenação).
- **Auto-fix ruff I001/F541 + format** — A6g.6b (provavelmente antes desta lane).
- **Rename `pipeline/llm/service.py`** — A6g.2c ✅ (mergeada 2026-04-22).
- **Scripts `backend/app/scripts/`** — deferido (65 ofensores P7 low).
- **P7 multiparagraph_docstring massa** — 254 ofensores; osmose quando tocar arquivo; nunca commit dedicado.
- **Decomposição de `pipeline_task.py` 753 l** em múltiplos módulos — ADR dedicada; fora de style sweep.
- **Migração `Dict[str, Any]` em código interno dinâmico** — ADR-097 aceita em internal; gate só em boundary.

---

## Referências

- [CLAUDE.md §Code style](../../CLAUDE.md#code-style) — regras
- [ADR-090](../DECISIONS.md) — Money nunca `float`
- [ADR-114](../DECISIONS.md) — enforcement A6g.6
- [ADR-097](../DECISIONS.md) — extract-then-refactor (padrão)
- [BACKLOG §A6g](../BACKLOG.md) — trilho completo + baseline audit
- `dev/audit_code_style.py` — auditor (A6g.1)
- `dev/code_style_baseline.json` — baseline atual (A6g.6)
- `dev/check_code_style_regression.py` — gate CI (A6g.6)
- Prompts paralelos/relacionados: [track_a6e4](track_a6e4_thin_routers.md), [track_a6g2](track_a6g2_pipeline_style_sweep.md), [track_a6g4](track_a6g4_frontend_style_sweep.md), [track_a6g5](track_a6g5_tests_sweep.md), [track_a6g6](track_a6g6_enforcement.md)
