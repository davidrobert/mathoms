---
id: A26.l9
type: lane
title: "citação determinística: renderizar valor R$ da folha (path) — value_mismatch → 0 estrutural"
sprint: A26
plan: PLAN-data-lineage
status: planned
priority: P1
branch_slug: citacao-deterministica
adrs:
  - "[[ADR-296]]"
  - "[[ADR-202]]"
  - "[[ADR-279]]"
depends_on:
  - "[[A26.l1]]"
parallel_with:
  - "[[A26.l6]]"
  - "[[A26.l7]]"
  - "[[A26.l8]]"
tags:
  - type/lane
  - sprint/a26
  - status/planned
  - priority/p1
  - area/data-lineage
  - area/llm
  - breaking/schema
---

# A26.l9 — `citacao-deterministica` (Onda 6 · cobertura de citação · Regime A)

> **Origem:** "Caminho aberto 1" da [[A26.l8]]. Implementa [[ADR-296]]. Co-design
> 6 especialistas 2026-06-19. **Escopo de sprint (product-manager): A27 / Onda 6**,
> NÃO consolidação A26 — é feature de *contrato*, e a A26 (desligar redes) fecha via
> [[A26.l2]] com o gate redefinido, sem esta lane. Registrada em A26 como origem;
> **Could / cortável; NÃO bloqueia o flip strict.** **Urgência rebaixada (2026-06-19):**
> o re-eval no 1.9.0 (regra de pareamento) levou needs_review de 22% → **6%**, abaixo do
> budget ≤15% da [[A26.l2]] — a l9 deixa de ser "necessária p/ viabilizar o flip" e vira
> **polir o resíduo de 6%→0** (incl. o núcleo determinístico que prompt não resolve: temp=0 3/10).

## Problema

Eval 1.8.0 (strict): gate per-parecer `needs_review` 22% (UB 35%) — não fecha <5%.
Resíduo do `value_mismatch` = **~87% wrong_pairing** (número REAL do E5, path/conceito
errado), **0% abreviação**. Raiz: o LLM **digita o número** e faz duas escolhas
independentes (número X, path Y) que divergem. A [[A26.l8]] (enforcement per-item) já
garante "0 número errado publicado" (drop/needs_review), mas não fecha o gate porque
73% das falhas são severidade alta → needs_review.

## Decisão ([[ADR-296]])

**O LLM para de autorar o número.** Emite `(claim SEM número, evidencia_path, rótulo)`;
o pipeline **renderiza o valor da folha** do path; o finalize grava o **snapshot**.
`value_mismatch` por transcrição vira **impossível por construção**.

**D1 (número inline renderizado do path) foi VETADO** (senior-cto + product-designer):
força número==valor-do-path → verificador sempre passa → wrong_pairing **indetectável**.
É a auto-correção que a [[ADR-295]] rejeitou, agravada.

## Escopo

1. **Contrato (schema breaking, bump major):** `evidencia_path: str` → `ancoras:
   [{path, rótulo, valor_renderizado}]` por Risco/Sugestao. `path`+`rótulo` do LLM;
   `valor_renderizado` escrito pelo finalize (não pelo LLM). Pareceres v1 **não
   migram** (`content_json` imutável, [[ADR-204]]); renderer faz dispatch por `version`.
   Zero Alembic. (Co-design `data-engineer`.)
2. **Cross-check determinístico `rótulo ↔ seção-do-path`** (`CatalogEntry.root` já
   existe) substitui a camada `value_mismatch` por `pairing_mismatch`; alimenta o
   **mesmo `enforce_strict_per_item`** ([[ADR-295]] reusado). `EVIDENCIA_VERIFICATION_VERSION`
   bump. Telemetria l6 (cobertura/correção) preservada — só troca o nome da camada.
3. **Snapshot, não lazy** (persiste `path` + `valor_renderizado`); imutabilidade
   ([[ADR-204]]). Drift do E5 vira badge derivado, nunca sobrescrita.
4. **Determinismo (ADR-090):** `format_value` no finalize (fonte única, = catálogo l1);
   fechar débito float de `_format_brl` via `Decimal(str(v))`. `<MonetaryValue/>` só exibe.
5. **Emissão LLM:** prosa SEM token R$ (invariante de contrato: `R$` cru na prosa =
   violação); `evidencia_path` reusa coerce [[ADR-292]]; `rótulo` é `Literal`+coerce→sentinela
   (nunca reask). Regra 11 reescrita; `PROMPT_VERSION` major. (Co-design `prompt-engineer`.)
6. **Forma do render — DECIDIDO: D2-puro** (owner, 2026-06-19). Prosa sem número +
   chips de âncora (`rótulo`/`valor_renderizado`) no rodapé do card. Descartados o
   **placeholder `{{N}}` inline** (prompt-engineer — preservava leitura) e o **híbrido**
   (senior-cto — inline quando `rótulo==root`, senão chip): product-designer argumenta
   que o híbrido vaza o modelo de confiança interno (inconsistência visual) e o D2-puro
   é o mais seguro — nunca intercala número autorado na prosa, reforça o invariante
   `number_in_prose_violation == 0`.

## Critério de aceite

- [[ADR-296]] `Proposto`→`Decidido` no merge da impl; emenda [[ADR-279]] §E registrada.
- Re-eval holdout (owner-gated): **`anchor_section_incoherence` per-parecer UB IC95
  <5%** (ground-truth = catálogo, automatizável); braço temp=0 = 0 (resíduo é design).
- `number_in_prose_violation == 0` (contrato: LLM nunca digita R$); `value_mismatch`
  provadamente impossível (teste de round-trip path→valor exibido).
- Densidade de âncoras não cai (anti-sub-citação reusado da l8); cobertura não regride.
- Teste adversarial: âncora `rótulo` incoerente com `path.root` → item dropado (não
  falsifica); alta severidade → needs_review.
- Zero novo gatilho de reask (path/rótulo inválido → coerce, não raise — [[ADR-292]]).
- Schema bump major; `make update-openapi-snapshot`; golden re-snapshot isolado.

## Notas

- **Não bloqueia [[A26.l2]]:** o enforcement da l8 já protege o usuário (0 falso
  publicado). O flip strict procede sob o gate redefinido (segurança binária +
  budget de needs_review), independente da l9.
- **Harness paralelo: ✅ committed** em `dev/run_parecer_eval_parallel.py` (6 workers,
  ~13 min; [#679](https://github.com/davidrobert/mathoms/pull/679)) — era pré-requisito
  (o eval sequencial de ~1,7h sofre kill). Resta `ANTHROPIC_API_KEY` no ambiente p/ rodar.
- **l9 coexiste com l8** (não supersede): l8 é a máquina de decisão; l9 muda o sinal.

## Owner

Agente da lane (A27); co-design `senior-cto` (contrato) + `data-engineer` (schema/
snapshot) + `prompt-engineer` (emissão/eval) + `product-designer` (forma do render) —
feito 2026-06-19.
