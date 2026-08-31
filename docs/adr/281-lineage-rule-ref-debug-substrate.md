---
id: ADR-281
type: adr
title: "rule_ref derivado de dict literal + lineage_diff (substrato de debug LLM)"
status: Decidido
phase: "A23 · F0"
date: "2026-06-02"
amended_at: ["2026-08-30"]
relates_to:
  - "[[ADR-143]]"
  - "[[ADR-111]]"
  - "[[ADR-116]]"
supersedes:
  - "[[ADR-045]]"
superseded_by: []
aliases: ["ADR 281", "rule_ref", "lineage_diff", "lineage debug substrate"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/data-lineage
  - area/llm
---

# ADR-281 — rule_ref derivado de dict literal + lineage_diff (substrato de debug LLM)

**Status:** Decidido (A23 · F0) • **Data:** 2026-06-02 • **Relaciona** [[ADR-143]], [[ADR-111]], [[ADR-116]] • **Supersede** [[ADR-045]].

> Camada D do plano [[PLAN-data-lineage]]. Gate F0 — **resolve B2**. Estende/supersede
> [[ADR-045]] (data lineage via tooltip — drill-down "para futuro"; este é esse futuro).
> Decisão fechada; lanes de implementação conformam.
>
> **Emendada 2026-08-30 ([[A27.l2]]):** o `check_lineage_refs` prometido abaixo é
> **existência pura** — não mede cobertura — e o eval derivava `expected` do próprio
> registro. Ver §Emenda no fim.

**Contexto:** o lineage precisa ser legível por um LLM (agente de debug OU Claude Code no repo) para saltar de "número errado" → "função a corrigir". Exige bridge nó→código refactor-safe e diff de regressão determinístico. A [[ADR-045]] decidiu o tooltip de UI e adiou o drill-down; aqui materializamos o substrato.

**Decisão:**
- **Bridge nó→código:** **dict literal eager** `pipeline/domain/lineage_registry.py` (`{rule_id: "module:qualname", adr}`) — **não** decorator import-side-effect (banido por CLAUDE.md §Dependências; não cabe na exceção [[ADR-111]] (a), que é p/ constantes). Refactor-safe vem do gate `dev/check_lineage_refs.py` (resolve `module:qualname` por import real + ADR existe). Registrar em `STATELESS_AUDIT.md §2` (B2).
- **Renderer LLM:** trace linearizada (passos numerados raiz→folha, inputs como `#N`), teto ~1.5k tokens inline, anomaly-first ordering. Distinto do renderer humano (tooltip [[ADR-045]]).
- **`lineage_diff`** puro/stateless: só nós mudados + `first-divergent-leaf` + propagação anotada.
- **Tools:** `explain_number`/`expand_node`/`trace_source` (cap `max_expand_iterations:6`, whitelist de `field`). Superfície: core de domínio (Claude Code sobre goldens, dia 1); MCP read-only no console interno ([[ADR-116]], `workspace_id` obrigatório, zero mutação) — fase posterior.
- **Eval:** injeção determinística de bug; `localization_accuracy@node ≥ 85%`.

**Consequências:**
- ✅ LLM (Claude Code no repo OU agente de debug) salta de "número errado" → `rule_ref` → função exata. Bridge refactor-safe: o gate `check_lineage_refs` quebra se o `module:qualname` não resolve por import real, então rename sem atualizar o dict é pego no pre-commit.
- ✅ Supersede [[ADR-045]] (bidirecional: `superseded_by` no frontmatter de 045 já aponta para cá): o tooltip vira o **renderer humano**; o renderer LLM linearizado é a face de debug do mesmo grafo.
- ⚠️ **Rejeitado decorator `@lineage_rule`** (import-side-effect banido por CLAUDE.md §Dependências; não cabe na exceção [[ADR-111]] (a), que é p/ *constantes*, não registry populado por side-effect). Dict literal eager registrado em `STATELESS_AUDIT.md §2` como mapping de domínio imutável.
- ⚠️ **MCP prod do debug substrate + índice reverso por `rule_ref` deferidos** (YAGNI) até um agente fechar o loop "número errado → função" sobre goldens (F7). Não construir observability platform antes da pergunta de impacto real.
- ⚠️ Eval de injeção de bug (F7): `localization_accuracy@node ≥ 85%` (regressão >2% bloqueia merge), temp=0/seed/model pinados; o renderer LLM e o `lineage_diff` são `pipeline/domain/services/*` puros/stateless (não importam framework).

## Emenda 2026-08-30 — cobertura medida contra o payload; ground truth do eval sai do registro (A27.l2)

**O que a decisão original afirmava:** que `check_lineage_refs` torna o bridge
refactor-safe. **Verdadeiro, e insuficiente** — ele resolve `module:qualname` e checa a
ADR, mas não tem noção de **cobertura**. Somado a um eval cujo `expected_rule_ref` saía de
`LINEAGE_RULE_REFS[rule_id]["ref"]`, acrescentar raiz ao E5 sem entrada no registro não
movia o gate nem a `localization_accuracy@node`: gate que só podia dar verde.

**Medido em 2026-08-30** (fixture dogfood sintética, `tests/pipeline_golden_substrate`):

| Medida | Valor |
| --- | --- |
| Raízes do payload que publicam dinheiro | 14 |
| Raízes com nó em `_lineage.fields` | 5 (`patrimonio`, `fluxo_caixa`, `investimentos`, `reserva_emergencia`, `endividamento`) |
| **Cobertura** | **5/14 = 35,7%** |
| `rule_id` do registro sem nenhum caso de eval | 4 de 8 |
| Refs distintos exercitados pelos 29 casos | 4 (contra 6 no registro; refs são compartilhados entre `rule_id`) |

**Emenda à decisão:**

- **O denominador da cobertura vem do payload publicado, nunca do registro.** Derivá-lo do
  registro devolve 100% por construção. O discriminante de "raiz que deve ter rastro" é
  `golden_diff.is_monetary` (monetário-por-default, [[ADR-090]]) — escolhido por classificar
  campo **sem consultar** o registro, que é o que mantém numerador e denominador
  independentes. Raiz em prosa/metadado fica fora: medir contra as 38 raízes do schema dava
  teto inalcançável, e KR que não pode chegar a 100% é KR que ninguém persegue.
- **O eval não deriva ground truth do registro que avalia.** `cases._EXPECTED_REFS` declara
  os refs por extenso; o cross-check por `rule_id` passa a poder falhar. Ler o registro para
  **fabricar a mutação** (`_swap_rule` — o bug injetado precisa citar enforcer que existe)
  segue legítimo: o que saiu foi o ground truth, não a mutação.
- **Gate compara conjunto, não contagem.** Raiz renomeada ou trocada não passa por
  compensação numérica.

**Enforcers:** `dev/lineage_coverage.py` (medida) · `tests/test_lineage_coverage.py` (gate +
controle positivo: raiz monetária sintética derruba a métrica e reprova, enquanto
`check_lineage_refs` segue verde na mesma mutação) ·
`tests/lineage_eval/test_eval_deterministic.py::test_expected_refs_declarados_batem_com_o_registro`.

**Não muda:** o bridge por dict literal eager, o renderer LLM, o `lineage_diff`, nem o
alvo `localization_accuracy@node ≥ 85%`. A emenda acrescenta a medida que faltava; não
reabre a decisão.
