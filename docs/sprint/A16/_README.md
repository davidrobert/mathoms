---
id: MOC-sprint-a16
type: moc
title: "Sprint A16 — Flip ADR-235 (`nu_proprietario` no enum `classification`)"
aliases: ["A16", "Sprint A16"]
sprint_status: paused
---

# Sprint A16 — Flip ADR-235 (`nu_proprietario`)

> **Status:** `paused` — sprint dedicada criada com escopo aberto. Não promovida para `current` (decisão de priorização em aberto pós-A15). Para retomar, edite o frontmatter (`paused → current`) e regenere `_generated/`.

## Resumo

Sprint **dedicada** à implementação de [[ADR-235]] (Proposto · 2026-05-20) — adiciona valor `nu_proprietario` ao enum `classification` para cobrir o caso de imóvel em nu-propriedade com usufruto vitalício de terceiro (cliente é nu-proprietário, antigo dono mora gratuitamente, consolidação plena ocorre no falecimento do usufrutuário).

**ADR canônica:** [[ADR-235]] (Proposto — A16) — entregue em [apps#382](https://github.com/davidrobert/mathoms/pull/382).

**Frequência esperada na base:** 5–15% do ICP wealth-tech BR (famílias com planejamento sucessório ativo).

## Escopo

Lane única. PR de **Decidido** que:

1. Adiciona migration Alembic estendendo CHECK constraint em `property_identity.classification` + `workspace_property_overrides.classification` com `nu_proprietario`.
2. Toca 6 call-sites identificados ([[ADR-235]] §"Plano de implementação"): models, classifier, real_estate_metrics, real_estate_adapter, type TS, dropdown UI.
3. Atualiza 4 ADRs adjacentes ([[ADR-215]] §1 lista valores, [[ADR-142]] invariante, [[ADR-145]] cat_2 não-gerador, [[ADR-216]] exclusão do denominador cap rate).
4. Atualiza prompt + golden + eval do parecer LLM E6 ([[ADR-199]]).
5. Adiciona CI gate `dev/check_classification_exhaustive.py`.
6. Testes de paridade com `uso_pessoal` + E2E `@critical`.
7. Regen OpenAPI snapshot.
8. Entrada [docs/CHANGELOG.md](../../CHANGELOG.md) citando ADR-235.
9. Flippa frontmatter da [[ADR-235]] para `Decidido (Sprint A16)`.

## Lanes

- [[TRACK-a16-adr235-nu-proprietario-flip]] (`ready`) — única lane da sprint.

## Pré-requisitos

- [[ADR-235]] mergeada em `main` ([apps#382](https://github.com/davidrobert/mathoms/pull/382) — auto-merge habilitado).

## Bloqueios externos

Nenhum. ADR-235 não introduz nova dependência externa nem altera infra. É extensão do enum + propagação cross-stack.

## Não-objetivos

Os mesmos da ADR-235 §"Não-objetivos":
- `expected_extinction_year`, modelagem de cenário condicional pós-consolidação, tábua atuarial.
- `valor_mercado_consolidado` separado de `valor_brl` IRPF (cabe em FU unificado com [[ADR-227]]).
- Sub-bucket "Patrimônio ilíquido condicional" como categoria nova em [[ADR-145]].

## Follow-ups potenciais (post-A16)

- **FU-1 · `valor_mercado_consolidado`** estendendo `property_market_value` ([[ADR-227]]).
- **FU-2 · Aviso de seguro de vida** no parecer E6 (heurística condicional).
- **FU-3 · `expected_extinction_year`** — só se demanda materializar (≥10 workspaces solicitando captura).
