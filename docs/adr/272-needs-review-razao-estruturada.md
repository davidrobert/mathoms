---
id: ADR-272
type: adr
title: "Razão estruturada de needs_review (ReviewReason tipado + tabela review_reasons consultável)"
status: Decidido
phase: A20.failure-diagnostics
date: "2026-05-30"
amended_at: ["2026-07-10"]
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
  - status/decidido
  - type/adr
---

# ADR-272 — Razão estruturada de `needs_review`

**Status:** Decidido (Sprint A20) • **Data:** 2026-05-30 • **Relaciona** [[ADR-097]] (warnings de domínio como dataclasses tipadas com `.format()` — padrão reaproveitado), [[ADR-165]] (`validation.issues` tipados), [[ADR-172]] (`failure_reason`), [[ADR-110]] (logging estruturado), [[ADR-273]] (logging estruturado do pipeline — par desta ADR no mesmo pacote)

> **Co-design (Fase 0 fechada 2026-05-30).** Forma de schema/persistência revisada por `data-engineer`; boundary `pipeline/domain` ↔ adapter e modelo de unificação revisados por `senior-cto`. Decisão de unificação **resolvida**: destino único (uma tabela, uma projeção) com produtores **desacoplados** via protocolo `ToReviewReason` (ver §"Unificação"). Plano operacional de implementação: [[TRACK-adr272-review-reasons]].

> **Escopo: pipeline/extração apenas.** Esta ADR cobre os `needs_review` setados em `pipeline/**` (extração LLM, stages, services de domínio). O mundo de **document-upload/classificação** (`backend/app/services/document_classification.py`, `document_upload_service.py`, `document_duplicates.py`, modelos `Document`/`Debt`) tem UX de revisão própria e **fica fora** — assim a garantia de completude (todo `needs_review` tem `ReviewReason`) é honesta e auditável por um gate de superfície fechada.

> **Emenda 2026-07-10 (A36.l3).** O mecanismo de pausa desta ADR passa a ser
> consumido pelo E7 (`validate_cross`): um check de **conservação** violado emite
> `validation.valid=False` e pausa o run como `needs_review`. Ver §Emenda ao final.

## Contexto

As últimas ~5 correções de produção foram de **output errado silencioso**, não de crash: dedup de transação furando por sufixo PIX variante ([[ADR-255]]), consolidador tratando a mesma pessoa como dois membros por slug≠CPF ([[ADR-267]]), informe regressivo travando por validação de `data_adesao` inexistente ([[ADR-238]]). Em todos, o agente (humano ou LLM) que depura gasta tempo desproporcional porque o sinal de "precisa revisão" é **booleano puro**.

Estado atual:

1. `needs_review` é um `bool` em schemas de extração LLM (`backend/app/schemas/informe_base.py`, `crlv.py`, `apolice.py`…), disparado quando `confidence < 0.7` e também por lógica de stage para condições de domínio.
2. O "porquê" fica espalhado em três lugares não-consultáveis: texto do prompt, `validation.errors` (lista de strings legado) e `validation.issues` (dataclasses tipadas, [[ADR-165]]).
3. Persistência: `PipelineStageLog.output_summary` (JSON blob) e `StageReview.validation_issues` (JSON). Nenhum permite a query-mãe — *"dado workspace X, último run falho, devolva todas as razões com campo ofensor + agregado por código"* — sem scan + `json_extract` sem índice.

## Decisão

Promover `needs_review` de bool para uma **razão estruturada tipada**, com **uma fonte e duas projeções**.

### Fonte única — `ReviewReason` dataclass em `pipeline/domain/review_reason.py`

Frozen dataclass ao lado dos warnings [[ADR-097]] D1 (mesmo padrão `code`/`offending_value`/`expected`/`.format()`), serializada pelo adapter do backend (`pipeline/**` não importa sqlalchemy — boundary enforçado por `check_pipeline_boundaries.py`):

```
ReviewReason(
  code: ReviewReasonCode,   # enum Python namespaced (ver abaixo)
  stage: str,               # nome descritivo (ADR-093)
  artifact_key: str,
  document_id: str | None,
  offending_value: str,     # REDIGIDO no __post_init__
  expected: str,
  message: str,             # via .format(), só IDs/contadores/enums
)
```

`ReviewReasonCode` (enum Python) é **hierárquico/namespaced** por origem, para que a query-mãe agregue por família sem regex no `code`: `extract.low_confidence`, `extract.llm_fallback`, `extract.missing_required_field`, `dedup.possible_duplicate`, `dedup.sentinel_period`, `domain.validation_conflict`, … Vocabulário versionado em `config/schemas/review_reason.schema.json` (`version: "1.0"`), validado em modo `warn` (default, [[ADR-212]] PR3a).

### Unificação — destino único, produtores desacoplados (`ToReviewReason`)

`ValidationIssue` ([[ADR-165]], conformidade de schema: `path`/`severity`/`context`) e os warnings de domínio ([[ADR-097]] D1) têm responsabilidades **genuinamente distintas** (SRP) — fundir os dois numa só dataclass seria acoplamento errado. O que se unifica é o **destino**: ambos projetam para `ReviewReason` via um protocolo fino:

```python
class ToReviewReason(Protocol):
    def to_review_reason(self, *, stage: str, artifact_key: str,
                         document_id: str | None) -> ReviewReason: ...
```

`ValidationIssue.to_review_reason()` mapeia `severity/path/context → code/offending_value/expected`; os warnings de domínio implementam o mesmo. O adapter de serialização (Fase 2) consome `list[ToReviewReason]` e materializa `list[ReviewReason]` — uma fonte de persistência, dois produtores que não se conhecem. Rejeitada a alternativa de "uma dataclass única" (acopla schema-conformity com regra de domínio).

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

### Redação de PII — no `__post_init__`, não no call-site

`offending_value` **vai vazar** CPF / valor monetário real / descrição de transação se gravado cru — e entra em DB consultável + (via [[ADR-273]]) log. O `__post_init__` de `ReviewReason` redige (mascara CPF, trunca valor, hash de descrição) — **não confiar no call-site**. Sem isso a ADR é vetor de vazamento.

**Cobertura obrigatória do `context` herdado.** Quando a `ReviewReason` nasce de uma `ValidationIssue` via `to_review_reason()`, o campo `context` da issue pode conter trecho de extrato (ex.: `context={"linha": "PIX João 1.234,56"}`). A projeção **não** copia `context` cru para `offending_value`/`message`; passa pela mesma redação. Util de redação compartilhado (`pipeline/domain/review_reason.py`), testado com fixture de CPF/valor **sintético** (gerador mod-11), nunca real. `message` só carrega IDs/contadores/enums — nenhum valor interpolado.

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
4. **Teste de redação:** fixture com CPF/valor **sintético** → assert que `offending_value` persistido está mascarado, **incluindo** quando a `ReviewReason` nasce de `ValidationIssue.to_review_reason()` com `context` contendo trecho de extrato.
4b. `ValidationIssue` e ≥1 warning de domínio implementam `to_review_reason()`; teste afirma que ambos produzem `ReviewReason` válida sem o adapter conhecer o tipo concreto.
5. Cap por `(run, code)`: run com 800 dups → ≤50 rows + `occurrence_count` agregado.
6. `StageReview.validation_issues` populado a partir das mesmas `ReviewReason` (sem divergência).
7. Snapshot `DB_SCHEMA_REFERENCE.md` atualizado.

## Alternativas consideradas

- **Estender `output_summary` (JSON) ou `validation_issues` (JSON):** rejeitado — sem índice por `code`, query-mãe vira scan + `json_extract`, agregação por gambiarra. Mata o único motivo da ADR.
- **Coluna nova em `pipeline_stage_logs`:** rejeitado — cardinalidade N-por-stage não cabe em coluna escalar; relação 1:N pede tabela.
- **`Enum` SQL para `code`:** rejeitado — `ALTER TYPE` não-transacional em rolling deploy + quebra de run antigo com valor desconhecido.
- **Manter bool + texto livre (status quo):** rejeitado — é exatamente o que custou tempo nas 5 correções recentes.
- **Fundir `ValidationIssue` + warning de domínio numa dataclass única:** rejeitado em Fase 0 (`senior-cto`) — acopla conformidade de schema com regra de domínio (viola SRP). Unifica-se o destino (`ReviewReason` + tabela), não o produtor; ponte é o protocolo `ToReviewReason`.

## Próximos passos

Plano operacional canônico em [[TRACK-adr272-review-reasons]]. Implementação em 4 fases verificáveis (cada uma um PR):

- **Fase 1 — fundação de dados:** `ReviewReason` + `ReviewReasonCode` + util de redação + `config/schemas/review_reason.schema.json` + model `ReviewReason` + migration `ADD TABLE` + testes (incl. redação). **Sem mudança em call-site** — só infraestrutura. Flippa esta ADR para `Decidido (Sprint A20)` no merge.
- **Fase 2 — seam de serialização:** `to_review_reason()` em `ValidationIssue` + warnings de domínio; `_record_stage_needs_review()` ([`pipeline_task.py`](../../backend/app/tasks/pipeline_task.py)) insere rows + popula `StageReview.validation_issues` da mesma fonte; teste de paridade.
- **Fase 3 — completude:** back-fill dos pontos `needs_review=true` da superfície pipeline/extração + gate `dev/check_needs_review_has_reason.py`.
- **PR follow-up:** endpoint interno `ops.mathoms.ai` ([[ADR-116]]) que devolve o bundle de diagnóstico consolidado por run (par com [[ADR-273]]).

## Emenda 2026-07-10 — gate de conservação do E7 consome o mecanismo (A36.l3)

**Contexto.** O E7 (`validate_cross`) rodava 14 checks de consistência sobre o E5 mas **sempre** retornava `success: True` sem emitir o bloco `validation` — então um plano com invariante de conservação violada era entregue ao cliente sem flag (achado DAT-01 da auditoria r4).

**Decisão.** `validate_cross.main_with_store` passa a emitir `validation: {"valid": ..., "errors": [...]}`. `_has_validation_errors` (já existente) dispara e o run pausa como `needs_review` — reusando este mecanismo, sem código novo no consumidor. `success` permanece `True` (rodou sem crashar; `valid=False` roteia para `needs_review`, não `failed_at_stage`).

**Gate por conjunto explícito, NÃO por `severity=="error"`.** O gate dispara em `_CONSERVATION_CHECKS = {CV1, CV2, CV3, CV6}` (checks numéricos), **não** na severidade genérica. Razão empírica (medição A36.l3 sobre 27 runs de dogfood): CV9/CV10 são `severity="error"` mas de **render** (narrativa/gráfico) e falham em run **incremental** ([[ADR-080]]) que reusa narrativa — gatilhar em `error` genérico pausaria 100% dos runs. Sob o conjunto de conservação a medição deu **0 pausas** (após o fix do CV6, que lia o campo morto `patrimonio.investivel` em vez de `investivel_efetivo`). CV9/CV10 e CV4 seguem **advisory** (fora do gate); render-gate dedicado fica como follow-up.

**Escopo.** Só a disposição do resultado + o conjunto de gate; não altera a lógica interna dos 14 checks. Cobertura: `tests/test_e7_conservation_gate.py` (conservação pausa; render não pausa; fluxo por `main_with_store`).
