---
id: A39.l11
type: lane
title: "Determinismo da classificação LLM: temperature=0 na via compartilhada + golden sintético + telemetria"
sprint: A39
status: planned
priority: P2
branch_slug: a39-l11-classificacao-llm-determinismo
adrs: ["[[ADR-081]]"]
depends_on: ["[[A39.l1]]"]
tags:
  - type/lane
  - sprint/a39
  - status/planned
  - priority/p2
  - area/pipeline
  - area/dados
---

# A39.l11 — `classificacao-llm-determinismo` (achado PC-07 · via LLM)

## Problema (certificação 2026-07-23)

A chamada LLM de classificação (`route_documents.classify_by_llm`,
`route_documents.py:569-573`) **não passa `temperature` nem seed** → roda em
`temperature=1.0` default. **Certificar um classificador não-determinístico mede
ruído, não cobertura** (prompt-engineer). O model é família (`claude-sonnet-4-6`),
não snapshot com data; a confidence é auto-reportada, não calibrada; não há
telemetria estruturada (só `log()` plano).

Isto é pré-condição para qualquer certificação da via LLM (o fallback do padrão
[[ADR-081]] regex→LLM→needs_review) — e **muda o runtime de TODO upload em prod**,
não só o harness.

## Escopo

- **ADR `Proposto` nova ANTES do PR de impl** (temperature=0 na via
  compartilhada é mudança de invariante de runtime; co-design senior-cto):
  `temperature=0` em `classify_by_llm`. Anthropic não expõe seed → aceite
  "quase-determinístico" + golden N=3 para detectar flip residual (lição
  determinismo residual em prod).
- **Golden sintético por tipo** em `tests/llm_golden/classification/`: preview
  autoral reproduzindo o **sinal estrutural** (headers), **PII substituída por
  token sintético**; expected = `{e0_doc_type, dest_group, needs_review, min_conf}`.
- **Telemetria `mathoms.llm.classification.*`** (ADR-110): `prompt_version`
  (SHA256 do template), `model`, `tokens_in/out`, `latency_ms`, `confidence`,
  `source` (`regex|llm_fallback`), `needs_review`, `cost_usd_estimated`. Drift:
  needs_review rate por tipo; share `source=llm_fallback` subindo; distribuição
  de confidence.

## Critério de aceite

- `temperature=0` presente na chamada; golden N=3 com **0 flips** de `e0_doc_type`.
- `pytest tests/llm_golden/classification -q` verde; gate por **match de
  doc_type contra golden**, não pelo número de confidence (auto-reportado).
- Telemetria `mathoms.llm.classification.*` logando prompt-version hash + tokens
  + latência.
- `rg` de CPF/valor/nome em `tests/llm_golden/` = 0 hits (PII-zero).

## Risco

Médio — `temperature=0` muda o comportamento de classificação de **todo upload em
prod** (via compartilhada), não só do harness. Mitigação: golden N=3 + ADR-gate +
co-design senior-cto antes do PR. P2 trailing.
