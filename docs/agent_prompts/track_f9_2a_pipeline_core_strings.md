# Track F9.2a — Strings descritivas em `pipeline/` (resíduo)

> **Lane ID:** F9.2a
> **Branch prefix:** `agent/f9-stage-rename/2a-pipeline-core/*`
> **Depende de:** F9.2 T1 ✅ (já em `main`: commits `332c51e`, `9758e59`, `ffca1b9`)
> **Bloqueia:** F9.2b, F9.2d
> **Onda:** F9 (sub-fatia 3a/7) — resíduo da fatia "string literals"
> **Fonte de verdade:** [ADR-093](../DECISIONS.md#adr-093) · [`STAGE_RENAME_MAP`](../../pipeline/stage_spec.py#L54)

> **Objetivo:** trocar strings literais de stage legado (`"E3"`, `"E5"`, `"E2-llm"`,
> etc.) restantes na árvore `pipeline/` por equivalentes descritivos
> (`"reconcile_transactions"`, `"analyze_finances"`, `"extract_with_llm"`...).
> T1 já flipou `STAGE_REGISTRY`/`FULL_ORDER`/`DETERMINISTIC_ORDER`/`orchestrator.py`.
> Esta fatia cobre o resto: `artifact_store.py`, `llm/`, `stages/*`, `domain/services/*`,
> `context.py`, `__init__.py`.

---

## Estado atual (após T1 mergeado)

`pipeline/stage_spec.py` já expõe:
- `STAGE_REGISTRY` com keys descritivas
- `STAGE_RENAME_MAP` (legacy → descriptive) como compat reverso
- `LEGACY_TO_DESCRIPTIVE`, `DESCRIPTIVE_TO_LEGACY`
- `resolve_stage_name(name) -> str` (normaliza para descritivo)
- `to_legacy_stage_name(name) -> str` (inverso, p/ adapters DB durante janela F9.2→F9.3)

`pipeline/orchestrator.py` já usa `_get_stage_runner` em descritivo + `FROM_MAP` aceita ambos.

## Hotspots (≈150 hits)

```
38  pipeline/artifact_store.py       # _STAGE_TO_DIR + _STAGE_TO_SUFFIX
34  pipeline/llm/validators.py       # error msg prefixes "E1: ...", "E2-llm: ..."
15  pipeline/stages/extract_with_llm.py
13  pipeline/stages/extract_baseline.py
10  pipeline/stages/extract_members.py
 9  pipeline/domain/services/e5_analyzer_adapter.py
 8  pipeline/stages/review_finances.py
 8  pipeline/orchestrator.py         # mostly docstring examples
 7  pipeline/domain/services/e4_categorizer_adapter.py
 6  pipeline/stages/e7.py
 6  pipeline/domain/services/e3_reconciler_adapter.py
 5  pipeline/domain/services/__init__.py
 5  pipeline/context.py
 1  pipeline/llm/litellm_client.py
 1  pipeline/llm/schemas/{e1_members,e15_baseline,e2_llm_extract,e7_review}.py
 1  pipeline/domain/{models/document,services/baseline_normalizer,
                    services/e5_member_resolver,services/e5_serialization,
                    services/narrativas/__init__,services/narrativas/builder,
                    services/statement_preprocessor}.py
 1  pipeline/__init__.py
 1  pipeline/stages/extract_statements.py
 1  pipeline/stages/extract_invoices.py
 1  pipeline/stages/consolidate_baseline.py
 2  pipeline/stages/e2.py
```

## Estratégia

### Tier A — `pipeline/artifact_store.py` (commit isolado)

`_STAGE_TO_DIR` e `_STAGE_TO_SUFFIX` usam keys legadas (`"E1"`, `"E3"`, `"E5"`...).
Decisão: **flipar keys para descritivas** + manter aliases legados via dict update
para não quebrar callers que ainda passem `"E3"` direto:

```python
_STAGE_TO_DIR_DESCRIPTIVE: dict[str, str] = {
    "extract_members": "members",
    "consolidate_baseline": "E2_extracts",
    "extract_baseline": "E2_extracts",
    "extract_invoices": "E2_extracts",
    "extract_statements": "E2_extracts",
    "extract_with_llm": "E2_extracts",
    "reconcile_transactions": "E3_reconciled",
    "categorize_transactions": "E4_unified",
    "analyze_finances": "E5_analysis",
    "generate_narratives": "E5_analysis",
    "validate_cross": "E7_review",
    "review_finances": "E7_review",
    "apply_review": "E7_review",
}

_STAGE_TO_DIR: dict[str, str] = {
    **_STAGE_TO_DIR_DESCRIPTIVE,
    **{legacy: _STAGE_TO_DIR_DESCRIPTIVE[descriptive]
       for legacy, descriptive in STAGE_RENAME_MAP.items()
       if descriptive in _STAGE_TO_DIR_DESCRIPTIVE},
    # Aliases extras de família:
    "E2": "E2_extracts",
    "E7": "E7_review",
    "E1.5a": "E2_extracts",  # extrato per-IRPF
}
```

Mesmo padrão para `_STAGE_TO_SUFFIX`. Lookup interno passa por
`resolve_stage_name(stage)` antes de indexar — assim `store.read("E3", ...)`
e `store.read("reconcile_transactions", ...)` funcionam.

**Gate:** `pytest tests/unit/pipeline/test_artifact_stores.py -q` verde.
**Commit:** `refactor(pipeline): artifact_store keys descritivas + compat (F9.2a — Tier A)`

### Tier B — `pipeline/stages/*.py` strings internas (commit por arquivo ou agrupado)

Substituir literais `"E3"`, `"E5"`, etc. em:
- `extract_with_llm.py`, `extract_baseline.py`, `extract_members.py`,
  `review_finances.py`, `e7.py`, `extract_statements.py`, `extract_invoices.py`,
  `consolidate_baseline.py`, `e2.py` (shim — só strings, não tocar import path).

Uso típico: `store.write("E3", ...)` → `store.write("reconcile_transactions", ...)`,
ou logger.info(`"stage=E3"`) → `"stage=reconcile_transactions"`.

**Atenção:**
- `pipeline/stages/extract_baseline.py:61` tem `"source": "E1.5-llm"` — esse não está
  no `STAGE_RENAME_MAP` (é tag de origem, não stage id). Mantenha como está OU
  troque para `"source": "extract_baseline-llm"` se preferir consistência (decida
  por leitura do contexto local; default: manter).
- `pipeline/stages/e2.py` é shim de compat mantido até F9.6 — não toque o import path.

**Gate:** `pytest tests -q` (ou `pytest tests/unit/pipeline -q` + `pytest tests/test_orchestrator.py`) verde.
**Commit(s):** `refactor(pipeline): stages strings descritivas (F9.2a — Tier B)`

### Tier C — `pipeline/domain/services/*` + `pipeline/context.py` + `pipeline/__init__.py`

Mesma operação, escopo isolado:
- adapters (`e3_reconciler_adapter.py`, `e4_categorizer_adapter.py`,
  `e5_analyzer_adapter.py`)
- helpers (`baseline_normalizer.py`, `statement_preprocessor.py`,
  `e5_member_resolver.py`, `e5_serialization.py`)
- `narrativas/__init__.py`, `narrativas/builder.py`
- `models/document.py`, `services/__init__.py`
- `pipeline/context.py`, `pipeline/__init__.py`

**Gate:** `pytest tests -q` verde.
**Commit:** `refactor(pipeline): domain/services strings descritivas (F9.2a — Tier C)`

### Tier D — `pipeline/llm/*` (error messages + docstrings)

- `pipeline/llm/validators.py` — error msg prefixes (`r.error("E1: no members extracted")`).
  Trocar para `"extract_members: ..."` é consistente, mas verifique se algum teste
  faz assert sobre o prefixo exato. Se sim, atualize teste junto.
- `pipeline/llm/litellm_client.py:280` — docstring com exemplo de stage; troque para
  descritivo.
- `pipeline/llm/schemas/*.py` (e1, e15, e2_llm, e7_review) — primeira linha de
  docstring. Substituir referência ao nome legado pelo descritivo + nota
  parentética legacy.

**Gate:** `pytest tests -q` + `pytest backend/tests -q` verdes.
**Commit:** `refactor(pipeline-llm): validators + schemas strings descritivas (F9.2a — Tier D)`

### Tier E — `pipeline/orchestrator.py` docstring

Atualizar examples na docstring no topo do módulo:
```python
result = run_from(ctx, "reconcile_transactions")  # antes: "E3"
result = run_stages(ctx, ["analyze_finances", "generate_narratives"])  # antes: ["E5","E5.N"]
```

**Commit:** pode ir junto com Tier C ou ser commit isolado pequeno.

---

## Sequência de execução

```bash
git fetch origin && git status
git checkout -b agent/f9-stage-rename/2a-pipeline-core/$(date +%Y%m%d-%H%M)
source ../../../.venv/bin/activate

# Baseline
pytest tests -q 2>&1 | tail -3
pytest backend/tests -q 2>&1 | tail -3

# Tier A → B → C → D → E (commit + pytest entre cada)

# Gate final
pre-commit run --all-files
pytest tests -q
pytest backend/tests -q

# Drift check + push
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest tests -q
git push origin HEAD:main
```

## Critérios de aceite

- [ ] `grep -rn '"E[0-9]' pipeline/` retorna apenas:
  (a) `STAGE_RENAME_MAP` em `stage_spec.py`,
  (b) `LEGACY_FROM_ALIASES` (`"E0"`, `"E2"`, `"E7"` sem sufixo),
  (c) docstrings/comentários explicitando mapping legacy.
- [ ] `pytest tests -q` (1458+) verde.
- [ ] `pytest backend/tests -q` (1307+) verde.
- [ ] `pre-commit run --all-files` verde.
- [ ] BACKLOG não atualizado nesta fatia (closeout em F9.2e).

## Anti-padrões

- ❌ Tocar `pipeline/stages/e2.py` ou `pipeline/stages/e7.py` (shims) além de strings
  internas — esses arquivos morrem em F9.6.
- ❌ Renomear filenames `pipeline/stages/*.py` (já feito em F9.1).
- ❌ Modificar goldens (`tests/pipeline/goldens/`, `*_golden*.py`).
- ❌ Tocar DB rows ou Alembic (F9.3).
- ❌ Misturar com mudança de lógica.

## Referências

- [F9.2 prompt master](track_f9_2_string_literals.md)
- [F9.2b scripts](track_f9_2b_scripts_strings.md)
- [F9.2c e_reset CLI](track_f9_2c_e_reset_deprecation.md)
- [F9.2d backend + tests](track_f9_2d_backend_tests.md)
- [F9.2e closeout](track_f9_2e_closeout.md)
