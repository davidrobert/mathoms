---
id: TRACK-citacao-deterministica
type: track
title: "Track A26.l9 — citação determinística (LLM emite path+rótulo; pipeline renderiza valor)"
lane: "[[A26.l9]]"
sprint: A27
plan: PLAN-data-lineage
status: ready
created_at: "2026-06-19"
agent_role: senior-cto
tags:
  - type/track
  - sprint/a27
  - status/ready
  - priority/p1
  - area/data-lineage
  - area/llm
  - breaking/schema
---

# Track A26.l9 — `citacao-deterministica`

> Executa a lane [[A26.l9]] · implementa [[ADR-296]] (`Proposto`→`Decidido` no merge).
> Co-design 6 especialistas feito 2026-06-19 — **não reabrir a decisão**; este track
> só a instancia. **Branch prefix:** `agent/a26-l9-citacao-deterministica/*`.
> **Tese:** o LLM para de digitar o número R$. Emite `(claim sem número, path, rótulo)`;
> o pipeline renderiza o valor da folha do path; o finalize grava o snapshot →
> `value_mismatch` por transcrição vira **impossível por construção**.

## Pré-requisitos (todos satisfeitos exceto a key)

- [x] Deps de código em `main`: catálogo l1 (#654), KPI l6 (#660), catálogo de listas
      l7 (#662), enforcement per-item l8 (#661/#666), ADR-296 (#669).
- [x] **§6 forma do render = D2-puro** (owner, 2026-06-19) — ver seção abaixo.
- [x] **Slice 0 — harness de eval paralelo** committed em
      [`dev/run_parecer_eval_parallel.py`](../../../../dev/run_parecer_eval_parallel.py)
      (#679); o eval sequencial (~1,7h) sofria kill.
- [ ] **`ANTHROPIC_API_KEY` no ambiente** — owner-gated; necessário só para o re-eval
      holdout do critério de aceite (não para escrever o código).

## Passos de execução

Ordem por dependência (cada passo = 1 commit coeso). Reusa o máximo do que já existe.

1. **Contrato / schema (breaking, bump `version` major).**
   [`config/schemas/parecer_planejador.schema.json`](../../../../config/schemas/parecer_planejador.schema.json):
   `evidencia_path: str` singular → `ancoras: [{path, rótulo, valor_renderizado}]` por
   Risco/Sugestao. `path`+`rótulo` vêm do LLM; **`valor_renderizado` é escrito pelo
   finalize, não pelo LLM** (padrão de `suggestion_dedup_key`). Pareceres v1 **não
   migram** (`content_json` imutável, [[ADR-204]]) — o renderer faz dispatch por
   `version`. **Zero Alembic.**

2. **Verificador → `pairing_mismatch`.**
   [`backend/app/services/parecer_evidencia.py`](../../../../backend/app/services/parecer_evidencia.py):
   trocar a camada `value_mismatch` (compara número-da-prosa) por cross-check
   determinístico **`rótulo ↔ seção-dona-do-path`** usando `CatalogEntry.root` (já existe
   em [`parecer_citation_catalog.py`](../../../../backend/app/services/parecer_citation_catalog.py)).
   **Bumpar `EVIDENCIA_VERIFICATION_VERSION`** (invalida cache). Preservar a telemetria da
   l6 (cobertura vs correção) — só troca o nome da camada.

3. **Enforcement — reusar intacto.** Alimentar o `pairing_mismatch` no **mesmo**
   [`enforce_strict_per_item`](../../../../backend/app/services/parecer_strict_enforcement.py)
   ([[ADR-295]]): item dropado (baixo/médio) ou `needs_review` (alta). **Não** criar
   máquina de decisão nova — l9 só troca o sinal que a alimenta.

4. **Finalize — snapshot, não lazy.**
   [`backend/app/services/parecer_finalization.py`](../../../../backend/app/services/parecer_finalization.py):
   resolver cada `path` via catálogo e gravar `valor_renderizado` + `path` no snapshot.
   Lazy-render reescreveria silenciosamente um parecer publicado se o E5 for reprocessado
   → viola [[ADR-204]]. Drift do E5 vira **badge derivado**, nunca sobrescrita.

5. **Determinismo (ADR-090).** Fonte única de formatação = `format_value` do catálogo
   (byte-idêntico ao que o LLM viu). **Fechar o débito float** de `_format_brl` em
   [`pipeline/llm/value_formatter.py`](../../../../pipeline/llm/value_formatter.py) via
   `Decimal(str(v))`. O `<MonetaryValue/>` só **exibe** o valor já resolvido.

6. **Emissão LLM + prompt.**
   [`config/prompts/parecer_planejador.yaml`](../../../../config/prompts/parecer_planejador.yaml)
   + [`pipeline/llm/prompts/parecer_planejador.py`](../../../../pipeline/llm/prompts/parecer_planejador.py):
   reescrever a Regra 11 — **prosa SEM token `R$`** (invariante de contrato: `R$` cru na
   prosa = violação). `evidencia_path` reusa o coerce `EvidenciaPath` ([[ADR-292]],
   path inválido→None); `rótulo` é `Literal` + `BeforeValidator`→sentinela (**nunca
   reask**). **Bumpar `PROMPT_VERSION` major** (orchestrator).

7. **Snapshots derivados.** `make update-openapi-snapshot` (schema mudou) + re-snapshot
   do golden do parecer **isolado** (commit só de baseline, sem código — hook G-c).

## Forma do render — D2-puro (decidido)

Prosa **sem número** + **chips de âncora** (`rótulo` + `valor_renderizado`) no rodapé de
cada card de Risco/Sugestao — em
[`frontend/src/components/report/`](../../../../frontend/src/components/report/) (tipos via
[`frontend/src/lib/api/planner-review.ts`](../../../../frontend/src/lib/api/planner-review.ts)).
Descartados o placeholder `{{N}}` inline e o híbrido: o híbrido vazaria o modelo de
confiança interno (inconsistência visual inline-vs-chip). D2-puro nunca intercala número
autorado na prosa → reforça `number_in_prose_violation == 0`. Validar com `product-designer`
no slice de UI; densidade de chips não pode regredir (anti-sub-citação herdado da l8).

## Gate de aceite (da lane)

- [[ADR-296]] `Proposto`→`Decidido` no merge; emenda [[ADR-279]] §E registrada.
- **Re-eval holdout** (owner-gated): rodar
  `ANTHROPIC_API_KEY=… python3 dev/run_parecer_eval_parallel.py --workers 6`.
  Meta: `anchor_section_incoherence` per-parecer **UB IC95 < 5%**; braço temp=0 = **0**
  (resíduo é design, não variância).
- `number_in_prose_violation == 0`; `value_mismatch` provadamente impossível (teste de
  round-trip path→valor exibido).
- Teste adversarial: âncora `rótulo` incoerente com `path.root` → item dropado (baixo/médio)
  ou `needs_review` (alta), **nunca** publica número no contexto errado.
- Zero novo gatilho de reask (path/rótulo inválido → coerce, não raise — [[ADR-292]]).

## Notas de coordenação

- **Não bloqueia [[A26.l2]]** (flip strict procede sob o gate redefinido). Pode rodar
  em paralelo com [[A27.l1]] (`evidencia-lineage-edge`): slices 1+3 do edge ∥ esta lane;
  slices 2+4 do edge **após** o merge desta.
- Co-design já feito: `senior-cto` (contrato) + `data-engineer` (schema/snapshot) +
  `prompt-engineer` (emissão/eval) + `product-designer` (forma). Reabrir só se um
  pressuposto cair na implementação — então **1 rodada** e escala pro `senior-cto`.
