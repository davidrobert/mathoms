---
id: A25.l7
type: lane
title: "Decisão do flip warn→strict do evidencia_path (requisito de done da A25)"
sprint: A25
plan: PLAN-data-lineage
status: shipped
priority: P0
branch_slug: evidencia-strict-decision
adrs:
  - "[[ADR-279]]"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a25
  - status/shipped
  - priority/p0
  - area/data-lineage
  - area/llm
---

# A25.l7 — `evidencia-strict-decision` (ÚLTIMA · requisito de done da sprint)

> **Plano:** [[PLAN-data-lineage]] · herdada de [[A24.l4]] (evidencia_path em modo
> `warn` desde 2026-06-10, telemetria ativa). Requisito de fechamento =
> **DECISÃO INFORMADA, não flip incondicional** (decisão owner 2026-06-10).

## Objetivo

Analisar a telemetria do `evidencia_path` e decidir o flip `warn→strict`. A
telemetria vive em `pipeline_stage_logs.output_summary` sob o bloco aninhado
**`evidencia_verification`** — campos `evidencia_verified`, `evidencia_failed`,
`failures_by_layer` (camadas `missing_path`/`whitelist_miss`/`resolve_null`/`value_mismatch`),
`prompt_version`, `needs_review_triggered` (ver `EvidenciaResult.summary` em
`backend/app/services/parecer_evidencia.py`). Só presente em gerações pós-[[A24.l4]]
(telemetria entrou em 2026-06-10, #580).

## Gate (cravado no kickoff)

- **Taxa de violação <5% sobre ≥20 gerações** → flipa: 1 linha
  (`evidencia_verification_mode: strict` em `config/prompts/parecer_planejador.yaml`),
  PR com a análise no corpo.
- **Taxa ≥5%** → NÃO flipa: ajustar regex/prompt (co-design `prompt-engineer`) e
  re-medir.
- **Amostra <20 gerações ao fim da sprint** → registrar decisão "carry-over A26 com
  gate idêntico" e a sprint fecha `done` mesmo assim — o flip não sequestra o
  fechamento.

## Acúmulo de amostra (desde o dia 1 da sprint)

Gerar parecer sobre goldens + dogfood na abertura e ao longo da sprint — a decisão
precisa de amostra; não deixar para o fim. Telemetria ativa desde 2026-06-10
([[A24.l4]] merge #580).

## Decisão (2026-06-16) — **carry-over A26** (amostra insuficiente)

Telemetria medida no DB de dogfood local (`mathoms.db`, stage `review_finances_holistic`).
Apenas **3 gerações** têm o bloco `evidencia_verification` (todas 12–13/06, pós-[[A24.l4]];
as outras 25 do banco são pré-feature). `prompt_version` 1.5.0.

| Geração | verified | failed | `failures_by_layer` |
|---|---|---|---|
| 12/06 | 0 | 7 | missing_path 3 · resolve_null 3 · value_mismatch 1 |
| 12/06 | 1 | 11 | resolve_null 9 · value_mismatch 2 |
| 13/06 | 3 | 14 | whitelist_miss 11 · value_mismatch 3 |
| **Σ** | **4** | **32** | taxa ≈ **89%** (32/36) |

**Gate aplicado:** `3 gerações << 20` → **carry-over A26 com gate idêntico** (3º ramo;
"o flip não sequestra o fechamento"). A taxa ~89% **reforça** a não-flipagem: `strict`
hoje bloquearia quase todo parecer. Modo permanece `warn`.

**Achado acionável p/ A26 (co-design `prompt-engineer`):** 81% das falhas são
**conformidade de citação** — `whitelist_miss` (11) + `resolve_null` (12) + `missing_path`
(3) = 26/32 — e só 19% é `value_mismatch` (6, alucinação de valor). O foco de A26 é
alinhar prompt/whitelist (citar só paths presentes/não-nulos/permitidos), não primeiro
combater alucinação de valor. Amostra é **dogfood local**, não produção (pré-launch ≈ 0).

### Query de referência (re-medição em A26)

```sql
-- Postgres prod: substituir json_extract por output_summary->'evidencia_verification'->>'campo'
SELECT count(*) AS geracoes,
       coalesce(sum(json_extract(output_summary,'$.evidencia_verification.evidencia_verified')),0) AS verified,
       coalesce(sum(json_extract(output_summary,'$.evidencia_verification.evidencia_failed')),0)   AS failed
FROM pipeline_stage_logs
WHERE stage='review_finances_holistic'
  AND json_extract(output_summary,'$.evidencia_verification') IS NOT NULL;
-- taxa = failed / (verified + failed); flipa se taxa < 5% E geracoes >= 20.
```

## Critério de aceite

- Decisão registrada (flip mergeado OU carry-over documentado) com a análise da
  telemetria no corpo do PR; nunca logar o VALOR (PII) — só camada + path.
  ✅ **Cumprido** — carry-over A26 registrado em §Decisão (2026-06-16); telemetria
  agregada PII-free (counts + camadas, zero valor). Flip real é nova lane na A26.

## Owner

Agente da lane; co-design `prompt-engineer` se taxa ≥5%.
