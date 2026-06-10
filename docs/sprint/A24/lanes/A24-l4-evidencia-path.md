---
id: A24.l4
type: lane
title: "Data Lineage F4 — evidencia_path: citação verificada E5→E6 no parecer"
sprint: A24
plan: PLAN-data-lineage
status: shipped
priority: P1
branch_slug: dl-f4-evidencia-path
adrs:
  - "[[ADR-279]]"
  - "[[ADR-199]]"
  - "[[ADR-233]]"
depends_on: []
parallel_with: ["[[A24.l1]]"]
tags:
  - type/lane
  - sprint/a24
  - status/shipped
  - priority/p1
  - area/data-lineage
  - area/llm
---

# A24.l4 — `dl-f4-evidencia-path`

> **Plano:** [[PLAN-data-lineage]] · F4 (∥, **independe de F2/F3**). Conforma à
> [[ADR-279]] §E (decisão travada: condicional-obrigatório fora do JSON Schema;
> guardrail 3 camadas; falha → `needs_review`). Co-design `prompt-engineer` +
> `data-engineer` registrado em 2026-06-09.

## Objetivo

Fechar a malha de verificação E5→E6: toda afirmação **monetária** na prosa do
parecer (riscos/sugestões) exige `evidencia_path` que (1) ∈ whitelist E5,
(2) resolve não-nulo no payload E5 **do mesmo run**, (3) casa número↔valor.
Falha → `needs_review` (padrão [[ADR-081]]), nunca hard-fail/retry.

## Decisões de co-design (travadas)

| # | Decisão | Racional |
|---|---|---|
| 1 | Verificação = `_check_evidencia(...)` no **orchestrator** (`parecer_orchestrator.py::_generate_with_llm`), logo após `_check_sigilo`, antes de `finalize_output` | NÃO `model_validator` com context: `ValidationError` viraria retry do Instructor (re-chama LLM); falha de evidência ≠ falha de parse. `_check_sigilo` é o precedente exato (valida pós-LLM → `_needs_review` sem retry) |
| 2 | Camadas 1+2 reusam `PlannerDrillDown.get_e5_jsonpath` em **instância separada** (`format_hints={}`, mesmo `e5_data` do run, mesma `tools_section_whitelist`) | Zero parser novo = drift impossível; instância separada não polui `tool_iterations`/`_meta.tool_trace` (KR3); sem format_hints o valor vem cru para o match |
| 3 | Detecção de prosa: regex **ancorada em `R$`** (`R$ 1.234,56`, `R$ 84.000`, `R$ 1,2 mi`, `R$ 800 mil`) | Percentuais/anos/multiplicadores ("6 meses", "25×") ficam FORA — derruba falso-positivo |
| 4 | Match (camada 3) em **cents int** ([[ADR-090]]): prosa com precisão de centavos → exato; prosa abreviada → **meia-casa-significativa** (`R$ 1,2 mi` ⇒ [1.150.000, 1.250.000)) — não % fixo | `R$ 1,2 mi` vs `1,18 mi` passa (arredondamento legítimo); vs `1,0 mi` falha. Múltiplos números na prosa: **≥1 casa** com o valor resolvido |
| 5 | Rollout: nasce em modo **`warn`** (loga violação, não marca needs_review) + **bump da cache key** (verification_version no composite) | warn elimina o risco de needs_review storm; key bump garante que gerações novas carregam a verificação (estoque antigo expira por TTL 7d). Flip `warn→strict` em PR separado após telemetria de canary |
| 6 | Prompt: instrução additive + 1 exemplo; `PROMPT_VERSION` 1.2.0 → **1.3.0** | gate `check_prompt_version_bumped` |
| 7 | Telemetria: agregado em `pipeline_stage_logs.output_summary` (`{evidencia_verified, evidencia_failed, failures_by_layer, needs_review_triggered}`) + detalhe em `_meta.evidencia_verification` no `content_json` | **Zero timestamp/latência no bloco persistido** (preserva `immutable_hash`/byte-identidade G3); nunca logar o VALOR (PII) — só camada + path. Sem tabela nova (YAGNI) |
| 8 | Limitação documentada: camada 3 verifica **magnitude, não semântica** — colisão de valor (path certo-sintaxe apontando para outro campo de mesmo valor) é resíduo aceito | verificar semântica exigiria LLM (loop) |

## Eval (golden estrutural, LLM mockado)

≥5 negative: (1) path fora da whitelist → `whitelist_miss`; (2) path não resolve
→ `resolve_null`; (3) número≠valor → `value_mismatch`; (4) **prosa com `R$` e
`evidencia_path=None`** (gatilho central); (5) path resolve para valor errado.
≥2 positive (match exato em cents + abreviado meia-casa) + 1 neutro (sem `R$` na
prosa, sem path → passa) + caso "prosa com 2 números, 1 casa → ok" (trava
semântica ≥1-casa). Teste de paridade dos 3 regex de JSONPath (resolver /
Pydantic / `$defs`).

## Critério de aceite

- `_check_evidencia` no orchestrator, padrão idêntico a `_check_sigilo`; modo
  `warn` default no merge.
- Golden estrutural completo (5 neg + 2 pos + 1 neutro) verde.
- Delta de tokens do `SYSTEM_PROMPT_TEMPLATE` **< 5%** (teste estático).
- `PROMPT_VERSION` 1.3.0; `dev/check_prompt_version_bumped.py` verde.
- `dev/check_planner_manifest_coverage.py` verde **sem** `--update-snapshot`.
- Cache key bumpada; teste: cache pré-F4 não é servido pós-bump.
- JSON Schema do parecer e persistência **inalterados** (zero migração).
- Limitação "magnitude, não semântica" anotada na [[ADR-279]] (nota §E).

## Não-escopo

- Flip `warn→strict` (PR separado, pós-telemetria) — **promovido a requisito de
  fechamento da Sprint A25** (decisão owner 2026-06-10; registrado em
  [[PLAN-data-lineage]] §Ondas, Onda 4).
- UX do estado `needs_review` no relatório (product-designer, fase F6).
- Threshold de materialidade do match (se contencioso → `financial-planner`).

## Owner

Agente da lane com co-design `prompt-engineer` + `data-engineer` (2026-06-09).
