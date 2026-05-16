---
id: TRACK-f9-1-pipeline-stages-rename
type: track
title: "Track F9.1 — `git mv pipeline/stages/e*.py` → nomes descritivos"
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

# Track F9.1 — `git mv pipeline/stages/e*.py` → nomes descritivos

> **Lane ID:** F9.1
> **Branch prefix:** `agent/f9-stage-rename/1-pipeline-stages/*`
> **Depende de:** F9.0 ✅ (auditoria fechada, mapa exaustivo)
> **Paralelo com:** nenhum (F9 é sequencial; bloqueia 9.2)
> **Conflita com:** qualquer commit em `pipeline/stages/`, `pipeline/stage_spec.py`, `pipeline/orchestrator.py`
> **Onda:** F9 (sub-fatia 2/7)
> **Índice de prompts:** [README.md](../../../../README.md)
> **Fonte de verdade:** [ADR-093](../../../DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a) · [`STAGE_RENAME_MAP`](../../../../pipeline/stage_spec.py#L129)

> **Objetivo:** renomear os 14 wrappers em `pipeline/stages/e*.py` para os
> nomes descritivos do `STAGE_RENAME_MAP`, atualizar imports e o registro
> no orquestrador. **Nada além disso** — strings literais ("E2", "E3"…) em
> código de produção continuam intactas (F9.2).

---

## Por que este slice agora

`pipeline/stages/` tem 14 wrappers (`e0_audit.py`, `e1.py`, `e15.py`,
`e15c.py`, `e2.py`, `e2_extratos.py`, `e2_faturas.py`, `e2_llm.py`, `e3.py`,
`e4.py`, `e5.py`, `e5n.py`, `e7.py`, `e7_review_llm.py` + `e0_route.py`,
`e0_unlock.py`). Esses são pontos de entrada limpos — cada um expõe `run`
+ um adapter. O `git mv` é **mecânico** e a maior parte dos imports é
consumida por `STAGE_REGISTRY` que é o único lugar a atualizar.

---

## Mapa de renames

Fonte: `STAGE_RENAME_MAP` em [pipeline/stage_spec.py:129](../../../../pipeline/stage_spec.py#L129).

| Antes (`pipeline/stages/`) | Depois (`pipeline/stages/`) |
|---|---|
| `e0_audit.py` | `audit_documents.py` |
| `e0_unlock.py` | `unlock_documents.py` |
| `e0_route.py` | `route_documents.py` |
| `e1.py` | `extract_members.py` |
| `e15.py` | `extract_baseline.py` |
| `e15c.py` | `consolidate_baseline.py` |
| `e2_extratos.py` | `extract_statements.py` |
| `e2_faturas.py` | `extract_invoices.py` |
| `e2_llm.py` | `extract_with_llm.py` |
| `e2.py` | (manter — é shim compartilhado de pasta E2 em disco; fora do mapa de stages executáveis) ⚠️ verificar com F9.0 |
| `e3.py` | `reconcile_transactions.py` |
| `e4.py` | `categorize_transactions.py` |
| `e5.py` | `analyze_finances.py` |
| `e5n.py` | `generate_narratives.py` |
| `e7.py` | (consolidar com `e7_review_llm.py`? — investigar antes) ⚠️ |
| `e7_review_llm.py` | `review_finances.py` |

**Itens com ⚠️:** F9.0 deve ter classificado. Se F9.0 deixou ambíguo, escreva
nota em `_scratch/f9_1_decisions.md` e siga o conservador: mantenha como está
e referencie no PR.

---

## Regras inegociáveis

1. **`git mv` puro** — não combine rename com mudança de conteúdo no mesmo commit.
   Hook `check_float_money._is_rename()` (entregue em A6g.2c) reconhece renames
   limpos e libera. Diff de conteúdo só após o `git mv` ter sido committed.
2. **Nenhum delete.** Rename apenas. Wrappers continuam com mesma API.
3. **Imports relativos não mudam.** `from .e3 import ...` vira `from .reconcile_transactions import ...` apenas em **F9.2**, não aqui. **Exceção:** o **único** import a atualizar nesta fatia é o lookup interno em `pipeline/stage_spec.py` (se houver mapeamento implícito de nome → módulo) e em `pipeline/orchestrator.py` (se carrega via `importlib`).
4. **`STAGE_REGISTRY` permanece com keys legadas** (`"E3"`, `"E5"`…) — F9.2 troca isso.

---

## Sequência de commits

Um commit **por wrapper** facilita revert cirúrgico se algo quebrar.

```bash
# Para cada par (antigo → novo):
git mv pipeline/stages/<antigo>.py pipeline/stages/<novo>.py
# Atualizar imports MÍNIMOS:
#   - pipeline/orchestrator.py (se houver mapeamento dinâmico nome→módulo)
#   - pipeline/stage_spec.py (se houver)
#   - tests/unit/pipeline/test_stage_wrappers.py (se importar por path)
pytest tests/unit/pipeline -q
git commit -m "refactor(pipeline): rename stages/<antigo>.py → <novo>.py (F9.1)"
```

Sequência sugerida (do mais isolado para o mais conectado):
1. `e0_audit` → `audit_documents`
2. `e0_unlock` → `unlock_documents`
3. `e0_route` → `route_documents`
4. `e1` → `extract_members`
5. `e15` → `extract_baseline`
6. `e15c` → `consolidate_baseline`
7. `e2_extratos` → `extract_statements`
8. `e2_faturas` → `extract_invoices`
9. `e2_llm` → `extract_with_llm`
10. `e3` → `reconcile_transactions`
11. `e4` → `categorize_transactions`
12. `e5` → `analyze_finances`
13. `e5n` → `generate_narratives`
14. `e7_review_llm` → `review_finances`

Após cada commit: `pytest tests/unit/pipeline -q` (suite rápida; verde antes do próximo).

---

## Sequência de execução

```bash
# Setup
git fetch origin && git status
git checkout -b agent/f9-stage-rename/1-pipeline-stages/$(date +%Y%m%d-%H%M)

# Antes do primeiro mv, baseline:
pytest tests -q 2>&1 | tail -3
pytest backend/tests -q 2>&1 | tail -3

# Loop: 14 commits sequenciais (ver lista acima)

# Gate final
pre-commit run --all-files
pytest tests -q                          # zero regressão (goldens E3/E4/E5/E5N/E7)
pytest backend/tests -q                  # zero regressão

# Drift check
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest tests -q
git push origin HEAD:main
```

---

## Critérios de aceite

- [ ] `ls pipeline/stages/e*.py` retorna **vazio** (todos renomeados).
- [ ] `ls pipeline/stages/{audit,unlock,route,extract,consolidate,reconcile,categorize,analyze,generate,review}_*.py` lista os 14 novos.
- [ ] 14 commits separados, cada um com `pytest tests/unit/pipeline -q` verde.
- [ ] `pytest tests -q` + `pytest backend/tests -q` finais idênticos a baseline (mesmo número de tests passing).
- [ ] Goldens E3/E4/E5/E5.N/E7 verdes.
- [ ] Pre-commit verde (hook `_is_rename()` libera diff puro de mv).
- [ ] BACKLOG + CHANGELOG atualizados.

---

## Rollback criteria — ABORTE se

- Qualquer golden falha após um `git mv` específico — `git revert` esse commit; investigue antes de retomar.
- Pre-commit reclama de "string literal de produção mudou" — você editou conteúdo junto com mv. Reset, separe.
- `pipeline/orchestrator.py` precisa de >5 linhas de mudança para ressolver imports — algo está errado, revisite F9.0.

---

## Atualizar documentação (obrigatório, último passo)

1. **`docs/BACKLOG.md`** — na lane F9, status: `🚧 F9.0 ✅ · F9.1 ✅ — 14 wrappers renomeados YYYY-MM-DD; F9.2 destravada`.
2. **`docs/CHANGELOG.md`** — entrada datada:
   ```markdown
   ### 2026-MM-DD — F9.1 pipeline/stages rename (ADR-093)

   - `git mv` em 14 wrappers de `pipeline/stages/e*.py` para nomes descritivos
     conforme `STAGE_RENAME_MAP`. Imports internos atualizados em
     `pipeline/orchestrator.py` e `pipeline/stage_spec.py`.
   - Strings literais (`"E2"`, `"E3"`…) em código de produção **inalteradas**
     — F9.2 endereça.
   - Goldens E3/E4/E5/E5.N/E7 verdes; zero regressão.
   ```
3. **`docs/reference/ARCHITECTURE.md` §7** — se houver tabela de stages com filenames,
   atualizar (provavelmente sim).
4. **`docs/DECISIONS.md`** ADR-093 — nota "F9.1 fechada YYYY-MM-DD".
5. Commit docs separado: `docs(f9): F9.1 rename pipeline/stages, F9.2 destravada (ADR-093)`.

---

## O que esta fatia NÃO entrega

- **Renames em `scripts/e*.py`** — F9.4.
- **Substituição de strings literais `"E2"`/`"E3"`** — F9.2.
- **Migration de DB** — F9.3.
- **Update das keys do `STAGE_REGISTRY`** — F9.2 (com alias compat se necessário).

---

## Referências

- F9.0 (prereq): [track_f9_0_audit.md](f9-0-audit.md)
- F9.2 (próximo): [track_f9_2_string_literals.md](f9-2-string-literals.md)
- ADR-093 (plano completo): `docs/DECISIONS.md:2228`
- `STAGE_RENAME_MAP`: `pipeline/stage_spec.py:129`
- Hook `_is_rename`: `dev/check_float_money.py` (ver A6g.2c).
