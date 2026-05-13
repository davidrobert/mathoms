---
id: ADR-202
type: adr
title: "Output schema + invariantes do parecer — `parecer_planejador.schema.json`"
status: Proposto
phase: "Ato 1 — fundação arquitetural do PLANNER_REVIEW"
date: "2026-05-13"
relates_to:
  - "[[ADR-026]]"
  - "[[ADR-090]]"
  - "[[ADR-153]]"
  - "[[ADR-199]]"
  - "[[ADR-200]]"
  - "[[ADR-201]]"
  - "[[ADR-203]]"
  - "[[ADR-206]]"
  - "[[ADR-207]]"
  - "[[ADR-208]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 202"
  - "Parecer output schema"
  - "Parecer invariantes"
tags:
  - area/llm
  - area/pipeline
  - area/report
  - phase/a11
  - status/proposto
  - type/adr
---

# ADR-202 — Output schema + invariantes do parecer — `parecer_planejador.schema.json`

**Status:** Proposto (Ato 1 — fundação arquitetural do PLANNER_REVIEW) • **Data:** 2026-05-13

## Contexto

- O parecer é consumido por (a) renderer React em `S_parecer`, (b) emissor de `Suggestion` aggregate ([[ADR-153]]), (c) exportador PDF, (d) consumidor de telemetria ([[ADR-206]]), (e) endpoint HTTP retornando DTO tipado. Sem schema canônico, cada consumer infere shape — recipe para drift catastrófico em produto pago.
- [[ADR-026]] estabelece **Instructor + Pydantic** como padrão para LLM structured output. Schema JSON é a fonte; Pydantic é codegen ou hand-crafted espelhando schema.
- Plano canônico `docs/plan/PLANNER_REVIEW/_README.md` enumera invariantes obrigatórias: 6+ sections, enums fechados, max 2 P0, regex anti-ticker, hard caps (D-0.2). Sem invariantes codificadas, LLM produz outputs visualmente plausíveis mas inválidos para downstream (ex.: 5 P0 → quebra UI; ticker `MGLU3` no body → quebra sigilo metodológico).

## Alternativas consideradas

1. **String livre + parsing post-hoc.** Pró: zero schema, prompt flexível. Contra: parsing brittle, drift garantido, downstream consumers brittle. **Rejeitada** — anti-padrão crítico de LLM em produção ([[ADR-026]] já fechou essa porta).
2. **Schema mínimo + validação lenient** (campos opcionais, sem caps, sem enums fechados). Pró: prompt simples. Contra: cada LLM-call produz shape diferente; UI defensiva por todo lado; sem proteção contra hallucination grosseira. **Rejeitada** — fail-fast em boundary (CLAUDE.md §Erros).
3. **Schema canônico + invariantes em Pydantic validators** (caps, enums, regex). Pró: fail-fast no boundary; UI confia; downstream consumers tipados; cap de P0 evita LLM "produzir muito" (sintoma de baixa confiança); regex anti-ticker enforça sigilo metodológico. Contra: schema longo + validator code não-trivial. **Aceita** — investimento que paga em todos os Atos 4-6.
4. **Schema canônico mas invariantes só no Python (não no JSON Schema).** Pró: JSON Schema simples; lógica complexa no Pydantic. Contra: JSON Schema vira inútil para validação externa (e.g., consumers Go futuros, frontend que valida payload). **Rejeitada parcialmente** — invariantes simples (enum, max items) viram JSON Schema; invariantes complexas (max 2 P0 dentro de array de sugestões, regex no body de strings específicas) viram Pydantic validators.

## Decisão

Adotar **schema JSON canônico** em `config/schemas/parecer_planejador.schema.json` (Draft-7) + **Pydantic model** codegen-equivalente em `pipeline/llm/schemas/parecer_planejador.py`.

### D1. Schema versionado

- `$id: "https://mathoms.ai/schemas/parecer_planejador.schema.json"`.
- `$comment: "schema_version: 1"` — bump na mudança breaking.
- `schema_version` persiste no aggregate `PlannerReview` ([[ADR-199]]) `_meta` — auditoria.

### D2. Estrutura do output (6+ sections obrigatórias)

```jsonc
{
  "schema_version": 1,
  "diagnostico": "Texto curto (≤500 chars) — diagnóstico geral",
  "pontos_fortes": [/* 3-5 items */],
  "riscos": [/* ≤ 12 items, ordenados por severidade */],
  "sugestoes_execucao": [/* ≤ 5 items, horizonte 4 semanas */],
  "sugestoes_tatico":   [/* ≤ 5 items, horizonte 3-12 meses */],
  "sugestoes_estrategico": [/* ≤ 5 items, horizonte 12+ meses */],
  "metricas": [/* ≤ 10 items, KPIs-alvo */],
  "notas_metodologicas": [/* notas breves, sigilo §13 enforça */],
  "campos_faltantes_pediria_se_iterasse": [/* JSONPath strings, telemetria M4 ADR-206 */],
  "_meta": {
    "persona_hash": "...",
    "manifest_version": 1,
    "schema_version": 1,
    "model_id": "claude-sonnet-4.5",
    "tool_trace": [/* drill-down audit, ADR-203 */]
  }
}
```

### D3. Enums fechados

- **Severidade (riscos):** `Crítica | Alta | Média | Baixa` (ordem decrescente).
- **Prioridade (sugestões):** `P0 | P1 | P2`. **Invariante:** count(P0) ≤ 2 no total agregado dos 3 horizontes. Violação → output rejeitado (status `needs_review`).
- **Confiança (por sugestão e por risco):** `alta | média | baixa`. Campo `impacto_estimado` (BRL ou pct) só permitido se `confianca == "alta"` ([[ADR-208]] gating — feature competitiva vs Pierre Finance).
- **`ancora_metodologica` (enum interno):** `perini | cerbasi | auvp | convergencia`. Cada sugestão e cada risco carrega uma. **Não exibido na UI** — mapeado para `tema_canonico` pelo frontend ([[ADR-207]]).
- **`tema_canonico` (enum user-facing, derivado do mapping ADR-207):** `Proteção | Alocação | Renda passiva | Liquidez | Custo tributário | Saúde de balanço | Diagnóstico de dados | Equilíbrio presente-futuro | Convergência metodológica` (9 valores fechados).

### D4. Regex anti-ticker no body textual

Strings em `diagnostico`, `pontos_fortes[].descricao`, `riscos[].descricao`, `sugestoes_*[].acao`, `notas_metodologicas[]` **rejeitam** regex:

```
/[A-Z]{4}\d{1,2}|[A-Z]{4}11/
```

(Padrão de ticker brasileiro: 4 letras + 1-2 dígitos; FII termina em `11`.) Justificativa: o parecer é **orientativo metodológico**, nunca recomendação de ativo específico. Detecção → status `needs_review`, retry 1× com prompt reforçado; 2ª falha → artifact não-publicado + alerta operacional.

Validador em `pipeline/domain/services/parecer_generator.py` (não no JSON Schema — Draft-7 não suporta regex negativo sobre strings em arrays profundamente nested de forma confiável).

### D5. Hard caps (mitigação "parecer monstro")

Decididos no plano canônico D-0.2:
- `riscos`: max 12 items
- Soma `sugestoes_execucao + sugestoes_tatico + sugestoes_estrategico`: max 15 items (5/5/5 ideal; LLM pode emitir 4/5/6 — distribuição flexível dentro do cap total).
- `metricas`: max 10 items.

Mobile review no Ato 5 (`product-designer`) pode revisitar para 10/12/8 se overflow visual.

### D6. Campo `impacto_estimado` opcional (defesa competitiva vs Pierre)

Reentrada de scope no plano §Out-of-scope item 3.
- Schema: `impacto_estimado: { tipo: "brl_cents" | "pct", valor: integer | number, horizonte_meses: integer }`.
- Permitido **apenas** quando `confianca == "alta"` (validator).
- UI mostra com tooltip "Estimativa indicativa, não garantia".

### D7. Campo `campos_faltantes_pediria_se_iterasse[]` para telemetria M4

JSONPath strings indicando campos do E5 que o LLM gostaria de ter visto mas não estavam no exec context. Alimenta tabela `planner_field_requests` ([[ADR-206]]). Validador rejeita strings que não sejam JSONPath bem-formados (mesmo subset do manifest [[ADR-200]]).

### D8. Pydantic model em `pipeline/llm/schemas/parecer_planejador.py`

- Espelha o JSON Schema 1-para-1.
- Validators custom (Pydantic v2 `@field_validator` / `@model_validator`):
  - `validate_p0_cap` (model-level): count P0 ≤ 2 em union dos horizontes.
  - `validate_anti_ticker_body` (field-level em strings de body): rejeita regex.
  - `validate_impacto_requires_alta_confianca`.
  - `validate_campos_faltantes_jsonpath_format`.
- Instructor injeta automaticamente nas chamadas LLM via [[ADR-026]] pattern.

### D9. Falha de validação → `status="needs_review"`

- 1 retry com prompt reforçado citando o motivo da falha (ex.: "Sua resposta anterior teve 4 sugestões P0; o limite é 2. Reordene.").
- 2ª falha → artifact escrito com `status=needs_review`, **não exposto** no relatório, alerta operacional via logger `mathoms.pipeline.parecer_planejador`.
- Métricas Prometheus: `planner_review_validation_failure_total{reason="p0_cap|anti_ticker|impacto_low_confidence|..."}`.

## Consequências

**Positivas:**
- Fail-fast no boundary: invalid LLM output **nunca** chega ao usuário.
- UI confiável: renderer assume invariantes verdadeiras (count P0 ≤ 2, enums fechados, sem ticker).
- Sigilo §13 ([[ADR-207]]) tem defesa em profundidade: persona ([[ADR-201]]) é primeira; regex no schema é segunda; CI `check_sigilo_terms.py` é terceira.
- Schema versionado permite evolução controlada (bump = nova ADR breaking).
- Telemetria M4 ([[ADR-206]]) tem contrato explícito.

**Negativas / trade-offs aceitos:**
- Schema longo (~300 linhas JSON). Aceito; comparável a `e5_analysis.schema.json`.
- LLM pode hit `needs_review` em primeiras execuções com persona em tunning — taxa esperada cai com refinement. Mitigação: logging detalhado de causa de falha permite tunar persona/manifest sem mudar schema.
- Hard caps são opinativos — `product-designer` mobile review pode revisar para baixo. Aceito; bump de `schema_version` se mudar.

**Riscos mitigados:**
- **Parecer monstro (PD23):** hard caps no schema.
- **Sigilo vazando via ticker em body:** regex defesa.
- **Hallucination de impacto estimado:** gate `confianca == "alta"`.
- **Drift schema ↔ consumer:** schema versionado + Pydantic codegen no mesmo PR.

## Implementação

- **Track(s) do plano:** T-06 (`planner-schema-output`).
- **Files touched (Ato 2):**
  - `config/schemas/parecer_planejador.schema.json` — schema canônico
  - `pipeline/llm/schemas/parecer_planejador.py` — Pydantic model + validators
  - `backend/app/api/dto/planner_review.py` — DTO HTTP espelhando schema (futuro Ato 3)
- **Critério de aceite:**
  - Schema valida fixture sintética válida (passa) e fixtures violando cada invariante (rejeitam com mensagem clara).
  - Pydantic model importa sem erro; validators dispatchados em ordem correta.
  - `make update-openapi-snapshot` reflete DTO no futuro Ato 3.
- **Gates CI:** `validate-schemas` (Draft-7), `pytest pipeline/llm/schemas/tests/`, OpenAPI snapshot (no Ato 3).

**Decisão pendente para outros especialistas:**
- **Caps definitivos** (12/15/10 vs 10/12/8) — `product-designer` mobile review no Ato 5.
- **Texto exato dos enums `tema_canonico`** — `financial-planner` valida em [[ADR-207]] co-design.
- **Pricing/tier do `impacto_estimado`** — `gtm-strategist` em [[ADR-208]] (gating freemium).
