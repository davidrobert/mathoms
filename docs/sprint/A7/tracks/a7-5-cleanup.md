---
id: TRACK-a7-5-cleanup
type: track
title: "Track A7.5 — Cleanup final (deletar `config/` + bridges)"
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

# Track A7.5 — Cleanup final (deletar `config/` + bridges)

> **Lane ID:** A7.5
> **Branch prefix:** `agent/a7-5-cleanup/*`
> **Depende de:** A7.1 ✅ + A7.2a ✅ + A7.2b ✅ + A7.3 ✅ + A7.4 ✅ — **todas mergeadas em `main`**.
> **Paralelo com:** — (única lane da Onda 4, BLOQUEANTE).
> **Conflita com:** qualquer commit ativo em `pipeline/adapters/file_config_store.py`, `backend/app/services/config_materializer.py`, `pipeline/stage_config.py`, `dev/check_forbidden_paths.py`, `config/`.
> **Onda:** 4 (final).
> **Plano canônico:** [CONFIG_CUTOVER_PLAN.md §5.5](../../../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md#§55-a75--cleanup-final)
> **ADR:** — (execução; ADRs já mergeadas em A7.0/.2a/.2b/.3).
> **Supervisão CTO:** G3 pré-merge + **G4 wave boundary final** (humano valida e tagueia).

> **Objetivo (1 frase):** remover bridges (`FileConfigStore`, `materialize_config`, fallback de disco em `StageConfig`), deletar `config/`, adicionar `config/` à lista de paths proibidos; produto roda 100% DB-first.

---

## Por que esta lane

Sprint A7 acumulou bridges intencionais (cada um com prazo `A7.5`). Esta lane fecha. Após merge, qualquer regressão exigirá re-modelagem (não restauração de arquivo) — fence is up.

---

## Pré-condições obrigatórias

Antes de começar, confirme **todas**:

```bash
git fetch origin
git log --oneline origin/main | head -20

# Verificar status de cada lane no BACKLOG:
grep -A1 "A7.0\|A7.1\|A7.2a\|A7.2b\|A7.3\|A7.4" docs/BACKLOG.md | head -40
# Cada uma deve estar ✅ mergeada em main.

# Sanity check — sem call-sites legados:
grep -rn "_init_config\|materialize_config" pipeline/ scripts/ backend/ | \
  grep -v "FileConfigStore\|test_\|tests/"
# ↑ deve retornar 0 hits

grep -rn "FileConfigStore" pipeline/ scripts/ backend/ | \
  grep -v "test_\|tests/\|file_config_store\.py"
# ↑ deve retornar somente o adapter file_config_store.py + sua importação direta em StageConfig default
```

Se alguma pré-condição falha → **pare**. Não esta lane pode começar.

---

## Regras inegociáveis

1. **Nada é deletado sem teste.** Cada removal acompanha smoke verde + grep confirmando zero call-site.
2. **`pipeline/adapters/file_config_store.py` removido apenas no último commit** — antes disso, mantém DeprecationWarning para detectar leitor legado escondido.
3. **Reverter é difícil** — esta lane fecha a janela. PR deve ter revisão CTO **muito** cuidadosa.
4. **Paths proibidos atualizados** — `dev/check_forbidden_paths.py` ganha `config/` para impedir re-introdução acidental.
5. **Plano canônico arquivado** — `docs/CONFIG_CUTOVER_PLAN.md` move para `docs/archive/CONFIG_CUTOVER_PLAN-YYYY-MM-DD.md` com header de fechamento.

---

## Entregáveis (CONFIG_CUTOVER_PLAN.md §5.5)

### Limpeza de bridges

1. **`pipeline/stage_config.py`**: campo `config_store: ConfigStore` torna-se obrigatório (sem default `FileConfigStore`).
2. **`pipeline/adapters/file_config_store.py`** removido.
3. **`backend/app/services/config_materializer.py`** removido completamente (todos os `serialize_*` + `materialize_config`).
4. **`backend/app/services/pipeline_adapter.py`**: remove a lógica condicional de "DBConfigStore quando flag, FileConfigStore senão". Sempre `DBConfigStore`.

### Limpeza de arquivos `config/`

5. **`git rm -r config/`** — diretório inteiro deletado.

   Verificação prévia: lance um `ls config/`. **Devem restar apenas:** `methodology.md`, `report_spec.md`, `cenarios.json`, `internal_operators.example.yaml`, `localization.json`, `pipeline.json`, `prompts/`, `schemas/`, `scoring.json`, `templates/` — todos **fora do escopo dos 11 arquivos da Sprint A7**.

   **Decisão:** dos 11 arquivos do plano, todos já foram migrados/movidos pelas lanes A7.1–A7.4. Outros conteúdos em `config/` continuam vivos por enquanto (são produto interno: schemas JSON, prompts LLM, templates) e **não** entram na deleção desta lane. Esta lane deleta **apenas** os 11 arquivos do plano (que já estão sendo deletados nas lanes individuais; aqui é confirmação + sweep).

   Re-leia [CONFIG_CUTOVER_PLAN.md §1](../../../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md#§1-sumário-executivo) — a meta é "zero arquivos em `config/` (diretório removido)" **dentre os 11**, não esvaziamento total. Outros 10+ arquivos em `config/` (schemas, prompts, templates, pipeline.json) seguem vivos e fora do escopo de A7.

   **Reescopo recomendado**: este passo é confirmação que os 11 arquivos foram removidos pelas lanes anteriores; `config/` permanece com os arquivos legítimos. Se o escopo final for esvaziar `config/` por completo, abre lane A8 separada.

### Paths proibidos

6. **`dev/check_forbidden_paths.py`** ganha entradas:
   - `config/categorization.json`
   - `config/family_members.json`
   - `config/institutions.json`
   - `config/report_layout.yaml`
   - `config/decisions.md`
   - `config/parametros_fiscais.json`
   - `config/taxas.json`
   - `config/definitions.md`
   - `config/regras_composicao_patrimonial.md`
   - `config/source_hierarchy.md`
   - `config/milhas.md`

   Adição como entradas explícitas, não wildcard `config/*` (porque `config/pipeline.json`, `config/prompts/`, `config/schemas/` continuam legítimos).

### Documentação final

7. `docs/CONFIG_CUTOVER_PLAN.md` → `docs/archive/CONFIG_CUTOVER_PLAN-YYYY-MM-DD.md` com `git mv`. Header novo:
   ```markdown
   # ARQUIVADO — Plano cutover de `config/` para DB multi-tenant
   > Sprint A7 fechada em YYYY-MM-DD. Todas as 7 lanes mergeadas em `main`.
   > Resultado: 11 arquivos do CLI legado removidos; pipeline 100% DB-first;
   > tabelas globais versionadas para fiscal/market; entidade `Decision`
   > event-sourced substitui markdown editorial.
   ```

8. `docs/archive/README.md` ganha entrada (≤8 linhas) com data e motivo.

9. **CHANGELOG `[Unreleased]`** vira **`[Sprint A7] Config DB Cutover — YYYY-MM-DD`** com sumário de cada lane + sign-off CTO.

10. **CLAUDE.md §Regras críticas** — atualizar referência se ainda cita `config/<arquivo>` que foi removido. Verificar §Fontes de verdade especificamente.

11. **STATELESS_AUDIT.md** — remover entrada de `FileConfigStore` (não existe mais).

---

## Sequência de commits sugerida

```
1. refactor(pipeline): make StageConfig.config_store required (no FileConfigStore default) (A7.5)
2. refactor(backend): pipeline_adapter always uses DBConfigStore (A7.5)
3. chore(pipeline): rm pipeline/adapters/file_config_store.py (A7.5)
4. chore(backend): rm backend/app/services/config_materializer.py (A7.5)
5. chore(dev): check_forbidden_paths.py blocks 11 config/* files (A7.5)
6. chore(docs): archive CONFIG_CUTOVER_PLAN.md → archive/CONFIG_CUTOVER_PLAN-YYYY-MM-DD.md (A7.5)
7. docs(claude): update §Fontes de verdade after config/ removal (A7.5)
8. docs(audit): remove FileConfigStore entry from STATELESS_AUDIT.md (A7.5)
9. docs(changelog): close Sprint A7 with full entry + CTO sign-off (A7.5)
```

---

## Gates de push

```bash
pre-commit run --all-files
pytest tests -q                                       # pipeline 100% verde
pytest backend/tests -q                               # backend 100% verde
pytest backend/tests/integration -q                   # integração 100% verde
cd frontend && npm test -- --run                      # vitest verde
cd frontend && npm run test:e2e -- --grep @critical   # Playwright @critical verde
make smoke                                            # E2E sem nenhum bridge

# Confirmação de fence:
grep -rn "FileConfigStore\|materialize_config" pipeline/ backend/ scripts/
# ↑ deve retornar 0 hits

ls config/categorization.json 2>&1 | grep "No such"
# ↑ confirma que arquivo não existe

git log --oneline origin/main HEAD | head -5
# ↑ confirma branch atrás de origin/main = 0
```

---

## Acceptance gates (CONFIG_CUTOVER_PLAN.md §5.5)

- [ ] `FileConfigStore` removido ✓
- [ ] `materialize_config` removido (arquivo `config_materializer.py` deletado) ✓
- [ ] `StageConfig.config_store` obrigatório (sem default) ✓
- [ ] 11 arquivos do plano confirmados ausentes em `config/` ✓
- [ ] `dev/check_forbidden_paths.py` bloqueia os 11 paths ✓
- [ ] `pytest` (pipeline + backend + integration) + `npm test` + `npm run test:e2e --grep @critical` verdes ✓
- [ ] `make smoke` verde ✓
- [ ] `CONFIG_CUTOVER_PLAN.md` arquivado em `docs/archive/` ✓
- [ ] CHANGELOG fechado com sign-off CTO ✓
- [ ] CLAUDE.md atualizado se referenciava arquivos removidos ✓
- [ ] STATELESS_AUDIT.md atualizado ✓
- [ ] CTO G3 ✅ + **G4 wave boundary final humano** ✅

---

## O que NÃO entrega

- Esvaziamento total de `config/` (arquivos fora dos 11 do plano permanecem — são produto: schemas, prompts, pipeline.json, templates).
- Migração de outras configs futuras (sprint A8 se houver).
- UI editor para `report_layout` no DB (decisão de produto futura — fora desta sprint).

---

## Coordenação com outros agentes

- **Última lane.** Bloqueia toda a sprint até fechar.
- **Hotspot extremo:** `CLAUDE.md`, `BACKLOG.md`, `CHANGELOG.md`. Avise no chat com **2 minutos de antecedência** antes de tocar — outras lanes que vão pegar pickup nas sprints seguintes podem estar editando.
- **CTO supervision G4 (humano):** após merge, humano (David) valida que produto está rodando puro DB-first; emite tag `v-config-free` no git para marcar o ponto de não-retorno.

---

## Rollback

- Em teoria, `git revert <merge-commit>` restaura tudo (incluindo arquivos `config/` deletados, restaurados via git history).
- **Na prática:** revertendo A7.5 pós-merge expõe bridges removidos, mas os 4 arquivos de `docs/methodology/` (A7.4) **continuam lá**, e tabelas globais (A7.2b) **continuam populadas**. Resultado é estado inconsistente.
- **Mitigação:** suíte completa de testes empíricos pré-merge. Não fazer merge se houver dúvida; preferir mais 1 sessão de validação.

---

## Estimativa

~1.5–2 sessões. Trabalho mecânico mas requer cuidado cirúrgico. Sessão final concentra revisão CTO + sign-off.
