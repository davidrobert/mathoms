---
id: ADR-088
type: adr
title: "StageConfig: configuração imutável por parâmetro"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 088"]
tags:
  - area/backend
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 54
---

# ADR-088 — StageConfig: configuração imutável por parâmetro

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 1.5.5

**Contexto:** `scripts/pipeline_common._init_config(base_dir)` reescrevia 12+
variáveis globais a cada reinicialização. Celery com processos separados é
seguro hoje, mas é uma bomba-relógio para qualquer mudança de topologia de
workers (multi-thread, async). Além disso, `from_context` silenciava
config faltante (`or {}` silenciava bugs de deploy).

**Decisão:** `pipeline/stage_config.py` com Pydantic `BaseModel` +
`ConfigDict(frozen=True)`:

```python
class StageConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    family_members: dict = {}
    pipeline: dict = {}
    institutions: dict = {}
    categorization: dict = {}
    goals: dict = {}
    scoring: dict = {}
    fiscal: dict = {}

    REQUIRED = frozenset({"family_members", "pipeline", "institutions", "categorization"})
```

- Pydantic frozen **deep-copia** na construção — imutabilidade verdadeira
  mesmo com campos dict/list (dataclass frozen só proíbe reassignment).
- `from_context(ctx)` **falha rápido** com `ConfigError` quando um dos 4
  `REQUIRED` está ausente. Campos opcionais (`goals`, `scoring`, `fiscal`)
  degradam para `{}` silenciosamente.
- `empty()` é o factory para testes que não precisam de config real.
- Thread-safe por construção — pode ser compartilhada entre workers.

**Regra geral de imutabilidade no plano (R11):**

| Tipo de objeto | Padrão | Motivo |
|---------------|--------|--------|
| Campos primitivos (str, int, Decimal, date) | `@dataclass(frozen=True)` | Sem dep extra |
| Campos dict/list (StageConfig) | Pydantic frozen | Deep-copy real |
| Campos `list[ValueObject]` que mutam (BankStatement.transactions) | dataclass não-frozen com invariante | Mutação restrita |

**Consequências:**
- ✅ `_init_config()` global removível na Fase 9.6.
- ✅ Config ausente quebra deploy imediatamente em vez de produzir output
  silenciosamente degradado.
- ⚠️ Todos os stages recebem o `StageConfig` completo mesmo quando só usam
  um subset — ISP é aplicado nos **domain services** (ADR-089).

**Arquivos:** `pipeline/stage_config.py`,
`tests/unit/pipeline/test_stage_config.py`.
