---
id: ADR-205
type: adr
title: "Boundary Python/Go — stages LLM permanecem Python; contratos imutáveis"
status: Proposto
phase: "Ato 1 — fundação arquitetural do PLANNER_REVIEW"
date: "2026-05-13"
relates_to:
  - "[[ADR-024]]"
  - "[[ADR-026]]"
  - "[[ADR-093]]"
  - "[[ADR-113]]"
  - "[[ADR-199]]"
  - "[[ADR-200]]"
  - "[[ADR-201]]"
  - "[[ADR-202]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 205"
  - "Stages LLM Python boundary"
  - "Contratos imutáveis parecer"
tags:
  - area/llm
  - area/pipeline
  - area/architecture
  - phase/a11
  - status/proposto
  - type/adr
---

# ADR-205 — Boundary Python/Go — stages LLM permanecem Python; contratos imutáveis

**Status:** Proposto (Ato 1 — fundação arquitetural do PLANNER_REVIEW) • **Data:** 2026-05-13

## Contexto

- Plano canônico `docs/plan/PLANNER_REVIEW/_README.md` Premissa 3 declara explicitamente: "Go pode substituir Python no stage runtime. Inteligência mora em manifests + persona + schemas (language-agnostic); stage é I/O orquestrador (~100-200 linhas) portável." Arquitetura-alvo pós-A6 ([[ADR-113]]) prevê serviços Go progressivamente substituindo serviços Python para componentes CPU-bound, latência-sensitive, ou de alta concorrência.
- Stages LLM são fundamentalmente diferentes de outros stages do pipeline:
  - **I/O bound** (latência dominada por roundtrip ao provider Anthropic/OpenAI; tens-of-seconds vs. tens-of-ms).
  - **Ecossistema maduro existe em Python:** LiteLLM ([[ADR-024]]), Instructor ([[ADR-026]]), Anthropic SDK oficial, OpenAI SDK oficial, `pydantic` para validação Pydantic — quase tudo é Python-first ou Python-only no estado da arte 2026.
  - **Tunning rápido** (mudança de prompt/persona) acontece **fora do código** (manifests YAML + persona Markdown — [[ADR-200]] e [[ADR-201]]).
- Sem pré-compromisso explícito, surge tentação: "se Go substitui o pipeline, vamos portar `parecer_planejador` para Go também". Custo desse port: re-implementar LiteLLM equivalent (ou bind via cgo); re-implementar Instructor equivalent; re-implementar Pydantic equivalent — tudo isso para ganhar 0 latência (tool é I/O bound) e 0 throughput (rate limit do provider domina, não CPU local).

## Alternativas consideradas

1. **Sem pré-compromisso — decisão case-by-case na hora.** Pró: flexibilidade. Contra: cada futuro debate "vamos portar para Go?" custa 30+ min de tempo de eng e abre porta para decisão errada por pressão de consistência ("tudo virou Go, só LLM ficou Python — feio"). **Rejeitada.**
2. **Pré-compromisso "tudo Python" sem justificativa.** Pró: simples. Contra: dogmático; perde oportunidade de migrar componentes CPU-bound legitimamente. **Rejeitada.**
3. **Pré-compromisso "stages LLM permanecem Python; outros stages avaliam Go individualmente; contratos JSON são language-agnostic e imutáveis sem ADR breaking".** Pró: clareza arquitetural; preserva ecossistema Python onde brilha; permite Go onde brilha (CPU-bound: parsing, reconciliação, agregação); contratos imutáveis garantem portabilidade futura sem ADR breaking. **Aceita.**

## Decisão

Adotar **pré-compromisso explícito**: stages LLM permanecem em **Python**; contratos entre stages (JSON, schemas) são **language-agnostic e imutáveis** (mudam apenas via ADR breaking). Outros stages avaliam Go individualmente conforme [[ADR-113]] e roadmap.

### D1. Stages LLM em Python — escopo

Cobrem:
- `parecer_planejador` ([[ADR-199]]) — esta ADR é o caso fundador.
- `section_summaries` ([[ADR-144]]).
- `e1_extract_*` (extração LLM existente).
- `e7_review_llm` (a ser deprecated; superseded por `parecer_planejador`).
- Quaisquer **stages futuros que façam chamada LLM como caminho crítico**.

Stack obrigatória:
- **LiteLLM** ([[ADR-024]]) — proxy universal, sem direct SDK calls.
- **Instructor + Pydantic** ([[ADR-026]]) — structured output.
- **Cache Redis** ([[ADR-144]] pattern) — runtime cache.
- **Fallback determinístico** quando aplicável ([[ADR-144]] pattern).

### D2. Contratos imutáveis (mudam só via ADR breaking)

Para que stages LLM possam **eventualmente** ser portados (hipoteticamente) sem reabrir esta ADR, listamos contratos imutáveis. Mudança em qualquer um deles exige **nova ADR breaking**:

1. **Stage I/O signature** ([[ADR-199]] §D1 para `parecer_planejador`):
   - Reads: artifacts identificados por `(stage, key)` via `ArtifactStore`.
   - Writes: artifacts identificados por `(stage, key)` via `ArtifactStore`.
   - Side-effects: emissão de `Suggestion` aggregate via repository.
2. **Schemas JSON** ([[ADR-202]]):
   - `parecer_planejador.schema.json`, `e5_analysis.schema.json`, `note-planner.schema.json`, `persona.schema.json`.
   - Mudança no schema = bump `schema_version` + ADR breaking.
3. **Manifest DSL** ([[ADR-200]] §D1):
   - JSONPath subset + format hints + null/empty/missing policies.
4. **Persona format** ([[ADR-201]] §D2):
   - Markdown + frontmatter YAML (`id`, `version`, `methodology_anchors`, `persona_hash`).
5. **Aggregate em DB** ([[ADR-199]] §D3):
   - `PlannerReview` aggregate fields + lifecycle states.
6. **HTTP API DTO** (Ato 3 do plano):
   - `GET /workspaces/{id}/reports/{run_id}/planner-review` response shape.
   - Validado por OpenAPI snapshot ([[ADR-109]]).
7. **Stage name no `STAGE_REGISTRY`** ([[ADR-093]]):
   - `parecer_planejador` é o nome canônico; legacy resolve via `resolve_stage_name`.

### D3. Pode mudar SEM ADR breaking — escopo de evolução livre

- Implementação interna do destilador / orchestrator / stage wrapper (refactor estrutural dentro de Python).
- Algoritmo de retry / backoff (sem mudar contrato externo).
- Provider LLM concreto (LiteLLM permuta sem ADR — Anthropic ↔ OpenAI ↔ Ollama ↔ ...).
- Logging / observabilidade interna (campos no log, namespace `mathoms.*` consistente).
- Cache layer (Redis ↔ Postgres+TTL, definido em [[ADR-144]]).
- Tunning de persona / manifest dentro da versão atual.

### D4. Anti-cenário: futuro arquiteto propõe "portar `parecer_planejador` para Go"

Resposta canônica (referenciar esta ADR):

1. Latência ganha? Não — I/O dominated (~10-30s LLM call vs <100ms Python overhead).
2. Throughput ganha? Não — rate limit do provider domina, não CPU local.
3. Manutenibilidade ganha? Não — perde ecossistema Python (Instructor, Pydantic, LiteLLM).
4. Consistência arquitetural? Sim, mas é estética. Custo de port (~2-4 semanas eng + risco) não justifica.
5. Saída: rejeitar **ou** apresentar nova ADR superseding com evidência empírica (e.g., latência local Python virou bottleneck real medido em prod).

### D5. Por que pré-compromisso e não "decidir depois"

- Plano canônico estabelece premissa, **mas** premissa pode ser questionada em futuras revisões da plataforma. Sem ADR, fica como "decisão informal do plano" — sujeita a desafio sem custo de criar ADR breaking.
- Custo de criar ADR é tempo de pensar bem **agora**, antes de decisão impulsiva depois.
- ADR explicit também sinaliza para `build-vs-buy` ([[ADR-024]] já estabeleceu LiteLLM): se decidirmos comprar serviço LLM-as-a-stage (e.g., serviço externo que faz parecer), também é decisão sob esta ADR.

## Consequências

**Positivas:**
- Decisão arquitetural explícita; futuros debates curtos.
- Preserva ecossistema Python onde brilha (LLM tooling).
- Permite Go onde brilha (CPU-bound stages: parsing, reconciliação, agregação) sem dogma.
- Contratos imutáveis garantem portabilidade hipotética **sem necessidade de port**.
- Investimento em manifest/persona/schema (declarativos, language-agnostic) é onde a inteligência mora — não em código.

**Negativas / trade-offs aceitos:**
- Heterogeneidade na pipeline em deploy futuro (alguns stages Python, alguns Go). Mitigação: contratos JSON imutáveis (D2); cada stage rodável como processo isolado via `ArtifactStore`.
- Operações: 2 runtimes para monitorar/deployar/atualizar. Aceito ([[ADR-113]] já contempla).
- Talento: time pode precisar dominar Python E Go para stages diferentes. Aceito.

**Riscos mitigados:**
- **Port impulsivo de stage LLM para Go** — ADR explícita rejeita por default.
- **Contratos drift entre Python e Go** — D2 enumera imutáveis; gates de schema validation enforçam.
- **Dependência implícita de LiteLLM** — D1 explicita; trocar exige ADR breaking.

## Implementação

- **Track(s) do plano:** sem track dedicado (esta ADR é pré-compromisso, não entrega de código). Documenta política aplicada nos Atos 2-6.
- **Files touched:**
  - Esta ADR documenta política. Sem código direto.
  - `docs/reference/ARCHITECTURE.md §17` (arquitetura-alvo pós-A6) ganha referência cruzada após merge.
- **Critério de aceite:**
  - ADR mergeada antes do Ato 2 ([[ADR-200]] manifest, [[ADR-201]] persona, [[ADR-202]] schema).
  - Sempre que futuro PR mencionar "Go" e "stage LLM" na mesma frase, reviewer aponta esta ADR.
- **Gates CI:** nenhum direto (decisão arquitetural não-executável). Hooks indiretos: `dev/check_pipeline_boundaries.py` continua validando que `pipeline/**` não importa frameworks; LiteLLM use enforçado por code review.

**Decisão pendente para outros especialistas:**
- **Nenhuma** — esta ADR é um pré-compromisso fechado pelo `senior-cto`. Reabertura exige nova ADR superseding com evidência empírica concreta.
