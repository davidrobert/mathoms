---
id: ADR-199
type: adr
title: "Parecer do planejador (E6) supersede review_finances — aggregate PlannerReview event-sourced"
status: Decidido
phase: "Ato 1 — fundação arquitetural do PLANNER_REVIEW"
date: "2026-05-13"
amended_at: ["2026-06-12", "2026-08-03"]
relates_to:
  - "[[ADR-024]]"
  - "[[ADR-026]]"
  - "[[ADR-076]]"
  - "[[ADR-093]]"
  - "[[ADR-128]]"
  - "[[ADR-131]]"
  - "[[ADR-136]]"
  - "[[ADR-143]]"
  - "[[ADR-144]]"
  - "[[ADR-153]]"
  - "[[ADR-187]]"
  - "[[ADR-188]]"
  - "[[ADR-200]]"
  - "[[ADR-201]]"
  - "[[ADR-202]]"
  - "[[ADR-203]]"
  - "[[ADR-204]]"
  - "[[ADR-205]]"
  - "[[ADR-206]]"
  - "[[ADR-207]]"
  - "[[ADR-208]]"
  - "[[ADR-270]]"
  - "[[ADR-289]]"
supersedes:
  - "[[ADR-128]]"
superseded_by: []
aliases:
  - "ADR 199"
  - "Parecer planejador"
  - "PlannerReview aggregate"
tags:
  - area/llm
  - area/pipeline
  - area/report
  - phase/a11
  - status/decidido
  - type/adr
---

# ADR-199 — Parecer do planejador (E6) supersede review_finances — aggregate PlannerReview event-sourced

**Status:** Decidido (Ato 1 — fundação arquitetural do PLANNER_REVIEW) • **Data:** 2026-05-13

> **Emenda 2026-08-03 ([[A40.l17]]):** dois invariantes do cache/custo do parecer
> nomeados — o cache guarda **somente output aprovado** (veredito negativo não é
> cacheável) e custo pertence ao envelope de **todo** retorno pós-chamada, com
> `cost_known=False` quando não há registro. Ver §Emenda 2026-08-03 no fim.

## Contexto

- Stage `review_finances` (E7-review-llm, [[ADR-128]]) produz hoje o artifact `("E7-review", "review_llm")` que **não é consumido por nenhum endpoint nem componente React** — output órfão descoberto no brainstorm 2026-05-12. O custo LLM é pago, o lineage é mantido, e nenhum cliente vê o resultado.
- Brainstorm consolidado em `docs/plan/PLANNER_REVIEW/_README.md` propõe substituir `review_finances` por um **parecer holístico orientativo** que (a) é renderizado em seção própria do relatório, (b) emite `Suggestion` aggregate ([[ADR-153]]) com `dedup_key` estável, (c) tem persona versionada (rules-as-code, estende [[ADR-143]]), (d) tem manifest declarativo espelhando [[ADR-144]], (e) reusa `Decision` event-sourced ([[ADR-136]]) para sugestões que viram compromissos.
- Plano canônico: `docs/plan/PLANNER_REVIEW/_README.md` §"Decisão central" formaliza substituição (não complementação) porque coexistência informal duplicaria custo LLM, ambiguidade narrativa, dois prompts pra manter sincronizados, dois schemas, dois artifacts.

## Alternativas consideradas

1. **Complementar — manter `review_finances` rodando em paralelo com `parecer_planejador`.** Pró: zero risco de regressão (output antigo já era órfão). Contra: dobro de custo LLM por relatório premium, dois prompts/schemas/personas a manter sincronizados, drift garantido entre os dois. **Rejeitada** — `review_finances` não tem consumer, não há "regressão" a evitar.
2. **Refator in-place do `review_finances`** (mesmo stage, mesmo artifact, novo prompt/schema). Pró: reaproveita slot no `STAGE_REGISTRY`, sem migration. Contra: viola [[ADR-093]] (nome de stage descritivo deve refletir intenção — `review_finances` é genérico e ambíguo, `parecer_planejador` é específico); confunde lineage histórico (artifacts antigos sob mesmo `stage` mas com schema diferente); reabre [[ADR-128]] em vez de superseder limpo. **Rejeitada** — clareza arquitetural vale o stage novo.
3. **Tabela `planner_reviews` dedicada** (aggregate em DB próprio, não em `pipeline_artifacts`). Pró: queries de dashboard sem JOIN em JSONB do artifact; índices por `status/persona_hash/manifest_version` triviais. Contra: duplica lineage (artifact + tabela), exige adapter de sync, viola [[ADR-131]] (relatório referencia pipeline artifact por FK); pareceres re-gerados produzem N linhas com semântica ambígua. **Rejeitada com fallback** — preferida pelo `data-engineer` no brainstorm; ADR aceita projection materializada `planner_review_findings` posterior se dashboard exigir, sem mudar fonte de verdade.
4. **Parecer como output direto do E5 (não stage separado).** Pró: zero infra nova. Contra: E5 vira misto (determinístico + LLM holístico), quebra invariante "E5 produz `analise_financeira` JSON estruturado", complica cache (E5 hoje é puro determinístico, fora do regime [[ADR-144]]); impossível regenerar parecer sem regenerar E5 inteiro. **Rejeitada** — separação de stages é o padrão do pipeline ([[ADR-093]]).

## Decisão

Adotar **substituição** com aggregate `PlannerReview` event-sourced, persistido em `pipeline_artifacts` (não em tabela dedicada), seguindo o pattern de [[ADR-144]] (section_summaries) e [[ADR-128]] (E7-review).

### D1. Novo stage `parecer_planejador` (E6)

- Stage name no `STAGE_REGISTRY` (`pipeline/stage_spec.py`): `"parecer_planejador"` (descritivo, [[ADR-093]]).
- `depends_on = ["analyze_finances"]` (lê E5 `("E5", "analise_financeira")`).
- Posição no `FULL_ORDER`: após E5, antes da renderização do relatório.
- Sem dependência circular com E7 (review antigo é fora da cadeia).

### D2. Aggregate root `PlannerReview` event-sourced

Lifecycle: `Pendente → Gerado → Publicado → Superseded`.

- `Pendente`: stage agendado, ainda não rodou (sem artifact).
- `Gerado`: LLM emitiu output válido contra schema; artifact escrito; ainda não exposto no relatório (gate dogfood / feature flag premium).
- `Publicado`: relatório publicado ([[ADR-187]]); parecer congelado, imutável.
- `Superseded`: re-run subsequente criou versão nova; `superseded_by_id` aponta para sucessor; histórico preservado eternamente (auditoria CVM/LGPD — ver [[ADR-204]]).

Lineage: cada `PlannerReview` referencia `pipeline_run_id` (pattern [[ADR-131]]) + `e5_artifact_id` (FK pra `pipeline_artifacts.id` do snapshot E5 que alimentou a geração). Re-run produz novo aggregate; aggregate antigo flippa para `Superseded`.

### D3. Persistência em `pipeline_artifacts` + projection materializada opcional

- **Fonte de verdade:** artifact `("E6-parecer", "parecer_planejador")` em `pipeline_artifacts` (JSONB). Lifecycle padrão [[ADR-131]] aplica.
- **Mapping no `artifact_store.py`:** `E6-parecer` → `E6_parecer/parecer_planejador-6_parecer.json` (filename pattern consistente com sufixos de stage, CLAUDE.md §Convenções de naming).
- **Sem tabela `planner_reviews` dedicada na V1.** Projection materializada `planner_review_findings(review_artifact_id, ancora, prioridade, tema, severidade)` entra em sprint posterior **somente se** dashboard de operação exigir queries que JOIN em JSONB tornem proibitivas. Premissa: análise inicial cabe em SQL com `jsonb_path_query`.
- **Status / persona_hash / manifest_version / model_id / cost_usd_cents / tokens_in/out / tool_call_count** persistem no artifact JSONB sob `_meta`, sem coluna dedicada. Repository expõe getters tipados.

### D4. Boundary Pipeline ↔ Application preservado

- `pipeline/stages/parecer_planejador.py` (stage wrapper, ≤100 linhas): orquestrador puro; lê via `ArtifactStore`, chama domain service, escreve via `ArtifactStore`. Sem `fastapi`/`celery`/`sqlalchemy` (CLAUDE.md §Pipeline não importa framework).
- `pipeline/domain/services/parecer_generator.py`: domain logic (validação, invariantes, redação anti-injeção).
- `backend/app/services/parecer_orchestrator.py`: wire-up (manifest + persona + cache Redis + `LLMService` + fallback determinístico). Espelha `section_summary_orchestrator.py` ([[ADR-144]]).
- `backend/app/models/planner_review.py`: model SQLAlchemy fino sobre `pipeline_artifacts` (aggregate root + repository pattern).

### D5. Reuso obrigatório de aggregates existentes

Parecer **não cria entidades novas**. Sugestões emitidas viram `Suggestion(origin="llm", source_artifact_id=<parecer_id>)` ([[ADR-153]]). Sugestões P0 promovidas a compromissos viram `Decision` ([[ADR-136]]). Sugestões promovidas a execução viram `Task` (existente). Cross-linking via `<SuggestionCalloutInline sectionId="...">` é automático nas seções fonte.

### D6. Output schema com invariantes (ver [[ADR-202]])

Output validado por `config/schemas/parecer_planejador.schema.json`: 6+ sections (diagnostico, pontos_fortes, riscos, sugestoes_execucao/tatico/estrategico, metricas, notas_metodologicas), enums fechados (severidade, prioridade com max 2 P0, confiança, `tema_canonico` 9-valor), regex anti-ticker no body, hard caps (riscos ≤ 12, sugestões ≤ 15 distribuídas 5/5/5 por horizonte, métricas ≤ 10). Falha de validação → `status="needs_review"`, artifact não-publicado.

### D7. ADR-128 fica superseded; cutover em sprint+1

- ADR-128 ganha `superseded_by: [[ADR-199]]` no frontmatter desta sprint (Ato 1).
- ADR-128 mantém `status: Decidido` até cutover real (Ato 6 do plano canônico).
- `review_finances` permanece no `STAGE_REGISTRY` como `deprecated` durante Atos 2-5; removido em sprint+1 após beta verde.
- Pareceres antigos de `review_finances` em `pipeline_artifacts` **não são deletados** — auditoria/lineage; lifecycle [[ADR-131]] preserva.

## Consequências

**Positivas:**
- Output órfão eliminado: parecer agora renderiza, gera Suggestion/Decision/Task, fecha o loop produto.
- Lineage explícito: `PlannerReview → pipeline_run → e5_artifact → workspace`; auditável end-to-end.
- Substituição limpa (não complementação): um stage, um schema, um prompt, um custo LLM por relatório.
- Pattern reusável: outras "interpretações holísticas LLM" futuras (executive summary, peer comparison) seguem o mesmo molde sem nova ADR estrutural.
- Reuso de aggregates produtivos (`Suggestion`/`Decision`/`Task`) — zero código novo no operating system de recomendações.

**Negativas / trade-offs aceitos:**
- Stage novo no pipeline = mais um nó no DAG, mais um ponto de falha. Mitigação: cache Redis 7d + fallback determinístico (sem-LLM produz parecer vazio + alerta operacional, relatório não falha).
- Dashboard de operação ("quantos pareceres com `risco severidade=Crítica` neste workspace?") precisa de `jsonb_path_query` até projection materializada existir. Aceito: V1 não tem dashboard.
- `pipeline_artifacts` cresce ~10-30KB por parecer; com 1k workspaces × 12 pareceres/ano = ~360MB/ano. Aceito; retention policy [[ADR-131]] aplica.

**Riscos mitigados:**
- **Coexistência ambígua review_finances ↔ parecer_planejador:** supersedure explícita, cutover em sprint definido (Ato 6).
- **Custo dobrado por coexistência:** substituição (não complementação) elimina.
- **Output sem consumer (problema atual ADR-128):** parecer tem section dedicada no relatório (`S_parecer`), endpoint dedicado, emissão de Suggestion automática.

## Implementação

- **Track(s) do plano:** T-02 (`planner-adr-mae-supersede`) — esta ADR é a entrega do track.
- **Files touched (futuros Atos 2-5):**
  - `pipeline/stage_spec.py` — novo entry no `STAGE_REGISTRY`
  - `pipeline/stages/parecer_planejador.py` — stage wrapper
  - `pipeline/domain/services/parecer_generator.py` — domain logic
  - `pipeline/artifact_store.py` — mapping `E6-parecer` → `E6_parecer/`
  - `backend/app/models/planner_review.py` — aggregate root model
  - `backend/app/repositories/planner_review.py` — repository
  - `backend/app/services/parecer_orchestrator.py` — wire-up
  - `backend/app/api/planner_review.py` — endpoint
  - `config/schemas/parecer_planejador.schema.json` — output schema ([[ADR-202]])
- **Critério de aceite:**
  - ADRs filhas ([[ADR-200]] a [[ADR-208]]) também `Proposto` antes do PR de Ato 2.
  - [[ADR-128]] marca `superseded_by: [[ADR-199]]` neste PR de Ato 1.
  - Plano canônico `docs/plan/PLANNER_REVIEW/_README.md` referenciado em cada ADR filha.
- **Gates CI:** `dev/validate_frontmatter.py`, `dev/check_doc_filename_id.py`, `dev/check_doc_links.py`, `dev/check_adr_anchors.py`, `dev/build_doc_index.py --check`.

**Decisão pendente para outros especialistas:**
- **Pricing exato (Premium tier)** — `gtm-strategist` fechou faixa R$ 79-149/mês BYOK em [[ADR-208]]; valor final + cobrança por workspace vs. por usuário pendente.
- **Mapeamento `ancora_metodologica → tema_canonico`** (1:N) — `financial-planner` co-design no Ato 2 ([[ADR-207]]).
- **Política de retenção pareceres `Superseded`** — `data-engineer` decide se TTL aplica ou se retém eternamente (default: reter, auditoria).

## Emenda 2026-06-12 — `prompt_version` entra na cache key

Incidente do parecer (ver emenda em [[ADR-270]]) expôs bug latente: a chave Redis
(`compute_cache_key`, pattern ADR-144) compunha
`workspace:e5_hash:manifest_version:schema_version:model_id:evN` — **sem**
`PROMPT_VERSION`. Bump de prompt (ex.: 1.4.0 → 1.5.0, limites de concisão
pós-migração [[ADR-289]]) não invalidava cache: parecer cacheado continuava
servindo output do prompt velho até o TTL (7d), e cache hit nunca exercitava o
prompt novo — tornando todo bump cosmético em hit.

**Decisão:** o prompt é entrada da geração, logo é entrada da chave.
`compute_cache_key` ganha `prompt_version` (default `PROMPT_VERSION` do módulo
de prompts) no composite (`:p{prompt_version}`). Todo bump futuro é
auto-invalidante; alternativa de bumpar `manifest_version` "de carona" foi
rejeitada — manifest descreve a projeção do E5, não o prompt. Teste:
`tests/test_parecer_orchestrator.py::test_cache_key_changes_with_prompt_version`.

## Emenda 2026-08-03 — cache guarda só output publicável; custo pertence a todo retorno pós-chamada

Origem: A40.l17, aberta pelo run `2ded7aab` (o `output_summary` do stage reportou
`tokens {in:0,out:0}, cost_usd 0.0` enquanto o `llm_call_log` registrava
76.133/17.000 e US$ 0,4834). Co-design `prompt-engineer` + `senior-cto`,
2026-08-03. Dois invariantes que já valiam por topologia do call-graph — e por
isso eram re-litigáveis — passam a ser decisão registrada:

**E1. O cache semântico do parecer guarda somente output aprovado por todos os
guardrails; veredito negativo não é cacheável.** A Decisão 3 original da
[[A40.l17]] ("escrever cache no caminho `needs_review`") está **rejeitada**, por
dois motivos independentes:

- O valor cacheado é o `ParecerPlanejadorOutput`, não o envelope: `status` e
  `error_detail` morrem no round-trip, e um hit devolve o valor com o `status`
  default (`"Gerado"`). Cachear o placeholder de `needs_review` o serviria como
  parecer publicável — a docstring do próprio `empty_needs_review_output` diz
  *"não é salvo nem publicado"*.
- Sob `temperature 0.1`, o veredito de red line / sigilo / evidência é função da
  **amostra**, não do input: **a re-geração é o retry**. Cachear a amostra
  rejeitada por 7 dias — sem primitiva de `delete` no `LLMCacheBackend` —
  converte um sorteio ruim em bloqueio determinístico de uma semana. Re-pagar é
  o preço de não travar amostragem estocástica. Continuidade da [[ADR-307]] §5
  ("write só em retorno validado — nunca exceção, nunca erro"), aplicada à
  camada que a §6 daquela ADR escopa para cá.

Se "não re-tentar agora" virar necessidade real, a forma é **cooldown** (key
própria com timestamp + attempt_count, TTL ≤15 min, zero payload — padrão
rate-limit da [[ADR-111]]), nunca cache de output; exige lane + decisão próprias
e primitiva de flush antes.

**E2. Custo/tokens pertencem ao envelope de todo retorno pós-chamada; ausência
de registro após tentativa é `cost_known=False`, não zero.** `_needs_review`
recebe as métricas da chamada (VO `LLMCallMetrics`, extraído uma única vez no
orchestrator), em paridade com o sucesso. E como `LLMService.call` só registra
em `summary.calls` **após** `create()` retornar, falha pós-cobrança (reask
storm, timeout) não deixa rastro nem ali nem em `llm_call_log` — esse `0.0` é
ignorância, não gasto zero, e sai marcado `cost_known=False` (paridade com a
coluna homônima de `LLMCallLog`). Recuperar o valor real dessa classe exige
mudança no choke-point (`litellm_client`) e fica **fora desta emenda** — é
trabalho futuro com emenda à [[ADR-173]].

Escopo intocado: o hard-stop de budget da [[ADR-173]] lê `llm_call_log` e nunca
leu `output_summary` — o defeito era de telemetria/leitura humana, não de
segurança de budget. Gates: `tests/test_parecer_cache_policy.py` (E1, com prova
de mutação) e `tests/test_parecer_custo_em_needs_review.py` (E2, polaridade
pinada nos dois sentidos).
