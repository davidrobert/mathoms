---
id: TRACK-f9-4-scripts-rename
type: track
title: "Track F9.4 — `git mv scripts/e*.py` → descritivos + alias CLI compat"
sprint: F9
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/f9
  - status/consumed
---

# Track F9.4 — `git mv scripts/e*.py` → descritivos + alias CLI compat

> **Lane ID:** F9.4
> **Branch prefix:** `agent/f9-stage-rename/4-scripts/*`
> **Depende de:** F9.3 ✅ (DB já em descritivo)
> **Paralelo com:** nenhum
> **Conflita com:** qualquer commit em `scripts/`, `pipeline/orchestrator.py`, runbooks que invoquem `python -m scripts.e*`
> **Onda:** F9 (sub-fatia 5/7)
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [ADR-093](../DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a) · [`STAGE_RENAME_MAP`](../../pipeline/stage_spec.py#L129)

> **Objetivo:** renomear scripts CLI em `scripts/e*.py` para nomes descritivos
> e adicionar alias compat em `scripts/e_reset.py --from <stage>` (legacy ou
> descritivo) por 1 release. Wrapper finos com warning de deprecação para
> os filenames legados, removidos em F9.6.

---

## Por que este slice agora

`scripts/e*.py` são pontos de entrada CLI/import. Renomear é mecânico (`git mv`)
mas tem dois cuidados:

1. **Imports externos** (`from scripts.e3_reconcile import X`) precisam continuar
   funcionando durante 1 release — wrapper de 2 linhas no path antigo.
2. **CLI args** em `e_reset.py --from E3` aceitam ambos via
   `resolve_stage_name()` (entregue em F9.2). Aqui só ajustamos help text +
   deprecation warning.

Pós-A6c, vários `main(root_dir)` legados foram removidos. F9.4 fecha o
restante dos filenames legados.

---

## Mapa de renames

Fonte: F9.0 audit + `STAGE_RENAME_MAP`. Esperado:

| Antes (`scripts/`) | Depois (`scripts/`) |
|---|---|
| `e0_audit.py` | `audit_documents.py` |
| `e0_route.py` | `route_documents.py` |
| `e0_unlock.py` | `unlock_documents.py` |
| `e15_consolidate.py` | `consolidate_baseline.py` |
| `e2_extract.py` | `extract_statements.py` (ou `extract.py` se for entrypoint unificado — F9.0 confirma) |
| `e3_reconcile.py` | `reconcile_transactions.py` |
| `e4_categorize.py` | `categorize_transactions.py` |
| `e5_analyze.py` | `analyze_finances.py` |
| `e5n_narrativas.py` | `generate_narratives.py` |
| `e7_review.py` | `review_finances.py` |
| `e_reset.py` | (mantém — não é stage; é utility) |

**Verificar com F9.0:** se algum script é só shim/CLI ou se algum stage tem
múltiplos scripts (E2 tem 3 wrappers em `pipeline/stages/` mas só 1 em
`scripts/`). Auditoria F9.0 deve esclarecer; se não, escreva nota e siga
conservador.

---

## Regras inegociáveis

1. **`git mv` puro.** Sem mudança de conteúdo no mesmo commit. F9.2 já
   atualizou strings internas; aqui é só rename de file.
2. **Wrapper de compat por 1 release.** Para cada antigo, criar `scripts/<antigo>.py`
   com 4 linhas:
   ```python
   import warnings
   warnings.warn("scripts/e3_reconcile.py é deprecated; use scripts/reconcile_transactions.py (remove em F9.6)", DeprecationWarning, stacklevel=2)
   from scripts.reconcile_transactions import *  # noqa: F401, F403
   ```
   Wrappers vão para `scripts/_legacy/` ou ficam na raiz (decisão F9.0). **Não**
   bypasse o warning — é o sinal para consumidores externos atualizarem.
3. **CLI alias bidirecional em `e_reset.py`.** `--from E3` aceita; emite
   warning único na primeira invocação. Já implementado em F9.2; aqui só
   atualiza help text:
   ```
   --from STAGE   Stage para reiniciar (descritivo: reconcile_transactions; legado: E3 — deprecated)
   ```
4. **Não toque `pipeline/stages/`** (F9.1).

---

## Sequência de commits

Um commit **por par** (rename + wrapper compat). 10-11 commits sequenciais.

```bash
# Padrão por par:
git mv scripts/e3_reconcile.py scripts/reconcile_transactions.py
# Criar wrapper scripts/e3_reconcile.py com warnings.warn + from … import *
pytest tests/unit/pipeline/test_e3_*.py -q  # smoke
git add scripts/reconcile_transactions.py scripts/e3_reconcile.py
git commit -m "refactor(scripts): rename e3_reconcile → reconcile_transactions + compat shim (F9.4)"
```

Sequência sugerida (do mais isolado para o mais crítico):
1. `e0_audit` → `audit_documents`
2. `e0_route` → `route_documents`
3. `e0_unlock` → `unlock_documents`
4. `e15_consolidate` → `consolidate_baseline`
5. `e2_extract` → `extract_statements` (ou `extract.py` per F9.0)
6. `e3_reconcile` → `reconcile_transactions`
7. `e4_categorize` → `categorize_transactions`
8. `e5_analyze` → `analyze_finances`
9. `e5n_narrativas` → `generate_narratives`
10. `e7_review` → `review_finances`

Por último: commit consolidado de help-text em `e_reset.py` se ainda houver pendência.

---

## Sequência de execução

```bash
git fetch origin && git status
git checkout -b agent/f9-stage-rename/4-scripts/$(date +%Y%m%d-%H%M)

# Baseline
pytest tests -q 2>&1 | tail -3

# Loop: 10 commits (rename + wrapper)

# Verificação dos wrappers
python -c "from scripts.e3_reconcile import *" 2>&1 | grep -i "deprecation"
# Esperado: warning emitido. Se silencioso, wrapper está errado.

# Gate final
pre-commit run --all-files
pytest tests -q                          # zero regressão; goldens passam
pytest backend/tests -q

# Smoke CLI
python scripts/e_reset.py --help | grep -E "descritivo|legado"   # help text atualizado
python scripts/e_reset.py --dry-run --from E3 2>&1 | grep -i "deprecat"  # warning emitido

# Drift
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest tests -q

git push origin HEAD:main
```

---

## Critérios de aceite

- [ ] `ls scripts/e[0-9]*.py` lista apenas os **wrappers** (cada um com `warnings.warn` + `from … import *`).
- [ ] `ls scripts/{audit,unlock,route,extract,consolidate,reconcile,categorize,analyze,generate,review}_*.py` retorna 10 entradas.
- [ ] `python -c "from scripts.e3_reconcile import *"` emite `DeprecationWarning`.
- [ ] `e_reset.py --from E3` emite warning e roda; `--from reconcile_transactions` roda silencioso.
- [ ] `pytest tests -q` + `pytest backend/tests -q` verdes.
- [ ] Goldens E3/E4/E5/E5.N/E7 verdes.
- [ ] BACKLOG + CHANGELOG atualizados.

---

## Rollback criteria — ABORTE se

- Wrapper compat quebra import (`from scripts.e3_reconcile import build_X` falha porque `*` não exporta `build_X` — adicione `__all__` no novo módulo).
- CLI `--from E3` deixa de funcionar (regressão do alias resolvido em F9.2).
- Goldens E3/E5/E5.N param de bater (provavelmente import path mudou e algum teste cacheava o módulo legado).

---

## Atualizar documentação (obrigatório, último passo)

1. **`docs/BACKLOG.md`** — lane F9 status: `🚧 F9.0-.3 ✅ · F9.4 ✅ — scripts renomeados YYYY-MM-DD com wrappers compat; F9.5 destravada (guardrail hard-fail)`.
2. **`docs/CHANGELOG.md`** — entrada datada:
   ```markdown
   ### 2026-MM-DD — F9.4 scripts/ rename (ADR-093)

   - `git mv` em 10 scripts CLI (`scripts/e0_audit.py` → `audit_documents.py` etc)
     conforme `STAGE_RENAME_MAP`.
   - Wrappers compat em `scripts/e*.py` emitem `DeprecationWarning` e
     re-exportam o módulo descritivo (remoção em F9.6).
   - `scripts/e_reset.py --from E3`: warning + alias bidirecional via
     `resolve_stage_name`.
   - Goldens verdes; zero regressão.
   ```
3. **`docs/reference/SETUP.md` / `docs/reference/RUNBOOK.md`** — comandos `python -m scripts.e3_reconcile` se citados, atualizar para descritivo (referência primária); manter nota "alias `e3_reconcile` ainda aceita até F9.6".
4. **`docs/reference/PIPELINE_ARTIFACTS.md`** — qualquer referência a script por nome.
5. **`CLAUDE.md` §Convenções de código do pipeline** — atualizar tabela "Scripts em `scripts/` seguem `eN_nome.py`": após F9.4, padrão é descritivo; aliases legados `eN_*.py` deprecados.
6. **`docs/DECISIONS.md`** ADR-093 — nota "F9.4 fechada YYYY-MM-DD".
7. Commit docs separado: `docs(f9): F9.4 scripts rename + compat, F9.5 destravada (ADR-093)`.

---

## O que esta fatia NÃO entrega

- **Remoção dos wrappers compat** — F9.6.
- **Hard-fail no `test_no_legacy_stage_names.py`** — F9.5.
- **Cleanup de `_init_config()` global e helpers órfãos** — F9.6.

---

## Referências

- F9.3 (prereq): [track_f9_3_alembic_migration.md](track_f9_3_alembic_migration.md)
- F9.5 (próximo): [track_f9_5_guardrail_hardfail.md](track_f9_5_guardrail_hardfail.md)
- ADR-093: `docs/DECISIONS.md:2228`
- Auditoria F9.0: `docs/archive/audits/f9_audit_<date>.md`
