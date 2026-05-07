---
id: ADR-087
type: adr
title: "StageSpec: dependências declarativas"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 087"]
tags:
  - area/llm
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 49
---

# ADR-087 — StageSpec: dependências declarativas

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 1.5

**Contexto:** `pipeline/orchestrator.py` mantinha `FROM_MAP` manualmente —
inserir um stage entre E3 e E4 exigia editar `FULL_ORDER`, `FROM_MAP`
(calculado à mão), `DETERMINISTIC_ORDER` e `_get_stage_runner()`, propenso a
erros silenciosos. Bug real: `E2-faturas` e `E2-extratos` mapeavam para o
mesmo `e2.run(ctx)` sem flags — ambos processavam tudo.

**Decisão:** `pipeline/stage_spec.py` com:

```python
@dataclass(frozen=True)
class StageSpec:
    name: str
    reads: tuple[str, ...]     # stages de input
    writes: tuple[str, ...]    # stages de output
    is_llm: bool = False
    tier: str = "free" | "premium"

STAGE_REGISTRY: dict[str, StageSpec] = { ... }  # Nomes legados nas Fases 1-8
VIRTUAL_ARTIFACT_STAGES = frozenset({"E5-revised"})  # não executáveis
FULL_ORDER = [...]                                   # decisão explícita do orquestrador
DETERMINISTIC_ORDER = [s for s in FULL_ORDER if not STAGE_REGISTRY[s].is_llm]
```

- `build_from_map(order)` deriva `FROM_MAP` sem manutenção manual.
- `validate_full_order(FULL_ORDER)` é chamado no import — falha rápido
  (`AssertionError`) se uma dependência é consumida antes de ser produzida.
- `validate_artifact_stage(stage)` aceita executável + virtual, rejeita
  desconhecido.
- `E2-faturas`/`E2-extratos` têm wrappers separados (`e2_faturas.py`/`e2_extratos.py`)
  que chamam `e2.run(ctx, faturas_only=True)` / `extratos_only=True`.

**Consequências:**
- ✅ Adicionar stage = uma linha no REGISTRY + uma posição no FULL_ORDER.
- ✅ Inconsistências de ordem são detectadas no startup, não em runtime.
- ✅ Três artifact stages distintos para E2 (`extract_statements`/`extract_invoices`/`extract_with_llm`)
  evitam colisão de `UNIQUE(run, stage, key)` quando o mesmo documento é
  processado por extrator determinístico + LLM fallback.
- ⚠️ Nomes legados `"E2"`, `"E3"`, `"E5"` permanecem até Fase 9 (renaming em
  bloco via `STAGE_RENAME_MAP`).

**Arquivos:** `pipeline/stage_spec.py`, `pipeline/orchestrator.py`,
`pipeline/stages/e2_faturas.py`, `pipeline/stages/e2_extratos.py`,
`tests/unit/pipeline/test_stage_spec.py`.
