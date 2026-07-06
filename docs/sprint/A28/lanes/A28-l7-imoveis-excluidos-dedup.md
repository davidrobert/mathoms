---
id: A28.l7
type: lane
title: "imóveis excluídos: dedup tático na projeção + gate de rotulagem do owner"
sprint: A28
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: imoveis-excluidos-dedup
adrs:
  - "[[ADR-246]]"
parallel_with:
  - "[[A28.l5]]"
  - "[[A28.l6]]"
  - "[[A28.l8]]"
tags:
  - type/lane
  - sprint/a28
  - status/in-progress
  - priority/p1
  - area/pipeline
---

# A28.l7 — `imoveis-excluidos-dedup` (Onda 1 · Should tático · gate `G-owner-label`)

## Problema

No dogfood `72883bde`, o módulo `real_estate` cobre só 4 imóveis (R$ 832k) de
~R$ 2,4M em imóveis — **11 entradas excluídas** por "Classificação pendente",
com o **mesmo imóvel repetido 4×** na lista ("CASA - LEONARDO DA VINCI 2707").
A concentração imobiliária de 63,36% — que ancora o risco **Crítico** do
parecer E6 — pode estar subestimada.

Raiz (investigação data-engineer 2026-07-03): a lista de excluídos **não** vem
do payload deduplicado — `real_estate_e5_integration._load_identities` carrega
**todas** as rows de `PropertyIdentity`, que são persistidas no e15 **step 3**
(1 row por declarante×variação) **antes** do dedup [[ADR-246]] rodar no step
3b. O `DedupResult.dropped_property_ids` é calculado e **descartado** — nunca
poda o DB. Payload E5 correto (1 imóvel); projeção de excluídos crua (4 rows).

## Escopo

**Código autônomo (fix tático — seguro, lista é informativa/CTA):**

1. Dedup da projeção de `excluded_properties` no boundary
   (`real_estate_adapter` / `real_estate_e5_integration`): colapsar por
   `endereco_canonical`/`property_id` vencedor do dedup ADR-246 — mesmo imóvel
   aparece 1×.
2. Teste de regressão: fixture co-declarada (titular + cônjuge × 2 anos) → 1
   entrada na lista de pendências.
3. Atualizar o comentário desatualizado em `real_estate_e5_integration.py`
   ("property_id casa por construção") — vale para incluídos, não para órfãos.

**Gate `G-owner-label` (ação do owner):**

4. Rotulagem dos imóveis pendentes em Configurações (pós-dedup, ~7-8 CTAs).

**Pós-gate (derivada — Could, cortável):**

5. Re-medição da concentração imobiliária com módulo cobrindo ≥90% do valor de
   cat_2; atualizar a âncora do risco do parecer no re-run.

## Critério de aceite

- Dogfood re-run: "CASA - LEONARDO DA VINCI 2707" aparece **1×** na lista de
  excluídos; contagem total de pendências = imóveis únicos pendentes.
- **Zero mudança de valor monetário** (dedup só na projeção informativa) —
  goldens de valor intocados; `tests/test_real_estate_metrics_payload.py` e
  `backend/tests/test_real_estate_e5_integration.py` rebaselinados com diff
  explicado.
- Invariante [[ADR-246]] preservado na projeção: soma proibida, maior valor
  vence, label "casal".

## Notas

- **Débito estrutural (A29+, fora desta sprint):** podar as `PropertyIdentity`
  órfãs usando `dropped_property_ids` (soft-delete `superseded_by` > hard
  delete), com migration + backfill idempotente + re-aponte de FK de
  `workspace_property_overrides` para o vencedor, respeitando imutabilidade de
  `codigo_rfb` ([[ADR-225]]). Não misturar com o fix tático.
- Rotulagem é pré-condição do KR de cobertura do plano, não desta lane — a lane
  fecha com o dedup tático.

## Owner

Agente da lane (código) + owner (gate `G-owner-label`); co-design
`data-engineer` feito 2026-07-03.
