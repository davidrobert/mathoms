---
id: ADR-137
type: adr
title: "Catalog + override resolver para `categorization` e `institutions`"
status: Decidido
phase: "Sprint A7"
date: "2026-04-26"
relates_to: ["[[ADR-097]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 137"]
tags:
  - type/adr
  - status/decidido
size_lines: 119
---

# ADR-137 — Catalog + override resolver para `categorization` e `institutions`

**Status:** Decidido (Sprint A7) • **Data:** 2026-04-26 • **Relaciona**
[ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy),
[ADR-101](#adr-101--princípios-r12-r17-dddsolid-no-backend-api-a6e),
[ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6),
[ADR-134](#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend).

**Contexto:** `config/categorization.json` mistura duas coisas no mesmo
schema:

1. **Taxonomia base do produto** (categorias, parent/child, keywords
   default) — versão evolui via ADR/seed (ex.: adicionar "Streaming" em
   2025 quando vira despesa relevante).
2. **Customização do cliente** (renomear "Mercado" para "Supermercado",
   adicionar keyword "Hortifruti", desabilitar "Veículos" se a família
   não tem carro).

Hoje, `categories` table guarda o estado merged por workspace. Update
do template (1) por dev → exige migration que sobrescreve customização
do workspace; ou customização do workspace (2) bloqueia update do
template. Drift garantido.

`config/institutions.json` é mais simples — catálogo de bancos
suportados. Cada workspace tem subset (via `BankAccount`), mas catálogo
em si é global.

Alternativas:

- **(a) Manter `categories` materializado por workspace.** Sem versão
  nem template. Custo: drift em todo update.
- **(b) Storage somente do template + computar overrides via diff.**
  Overrides ficam implícitos; histórico de "o que o usuário mudou" se
  perde.
- **(c) Tabela `category_templates` global + tabela
  `workspace_category_overrides` (entradas explícitas só onde diverge);
  resolver no read-path.** Storage mínimo, histórico explícito,
  template evolui sem invalidar overrides.

**Decisão:** Adotar (c) para `categorization`. Para `institutions`:
tabela global `institution_catalog` única (sem override por workspace
nesta lane — bancos do cliente já são `BankAccount` rows, não
customização do catálogo).

Schema:

```sql
category_templates (
  id UUID PK,
  key TEXT NOT NULL,              -- "alimentacao.restaurantes"
  parent_key TEXT NULL,
  label TEXT NOT NULL,
  default_keywords TEXT[] NOT NULL,
  sort_order INT NOT NULL,
  template_version INT NOT NULL,  -- v1, v2 quando templ-set evolui
  UNIQUE (key, template_version)
);

workspace_category_overrides (
  id UUID PK,
  workspace_id UUID FK NOT NULL,
  template_key TEXT NOT NULL,
  label_override TEXT NULL,
  keywords_override TEXT[] NULL,  -- NULL = usa default; [] = lista vazia
  disabled BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE (workspace_id, template_key)
);

institution_catalog (
  id UUID PK,
  code TEXT UNIQUE NOT NULL,      -- "itau", "c6bank"
  name TEXT NOT NULL,
  default_parser TEXT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'
);
```

Resolver (`backend/app/services/category_resolver.py`):

```python
def resolve_categories(workspace_id: UUID, db: Session) -> list[ResolvedCategory]:
    template = load_active_template(db)        # cached Redis
    overrides = repo.list_overrides(workspace_id, db)
    return [merge(t, overrides.get(t.key)) for t in template if not overrides.get(t.key, EMPTY).disabled]
```

Cache Redis com chave `categories:{workspace_id}:{template_version}`,
invalidado por evento `category_override.changed` ou pelo bump de
`template_version`. Sem `@lru_cache`.

Migration: backfill `category_templates` a partir do
`config/categorization.json` atual (template_version=1). Linhas
existentes em `categories` que diferem do template viram entradas em
`workspace_category_overrides`. Demais linhas viram derivadas no read.

API: endpoints existentes em `/v1/workspaces/{id}/categories` continuam
mesmo contrato (frontend não muda); rota write passa a criar/atualizar
`workspace_category_overrides`.

Regra rígida: **`category_templates.key` jamais é renomeado** após
publicado. Adicionar key nova OK; deprecate (flag em metadata) OK;
rename = breaking, exige nova `template_version` + migration de
overrides.

**Consequências:**
- ✅ Template evolui (add categoria) sem invalidar overrides.
- ✅ Override é explícito; UI mostra "padrão Mathoms" vs "modificado".
- ✅ Storage mínimo — workspace que não customiza nada tem zero rows
  em `workspace_category_overrides`.
- ⚠️ Read-path é resolver, não SELECT direto. Cache Redis é
  obrigatório em hot path (relatório lê 50+ vezes em E4/E5). Bench
  antes/depois mostra latência.
- ⚠️ Rename de template_key é proibido. Ergonomia de evolução exige
  disciplina; aceita-se.
- ❌ `institution_catalog` sem override por workspace impede cliente
  raro com banco fora do catálogo. Mitigação: cliente abre ticket,
  produto adiciona ao catálogo via seed/admin. Aceito como simplicidade.
