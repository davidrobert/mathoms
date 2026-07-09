---
id: ADR-203
type: adr
title: "Tool use híbrido + guardrails — drill-down sob demanda no parecer"
status: Decidido
phase: "Ato 1 — fundação arquitetural do PLANNER_REVIEW"
date: "2026-05-13"
relates_to:
  - "[[ADR-024]]"
  - "[[ADR-111]]"
  - "[[ADR-199]]"
  - "[[ADR-200]]"
  - "[[ADR-202]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 203"
  - "Tool use parecer"
  - "Drill-down LLM"
tags:
  - area/llm
  - area/pipeline
  - area/security
  - phase/a11
  - status/decidido
  - type/adr
---

# ADR-203 — Tool use híbrido + guardrails — drill-down sob demanda no parecer

**Status:** Decidido (Ato 1 — fundação arquitetural do PLANNER_REVIEW) • **Data:** 2026-05-13

## Contexto

- Exec context inicial do parecer (manifest [[ADR-200]]) é **filtrado** para custo/latência. Não cabe E5 inteiro (~50-200KB) no system prompt — input cost explode. Mas LLM pode genuinamente precisar de detalhe pontual: "qual a composição exata da categoria 'Custos fixos' para fundamentar o risco P0 que estou prestes a emitir?". Sem drill-down, LLM ou (a) alucina o detalhe, ou (b) emite sugestão genérica de baixo valor.
- Pattern de **tool use híbrido** (LLM emite tool_call → orchestrator executa → retorno injetado no contexto → LLM continua) é nativo em Anthropic SDK e abstraído por LiteLLM ([[ADR-024]]). Risco: tool use mal-instrumentado vira loop infinito ou ataque de path traversal (LLM pede `$..*` que retorna E5 inteiro — derrota propósito da filtragem).
- Plano canônico `docs/plan/PLANNER_REVIEW/_README.md` §"Ato 4" especifica 2 tools (`get_e5_section`, `get_e5_jsonpath`), cap de 6 iterações, whitelist de paths, cache em sessão, audit trail.

## Alternativas consideradas

1. **Sem tool use — exec context fixo + grande.** Pró: simples; zero infra de tools. Contra: input cost ~5x maior por chamada (~$1+/call workspace grande, CTO-G5); LLM tem informação que **não** precisa, ofuscando o que precisa; impossível para LLM pedir o que faltou (campos_faltantes vira chute, não signal real). **Rejeitada.**
2. **Tool use sem cap.** Pró: LLM "explora" livre. Contra: loop infinito real (LLM emite tool_call atrás de tool_call por incerteza); cost cliff; sem audit trail. **Rejeitada** — cap obrigatório.
3. **Tool use com cap + JSONPath aberto.** Pró: máxima flexibilidade. Contra: ataque de path traversal trivial — LLM emite `$..*` ou `$..[?(...)]`, recebe E5 inteiro, propósito da filtragem do manifest derrotado. **Rejeitada** — whitelist obrigatória.
4. **Tool use com cap + whitelist derivada do schema E5.** Pró: LLM só pode pedir o que existe no schema; cap previne loop; cache evita recompute. **Aceita.**
5. **Tool use com chamadas async ao DB.** Pró: handler poderia carregar campos lazy. Contra: stages LLM não importam SQLAlchemy (CLAUDE.md §Pipeline boundaries); latência adicional por roundtrip DB; complexidade desnecessária — E5 já foi lido no início do stage, está em memória. **Rejeitada.**

## Decisão

Tool use híbrido com **2 tools fechadas**, **cap 6**, **whitelist JSONPath**, **cache em sessão**, **audit trail**, **handler in-memory** (zero DB calls).

### D1. Duas tools

```python
# Tool 1: get_e5_section(key: str) -> dict
# Retorna seção inteira do E5 (paridade com manifest sections).
# Use quando LLM quer contexto de toda a seção (ex.: "kpis_macro").

# Tool 2: get_e5_jsonpath(path: str) -> Any
# Retorna valor em path específico (paridade com manifest paths).
# Use quando LLM quer campo único (ex.: "$.dependentes_irpf.dependente.idade").
```

Schema das tools em formato compatível LiteLLM/Anthropic. Descrições explícitas no JSON schema da tool ensinam LLM quando usar cada uma.

### D2. Cap `max_tool_iterations: 6` (no orchestrator, não no LLM)

- Contador incrementa a cada round-trip LLM → tool → LLM.
- Atingiu cap → orchestrator injeta system message "limite de drill-down atingido, conclua com o que tem" e LLM emite output final sem tool_call adicional.
- Cap **no orchestrator** (não confiável no LLM, que pode ignorar instrução no prompt). Cap **per-LLM-call** (não global do stage).
- Telemetria: histogram `planner_review_tool_iterations` (Prometheus) — alarme se p95 > 4 (sinal de manifest mal-calibrado).

### D3. Whitelist JSONPath derivada do schema E5

- Parser de JSONPath rejeita features perigosas:
  - `$..*` (recursive descent) — **proibido**, derrota filtragem.
  - `$..[?(...)]` (filtros) — **proibido**, complexidade desnecessária.
  - Wildcards em paths não-folha (`$.arr[*]`, `$.obj.*`) — **proibido** exceto onde explicitamente whitelisted.
- ~~Whitelist gerada por script: `dev/build_planner_jsonpath_whitelist.py` cruza `e5_analysis.schema.json` (PR-1 fixou `additionalProperties: false`) e produz lista de paths válidos. Roda em pre-commit; mudança no E5 schema regenera whitelist.~~ *(Correção audit r6, 2026-07-03: o script + pre-commit nunca existiram. A whitelist real deriva do manifest em runtime — `manifest.tools_section_whitelist` → `backend/app/services/parecer_orchestrator.py:410` → `section_whitelist: frozenset` em `pipeline/llm/tools/planner_drill_down.py`. A proteção `path_not_whitelisted` está mantida.)*
- Path fora da whitelist → tool retorna `{"found": false, "path": <path>, "reason": "path_not_whitelisted"}`, **sem** stack trace expondo schema interno.

### D4. Cache em sessão (memória local, ADR-111 categoria b — exceção idempotente)

- Cache `Dict[path, Any]` **local ao orchestrator** durante uma única chamada LLM.
- Justificativa de exceção a [[ADR-111]] (stateless rigoroso): cache é **per-call** (não compartilhado entre requests, não persistente além da chamada), **idempotente** (mesma key → mesmo valor, derivado do E5 já carregado), **categoria b** dos exception types ("singletons lazy idempotentes" — aqui é cache per-call, igualmente determinístico).
- Liberado ao fim da chamada LLM. Não viaja entre workers, não persiste entre requests.
- Mitiga loop "LLM pede mesmo path 3 vezes" — economiza tool invocation mesmo dentro do cap.

### D5. Audit trail em `content_json._meta.tool_trace`

```jsonc
{
  "_meta": {
    "tool_trace": [
      {
        "iter": 1,
        "tool": "get_e5_jsonpath",
        "input": {"path": "$.dependentes_irpf.dependente.idade"},
        "result_summary": {"found": true, "type": "int"},
        "latency_ms": 1,
        "cache_hit": false
      },
      // ...
    ]
  }
}
```

- `result_summary` não persiste o valor cru (evita PII em audit) — só metadata.
- Permite root-cause em incidente: "qual path o LLM consultou antes de emitir o risco X?".
- Persistido no aggregate `PlannerReview` ([[ADR-199]]).

### D6. Tool handler in-memory (zero DB calls)

- Stage carrega E5 uma vez via `ArtifactStore` no início.
- Tools operam sobre **dict em memória** — zero roundtrip DB, zero IO.
- Pipeline boundary preservado: `pipeline/domain/services/parecer_generator.py` recebe `e5_dict` como input, tools são closures sobre ele.

### D7. Tool retorna `{"found": false, ...}` quando ausente — nunca `null` stringificado

- Ausência semântica clara: `{"found": false, "path": "...", "reason": "..."}`.
- Justifica para LLM o porquê (path inválido vs valor `null` no E5 real vs cap atingido).
- LLM emite `campos_faltantes_pediria_se_iterasse[<path>]` quando `found=false` por motivo "path_not_whitelisted" — alimenta M4 ([[ADR-206]]).

### D8. Formatter compartilhado entre destilador (manifest) e tool handler

- Risco crítico (CTO no plano): "Tools podem contradizer destilado — `rentabilidade_pct: '3.2%'` no destilado vs `0.032` raw da tool".
- Mitigação: format hints do manifest ([[ADR-200]]) (`brl`, `pct`, `percent2`) compartilhados via módulo único `pipeline/llm/value_formatter.py`.
- Tool handler aplica **mesmo formatter** do manifest na chave retornada — LLM vê valores numéricos sempre formatados consistentemente.

### D9. Redação anti-injeção em `narrativas` E5

- E5 contém campo `narrativas` (textos gerados por outros stages LLM, [[ADR-144]] e similares). Esses textos podem conter strings hostis se input do cliente foi adversarial.
- Risco (CTO): "Prompt injection via `narrativas` E5". Mitigação:
  - Tool `get_e5_jsonpath` aplica escape de `</system>`, `<|im_end|>`, `</assistant>` (sentinel tokens) **antes** de injetar no exec context.
  - Limite 500 chars por string de `narrativas`.
  - Padrões suspeitos (ex.: "ignore previous instructions", "you are now") detectados via regex → string redactada com placeholder `[REDACTED_SUSPECT_PATTERN]`.

## Consequências

**Positivas:**
- Tool use produz parecer mais preciso (LLM pede o que falta vs alucinar).
- Cap + whitelist + cache + audit = **defense in depth** contra cost cliff, path traversal, injection.
- Telemetria M4 ([[ADR-206]]) ganha signal real ("LLM pediu este path por X% das vezes — destilar no manifest v2").
- Stage stateless preservado ([[ADR-111]]) — cache é per-call, não cross-request.
- Tools são extensíveis (futuro: `get_decision_ledger`, `get_suggestion_history`) sem ADR breaking.

**Negativas / trade-offs aceitos:**
- Cap 6 pode ser atingido em workspaces complexos — LLM emite com info parcial. Mitigação: telemetria de `tool_iterations==cap` detecta sub-calibration; bump cap em ADR posterior se evidência suportar.
- Latência: cada tool round-trip adiciona ~2-5s. Cap 6 → +12-30s worst case. Mitigação: cache hit elimina round-trip; UX já avisa "gerando parecer..." (não-instantâneo, ver [[ADR-144]] consequências).
- Whitelist gerada de E5 schema — desync entre código e schema é possível. Mitigação: regeneração em pre-commit + diff visível.
- Maintenance overhead: novas tools = nova ADR (boundary preservado).

**Riscos mitigados:**
- **Cost cliff workspaces grandes (CTO-G5):** cap 6 + whitelist + circuit breaker `max_total_input_tokens` no orchestrator.
- **Path traversal:** whitelist explícita.
- **Loop infinito:** cap no orchestrator (não confiável no LLM).
- **Tools contradizem destilado (CTO):** formatter compartilhado.
- **Injection via `narrativas`:** redação determinística pré-prompt.

## Implementação

- **Track(s) do plano:** T-15 (`planner-tools-drilldown`).
- **Files touched (Ato 4):**
  - `pipeline/llm/tools/planner_drill_down.py` — definição das tools (schema + handler; o nome `planner_tools.py` previsto originalmente não foi usado)
  - `pipeline/llm/value_formatter.py` — formatter compartilhado
  - ~~`dev/build_planner_jsonpath_whitelist.py` — geração do whitelist~~ *(nunca existiu — ver correção em §D3)*
  - `backend/app/services/parecer_orchestrator.py` — cap + cache + audit wire-up
- **Critério de aceite:**
  - Tools rejeitam paths fora do whitelist (teste unit).
  - Cap 6 enforçado (teste integration com LLM mockado emitindo 10 tool_calls).
  - Audit trail completo no `_meta.tool_trace` (teste golden).
  - Redação anti-injeção pega 3 padrões hostis sintéticos (teste).
  - Formatter idêntico entre manifest e tool (teste).
- **Gates CI:** `pytest pipeline/llm/tools/tests/`, `pytest backend/tests/integration/test_parecer_orchestrator.py`.

**Decisão pendente para outros especialistas:**
- **Cap exato (6 vs 4 vs 8)** — calibrar empiricamente no Ato 4 com fixtures reais; `data-engineer` decide.
- **Limite de tokens hard (`max_total_input_tokens`)** — `sre-devops` define FinOps threshold em conjunto com [[ADR-208]] pricing.
