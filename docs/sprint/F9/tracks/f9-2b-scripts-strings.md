---
id: TRACK-f9-2b-scripts-strings
type: track
title: "Track F9.2b — Strings descritivas em `scripts/` (excluindo `e_reset.py`)"
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

# Track F9.2b — Strings descritivas em `scripts/` (excluindo `e_reset.py`)

> **Lane ID:** F9.2b
> **Branch prefix:** `agent/f9-stage-rename/2b-scripts/*`
> **Depende de:** F9.2a ✅ (artifact_store + pipeline/* migrados)
> **Bloqueia:** F9.2e (closeout)
> **Paralelo com:** F9.2c (`e_reset.py`) e F9.2d (backend+tests) — operam em escopos disjuntos
> **Onda:** F9 (sub-fatia 3b/7)
> **Fonte de verdade:** [ADR-093](../../../DECISIONS.md#adr-093) · [`STAGE_RENAME_MAP`](../../../../pipeline/stage_spec.py#L54)

> **Objetivo:** substituir strings legadas (`"E3"`, `"E5"`, `"E2-llm"`...) por
> descritivas em todos os `scripts/e*.py` **exceto `scripts/e_reset.py`**
> (esse vai em F9.2c por causa do CLI alias). Filenames continuam legados —
> rename é F9.4.

---

## Estado atual

- F9.2a entregue: `pipeline/artifact_store.py` aceita ambos os formatos via
  `resolve_stage_name`. Scripts podem migrar sem coordenação com pipeline core.
- Filenames `scripts/e*.py` permanecem legados (F9.4 endereça).

## Hotspots (≈120 hits)

```
41  scripts/e3_reconcile.py
19  scripts/e5_analyze.py
12  scripts/e2_extract.py
10  scripts/e5n_narrativas.py
 8  scripts/e7_review.py
 7  scripts/e15_consolidate.py
 6  scripts/e4_categorize.py
 5  scripts/pipeline_common.py
 5  scripts/e2/common.py
 2  scripts/e2/banks/c6bank.py
 2  scripts/e2/banks/itau.py
 2  scripts/e2/banks/santander.py
 1  scripts/e2/banks/{bankofamerica,bradesco,btg,caixa,picpay,quintoandar,rico,wise}.py
 1  scripts/e0_audit.py
 1  scripts/e0_route.py
 1  scripts/e0/{audit_filename,audit_helpers,audit_integrity,audit_ledger}.py
```

## Estratégia

### Tier A — `scripts/e3_reconcile.py` + `scripts/e5_analyze.py` (maiores)

Maior densidade. Substitua literais. Use `resolve_stage_name` se houver
boundary externo (CLI args). Logger calls e `store.read("E3", ...)` → descritivo.

**Gate:** `pytest tests -q -k "e3 or e5 or reconcile or analyze"` verde.
**Commit:** `refactor(scripts): e3_reconcile + e5_analyze strings descritivas (F9.2b — Tier A)`

### Tier B — restantes scripts E*

`e2_extract.py`, `e5n_narrativas.py`, `e7_review.py`, `e15_consolidate.py`,
`e4_categorize.py`, `e0_audit.py`, `e0_route.py`, `pipeline_common.py`.

**Gate:** `pytest tests -q` verde.
**Commit:** `refactor(scripts): e0/e2/e4/e7/e15 strings descritivas (F9.2b — Tier B)`

### Tier C — `scripts/e2/banks/*.py` + `scripts/e2/common.py` + `scripts/e0/*`

Hits pequenos por arquivo (1-5). Strings em logs/tags.

**Gate:** `pytest tests -q` verde.
**Commit:** `refactor(scripts): e2/banks + e0 helpers strings descritivas (F9.2b — Tier C)`

---

## Sequência

```bash
git fetch origin
git checkout -b agent/f9-stage-rename/2b-scripts/$(date +%Y%m%d-%H%M)
source ../../../.venv/bin/activate

pytest tests -q 2>&1 | tail -3   # baseline

# Tier A → B → C (pytest entre)

pre-commit run --all-files
pytest tests -q
pytest backend/tests -q

git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest tests -q
git push origin HEAD:main
```

## Critérios de aceite

- [ ] `grep -rn '"E[0-9]' scripts/ | grep -v e_reset.py` retorna apenas:
  (a) literais não-stage (códigos de banco que coincidem? confirme caso a caso),
  (b) comentários/docstrings explicitando legacy.
- [ ] `pytest tests -q` (1458+) verde.
- [ ] `pre-commit run --all-files` verde.

## Anti-padrões

- ❌ Tocar `scripts/e_reset.py` (vai em F9.2c).
- ❌ Renomear `scripts/e*.py` (F9.4).
- ❌ Misturar com refactor de lógica.

## Referências

- [F9.2a pipeline core](f9-2a-pipeline-core-strings.md)
- [F9.2c e_reset CLI](f9-2c-e-reset-deprecation.md)
- [F9.2d backend + tests](f9-2d-backend-tests.md)
- [F9.2e closeout](f9-2e-closeout.md)
