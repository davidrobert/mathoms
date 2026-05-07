---
id: TRACK-a7-1-cutover-materialize
type: track
title: "Track A7.1 — Cutover `materialize_config` → `ConfigStore`"
sprint: A7
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a7
  - status/consumed
---

# Track A7.1 — Cutover `materialize_config` → `ConfigStore`

> **Lane ID:** A7.1
> **Branch prefix:** `agent/a7-1-cutover-materialize/*`
> **Depende de:** A7.0 ✅ mergeada em `main` (Protocol + adapters existem).
> **Paralelo com:** A7.2a (Decision aggregate), A7.2b (fiscal/market), A7.4 (docs metodologia).
> **Conflita com:** qualquer commit ativo em `pipeline/stages/e[3-5]*.py`, `scripts/e[3-5]*.py`, `backend/app/services/config_materializer.py`, `backend/app/services/pipeline_adapter.py`.
> **Onda:** 2 (paralelizável).
> **Plano canônico:** [CONFIG_CUTOVER_PLAN.md §5.1](../CONFIG_CUTOVER_PLAN.md#§51-a71--cutover-materialize_config--configstore)
> **ADR:** [ADR-134](../DECISIONS.md#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend) (já existe — esta lane é execução).
> **Supervisão CTO:** G3 pré-merge.

> **Objetivo (1 frase):** todos os leitores user-facing (pipeline E3/E4/E5/E5.N + scripts) consomem `ConfigStore` em vez de `_init_config()`/`materialize_config()`. Bridge `materialize_config` ganha `DeprecationWarning` + log estruturado.

---

## Por que esta lane

A7.0 entregou Protocol + adapters. Hoje pipeline lê config via `_init_config()` em scripts ou por leitura direta de `Path`. Esta lane migra todos os leitores para o Protocol — **sem** quebrar a leitura legada (fallback disco continua funcionando via `FileConfigStore`).

**Configs cobertos por esta lane:** `categorization`, `family_members`, `report_layout`, `institutions`, `transfer_configs`. **NÃO** cobre `parametros_fiscais`/`taxas` (são A7.2b) nem `decisions` (é A7.2a).

---

## Regras inegociáveis

1. **Pipeline não importa SQLAlchemy/FastAPI** (CLAUDE.md §Regras críticas) — leitor recebe `ConfigStore` injetado, não cria `DBConfigStore` direto em `pipeline/`.
2. **Stateless rigoroso** ([ADR-111](../DECISIONS.md#adr-111--stateless-rigoroso-em-backendapp-e-pipeline-a6f6)) — cache vai para Redis quando hot-path; sem `@lru_cache`.
3. **Money nunca é float** ([ADR-090](../DECISIONS.md)).
4. **Funções 4-20 linhas, módulos ≤500** (CLAUDE.md §Code style).
5. **Bridge `materialize_config` permanece** funcional até A7.5. Esta lane só adiciona DeprecationWarning + log; não remove.
6. **Smoke E2E verde após cada commit** — não merge intermediário com pipeline quebrado.

---

## Estado atual — call-sites a migrar

| Call-site | Arquivo | Ação |
|---|---|---|
| `_init_config()` em E5 | `scripts/e5_analyze.py` (linhas ~70-90 — `CONFIG_*` paths) | Aceita `ConfigStore` opcional via parâmetro; fallback para FileConfigStore com warning |
| `_init_config()` em E5.N | `scripts/e5n_narrativas.py` ou `pipeline/stages/e5n.py` | Idem |
| Leitura de `categorization` em E4 | `pipeline/stages/e4.py` + `pipeline/domain/services/categorization_service.py` | Receber `CategorizationConfig` via construtor |
| Leitura de `family_members` em E3/E4 | `pipeline/stages/e3.py`, `pipeline/stages/e4.py` | Receber `FamilyMembersConfig` via construtor |
| Leitura de `report_layout` em E6 (já removido em ADR-129) e em renderer React | já consumido via codegen — confirmar que codegen lê via ConfigStore no build (`dev/codegen_report_layout.py`) | Migrar codegen para usar DBConfigStore quando flag ativa, FileConfigStore senão |
| `materialize_config()` em `pipeline_adapter.py` | `backend/app/services/pipeline_adapter.py` | Adicionar DeprecationWarning + log estruturado `mathoms.config.materialize.legacy_call`; manter funcional |
| Service `list_consumo_pontuais` (lê transfer_configs do disco) | `backend/app/application/.../list_consumo_pontuais.py` | Receber `TransferConfig` via DI (já está em ADR-133 — confirmar e propagar) |

Confirme com:
```bash
grep -rn "config/categorization\|config/family_members\|config/report_layout\|config/institutions\|config/transfer" pipeline/ scripts/ backend/
grep -rn "_init_config\|materialize_config" pipeline/ scripts/ backend/
```

---

## Sequência de commits sugerida

### Commit 1 — Pipeline adapter injeta DBConfigStore
```
feat(backend): pipeline_adapter injects DBConfigStore in StageConfig (A7.1)
```
- `backend/app/services/pipeline_adapter.py`: ao montar `StageConfig`, instancia `DBConfigStore(db=session)` quando `MATHOMS_USE_DB_ARTIFACTS=true`; `FileConfigStore()` caso contrário.
- Tests: novo teste em `backend/tests/test_pipeline_adapter.py` confirma injeção.

### Commit 2 — E4 categorization via Protocol
```
refactor(pipeline): e4 + categorization_service consume CategorizationConfig from ConfigStore (A7.1)
```
- `pipeline/domain/services/categorization_service.py` aceita `CategorizationConfig` no construtor.
- `pipeline/stages/e4.py` resolve config via `ctx.config_store.get_categorization(workspace_id)`.
- Testes com `InMemoryConfigStore` (não monkeypatch).
- Goldens: rodar `pytest tests/test_e4_golden_execution.py -q` — output deve ser idêntico.

### Commit 3 — E3 family_members via Protocol
```
refactor(pipeline): e3 reconcile consumes FamilyMembersConfig from ConfigStore (A7.1)
```
- Idem para reconcile (members + bank_member resolução).
- Goldens E3.

### Commit 4 — E5/E5.N via Protocol
```
refactor(scripts): e5_analyze + e5n consume ConfigStore (A7.1)
```
- `scripts/e5_analyze.py`: assinatura `analyze_*(ctx, config_store=None)`. Default `FileConfigStore()` com warning.
- `scripts/e5n_narrativas.py` ou `pipeline/stages/e5n.py`: idem.
- Goldens E5/E5.N.

### Commit 5 — `materialize_config` ganha DeprecationWarning
```
chore(backend): materialize_config emits DeprecationWarning + structured log (A7.1)
```
- `backend/app/services/config_materializer.py`: `materialize_config(...)` emite `warnings.warn("Use ConfigStore via StageConfig; materialize_config will be removed in A7.5", DeprecationWarning)` + `logger.info("mathoms.config.materialize.legacy_call", extra={...})`.
- Bridge **continua funcional**.

### Commit 6 — Smoke + goldens
```
test(a7-1): smoke + golden parity post-cutover
```
- Roda `make smoke` com `MATHOMS_USE_DB_ARTIFACTS=true` em workspace fixture.
- Confirma logs do smoke **não** contêm `mathoms.config.materialize.legacy_call` (sinal de call-site não migrado).
- Goldens E3/E4/E5/E5.N todos verdes byte-a-byte.

### Commit 7 — Documentação
```
docs(a7): mark A7.1 ✅ + update CHANGELOG
```

---

## Gates de push

Idêntico a A7.0 + obrigatório:

```bash
make smoke                          # E2E pipeline em fixture
grep -rn "_init_config\|materialize_config" pipeline/ scripts/  # só fallback warned + testes
```

---

## Acceptance gates (CONFIG_CUTOVER_PLAN.md §5.1)

- [ ] `pipeline_adapter` injeta `DBConfigStore` quando flag ativa ✓
- [ ] E3, E4, E5, E5.N migrados para `ConfigStore` ✓
- [ ] `materialize_config` emite DeprecationWarning + log ✓
- [ ] `pytest tests -q && pytest backend/tests -q` verdes ✓
- [ ] `make smoke` verde ✓
- [ ] Logs do smoke **não** contêm `mathoms.config.materialize.legacy_call` ✓
- [ ] Goldens E3/E4/E5/E5.N byte-a-byte idênticos ao baseline pré-cutover ✓
- [ ] CTO G3 ✅

---

## O que NÃO entrega

- Migração de `parametros_fiscais` ou `taxas` (A7.2b).
- Migração de `decisions.md` (A7.2a).
- Remoção de `materialize_config` (A7.5).
- Catalog/override split (A7.3).
- Movimentação de docs metodologia (A7.4).

---

## Coordenação com outros agentes

- **Paralelo com A7.2a, A7.2b, A7.4**: arquivos disjuntos.
  - A7.2a toca `backend/app/{models,application/decisions,api/decisions}` + `frontend/.../PlanoDeAcao` — zero overlap.
  - A7.2b toca `pipeline/domain/services/{previdencia,cenarios}_*` (A7.1 toca `e[3-4-5].py`/`categorization_service`) — overlap **zero** se A7.1 não toca os domain services fiscais. Confirmar antes de cada commit.
  - A7.4 toca somente `docs/methodology/` — zero overlap.
- **Hotspot cross-lane único:** `pipeline/stage_config.py`. Solução: A7.0 já adicionou o campo `config_store`. A7.1 e A7.2b apenas leem dele. Se ambos rebaseiam em `main` antes de push, sem conflito.
- **Co-revisão:** se A7.2b precisa **estender** Protocol (improvável — já está stub), avise via CHANGELOG `[Unreleased]` antes de tocar `pipeline/ports/config_store.py`.

---

## Rollback

`git revert` por commit. Goldens detectam regressão imediata. Bridge legado (`materialize_config`) continua funcionando se a migração for revertida.

---

## Estimativa

~2–3 sessões de 2h. Trabalho mecânico (refactor de chamadores) + verificação de goldens.
