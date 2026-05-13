---
id: PLAN-planner-review
type: plan
title: Parecer do Planejador (E6) — substituição de review_finances + aterrissagem operacional
status: draft
created_at: 2026-05-12
last_review: 2026-05-12
sprint_origem: A11
sprint_atual: A11
sprints_envolvidas: [A11, A12]
paused_at: null
pause_reason: null
adrs_canonical: []
tags:
  - type/plan
  - status/draft
  - area/llm
  - area/pipeline
  - area/relatorio
---

# Parecer do Planejador (E6) — substituição de review_finances + aterrissagem operacional

> **Origem:** brainstorm 2026-05-12 com protótipos V1 (markdown destilado, ~$0.15) e V2 (E5 JSON cru, ~$0.24) usando subagent `financial-planner` sobre workspace real (família Campos). Consolidação multi-agente em 2026-05-12 com pareceres independentes de `senior-cto`, `data-engineer` e `product-designer`.
>
> **Não conflita com lanes ativas:** verificado contra `git worktree list` + `origin/agent/*` <48h em 2026-05-12.
>
> **Achados habilitadores descobertos no brainstorm:**
> 1. Stage `review_finances` (E7-review) **já existe** e produz artifact `("E7-review", "review_llm")` que **não é consumido por nenhum endpoint nem componente React** — dead-output. ADR-128 vira substituível.
> 2. Pattern de **manifest YAML + JSON Schema + cache Redis + fallback determinístico** já existe para `section_summaries` (ADR-144). É o pattern a espelhar.
> 3. Operating system de recomendações **já está em produção**: `Suggestion` (event-sourced, dedup_key, status Pendente/Aceita/Modificada/Descartada), `Task` (priority S/R/O, deadline_kind, parent_task_id), `Decision` (event-sourced ADR-136), `risks`, `protections`. Parecer **emite suggestions com origin=llm**; resto do fluxo é o que já existe (`/acao`, ADR-153).
> 4. `<SuggestionCalloutInline>` já existe e renderiza sugestões automaticamente nas seções fonte do relatório — cross-linking bidirecional sem código novo.

---

## NEXT UP

| Lane | Status | Owner | Notas |
|---|---|---|---|
| Ato 0 — Decisões pendentes resolvidas | proposed | `product-manager` | Tema canônico enum, hard caps, snooze_until |
| Ato 1 — ADRs Proposto | proposed | `senior-cto` | ADR-mãe + filhas P0 (manifest, persona, schema) |
| Pré-requisitos bloqueantes | proposed | varies | 4 bloqueios, ver §Pré-requisitos |

---

## Decisão central

O stage `review_finances` (E7-review) é **substituído** por `parecer_planejador` (E6). Não há cutover-pesado porque o output atual é órfão (nenhum consumer). ADR-128 marca `superseded_by: [[ADR-NNN]]`; remoção do código antigo em sprint+1 após cutover.

**Por que substituir e não complementar:** custo LLM dobrado, ambiguidade narrativa, dois prompts pra manter sincronizados, dois schemas, dois artifacts. Coexistência só faria sentido se ADR-128 tivesse consumer real — não tem.

---

## Premissas operacionais

1. **Tempo de implementação não é restrição** (decisão do owner). Otimizar por arquitetura, não pragmatismo.
2. **React pode ser substituído** por outro framework no futuro. Design não amarra a hooks/lazy React-only; usa `<details>` HTML nativo onde possível.
3. **Go pode substituir Python** no stage runtime. Inteligência mora em manifests + persona + schemas (language-agnostic); stage é I/O orquestrador (~100-200 linhas) portável.
4. **Reuse obrigatório** de `Suggestion`, `Task`, `Decision` aggregates. Parecer NÃO cria entidades novas.
5. **LiteLLM (ADR-024) + Instructor (ADR-026)** são obrigatórios; Anthropic SDK direto está proibido.
6. **Sigilo §13 do COPY_GUIDELINES** atravessa o output: "Perini", "Cerbasi", "AUVP" não podem aparecer em user-facing (relatório, PDF, app). LLM emite `ancora_metodologica` (enum interno); UI exibe `tema_canonico` (enum user-facing). Mapeamento explícito.

---

## Pré-requisitos bloqueantes

Sem estes 4, o parecer vira armadilha. Resolver antes ou em paralelo com Atos 1-2.

| # | Bloqueio | Origem | Impacto se não resolvido |
|---|---|---|---|
| PR-1 | `additionalProperties: true` no `config/schemas/e5_analysis.schema.json` (W6-T01 PLATFORM_REVIEW) | data-engineer (DE-I.1) | Campos novos no E5 viajam pro LLM sem CI gate; drift silencioso garantido. |
| PR-2 | Inconsistência de unidades pct no E5 (`44.7` absoluto vs `0.447` fracional em campos diferentes) | data-engineer (DE-I.2) | Hallucination numérica garantida ("rentabilidade 0,45%" quando real é 45%). |
| PR-3 | Tabela `pipeline_run_costs` para FinOps por workspace (LLM cost tracking) | data-engineer (D) | Sem isso, impossível responder "quanto cada workspace premium custa em LLM"; bloqueia precificação. |
| PR-4 | Decisão substituir × complementar `review_finances` formalizada em ADR-mãe | senior-cto (F) | Sem ADR, coexistência informal vira tech debt permanente. |

PR-4 já está resolvido (decisão: substituir). PR-1, PR-2, PR-3 são lanes técnicas paralelas — não bloqueiam Atos 1-3 mas bloqueiam Ato 5 (shipping pra usuário pagante).

---

## Decisões pendentes (Ato 0)

Resolver com `product-manager` + `financial-planner` antes de Ato 1.

| Decisão | Opções | Recomendação tentativa |
|---|---|---|
| Enum `tema_canonico` user-facing | `Proteção · Alocação · Renda passiva · Liquidez · Custo tributário · Saúde de balanço · Diagnóstico de dados · Equilíbrio presente-futuro · Convergência metodológica` (9 valores) | Adotar; co-design com `financial-planner` para fechar mapeamento `ancora_metodologica → tema_canonico` (1 ancora pode produzir vários temas dependendo do contexto da sugestão) |
| Hard caps no schema do parecer | riscos ≤ N, sugestões ≤ N por horizonte, métricas ≤ N | riscos ≤ 12, sugestões ≤ 15 (5/5/5), métricas ≤ 10 |
| Coluna `snooze_until` no `Suggestion` | Adicionar agora ou cortar ação "Adiar" do MVP | Adicionar; baixo custo, fecha gap UX |
| Premium tier — parecer é gate de pricing? | Sim / Não / Híbrido (free recebe diagnóstico, premium recebe sugestões) | Pendente — invocar `gtm-strategist` |
| Frequência de regeneração | Mensal automática / Sob demanda / Híbrido | Híbrido: gera 1× por relatório premium; usuário pode regenerar manualmente (rate-limited a 3/workspace/dia) |
| Aterrissagem visual: seção nova `S_parecer` vs. expandir `S10` | Nova / Expandir | **Nova** — recomendação `product-designer` §Trade-off 1. S10 é síntese determinística; parecer é orientativo. Misturar dilui ambos. |

---

## ADR-mãe + filhas

| ADR | Título | Prioridade | Status |
|---|---|---|---|
| **ADR-NNN (mãe)** | Parecer planejador (E6) supersede review_finances (ADR-128) — aggregate `PlannerReview`, manifest declarativo, integração com Suggestion | **P0** | Proposto |
| ADR-filha-1 | Manifest declarativo F5 — `config/prompts/parecer_planejador.yaml` + DSL JSONPath subset | P0 | Proposto |
| ADR-filha-2 | Persona como rules-as-code — `config/agents/planner_persona.md` versionado (estende ADR-143) | P0 | Proposto |
| ADR-filha-3 | Output schema — `parecer_planejador.schema.json` + invariantes (max 2 P0, enums, regex anti-ticker, hard caps) | P1 | Proposto |
| ADR-filha-4 | Tool use híbrido + guardrails — drill-down sob demanda com cap=6, whitelist JSONPath, cache em sessão | P1 | Proposto |
| ADR-filha-5 | Imutabilidade do parecer pós-publicação (estende ADR-187) | P1 | Proposto |
| ADR-filha-6 | Boundary Python/Go — stages LLM permanecem Python; contratos JSON são imutáveis | P1 | Proposto |
| ADR-filha-7 | Telemetria de "campo faltante" como signal de evolução do manifest (estende ADR-188) | P2 | Proposto |
| ADR-filha-8 | Sigilo metodológico no parecer LLM — mapeamento `ancora_metodologica` → `tema_canonico` (estende COPY_GUIDELINES §13) | P0 | Proposto |

---

## Atos (lanes implementáveis)

Cada ato é PR mergeável, CI verde, sem dependência circular.

### Ato 1 — ADRs Proposto (docs-only)

**Escopo:** abrir 9 ADRs (mãe + 8 filhas) como `Proposto`. Zero código. PR docs-only.

**Critério de aceite:**
- 9 ADRs em `docs/adr/NNN-slug.md` com frontmatter validado por `dev/validate_frontmatter.py`
- ADR-128 marca `superseded_by` (provisório; flippa para `Decidido` após Ato 4)
- Cada ADR cita pelo menos 1 ADR existente como precedente (ADR-024, ADR-026, ADR-076, ADR-128, ADR-136, ADR-143, ADR-144, ADR-153, ADR-187, ADR-188)
- Review obrigatória: `senior-cto` + `data-engineer` + `financial-planner` + `product-designer`

**Estimativa:** 1-2 dias.

### Ato 2 — Schemas + manifest + persona (foundation)

**Escopo:**
- `config/schemas/parecer_planejador.schema.json` (output schema com invariantes)
- `config/prompts/parecer_planejador.yaml` (manifest F5 espelhando `section_summaries.yaml`)
- `config/agents/planner_persona.md` (persona com frontmatter versionado; hash registrado no aggregate)
- `docs/_schemas/note-planner.schema.json` (valida shape do manifest)
- `docs/_schemas/persona.schema.json` (valida frontmatter da persona)
- `.claude/agents/financial-planner.md` vira shim que referencia `config/agents/planner_persona.md`
- `dev/check_planner_manifest_coverage.py` — coverage gate em CI (M1):
  - Manifest ↔ E5 schema: JSONPaths referenciados existem
  - Manifest ↔ report_layout.yaml: section_ids alinham
  - Snapshot diff E5 schema dispara warning se manifest não muda no mesmo PR

**Critério de aceite:**
- Pré-commit hook `planner-manifest-coverage` verde
- Persona inclui mapeamento explícito `ancora_metodologica → tema_canonico` (regra do sigilo §13)
- Validação JSON Schema do output cobre: 9 valores de `tema_canonico`, max 2 P0, regex anti-ticker, hard caps (riscos ≤ 12, sugestoes ≤ 15, metricas ≤ 10)
- **Não chama LLM ainda.** Apenas contratos.

**Estimativa:** 3-5 dias.

### Ato 3 — Aggregate + repository + endpoint stub

**Escopo:**
- `backend/app/models/planner_review.py` — model SQLAlchemy `PlannerReview` (aggregate root)
- Alembic migration: `planner_reviews(id, workspace_id, pipeline_run_id, e5_artifact_id, persona_hash, manifest_version, schema_version, model_id, cost_usd_cents, tokens_in, tokens_out, tool_call_count, status, content_json, created_at, published_at, superseded_by_id, ...)`
- Decisão alternativa (data-engineer prefere): armazenar em `pipeline_artifacts` (stage='E6-parecer', artifact_key='parecer_planejador') + projection materializada `planner_review_findings(review_artifact_id, ancora, prioridade, tema)` quando dashboard exigir. **Decidir no Ato 1 (ADR-mãe).**
- Tabela `pipeline_run_costs` (PR-3, paralela)
- `backend/app/repositories/planner_review.py` — repository
- `backend/app/api/planner_review.py` — endpoint `GET /workspaces/{id}/reports/{run_id}/planner-review` retornando `404 not_generated_yet`
- `make update-openapi-snapshot` aplicado
- Coluna `snooze_until` opcional em `suggestion` (se Decisão Pendente resolvida = adicionar)

**Critério de aceite:**
- Migration aplica e reverte limpa
- Endpoint responde 404 corretamente
- `dev/check_response_models.py` verde (ADR-102)
- OpenAPI snapshot atualizado
- **Não chama LLM ainda.** Apenas infra.

**Estimativa:** 2-3 dias.

### Ato 4 — Stage + LLM call + golden mockado

**Escopo:**
- `pipeline/stages/parecer_planejador.py` (stage wrapper, ≤100 linhas)
- `pipeline/domain/services/parecer_generator.py` (domain logic; pipeline não importa fastapi/celery/sqlalchemy — CLAUDE.md)
- `backend/app/services/parecer_orchestrator.py` (wire-up: manifest + persona + cache Redis + LLMService + fallback determinístico) — espelha `section_summary_orchestrator.py`
- `pipeline/llm/prompts/parecer_planejador.py` — system prompt; deriva da persona (não duplica)
- `pipeline/llm/schemas/parecer_planejador.py` — Pydantic do output (codegen do JSON Schema)
- Tools: `get_e5_section(key)`, `get_e5_jsonpath(path)` com:
  - Cap `max_tool_iterations: 6` no orchestrator (não no LLM)
  - Whitelist JSONPath derivada do schema E5
  - Cache em sessão (memória local, ADR-111 categoria b — exceção idempotente)
  - Audit trail em `content_json._meta.tool_trace`
  - Tool retorna `{"found": false, "path": "...", "reason": "..."}` quando ausente
  - Tools operam sobre E5 já carregado em memória — zero DB calls do tool handler
- Stage emite `Suggestion` (origin=llm) com `dedup_key` estável (hash da ação + ancora + workspace_id)
- Stage emite com `section_id` apontando seção fonte — `<SuggestionCalloutInline>` renderiza automaticamente
- Cache Redis com chave `sha256(e5_content_hash || manifest_version || schema_version || model_id)`, TTL 7d
- `tests/test_parecer_golden_execution.py` — golden test estrutural (LLM mockado):
  - Schema válido
  - Invariants (count P0 ≤ 2, âncoras presentes, regex anti-ticker, hard caps)
  - Tema canônico ∈ enum
  - Sugestões têm `section_id` correspondente a seção do relatório
- Feature flag `MATHOMS_ENABLE_PARECER_PLANEJADOR` (default false) — Ato 5 promove para true
- Stage retorna `{"skipped": true, ...}` se workspace não-premium (tier free)
- Falha de validação → `status="needs_review"`, artifact não-publicado, alerta operacional

**Critério de aceite:**
- Stage roda end-to-end com `LLMService` mockado em CI
- Golden estrutural verde (não textual)
- Suggestions emitidas com `dedup_key` reproduzível
- Cost tracking em `pipeline_run_costs` populado
- Logs estruturados sem PII (regex test caça `insights=`, nomes próprios em log)
- Stage usa LiteLLM (ADR-024) + Instructor (ADR-026)

**Estimativa:** 5-7 dias.

### Ato 5 — Renderer + telemetria + cutover

**Escopo:**

5a — **Seção `S_parecer` no `report_layout.yaml`:**
- Novo section_id `S_parecer` com `x-planner-skip: true` (não é input do destilador)
- Posição: entre `S10` e `plano_de_acao` (lane "Síntese")
- Top-nav entrada `11.1` em "Síntese"
- 4 blocos: hero diagnóstico, estado atual (pontos fortes + riscos), movimentos (3 horizontes), métricas

5b — **Componentes React (novos, 5):**
- `<ParecerHeroDiagnostico>` (variant highlight, full)
- `<ParecerRisksTable>` (tabela densa top-5 + expand)
- `<ParecerMovimentoCard>` (P0/P1/P2 dot + ação + impacto + meta + 3 ações inline)
- `<ParecerHorizonteList horizon="execucao|tatico|estrategico">`
- `<ParecerMetricasTable>` (mini-trilha via `<progress>` nativo)

5c — **Interaction model das sugestões:**
- 3 ações inline: `Promover para ação` (CTA primário) | `Já considerei` | `Descartar com motivo ▾`
- "Promover" abre `/acao?tab=inbox#SUG-<id>` (padrão ADR-153 — SuggestionCallout)
- "Já considerei" → `suggestion.status=Descartada, dismissed_reason=ja_considerei` (honra `DISMISS_RESPECT_WINDOW_DAYS=90`)
- "Descartar com motivo" → dropdown: `Não se aplica` / `Discordo do diagnóstico` / `Adiar por 3 meses` (requer `snooze_until`) / `Outro motivo`
- Sugestão promovida (existe `task.source_suggestion_id`) → card colapsado com badge `Promovida em DD/MM`
- Sugestão descartada → não aparece; conta agregada `12 sugestões descartadas neste ciclo · ver histórico`
- Reincidente (descartada+90d) → badge âmbar `Reincidente · você descartou em fev/26 como "<reason>"`

5d — **Reuso:** `<SuggestionCalloutInline sectionId="...">` renderiza automaticamente nas seções fonte (S1/S2/S3/S7/S8/S9). Zero código novo.

5e — **PDF (Playwright):**
- CSS `@media print { .parecer-action { display: none; } }`
- `<details>` forçados `[open]` em print
- Disclaimer fiduciário visível no fim da seção
- Lista de descartadas anteriores oculta no PDF (clutter sem ação)

5f — **Sigilo §13:** UI nunca cita Perini/Cerbasi/AUVP. Mostra `tema_canonico` (enum fechado de 9 valores). Frontend valida com `dev/check_sigilo_terms.py`.

5g — **Telemetria M4:**
- Tabela `planner_field_requests(date, field_path, count, workspace_id)`
- Planner emite no output `campos_faltantes_pediria_se_iterasse[]`
- Aggregate semanal → top 10 campos pedidos → input do tunning v2 do manifest
- Review mensal no Now/Next/Later

5h — **Smoke cross-provider weekly:**
- CI roda 1× por semana com Anthropic + 1 outro provider (OpenAI ou Ollama)
- Mesmas assertions estruturais
- Detecta lock-in via tool use format (CTO-G6)

5i — **Cutover:**
- Feature flag promove `MATHOMS_ENABLE_PARECER_PLANEJADOR=true` para workspaces piloto
- Deprecate `review_finances` no `STAGE_REGISTRY` (status `deprecated`)
- Sprint+1: remove `review_finances` stage, prompt antigo, schema antigo
- ADR-128 flippa para `Decidido (superseded by ADR-NNN)`

**Critério de aceite:**
- Axe DevTools: 0 violations em desktop + mobile
- Navegação por teclado: Tab atravessa Hero → cada sugestão → tabela métricas → notas em ordem visual
- Screen reader testado (VoiceOver/NVDA)
- Contraste P0/P1/P2 ≥ 4.5:1 em light e dark
- E2E `@critical` Playwright: relatório gera com `S_parecer` renderizado, "Promover para ação" funciona
- Smoke cross-provider verde
- Telemetria populando

**Estimativa:** 7-12 dias (incluindo handoff de design pra implementação).

---

## Riscos consolidados

Em ordem de severidade. Cada um tem mitigação concreta.

### Críticos — bloqueiam shipping pra cliente pagante

1. **Sigilo §13 vazando** (PD). LLM cita Perini/Cerbasi/AUVP no output e vaza pra UI. **Mitigação:** schema do output usa `ancora_metodologica` (enum interno) + `tema_canonico` (enum user-facing); validador rejeita output que contém termos proibidos no body textual; `dev/check_sigilo_terms.py` no CI.
2. **E5 schema `additionalProperties: true`** (DE-I.1). Resolver antes do parecer virar SKU pago.
3. **Inconsistência unidades pct E5** (DE-I.2). Resolver antes; documentar como rule no system prompt enquanto não resolve.
4. **Coexistência ambígua review_finances ↔ parecer_planejador** (DE). Mitigação: ADR-mãe explicita supersedure; cutover em sprint definido.

### Altos — bloqueiam ship em produção estável

5. **Persona drift entre versões do modelo** (CTO-G1). Anthropic deprecate model silenciosamente. **Mitigação:** golden parecer rodando **mensalmente** com modelo real (não só nightly), alerta se variação semântica > threshold; pin de model snapshot em `LLMConfig`.
6. **Cost cliff workspaces grandes** (CTO-G5). Workspace 5 anos = E5 200KB+ × 5 tool iterations = $$ explode. **Mitigação:** circuit breaker `max_total_input_tokens: 50000`, exec context base hard-limited a 5KB, alerta `planner_review_cost_usd > $1 per single call`.
7. **Lock-in Anthropic via tool use format** (CTO-G6). LiteLLM normaliza mas sutilezas escapam. **Mitigação:** smoke cross-provider weekly em CI.
8. **PII em logs estruturados** (CTO-G4). `MathomsJsonFormatter` pode vazar nomes. **Mitigação:** hard rule + regex em testes que caçam isso (`logger.info("parecer_generated", insights=...)` proibido).
9. **Telemetria M1 só pega metade do drift** (DE-E inverso). M1 detecta campo referenciado ausente; **não** detecta campo novo no E5 que deveria entrar no manifest. **Mitigação:** snapshot diff E5 schema dispara warning quando manifest não muda no mesmo PR; M4 (telemetria) é backup empírico.
10. **`additionalProperties: true` permite tudo viajar pro LLM sem gate** (DE). Cobre PR-1.

### Médios — refinam qualidade

11. **Dual-shell persona dev-time × runtime** (CTO-G10). **Mitigação:** persona-base canônica + 2 shells (orquestração interativa em `.claude/agents/financial-planner.md` adiciona contexto de BACKLOG; stage runtime injeta só E5 + manifest).
12. **`narrativas` E5 é caixa preta com LLM-on-LLM** (DE-I.8). **Mitigação:** parecer **não** consome `narrativas`; só campos estruturados.
13. **Tools podem contradizer destilado** (CTO). `rentabilidade_pct: "3.2%"` no destilado vs `0.032` raw da tool. **Mitigação:** formatter compartilhado entre destilador e tool handlers.
14. **Prompt injection via `narrativas` E5** (CTO). **Mitigação:** redação determinística antes de injetar (escapa `</system>`, limita a 500 chars, rejeita padrão suspeito).
15. **Manifest vazando pra persona** (CTO-G2). Persona instruindo "se faltar X, chame tool Y" mistura domínio com plumbing. **Mitigação:** persona fala metodologia; manifest fala extração; stage cola.
16. **Idempotência aparente não real** (CTO-G3). Mesmo input ≠ mesmo output (LLM não-determinístico). **Mitigação:** golden estrutural não textual; temperatura ≤ 0.3; cache por hash do input.
17. **Subset/superset de stages futuro** (CTO-G8). **Mitigação:** `STAGE_REGISTRY[parecer_planejador].depends_on = ["analyze_finances"]` enforçado; variantes = stages novos.
18. **Parecer LLM "muda de ideia" entre rodadas** (PD). **Mitigação:** dedup_key estável; cache Redis 7d.
19. **Parecer não declarado como snapshot** (PD). **Mitigação:** badge "Snapshot dos dados em DD/MM/YYYY" + tooltip explicativo.
20. **Risco P0 falso por dado não cadastrado** (PD). **Mitigação:** toda sugestão P0 deve linkar dado-fonte; quando ausente, sugestão vira "Verifique se [X] está cadastrado".
21. **Sugestão envolvendo cônjuge sem consentimento** (PD). **Mitigação:** copy descreve decisão, não pessoa; uso de `family_members` só com permissão.
22. **Filtros como avoidance** (PD). **Mitigação:** P0 sempre incluído; contador "Mostrando 3 de 11" sempre visível.
23. **Parecer monstro** (PD). **Mitigação:** hard caps no schema (riscos ≤ 12, sugestões ≤ 15, métricas ≤ 10).

### Baixos — polish

24. Componente novo no relatório expande top-nav (12 entradas). Aceito.
25. Persona-base + dois shells é arquivo + 2 imports. Aceito.

---

## Contratos imutáveis (Python ↔ Go)

Definidos pelo `senior-cto`. Mudam apenas via ADR breaking.

1. **Stage I/O signature:**
   - Reads: `("E5", "analise_financeira")` artifact, `config/agents/planner_persona.md`, `config/prompts/parecer_planejador.yaml`
   - Writes: `("E6-parecer", "parecer_planejador")` artifact validado por `parecer_planejador.schema.json`
2. **Schemas JSON** (`e5_analysis.schema.json`, `parecer_planejador.schema.json`, `note-planner.schema.json`).
3. **Formato declarativo do manifest** (DSL: JSONPath subset + format hints).
4. **Persona format** (Markdown + frontmatter `id/version/methodology_anchors/persona_hash`).
5. **Aggregate em DB** (`PlannerReview` model + colunas + índices).
6. **HTTP API DTO** (`GET /workspaces/{id}/reports/{run_id}/planner-review` response shape).
7. **Stage name** no `STAGE_REGISTRY` (descritivo ADR-093: `review_finances_holistic` ou `parecer_planejador`).

**Pode mudar sem ADR breaking:**
- Implementação interna do distiller/orchestrator/stage
- Algoritmo de retry/backoff
- Provider LLM concreto (LiteLLM permuta sem ADR)
- Logging/observabilidade interna
- Cache layer (Redis ou nada)
- Refactor estrutural dentro de Python ou Go

---

## Critério de aceite consolidado

### Funcional
- [ ] 9 ADRs em `Proposto` → `Decidido` ao final do Ato 5
- [ ] `dev/check_planner_manifest_coverage.py` verde
- [ ] `dev/check_sigilo_terms.py` verde sobre `frontend/src/components/report/sections/SParecer*.tsx`
- [ ] Tabela `pipeline_run_costs` populada por stage runs
- [ ] Suggestions emitidas com `dedup_key` reproduzível e `section_id` correto
- [ ] `<SuggestionCalloutInline>` renderiza automaticamente nas 6 seções fonte (S1, S2, S3, S7, S8, S9)
- [ ] Cost cache hit ≥ 70% em PRs após 4 semanas
- [ ] Smoke cross-provider weekly verde
- [ ] Golden estrutural verde

### Acessibilidade (gates pre-merge)
- [ ] Axe DevTools 0 violations
- [ ] Navegação por teclado completa em ordem visual
- [ ] Screen reader testado (VoiceOver + NVDA)
- [ ] Contraste P0/P1/P2 ≥ 4.5:1 em light e dark
- [ ] `<progress>` com `aria-valuetext` em métricas

### Responsivo + PDF
- [ ] Mobile <420: P1/P2 colapsados, P0 sempre expandidos
- [ ] Tablet 768-1024: bloco pontos+riscos vira stack vertical
- [ ] PDF Playwright: zero botão, `<details>` abertos, disclaimer visível, ≤2 páginas extras

### Observabilidade
- [ ] Logger `mathoms.pipeline.parecer_planejador` com fields padronizados (workspace_id, persona_hash, manifest_version, model, tokens_in/out, cost_usd, latency_ms, status, tool_iterations)
- [ ] Métricas Prometheus: `planner_review_cost_usd_total`, `planner_review_tool_iterations_histogram`
- [ ] Alerta: `cost_usd > $1` por chamada individual
- [ ] Tabela `planner_field_requests` agregada semanalmente

### Cutover
- [ ] ADR-128 marca `superseded_by: [[ADR-NNN]]`
- [ ] ADR-NNN marca `Decidido (Sprint A12.X)` no merge final
- [ ] `review_finances` removido em sprint+1 (`STAGE_REGISTRY` deprecated → removed)
- [ ] Feature flag `MATHOMS_ENABLE_PARECER_PLANEJADOR=true` global

---

## Out-of-scope (cortes do MVP)

Itens explicitamente removidos. Revisitar pós-beta.

1. ❌ "Aceitar com modificação" inline — leva para `/acao` editar
2. ❌ Bulk actions ("aceitar todas P0")
3. ❌ Estimativa de impacto futuro condicional ("reduziria gap IF em 18m")
4. ❌ Métricas evolutivas (% aceitação histórica) — vai pra `/acao`
5. ❌ Diff visual entre pareceres mensais (só banner textual "Mudança material")
6. ❌ Hover preview de seções fonte
7. ❌ Mini-mapa de cross-linking lateral
8. ❌ Modal de detalhes (substituído por `<details>` HTML)
9. ❌ Animação de transição entre estados
10. ❌ Multi-persona (parecer "Perini-flavored" vs "Cerbasi-flavored" lado a lado)
11. ❌ Anthropic SDK direto (proibido por ADR-024)
12. ❌ Stage em Go (premissa 3 confirma Python permanece pra stages LLM)
13. ❌ Persona em formato não-markdown
14. ❌ Tabela `planner_reviews` própria no DB (usar `pipeline_artifacts` + projection)
15. ❌ Apagar artifacts antigos do `review_finances` (deixar dormindo p/ auditoria)

---

## Glossário

| Termo | Definição |
|---|---|
| **Parecer** | Output estruturado do LLM (diagnóstico + pontos fortes + riscos + sugestões 3 horizontes + métricas + notas metodológicas) |
| **Ancora metodológica** (interna) | Enum LLM emite: `perini`, `cerbasi`, `auvp`, `convergencia`. **Nunca aparece em UI.** |
| **Tema canônico** (user-facing) | Enum exibido: `Proteção`, `Alocação`, `Renda passiva`, `Liquidez`, `Custo tributário`, `Saúde de balanço`, `Diagnóstico de dados`, `Equilíbrio presente-futuro`, `Convergência metodológica` |
| **Sugestão** | Item acionável do parecer; vira `Suggestion` aggregate (origin=llm) |
| **Movimento** | Sinônimo user-facing de "sugestão" no UI |
| **Horizonte** | Escala temporal: execução (4 semanas) / tático (3-12 meses) / estratégico (12+ meses) |
| **Prioridade** | P0 (urgente, max 2 por parecer) / P1 (importante) / P2 (oportunidade) |
| **Confiança** | LLM declara: alta / média / baixa. Sempre visível, não esconde |
| **Severidade (riscos)** | Crítica / Alta / Média / Baixa. Top-5 visíveis; Baixa apenas em expand |
| **Manifest** | `config/prompts/parecer_planejador.yaml` — declarativo, F5, single-source-of-truth do exec context |
| **Persona** | `config/agents/planner_persona.md` — rules-as-code, versionada, hash registrado no aggregate |
| **Drill-down** | Tool use híbrido: LLM consulta E5 sob demanda via `get_e5_section`/`get_e5_jsonpath`, cap=6 |
| **Reincidente** | Sugestão que ressurge >90d após descarte com badge âmbar e contexto do descarte anterior |

---

## Links e referências

### ADRs relevantes (precedentes)
- [ADR-024 — LiteLLM como proxy universal](../../adr/024-litellm-como-proxy-universal.md)
- [ADR-026 — Instructor + Pydantic para structured output](../../adr/026-instructor-pydantic-para-structured-output.md)
- [ADR-076 — Design system + codegen report_layout](../../adr/076-design-system-codegen-report-layout.md)
- [ADR-093 — Stage identifiers descritivos](../../adr/093-stage-identifiers-descritivos.md)
- [ADR-128 — E7-review LLM lê/escreve via ArtifactStore](../../adr/128-e7-review-llm-leescreve-via-artifactstore.md) (a ser superseded)
- [ADR-136 — Decisions aggregate event-sourced](../../adr/136-decisions-aggregate-event-sourced.md)
- [ADR-143 — Methodology as code](../../adr/143-methodology-as-code.md)
- [ADR-144 — Section summaries LLM-driven com cache](../../adr/144-section-summaries-llm-driven-em-e5-com-cache.md)
- [ADR-153 — SuggestionCallout transição editorial em /acao](../../adr/153-suggestion-callout-em-acao.md)
- [ADR-187 — Imutabilidade de relatório pós-publicação](../../adr/187-imutabilidade-relatorio-publicado.md)
- [ADR-188 — Schema evolution learning loop](../../adr/188-schema-evolution-learning-loop.md)

### Arquivos-chave
- `pipeline/stages/review_finances.py` (a substituir)
- `pipeline/llm/litellm_client.py` (LLMService — reusar)
- `backend/app/services/section_summary_orchestrator.py` (pattern a espelhar)
- `backend/app/services/llm_cache.py` (cache Redis — reusar)
- `backend/app/models/suggestion.py`, `task.py`, `decision.py` (aggregates a alimentar)
- `frontend/src/components/report/sections/SuggestionCallout.tsx` (componente a reusar)
- `frontend/src/components/report/sections/PlanoDeAcao/` (precedente de aterrissagem)
- `config/report_layout.yaml` (adicionar section `S_parecer`)
- `config/prompts/section_summaries.yaml` (precedente do manifest pattern)
- `_scratch/planner_parecer_campos.md` (protótipo V1 — referência de conteúdo)
- `_scratch/planner_parecer_campos_v2_cru.md` (protótipo V2 — referência de qualidade)

### Pareceres dos especialistas (artefatos do brainstorm)
- senior-cto: 8 ADRs propostas, 10 riscos novos (G1-G10), stage I/O orquestrador, boundary Python/Go, `LiteLLM + Instructor` obrigatório
- data-engineer: F5 vence (manifest separado), reuso `LLMService`, padrão `section_summaries`, 9 achados E5 schema (I.1-I.8), 4 pré-requisitos bloqueantes
- product-designer: 5 componentes novos, hierarquia 4-blocos, interaction model 3 ações, sigilo §13 atravessa schema, hard caps, mapeamento ancora↔tema canônico, 8 riscos UX
