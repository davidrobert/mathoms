---
id: ADR-296
type: adr
title: "Citação determinística: LLM emite (claim, path, rótulo); pipeline renderiza o valor da folha"
status: Proposto
phase: "A27 · parecer reliability"
date: "2026-06-19"
relates_to:
  - "[[ADR-202]]"
  - "[[ADR-279]]"
  - "[[ADR-292]]"
  - "[[ADR-295]]"
  - "[[ADR-293]]"
supersedes: []
superseded_by: []
aliases: ["ADR 296", "citação determinística", "render value from path"]
tags:
  - type/adr
  - status/proposto
  - area/llm
  - area/pipeline
  - phase/a27
---

# ADR-296 — Citação determinística (render value-from-path)

**Status:** Proposto (A27 · parecer reliability) • **Data:** 2026-06-19 •
**Relaciona** [[ADR-202]] (schema do parecer), [[ADR-279]] (citação verificada §E),
[[ADR-292]] (coerce path→None), [[ADR-295]] (enforcement per-item), [[ADR-293]]
(citação como edge de lineage). Co-design `senior-cto` + `data-engineer` +
`prompt-engineer` + `product-designer` + `product-manager` + `information-architect`
(2026-06-19). Implementação na lane [[A26.l9]].

## Contexto

A [[A26.l1]] (catálogo) + [[ADR-292]] (coerce) + [[A26.l8]]/[[ADR-295]] (enforcement
per-item) levaram a conformidade **por citação** a 96%, mas o eval 1.8.0 (strict)
mostrou que o gate **per-parecer** não fecha: `needs_review` 22% (UB 35%). A
classificação do resíduo é decisiva — **~87% é `wrong_pairing`**: o LLM escreve um
número **real** do E5 mas atrela ao **path/conceito errado** (ex.: escreve a receita
R$ 720k citando `previdencia_pgbl.contribuicao_anual`=R$ 50k); 0% é abreviação.

A raiz é que **o LLM digita o número à mão** e faz duas escolhas independentes que
precisam casar (número X; path Y) — divergem em ~22%/parecer. Renderizar o número
**do path** (chamada D1) fecharia o gate, mas força "número == valor-do-path" → o
verificador de magnitude **sempre passa** → se o path está errado, publica número
real no contexto errado, **indetectável**. D1 é a auto-correção que a [[ADR-295]]
rejeitou, agravada (inobservável). **D1 vetado.**

## Decisão

**O LLM para de autorar o número.** Cada citação vira estruturada: o LLM emite
`(claim em prosa SEM número, evidencia_path, rótulo_do_conceito)`; o **pipeline
renderiza o valor da folha** do path (via a mesma `format_value` do catálogo l1) e o
**finalize grava o valor renderizado como snapshot**. `value_mismatch` por
transcrição torna-se **estruturalmente impossível** (não há número autorado a
divergir).

1. **Contrato (schema, breaking — bump `version` major):** `evidencia_path: str`
   singular por item → `ancoras: [{path, rótulo, valor_renderizado}]`. `path` +
   `rótulo` são emitidos pelo LLM; `valor_renderizado` é escrito **pelo finalize**
   (não pelo LLM — padrão de `suggestion_dedup_key`). Pareceres v1 persistidos
   **não migram** (`content_json` imutável, [[ADR-204]]); renderer faz dispatch por
   `version`. Zero Alembic.

2. **Nova camada de correção `pairing_mismatch`** substitui `value_mismatch`: o
   verificador deixa de comparar número-da-prosa e passa a cruzar
   **`rótulo ↔ seção-dona-do-path`** (`CatalogEntry.root`, determinístico). Incoerência
   → alimenta o **mesmo `enforce_strict_per_item`** ([[ADR-295]] reusado intacto):
   item dropado (baixo/médio) ou `needs_review` (alta). `EVIDENCIA_VERIFICATION_VERSION`
   bump (invalida cache). Telemetria l6 (cobertura vs correção) preservada — só troca
   o nome da camada.

3. **Snapshot, não lazy:** persiste `path` + `valor_renderizado`. Lazy-render do E5
   da época reescreveria silenciosamente o número de um parecer **publicado e
   imutável** se o E5 for reprocessado — viola [[ADR-204]]. O `path` persiste junto
   (lineage forward/reverso íntegro; drift vira badge derivado, nunca sobrescrita).

4. **Determinismo (ADR-090):** fonte única de formatação = `format_value` no
   finalize backend (mesma do catálogo → byte-idêntico ao que o LLM viu); fecha o
   débito float de `_format_brl` via `Decimal(str(v))`. O `<MonetaryValue/>` exibe o
   valor já resolvido; não reformata.

5. **Emissão LLM + reask:** `evidencia_path` reusa o coerce `EvidenciaPath`
   (path inválido→None, [[ADR-292]]); `rótulo` é `Literal` + `BeforeValidator`→sentinela
   (nunca raise). Âncora malformada → tratada pelo verificador per-item, **não** reask.

## Consequências

- **`value_mismatch` = 0 estrutural**; o gate per-parecer torna-se atingível porque a
  barra deixa de ser "transcrever número perfeito" e vira "escolher o path certo do
  catálogo" (vocabulário que o l1 já fornece).
- **Resíduo:** `pairing_mismatch` intra-seção (path errado dentro da seção certa) —
  menor, vai para `needs_review`/drop; honestamente não eliminado.
- **[[ADR-295]] coexiste** (não superseded): é a máquina de decisão (drop vs
  needs_review); l9 só troca o sinal que a alimenta. Protege também pareceres v1
  legados durante a transição.
- **Forma do render: D2-puro** (decisão do owner, 2026-06-19) — prosa sem número +
  chips de âncora (`rótulo`/`valor_renderizado`) no rodapé do card. Descartados o
  placeholder `{{N}}` inline e o híbrido: `product-designer` argumenta que o híbrido
  vaza o modelo de confiança interno (inconsistência visual entre âncora inline vs
  chip), e o D2-puro é o mais seguro (nunca intercala número autorado na prosa,
  reforçando o invariante `number_in_prose_violation == 0`).

## Alternativas rejeitadas

- **D1 (número inline renderizado do path):** verificador vira gerador; wrong_pairing
  indetectável. É a auto-correção da [[ADR-295]] §Fora-de-escopo, agravada. Vetada.
- **Tabela top-level de âncoras + refs por índice:** indireção dupla, quebra a
  remoção-por-índice do enforcement [[ADR-295]]. Rejeitada (data-engineer).
- **`{{$.path}}` cru inline na prosa:** sem boundary de validação Pydantic; path
  malformado vira texto publicado. Rejeitada (prompt-engineer).

## Fora de escopo

- **Escopo de sprint:** `product-manager` crava que isto é **A27/Onda 6** (feature de
  contrato), não consolidação A26. A A26 fecha via redefinição do gate da [[A26.l2]]
  (segurança "0 falso publicado" já atingida + budget de `needs_review`), sem l9.
- Materialização da citação como **edge de lineage por chave natural** ([[ADR-293]]).

## Implementação — design do `rótulo` (co-design `prompt-engineer`, 2026-06-19)

Ponto deixado em aberto pela §Decisão, fechado na implementação da [[A26.l9]]:

- **`rotulo` é validação dinâmica, NÃO `Literal` estático.** `Rotulo =
  Annotated[Optional[str], BeforeValidator]` coage só a FORMA (`isidentifier()` ASCII +
  ≤64 chars → `None`); a PERTINÊNCIA (`rotulo == root do path`) é do verificador. Um
  `Literal` dos money-roots quebraria a paridade catálogo↔geração e geraria falso-drop
  sistemático em root novo do E5.
- **`rotulo` = root puro** (1º segmento do path), copiado do cabeçalho de grupo do
  catálogo (`**reserva_emergencia**`). Legibilidade do chip é do renderer (root→label),
  não do contrato. Detecção de `wrong_pairing` vem do LLM cruzar grupos (path de um,
  rotulo de outro).
- **Sentinela = `None`** → `pairing_mismatch` ∈ `_CORRECTNESS_LAYERS`/`_HARD_LAYERS`
  (drop/needs_review). `path=None` + rotulo presente → continua `missing_path`
  (cobertura, fail-open — ADR-292). Nunca reask.
- **Densidade:** `ancoras: list[Ancora]` cap 3, sem piso por-item (anti-sub-citação é
  agregado por parecer, telemetria — não constraint Pydantic).
- **Estado (2026-06-19):** backend implementado e verde (2658 testes backend + 199
  pipeline parecer). `EVIDENCIA_VERIFICATION_VERSION` 3, `PROMPT_VERSION` 2.0.0,
  schema `version` 2.0. Pendente: renderer D2-puro (frontend) + re-eval holdout
  (owner-gated) → flip desta ADR para `Decidido` no merge final.
