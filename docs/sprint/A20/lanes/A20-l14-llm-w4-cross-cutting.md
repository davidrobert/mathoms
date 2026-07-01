---
id: A20.l14
type: lane
title: "LLM Hardening — W4 cross-cutting (InstitutionCatalogProvider + RFB YAML)"
sprint: A20
plan: PLAN-llm-prompts-hardening
status: planned
priority: P1
branch_slug: a20-l14-llm-w4-cross-cutting
depends_on:
  - "[[A17.l5]]"
  - "[[A20.l15]]"
  - "[[A20.l11]]"
parallel_with:
  - "[[A20.l12]]"
  - "[[A20.l13]]"
adrs:
  - "[[ADR-137]]"
  - "[[ADR-157]]"
tags:
  - type/lane
  - sprint/a20
  - status/planned
  - priority/p1
  - area/llm
  - area/pipeline
---

# A20.L14 — W4 cross-cutting (2 PRs)

> **Onda 4 do plano [[PLAN-llm-prompts-hardening]].** Elimina drift entre system prompt e catálogos externos:
> 1. Listas de bancos/seguradoras saem do system prompt e entram via injection do `institution_catalog` ([[ADR-137]]).
> 2. Códigos RFB do `e16_irpf_full` migram para `config/prompts/e16_codigos_rfb_<ano_base>.yaml` versionado anualmente.

## Objetivo

Hoje, listas de bancos hardcoded em 3 prompts (`e1_members`, `e2_llm`, `apolice`) drift com `institution_catalog` (DB, [[ADR-137]]) — adicionar banco novo no DB exige bump de prompt. Mesma classe de problema com códigos RFB do IRPF em `e16_irpf_full.py` que mudam anualmente.

Solução: injetar catálogos via **user prompt**, não system prompt — mantém prompt curto e elimina bumps por motivo de dados.

## Critério de aceite (gate binário falsifiável)

- `grep -rn "itau\|santander\|bradesco" pipeline/llm/prompts/` retorna 0 ocorrências de listas hardcoded.
- `institution_catalog` cobre ≥30 entries categorizadas (15 pós-[[A17.l5]] + base inicial).
- Atualização anual RFB possível **sem** PR de prompt (apenas edit YAML + bump YAML version).
- `pytest tests -q -k "institution_provider or rfb_codes"` verde.
- Lane `a21-rfb-codes-annual-update` reservada para fevereiro/cada ano.

## Sub-tarefas (2 PRs paralelos)

### W4-T01 — `InstitutionCatalogProvider` protocol injetado (~1d)

Protocol em `pipeline/llm/institution_provider.py`:

```python
from typing import Protocol

class InstitutionCatalogProvider(Protocol):
    def list_codes(self, category: str | None = None) -> list[str]:
        """Retorna lista de códigos canônicos (não ORM)."""
        ...
```

Retorna `list[str]` (códigos), não `InstitutionCatalog` ORM — evita circular import e isola boundary (`pipeline/` não importa `backend.app`).

Implementação concreta em `backend/app/services/institution_catalog_provider.py` injetada pelo orchestrator que consome o pipeline:

```python
class DbInstitutionCatalogProvider:
    def __init__(self, db: Session): self.db = db
    def list_codes(self, category=None) -> list[str]:
        stmt = select(InstitutionCatalog.code)
        if category:
            stmt = stmt.where(InstitutionCatalog.category == category)
        return [r[0] for r in self.db.execute(stmt).all()]
```

Mudanças nos 3 prompts (`e1_members`, `e2_llm`, `apolice`):

- Remover lista hardcoded do system prompt (`"itau, santander, ..."`).
- User prompt recebe `available_institutions: list[str]` populado pelo orchestrator.
- System prompt referencia: `"use SOMENTE códigos da lista available_institutions injetada no prompt do usuário"`.
- Bump dos 3 prompts (minor — comportamento mantém).
- Atualizar goldens com `available_institutions` populado (deterministic baseline).

### W4-T02 — Códigos RFB para YAML versionado por ano-base (~1d)

Estrutura `config/prompts/e16_codigos_rfb_<ano_base>.yaml`:

```yaml
ano_base: 2024
codigos_bens:
  "01": "Imóveis - Prédio residencial"
  "02": "Imóveis - Prédio comercial"
  # ...
codigos_rendimentos_isentos:
  "06": "Bolsa estudos pesquisa"
  "12": "Rendimento sócio/titular cota empresarial"
  # ...
codigos_rendimentos_exclusivos:
  # ...
codigos_pagamentos:
  # ...
```

Entregas:

- JSON Schema validador em `config/schemas/e16_codigos_rfb.schema.json`.
- Loader `pipeline/llm/rfb_codes_loader.py` resolve por `ano_base` do documento.
- System prompt `e16_irpf_full.py` referencia: `"use tabela RFB injetada no user prompt"` em vez da tabela inline.
- **Runbook anual** em `docs/reference/runbooks/rfb_codes_annual_update.md`:
  - Fonte oficial: Manual de Preenchimento DIRPF (PDF anual RFB, fevereiro/cada ano).
  - Fluxo de extração manual (PDF → YAML).
  - Validação contra golden fixture de declaração do ano-base.
- Atualização anual RFB = edit YAML + bump YAML version (não `PROMPT_VERSION` — prompt em si não muda).

## Coordenação

**Depende de**:
- [[A17.l5]] (W4-T00 — seed expandido `institution_catalog` com 15+ entries alta renda PJ).
- [[A20.l15]] (W1α — prompts bumpados para semver puro pós-LGPD).
- [[A20.l11]] (W1β — `e15_baseline` em `Decimal` ADR-090).

**Paralelo a**: [[A20.l12]] (W2) e [[A20.l13]] (W3) — não competem por arquivos.

## Detalhe operacional

Plano canônico: [[PLAN-llm-prompts-hardening]] §W4. ADRs canônicas: [[ADR-137]] (`institution_catalog`) + [[ADR-157]] (IRPF E1.6 ADR-090 sub-decisão).

**Capacity estimada**: ~2d eng-time.
