---
id: ADR-200
type: adr
title: "Manifest declarativo F5 do exec context — `config/prompts/parecer_planejador.yaml`"
status: Proposto
phase: "Ato 1 — fundação arquitetural do PLANNER_REVIEW"
date: "2026-05-13"
relates_to:
  - "[[ADR-076]]"
  - "[[ADR-144]]"
  - "[[ADR-188]]"
  - "[[ADR-199]]"
  - "[[ADR-201]]"
  - "[[ADR-202]]"
  - "[[ADR-203]]"
  - "[[ADR-206]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 200"
  - "Manifest parecer planejador"
  - "Exec context DSL"
tags:
  - area/llm
  - area/pipeline
  - area/methodology
  - phase/a11
  - status/proposto
  - type/adr
---

# ADR-200 — Manifest declarativo F5 do exec context — `config/prompts/parecer_planejador.yaml`

**Status:** Proposto (Ato 1 — fundação arquitetural do PLANNER_REVIEW) • **Data:** 2026-05-13

## Contexto

- O parecer LLM consome **subset filtrado e formatado** do snapshot E5 (`analise_financeira-5_analysis.json`) como exec context. Sem um contrato declarativo, esse subset vive embutido no código Python do orchestrator: cada novo campo do E5 que vira input do parecer requer alteração de código (push de string, format hint, branch `if`).
- Pattern de manifest YAML já existe em produção: `config/prompts/section_summaries.yaml` ([[ADR-144]]). Espelhar esse pattern é o caminho de menor surpresa.
- Plano canônico: `docs/plan/PLANNER_REVIEW/_README.md` §"Ato 2" especifica `config/prompts/parecer_planejador.yaml` como **single-source-of-truth do exec context**, separado da persona (rules-as-code, [[ADR-201]]) e do output schema ([[ADR-202]]).
- Sem coverage gate, manifest e E5 schema podem drift silenciosamente: campo novo no E5 viaja pro LLM sem CI gate; campo removido do E5 ainda referenciado no manifest produz `null` no prompt → hallucination. [[ADR-188]] (learning loop) é precedente de "telemetria de drift como signal de evolução".

## Alternativas consideradas

1. **F2 — estender `config/report_layout.yaml`** com bloco `planner_context:` por seção. Pró: reuso do codegen ([[ADR-076]]); um único YAML para layout + prompt. Contra: viola Single Responsibility — `report_layout.yaml` descreve renderização visual, não consumo LLM; codegen `dev/codegen_report_layout.py` ganharia complexidade que não pertence a ele; mudança no manifest do parecer requereria re-codegen do frontend (acoplamento espúrio). **Rejeitada.**
2. **F6 — pollute `e5_analysis.schema.json` com flags** `x-planner-include: true` por campo. Pró: schema único; coverage trivial. Contra: schema vira documento misto (validação de dado + intenção de consumo LLM); E5 schema é consumido por backend/frontend/tests, todos teriam que ignorar campos `x-planner-*`; learning loop ([[ADR-188]]) ficaria menos legível. **Rejeitada.**
3. **F4 — hardcode no Python** (`backend/app/services/parecer_orchestrator.py` constrói exec context inline). Pró: zero arquivo de config novo. Contra: cada evolução do parecer = mudança de código; impossível auditar drift via diff de YAML; tunning editorial (`product-manager`) depende de PR no backend. **Rejeitada.**
4. **F5 — manifest YAML dedicado em `config/prompts/parecer_planejador.yaml`.** Pró: separation of concerns DDD; espelha pattern [[ADR-144]]; tunning editorial sem mudança de código; coverage gate trivial via parser de YAML; future-proof para extensão (multi-persona, A/B test de manifest). Contra: arquivo novo de config; um YAML a mais para o agente entender. **Aceita** (custo é o do CLAUDE.md §"Convenções intencionais" — YAML aceito quando justificado por comentários inline + tunning editorial).

## Decisão

Adotar **F5 — manifest declarativo dedicado** em `config/prompts/parecer_planejador.yaml`, com DSL própria, validado por JSON Schema próprio, gateado em CI.

### D1. DSL — JSONPath subset + format hints + null/empty/missing policies

```yaml
# config/prompts/parecer_planejador.yaml (esqueleto)
manifest_version: 1
schema_version: 1
description: "Exec context declarativo para o parecer do planejador (E6)."

sections:
  - key: kpis_macro
    title: "KPIs macro do mês"
    sources:
      - path: "$.kpis.patrimonio_total_brl_cents"
        as: patrimonio_total
        format: brl
        on_null: skip          # skip | placeholder | error
      - path: "$.kpis.rentabilidade_pct"
        as: rentabilidade
        format: pct             # pct | percent2 | brl | int | string
        on_missing: error       # campo deve existir no schema E5
      - path: "$.kpis.indice_financeiro"
        as: indice_financeiro
        format: int
        on_empty: skip          # null OU 0 OU [] → skip
```

**Subset JSONPath suportado** (não JSONPath completo):
- `$.field`, `$.nested.field`, `$.array[*].field` — paths estáticos, sem predicates.
- **Proibidos:** `$..*`, `$..[?(...)]`, filtros, regex em path. Rejeitados pelo parser; falha de schema → CI vermelho.
- Whitelist derivada do schema E5: parser cruza com `e5_analysis.schema.json` no `dev/check_planner_manifest_coverage.py`.

**Format hints** (canônicos, fechados):
- `brl` — valor em cents → `R$ 1.234,56` (usa `Money.brl` formatter, [[ADR-090]]).
- `pct` — fracional (0.447 → "44,7%") OU absoluto (44.7 → "44,7%") dependendo do schema E5 PR-2 normalizar.
- `percent2` — duas casas decimais.
- `int` — inteiro formatado pt-BR (`1.234`).
- `string` — passthrough.

**Null/empty/missing policies:**
- `on_null: skip|placeholder|error` — comportamento quando valor é `null`. Default: `skip` (campo não entra no exec context).
- `on_empty: skip|placeholder|error` — comportamento quando valor é `0`, `""`, `[]`. Default: `placeholder` (`"—"`).
- `on_missing: error|skip` — campo ausente no JSON. Default: `error` (drift catastrófico, CI deve pegar antes).

### D2. Schema próprio em `docs/_schemas/note-planner.schema.json`

Schema JSON Draft-7 valida shape do manifest (sections obrigatórias, paths bem-formados, format hints ∈ enum fechado). Hook pre-commit `validate-planner-manifest` roda em `config/prompts/parecer_planejador.yaml`. Drift de DSL → CI vermelho.

### D3. Coverage gate em CI — `dev/check_planner_manifest_coverage.py`

Script cruza 3 fontes (M1 da defesa em profundidade contra drift, complementa M4 de [[ADR-206]]):

1. **Manifest ↔ E5 schema:** todo `$.path` no manifest existe em `config/schemas/e5_analysis.schema.json`. Path ausente → erro.
2. **Manifest ↔ `report_layout.yaml`:** `section.key` no manifest **deve** ter contrapartida em `report_layout.yaml` (ou ser explicitamente `x-planner-internal: true` para sections que existem só no parecer, ex.: `dependentes_irpf`).
3. **Snapshot diff E5 schema:** se E5 schema mudou no mesmo PR (diff de `config/schemas/e5_analysis.schema.json`) e `parecer_planejador.yaml` **não** mudou, dispara **warning** (não erro — campo novo pode não ser relevante ao parecer; mas dev é forçado a justificar).

Roda em pre-commit + CI. Fail rápido no plano canônico §"Ato 2 critério de aceite".

### D4. Versionamento

- `manifest_version` no topo do YAML. Bump na mudança breaking (DSL alterada, formato de output mudou).
- `schema_version` ortogonal (versão do `note-planner.schema.json`).
- `manifest_version` é registrada no aggregate `PlannerReview` ([[ADR-199]]) — auditoria: "este parecer foi gerado sob manifest v3".
- Cache Redis ([[ADR-144]] pattern) tem `manifest_version` na chave: bump = invalidação automática.

### D5. Separation of concerns — manifest ≠ persona ≠ schema

- **Manifest ([[ADR-200]]):** **o quê** o LLM lê do E5 e como formata. Plumbing pura.
- **Persona ([[ADR-201]]):** **como** o LLM raciocina (metodologia, tom, postura fiduciária). Rules-as-code.
- **Output schema ([[ADR-202]]):** **o quê** o LLM escreve (Pydantic-validated). Contrato com downstream.
- **Tools ([[ADR-203]]):** **o quê** o LLM pode pedir além do exec context inicial. Drill-down.

Mistura desses 4 = "manifest vazando pra persona" (CTO-G2 no plano canônico). Cada ADR tem responsabilidade única.

## Consequências

**Positivas:**
- Tunning do exec context sem mudança de código Python (PR docs-only de `product-manager` ou `financial-planner` é suficiente).
- Drift E5 ↔ parecer detectado em CI (M1) antes do PR mergear.
- Pattern reusável: outras stages LLM futuras (executive summary, peer comparison) usam mesmo manifest pattern.
- Auditoria explícita: `PlannerReview.manifest_version` rastreia versão exata que produziu o output.

**Negativas / trade-offs aceitos:**
- Mais um arquivo de config no repo. CLAUDE.md já aceita YAML quando justificado (precedente: `report_layout.yaml`, `section_summaries.yaml`).
- Parser custom de JSONPath subset (~80 linhas) em `pipeline/llm/manifest_loader.py` (futuro Ato 2) — não usar `jsonpath_ng` (overkill + introduz path features que queremos proibir).
- DSL fechada: campo novo no E5 que precisa de format hint **não previsto** exige bump de `manifest_version` + ADR breaking. Aceito — drift silencioso é pior que ADR explícita.

**Riscos mitigados:**
- **Drift E5 ↔ parecer silencioso:** coverage gate M1.
- **Manifest vazando pra persona (CTO-G2):** ADR explicitamente segrega — persona não fala de paths, manifest não fala de metodologia.
- **Hallucination numérica por unidade ambígua:** format hints fechados + PR-2 normalizando E5 pct.

## Implementação

- **Track(s) do plano:** T-07 (`planner-manifest-yaml`) + T-09 (`planner-manifest-coverage-gate`).
- **Files touched (Ato 2):**
  - `config/prompts/parecer_planejador.yaml` — manifest
  - `docs/_schemas/note-planner.schema.json` — schema validator
  - `dev/check_planner_manifest_coverage.py` — coverage gate
  - `pipeline/llm/manifest_loader.py` — parser DSL (futuro)
- **Critério de aceite:**
  - Manifest cobre 100% dos campos do E5 que entram no exec context da V1.
  - `dev/check_planner_manifest_coverage.py` verde em pre-commit.
  - JSON Schema valida shape (DSL fechada).
- **Gates CI:** `validate-planner-manifest` (frontmatter check), `planner-manifest-coverage` (cross-ref).

**Decisão pendente para outros especialistas:**
- **Conteúdo concreto do manifest V1** (quais campos do E5 entram, em que ordem) — `data-engineer` co-design no Ato 2, baseado em protótipos V1/V2 em `_scratch/planner_parecer_campos*.md`.
- **PR-2 normalização de unidades pct E5** — bloqueador documentado no plano §Pré-requisitos.
