---
id: ADR-272
type: adr
title: "Razão estruturada de needs_review (ReviewReason tipado + tabela review_reasons consultável)"
status: Proposto
phase: A20.failure-diagnostics
date: "2026-05-30"
relates_to:
  - "[[ADR-097]]"
  - "[[ADR-110]]"
  - "[[ADR-165]]"
  - "[[ADR-172]]"
  - "[[ADR-273]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 272"
  - "needs_review razão estruturada"
  - "ReviewReason"
tags:
  - area/pipeline
  - area/backend
  - status/proposto
  - type/adr
---

# ADR-272 — Razão estruturada de `needs_review`

**Status:** Proposto (Sprint A20) • **Data:** 2026-05-30 • **Relaciona** [[ADR-097]] (warnings de domínio como dataclasses tipadas com `.format()` — padrão reaproveitado), [[ADR-165]] (`validation.issues` tipados), [[ADR-172]] (`failure_reason`), [[ADR-110]] (logging estruturado), [[ADR-273]] (logging estruturado do pipeline — par desta ADR no mesmo pacote)

> **Co-design.** Forma de schema/persistência revisada por `data-engineer` antes do PR. Boundary `pipeline/domain` ↔ adapter a revisar por `senior-cto` no PR de implementação.

## Contexto

As últimas ~5 correções de produção foram de **output errado silencioso**, não de crash: dedup de transação furando por sufixo PIX variante ([[ADR-255]]), consolidador tratando a mesma pessoa como dois membros por slug≠CPF ([[ADR-267]]), informe regressivo travando por validação de `data_adesao` inexistente ([[ADR-238]]). Em todos, o agente (humano ou LLM) que depura gasta tempo desproporcional porque o sinal de "precisa revisão" é **booleano puro**.

Estado atual:

1. `needs_review` é um `bool` em schemas de extração LLM (`backend/app/schemas/informe_base.py`, `crlv.py`, `apolice.py`…), disparado quando `confidence < 0.7` e também por lógica de stage para condições de domínio.
2. O "porquê" fica espalhado em três lugares não-consultáveis: texto do prompt, `validation.errors` (lista de strings legado) e `validation.issues` (dataclasses tipadas, [[ADR-165]]).
3. Persistência: `PipelineStageLog.output_summary` (JSON blob) e `StageReview.validation_issues` (JSON). Nenhum permite a query-mãe — *"dado workspace X, último run falho, devolva todas as razões com campo ofensor + agregado por código"* — sem scan + `json_extract` sem índice.

## Decisão

Promover `needs_review` de bool para uma **razão estruturada tipada**, com **uma fonte e duas projeções**.

### Fonte única — `ReviewReason` dataclass em `pipeline/domain/`

Frozen dataclass ao lado dos warnings [[ADR-097]] D1 (mesmo padrão `code`/`offending_value`/`expected`/`.format()`), serializada pelo adapter do backend (`pipeline/**` não importa sqlalchemy — boundary enforçado por `check_pipeline_boundaries.py`):

```
ReviewReason(
  code: ReviewReasonCode,   # enum Python estável
  stage: str,               # nome descritivo (ADR-093)
  artifact_key: str,
  document_id: str | None,
  offending_value: str,     # REDIGIDO no construtor
  expected: str,
  message: str,             # via .format(), só IDs/contadores/enums
)
```

`ReviewReasonCode` (enum Python): `low_confidence`, `validation_conflict`, `possible_duplicate`, `missing_required_field`, `sentinel_period`, `llm_fallback`, … Vocabulário versionado em `config/schemas/review_reason.schema.json` (`version: "1.0"`), validado em modo `warn` (default, [[ADR-212]] PR3a).

### Projeção 1 — tabela `review_reasons` (consultável)

Tabela nova, **não** JSON blob — consultabilidade indexada é o único motivo desta ADR:

| coluna | tipo | nota |
|--------|------|------|
| `id` | PK | |
| `workspace_id` | FK CASCADE, **index** | multi-tenant |
| `pipeline_run_id` | FK CASCADE, **index** | |
| `stage` | String(50) | descritivo (ADR-093) |
| `code` | **String** (não SQL Enum) | + enum Python no call-site |
| `artifact_key` | String | |
| `document_id` | FK nullable | |
| `offending_value` | Text **redigido** | |
| `expected` | Text | |
| `message` | Text | |
| `occurrence_count` | Integer | agregação (ver cap) |
| `created_at` | DateTime | |

Índice composto `(workspace_id, pipeline_run_id, code)`.

`code` é `String`, **não** `Enum` SQL: `ALTER TYPE ... ADD VALUE` é não-transacional e dói em rolling deploy; valor desconhecido quebraria run antigo. Code novo = membro no enum Python + entrada no JSON Schema. Sem migration.

### Projeção 2 — `StageReview.validation_issues`

Continua existindo como **snapshot denormalizado** para a UI de revisão humana, populado a partir das **mesmas** `ReviewReason`. Não é terceira fonte do "porquê": é projeção da fonte única. `validation.errors` (strings legado) fica deprecado em favor de `ReviewReason`.

### Cap de cardinalidade

Stage que seta `needs_review` por-linha (dedup em run com 800 transações duplicadas) **não** gera 800 rows. Cap por `(pipeline_run_id, code)` em **50 rows**; excedente vira `occurrence_count` agregado no último. Decisão enumeração-vs-agregação fixada no schema.

### Redação de PII — no construtor, não no call-site

`offending_value` **vai vazar** CPF / valor monetário real / descrição de transação se gravado cru — e entra em DB consultável + (via [[ADR-273]]) log. O construtor de `ReviewReason` redige (mascara CPF, trunca valor, hash de descrição) — **não confiar no call-site**. Sem isso a ADR é vetor de vazamento.

## Consequências

**Positivas:**
- A query-mãe vira `SELECT` indexado; "top 5 códigos do workspace nas últimas 4 semanas" é agregação trivial.
- Reaproveita padrão [[ADR-097]] D1 — onboarding zero para quem já escreve warnings.
- Fonte única elimina o espalhamento atual em 3 lugares.

**Negativas / trade-offs aceitos:**
- Migration `ADD TABLE` (barata, sem lock em tabela quente, sem backfill — runs antigos não têm reasons; valor é forward-looking).
- Custo de redação no construtor + teste de redação obrigatório.
- Cap de 50 perde detalhe fino em runs patológicos — aceito (o agregado preserva o sinal; o caso raro está nos logs [[ADR-273]]).

## Retenção

Atrelada ao ciclo de vida do `pipeline_run` (CASCADE) + purge de runs antigos. É diagnóstico, não dado de cliente nem audit regulatório — TTL mais curto que `pipeline_artifacts`, sem piso de retenção.

## Critério de aceite

1. Migration `ADD TABLE review_reasons` com índice composto; `EXPLAIN` da query-mãe usando o índice.
2. `config/schemas/review_reason.schema.json` versionado, validação `warn` no CI.
3. Todo ponto que seta `needs_review=true` anexa uma `ReviewReason`; gate detecta `needs_review=true` sem reason.
4. **Teste de redação:** fixture com CPF/valor sintético → assert que `offending_value` persistido está mascarado.
5. Cap por `(run, code)`: run com 800 dups → ≤50 rows + `occurrence_count` agregado.
6. `StageReview.validation_issues` populado a partir das mesmas `ReviewReason` (sem divergência).
7. Snapshot `DB_SCHEMA_REFERENCE.md` atualizado.

## Alternativas consideradas

- **Estender `output_summary` (JSON) ou `validation_issues` (JSON):** rejeitado — sem índice por `code`, query-mãe vira scan + `json_extract`, agregação por gambiarra. Mata o único motivo da ADR.
- **Coluna nova em `pipeline_stage_logs`:** rejeitado — cardinalidade N-por-stage não cabe em coluna escalar; relação 1:N pede tabela.
- **`Enum` SQL para `code`:** rejeitado — `ALTER TYPE` não-transacional em rolling deploy + quebra de run antigo com valor desconhecido.
- **Manter bool + texto livre (status quo):** rejeitado — é exatamente o que custou tempo nas 5 correções recentes.

## Próximos passos

- **PR1 (este escopo):** model + migration + `ReviewReason` em `pipeline/domain/` + adapter de serialização + schema + redação + gate "needs_review sem reason" + testes. Flippa para `Decidido (Sprint A20)` no merge.
- **PR2 (follow-up):** retrofit dos call-sites legados de `validation.errors` (strings) para `ReviewReason`.
- **PR3 (follow-up):** endpoint interno `ops.mathoms.ai` ([[ADR-116]]) que devolve o bundle de diagnóstico consolidado por run (par com [[ADR-273]]).
