---
id: ADR-165
type: adr
title: "`ValidationIssue` estruturado em `ValidationResult` e `StageReview`"
status: Decidido
date: "2026-05-06"
relates_to: ["[[ADR-097]]", "[[ADR-110]]", "[[ADR-143]]", "[[ADR-157]]", "[[ADR-158]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 165"]
tags:
  - type/adr
  - status/decidido
size_lines: 80
---

# ADR-165 — `ValidationIssue` estruturado em `ValidationResult` e `StageReview`

**Status:** Decidido • **Data:** 2026-05-06 • **Relaciona** [ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy) (D1 — warnings de domínio tipados), [ADR-110](#adr-110--structured-json-logging--opentelemetry-bootstrap-a6f3) (logging estruturado), [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76) (rules-as-code), [ADR-157](#adr-157--schema-irpf-completo-stage-extract_irpf_full) (gatilho concreto), [ADR-158](#adr-158--pipeline-review-screen--ui-dedicada-para-aprovareditar-stagereview) (tela consumidora).

**Contexto:** `pipeline/llm/validators.py` modela falhas de schema como `errors: list[str]` e `warnings: list[str]` — mensagens livres construídas com `f"E1.6: dividas_onus[{i}] contém CPF não-mascarado em discriminacao"` espalhadas por ~50 call-sites em 4 stages (E1, E1.5, E2-llm, E1.6). `_record_stage_needs_review` em `backend/app/tasks/pipeline_task.py` persiste isso no DB como `StageReview.validation_errors: Text` via `"\n".join(...)`. A UI (ADR-158) recebe a string, quebra por `\n` e tenta heurística regex (`extractPath`) para casar campos com o `JsonViewer` — falsos negativos toleráveis hoje, mas (a) o card da listagem (`ReviewListItem`) corta em 80 chars e expõe ao usuário a string técnica em pt/en misturado ("E1.6: dividas_onus[0]…") e (b) qualquer evolução de copy obriga search-and-replace em código + testes + dados em produção. ADR-097 D1 já estabelece princípio análogo para warnings de domínio (dataclass tipada com `.format()`); validation issues são o gap simétrico em `pipeline/llm/`. Gatilho concreto: ADR-157 (E1.6 — IRPF) introduziu strings densamente categorizáveis (PII, reconciliação cross-field, sandtraps PGBL/dependente), tornando a falta de `code` materialmente cara para suporte e métricas LLMOps.

**Alternativas consideradas:**

1. **Manter strings livres + i18n table no frontend por regex/prefixo**: zero migração de DB/API, zero código novo no backend. Custo: heurística frágil (cada nova mensagem exige regex novo); impossível agregar métricas por categoria de falha; copy fica acoplado ao parser de string. Dropping — debt já cobra juro hoje.
2. **JSONSchema/Pydantic `ValidationError` puro como contrato**: usar diretamente a saída de `pydantic.ValidationError` (já tem `loc`, `msg`, `type`). Custo: cobre só erros estruturais de tipo; deixa de fora reconciliação cross-field, anti-PII, sandtraps de domínio (PGBL/idade dependente) que são a maioria dos casos em E1.6. Não é abstração-supersede: fica como **uma fonte** que produz `ValidationIssue`s, não substitui.
3. **`ValidationIssue` dataclass + `code` discriminator (escolhida)**: cada issue carrega `code` (chave estável), `severity`, `path` (JSONPath), `context` (campos por-stage) e `legacy_message` (fallback humano gerado no momento, idempotente). `ValidationResult.errors`/`warnings` viram `list[ValidationIssue]`. Backwards-compat: `validation_errors: Text` continua, populado por `"\n".join(legacy_message)`; nova coluna JSON `validation_issues` carrega o estruturado.

**Decisão:** Adotar (3) com 4 ondas faseadas (próxima sub-decisão). O contrato:

```python
@dataclass(frozen=True)
class ValidationIssue:
    code: str                          # "e16.pii.unmasked_cpf"
    severity: Literal["error", "warning"]
    path: str | None                   # "$.dividas_onus[0].discriminacao" — JSONPath
    context: dict[str, Any]            # {index: 0, field: "discriminacao", section_label: "Dívidas e ônus"}
    legacy_message: str                # mensagem humana gerada hoje — fallback p/ runs antigas e logs
```

`StageReview` ganha:
- `validation_issues: JSON | None` — lista serializada (NULL para runs pré-cutover).
- `summary: str` — frase curta (≤80 chars) gerada **on-the-fly no DTO** (não persistida) a partir do `code` mais grave + count, ex.: `"3 erros de PII + 2 avisos de reconciliação"`.

**Sub-decisões:**

1. **Naming dos `code`s — `<stage>.<domain>.<rule>` (3 níveis)**: `e16.pii.unmasked_cpf`, `e16.reconcile.ir_pago_divergente`, `e1.member.duplicate_key`, `e15.item.invalid_category`. Trade-off: `<stage>.*` perde estabilidade quando regra se generaliza (ex.: anti-PII vira cross-stage), mas ganha **navegação e ownership claros** — `grep "e16."` lista todas as regras do stage; copy table fica organizada por stage; rename é refactor mecânico tracked por test (vide D6). Alternativa rejeitada: `<domain>.<rule>` puro (`pii.unmasked_cpf`) força namespace global inflado e perde info útil pro suporte.
2. **Dicionário de copy mora no frontend (`frontend/src/lib/validation-copy.ts`)** — único consumidor user-facing. Backend mantém `legacy_message` em pt-BR como **fallback** (logs estruturados ADR-110, e2e debug, runs pré-cutover). i18n futuro (ADR-130) absorve `validation-copy.ts` em `messages/<locale>/validation.json` quando a feature avançar — não bloquear hoje. **Não duplicar mapping no backend**: copy é UX, não regra.
3. **Forma de `context`** — campos comuns como **opcionais nominais** no dataclass para discoverability (`index: int | None`, `field: str | None`, `section_label: str | None`); resto livre em `extras: dict`. Compromisso entre (a) `dict` puro (zero ceremony, zero typing) e (b) hierarquia de subclasses por code (over-engineered p/ ~30 codes esperados na onda 4).
4. **`summary` é derived no DTO, não snapshot**: trade-off explícito. Snapshot persiste a frase no momento do `_record_stage_needs_review` (rápido em GET, mas copy update não retroage); derived recomputa em cada GET (CPU desprezível p/ ~10 issues/review × ~queries/min, copy update é instantâneo). Escolhemos derived — UX consistency > 5µs/request. Se métrica P99 do endpoint `GET /reviews` subir >10ms, reavaliar (cachear no Redis com chave `review:{id}:summary` invalidada quando copy muda).
5. **`path` é JSONPath dot/bracket** (`$.dividas_onus[0].discriminacao`): casa com a heurística atual do `JsonViewer` (extrai `data-json-path` igual). Verificar empiricamente na onda 3 que o viewer aceita o prefixo `$.` ou se precisa stripar — ajuste é trivial. **Não introduzir RFC 6901** (`/dividas_onus/0/discriminacao`) hoje; menos legível em logs.
6. **Política de evolução de `code`** — análoga ao rename de stages F9.2 (ADR-093):
   - **Adição** de code: livre, sem migration.
   - **Rename**: criar code novo + manter `CODE_ALIASES: dict[str, str]` em `validators.py` mapeando velho→novo por 1 sprint. Frontend resolve via alias antes do lookup. Remover alias após sprint de janela.
   - **Deprecação**: code marcado `_deprecated_at: date` no docstring; warning estruturado quando emitido; remoção em sprint+1.
   - Test gate (onda 1): `test_codes_unique` + `test_legacy_message_renders_for_every_code` — proíbe code órfão de copy ou mensagem.

**Implementação faseada** (track operacional em `docs/agent_prompts/track_validation_issues_structured.md`):

| Onda | Escopo | Exit gate |
|---|---|---|
| 1 | Tipo `ValidationIssue` + helper `r.error(code=..., path=..., context=..., legacy_message=...)` mantendo API antiga via `r.error(msg)` deprecated; migrar **só** `validate_e16_output` (~6 sites); tests de paridade `legacy_message ↔ rendered`, codes únicos, schema da context dict por code. **Sem** mudança em DB/API. | `pytest tests/llm/test_validators_e16.py -q` verde + diff `legacy_message` ↔ string atual byte-equal. |
| 2 | Alembic add `stage_reviews.validation_issues JSON NULL`; `StageReviewResponse` ganha `validation_issues: list[ValidationIssue] \| None` + `summary: str`; `_record_stage_needs_review` popula ambas colunas (fallback `"\n".join(legacy_message)` em `validation_errors` mantido); `make update-openapi-snapshot`. | Smoke run E1.6 → review aparece com `validation_issues` populado no GET; `validation_errors` continua igual. |
| 3 | `frontend/src/lib/validation-copy.ts` (com product-designer); `ValidationErrorsPanel` consome `validation_issues` quando presente, fallback string quando `null`; `ReviewListItem` usa `summary` em vez do truncate de 80 chars; remover heurística `extractPath` da v1 (path agora vem estruturado). | Vitest cobertura + Playwright `@critical` review-screen verde. |
| 4 | Migrar E1, E1.5, E2-llm (~44 sites restantes); deprecar API antiga `r.error(msg)`; remover quando coverage estável. ADR vira final (sem mudança de status, é um "implementação completa"). | Lint regra `no-string-validation-error` em `pipeline/llm/validators.py`; `validation_errors: Text` marcado `deprecated` no model com janela ≥2 sprints antes de drop. |

**Consequências:**

- ✅ **Métricas LLMOps tracking-ready** — agregação por `code` permite "qual rule do E1.6 mais cai em review?" e "% PII caught" como KPI de qualidade do prompt (eval input para ADR-144 / ADR-110).
- ✅ **Copy desacoplado do parser** — product-designer edita `validation-copy.ts` sem PR de pipeline; i18n natural quando ADR-130 evoluir.
- ✅ **Highlight no `JsonViewer` deixa de ser heurística** — `path` estruturado elimina os falsos negativos do `extractPath` regex (ADR-158 sub-decisão 3).
- ✅ **`summary` no card da listagem é UX-friendly** — usuário vê "3 erros de PII + 2 avisos de reconciliação" em vez de "E1.6: dividas_onus[0] contém CPF nã…".
- ✅ **Backwards-compat preservado** — runs antigas (`validation_issues IS NULL`) renderizam fallback string; nenhuma migration de dados; deprecação de `validation_errors: Text` faseada.
- ✅ **Coerente com ADR-097 D1** — extensão natural do princípio "warnings de domínio são tipados" para validation errors.
- ⚠️ **~50 call-sites a migrar** — onda 4 é o trabalho real; estimativa 1 dia de migração mecânica + 1 dia de ajuste de copy com product-designer. Bloqueio risco-baixo: api antiga coexiste durante a janela.
- ⚠️ **Coluna `validation_errors: Text` vira tech debt explícito** — drop só após todos runs com `validation_issues IS NULL` expirarem ou backfill ad-hoc. Não bloqueia esta ADR.
- ⚠️ **`summary` derived no DTO** custa CPU em cada GET — desprezível hoje (≤10 issues/review), mas cresce com escala se copy ficar dependente de i18n table. Cache em Redis fica como follow-up se P99 subir.
- ❌ **Tipagem de `context` por code não é estática** — `context: dict[str, Any]` aceita qualquer shape; test gate (D6) garante presença dos campos esperados por code, mas não há `Literal`/`TypedDict` por code. Trade-off: subclasses por code quebram a uniformidade da lista; aceito até codes >50.

**Relação com outras ADRs:**

- **ADR-097 D1** — esta ADR é a extensão simétrica para validation issues (warnings de domínio já são tipados; validation errors agora também).
- **ADR-110** — issues estruturadas alimentam logs JSON com `code`/`severity` discoverable, não free-form text.
- **ADR-143** — `code` + docstring no enforcer é a forma rules-as-code aplicada a validators.
- **ADR-157** — gatilho concreto; E1.6 é o primeiro stage migrado (onda 1).
- **ADR-158** — esta ADR cobre o **contrato** consumido pela tela; ADR-158 cobre a **tela**. Não substitui.

**Follow-ups (não bloqueiam merge desta ADR):**

1. Track operacional `docs/agent_prompts/track_validation_issues_structured.md` (a criar pelo agente que executa onda 1).
2. Drop de `validation_errors: Text` quando todos os runs em produção estiverem com `validation_issues` populado (sprint+2 mínimo).
3. Cache do `summary` em Redis se P99 do `GET /reviews` subir >10ms — apenas se métrica disparar.
4. Codegen de `ValidationIssue` TS a partir do schema Python no boundary backend↔frontend (substitui escrita manual em `lib/api/pipeline.ts`).
5. Lint rule custom `no-string-validation-error` para `pipeline/llm/validators.py` (pré-commit).
