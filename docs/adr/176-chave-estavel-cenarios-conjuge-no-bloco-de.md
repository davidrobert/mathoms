---
id: ADR-176
type: adr
title: "Chave estável `cenarios_conjuge` no bloco de narrativas E5.N"
status: Proposto
date: "2026-05-06"
relates_to: ["[[ADR-143]]", "[[ADR-166]]", "[[ADR-167]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 176"]
tags:
  - type/adr
  - status/proposto
size_lines: 39
---

# ADR-176 — Chave estável `cenarios_conjuge` no bloco de narrativas E5.N

**Status:** Proposto • **Data:** 2026-05-06 • **Relaciona** [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76), [ADR-166](#adr-166--schema-estável-cenarios_conjuge-no-payload-e5), [ADR-167](#adr-167--eligibility-gate-de-cenário-do-cônjuge-no-domain-service). **Origem:** card "Cenários de Estresse — Sem renda do cônjuge" renderizando vazio em [S3InvestimentosSection.tsx:68](../frontend/src/components/report/sections/S3InvestimentosSection.tsx:68).

**Contexto:** ADR-166 estabilizou a chave do **payload** E5 em `cenarios_conjuge` literal, mas explicitamente **não tocou** `key_cenarios_section` (em `pipeline/domain/services/narrativas/context.py:69`), que continua derivando `f"{conjuge_key}_cenarios"` (ex.: `mariana_cenarios`) e é usada em `ChartsNarrator.narrate()` (em `pipeline/domain/services/narrativas/charts_narrator.py:81`) como chave de inserção no dict `narratives.charts`. ADR-166 §Follow-ups item 2 deixou registrado: *"`key_cenarios_section` ({conjuge_key}_cenarios) — outro rename, ADR separada quando justificado."*

O frontend, porém, lê `narratives.charts.cenarios_conjuge` em [NarrativeChartCard.tsx:23](../frontend/src/components/report/charts/NarrativeChartCard.tsx:23) (com `chartId="cenarios_conjuge"` em S3). Resultado prático: o card "Cenários de Estresse — Sem renda do cônjuge" **nunca encontra** a narrativa real (que está em `narratives.charts.mariana_cenarios` ou similar) e cai no fallback determinístico de [conclusionUtils.ts:157](../frontend/src/components/report/utils/conclusionUtils.ts:157) — "Cenário de estresse — sem renda do cônjuge." — uma frase placeholder que não traz informação. Bug latente em todos os workspaces, não só o piloto.

A justificativa que destrava o follow-up é a mesma de ADR-166: ADR-143 (methodology = code) é taxativa — chaves universais devem ser fixas. Ter chave dinâmica derivada de config de workspace para um conceito universal (cenário "Sem renda do cônjuge") é o anti-padrão exato que ADR-143 combate. Manter a inconsistência por mais um ciclo é dívida sem benefício.

**Alternativas avaliadas:**

1. **Frontend tenta dual-key (`narratives.charts.cenarios_conjuge ?? narratives.charts[<conjuge>_cenarios]`)** — mais barato, mas perpetua chave dinâmica; viola ADR-143; obriga frontend a conhecer convenção `<membro>_cenarios`. Rejeitada.
2. **Manter `key_cenarios_section` mas setá-la para `"cenarios_conjuge"` literal sem remover o campo** — preserva API do `NarrativasContext`, custo zero em call-sites externos. Deixa lixo: dois campos sinônimos (`key_cenarios_conjuge` e `key_cenarios_section`) apontando pra mesma string. Rejeitada por preferir consolidação.
3. **Consolidar em `key_cenarios_conjuge` (ADR-166 já injeta `"cenarios_conjuge"`); remover `key_cenarios_section` (escolhida)** — narrator usa `ctx.key_cenarios_conjuge` direto; um campo, fonte única, alinhado com ADR-143/166. Custo: atualizar 1 referência em narrator + 5 referências em testes + 2 referências legadas em `scripts/e5n_narrativas.py` + 1 default em `format_helpers.validate_narrativas`.

**Decisão:** Adotar (3). Fechar o follow-up de ADR-166.

- **`pipeline/domain/services/narrativas/context.py`:** remover campo `key_cenarios_section`; `key_cenarios_conjuge` (já existente, valor literal `"cenarios_conjuge"`) torna-se a única referência.
- **`pipeline/domain/services/narrativas/charts_narrator.py:81`:** `ctx.key_cenarios_section` → `ctx.key_cenarios_conjuge`.
- **`pipeline/domain/services/narrativas/format_helpers.validate_narrativas`:** default `cenarios_section_key="mariana_cenarios"` → `"cenarios_conjuge"`. Parâmetro mantido por compat reversa (chamadores externos podem passar override durante janela transitória), mas não é mais necessário.
- **`scripts/e5n_narrativas.py`:** `_KEY_CENARIOS_SECTION` (linhas 75 e 127) → string literal `"cenarios_conjuge"`. Variável global mantida como alias estável para módulo legado.
- **Frontend:** **nenhuma mudança** — já espera a chave estável.

**Consequências:**

- ✅ Bug visível corrigido: card "Cenários de Estresse — Sem renda do cônjuge" passa a renderizar `context` + `conclusion` reais quando E5.N roda em workspace elegível (ADR-167 gate).
- ✅ ADR-143 honrado: chave universal é fixa; nenhum acoplamento residual a `_CONJUGE_KEY` no shape de narrativa.
- ✅ Consolidação de campo: `NarrativasContext` perde 1 atributo (`key_cenarios_section`), reduzindo superfície de erro. `key_cenarios_conjuge` é fonte única.
- ⚠️ **Sem backfill operacional** — diferente de ADR-166, narrativas E5.N são re-geradas em todo run de `analyze_finances` (não persistem entre runs como o payload E5 em `pipeline_artifacts.content_json`). O próximo `e5n_narrativas` em qualquer workspace já produz output com a chave nova. Workspaces que ainda não rodaram E5.N pós-merge continuam vendo o fallback determinístico — comportamento idêntico ao estado atual, sem regressão.
- ⚠️ Test `test_builder_charts_key_cenarios_uses_conjuge_name` (afirma chave dinâmica) precisa **inverter** para `test_builder_charts_key_cenarios_uses_universal_key` — documenta o novo invariante (regressão-bloqueada).
- ⚠️ Cache LLM (ADR-144) **não invalida automaticamente** porque `compute_snapshot_hash` opera sobre payload E5 (já estável desde ADR-166), não sobre keys de narrativa. Aceito: narrativa de cenário é determinística (sem chamada LLM) — re-gera bit-a-bit no próximo run.
- ❌ Não toca `_KEY_RENDA_CONJUGE_EUA_PROJ` (`renda_<conjuge>_eua_projetada`), `_KEY_INST_CONJUGE` etc. — fora de escopo. Esses são campos de **payload de métricas** não consumidos diretamente por chave universal no frontend; podem virar follow-up se mostrarem o mesmo sintoma.

**Implementação:** PR único. Vira `Decidido (A8.4)` no merge — completa o follow-up #2 de ADR-166.

**Referências:** [ADR-166 §Follow-ups item 2](#adr-166--schema-estável-cenarios_conjuge-no-payload-e5), [docs/reference/ARCHITECTURE.md §4.1 Domain glossary](ARCHITECTURE.md).
