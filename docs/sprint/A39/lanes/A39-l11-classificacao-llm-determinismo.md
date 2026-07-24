---
id: A39.l11
type: lane
title: "Determinismo da classificação LLM: temperature=0 na via compartilhada + golden sintético + telemetria"
sprint: A39
status: shipped
priority: P2
branch_slug: a39-l11-classificacao-llm-determinismo
adrs: ["[[ADR-081]]", "[[ADR-348]]", "[[ADR-349]]"]
depends_on: ["[[A39.l1]]"]
tags:
  - type/lane
  - sprint/a39
  - status/shipped
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

## Nota de execução (2026-07-24) — co-design reescopou a lane; parte cirúrgica FECHADA

Co-design (senior-cto + prompt-engineer) **reescopou** o plano original. Achado
central do prompt-engineer: `classify_by_llm` usa `anthropic.Anthropic()` cru que
**bypassa o choke-point `LLMService.call`** — que já entrega temp=0, structured
output com enum, `mathoms.llm.*`, budget ([[ADR-173]]), cache ([[ADR-307]]),
anti-injection. É a chamada LLM de **maior volume** do produto, hoje sem cache/
budget/enum-validation. Cabear telemetria/budget à mão no path cru = **build-then-
delete** (VETO senior-cto; `LLMCallLog` nem roda no path CLI-isolado).

**Decisão de escopo (senior-cto fecha):** a l11 fica **cirúrgica** — só os dois
riscos agudos, com adições puras; o re-route (que traz a instrumentação toda de
uma vez) vira **lane própria P1** com [[ADR-349]] `Proposto`.

**Shipado na l11** ([[ADR-348]] `Decidido`):
- `temperature=0` (constante `_LLM_TEMPERATURE`, fora do config — invariante não
  tunável; conforma ao que `section_summary_orchestrator` já faz). Anthropic sem
  seed → argmax quase-determinístico (não "determinístico").
- **Validação estrita de `dest_group`** (o achado mais agudo do co-design):
  `dest_dir_for_group` faz `base/"data"/group` com valor cru → alucinação = doc em
  `data/<lixo>/` (perda silenciosa) + path-traversal. `_DEST_GROUPS` fonte única
  (inclui `comprovantes`); miss → `nao_identificados/`. `doc_type` guard não-fatal.
- Spy offline (sem API) afirmando `temperature==0` + `dest_group` alucinado/`../x`
  → `None`. Gate por-PR, custo zero.

**Reescopo vs o plano original desta lane:**
- **Telemetria `mathoms.llm.classification.*`** → NÃO nesta lane. Vem com o re-route
  ([[ADR-349]]), via `mathoms.llm.*` com `prompt_name="classification"` (namespace
  paralelo VETADO). A observabilidade da chamada de maior volume é a **justificativa**
  do re-route, não algo para meio-consertar num P2.
- **Golden real-LLM N=3** → é owner-gated (custo de API) e melhor construído COM o
  re-route (structured output valida enum). Follow-up na lane do re-route
  (~15-20 fixtures edge PII-zero, k≥2, `dest_group`+`doc_type` exact-match).
- **`caixa.py` extração por visão** tem a mesma omissão de `temperature` — declarado
  **out-of-scope** ([[ADR-348]]): é extração (muda números), não classificação
  (muda rótulos); outro dono/golden.

**Fast-follow rastreado:** re-route pelo `LLMService` — [[ADR-349]] `Proposto`,
lane própria P1 (priorização `product-manager`), faseada (Fase 1 texto+JPG/PNG;
Fase 2 estende choke-point p/ bloco `document` do PDF-imagem).
