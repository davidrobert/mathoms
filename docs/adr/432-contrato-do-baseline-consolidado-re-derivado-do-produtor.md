---
id: ADR-432
type: adr
title: "O contrato do baseline consolidado é re-derivado do produtor, e o ramo `declarations` da raiz é aposentado"
status: Decidido
phase: A40.l110
date: "2026-09-01"
relates_to:
  - "[[ADR-409]]"
  - "[[ADR-427]]"
  - "[[ADR-284]]"
  - "[[ADR-212]]"
  - "[[ADR-431]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 432"
  - "contrato do baseline consolidado"
  - "colapso do oneOf de baseline_patrimonial"
  - "additionalProperties do baseline"
tags:
  - type/adr
  - status/decidido
  - area/dados
  - area/pipeline
---

# ADR-432 — O contrato do baseline consolidado é re-derivado do produtor, e o ramo `declarations` da raiz é aposentado

**Status:** Decidido (A40.l110 · PR-B) • **Data:** 2026-09-01 • **Relaciona**
[[ADR-409]] §F (que recusou promover este schema e deferiu a re-derivação),
[[ADR-427]] D3/D5 (dois produtores; completude por igualdade de conjunto),
[[ADR-284]] (modo `warn`/`strict`), [[ADR-212]] (validação pós-write),
[[ADR-431]] (valor não apurado — dona do resíduo de valor).

## Contexto

A [[ADR-409]] §F tirou `baseline_patrimonial` da fila de flip com a razão escrita:
o contrato *"descreve 5/13 do payload"*. O PR-A da [[A40.l110]] matou 2 `required`
fósseis e o `date.today()` que era gravado no artefato, mas **não** re-derivou o
contrato — deixou-o em 5 de 11, e instalou `_CONTRATO_NAO_DERIVADO` no
`dev/measure_schema_drift.py` para que o veredito não saísse `GO` sobre contrato
irreal enquanto isso.

Censo do corpus inteiro (169 artefatos, 105 runs, **0 ilegíveis**), por produtor:

| chave | E1.5c | E4 `patrimonio` | declarada antes |
| --- | --- | --- | --- |
| `_meta` · `dividas` · `imoveis_consolidados` · `investimentos_consolidados` · `itens` · `patrimonio_por_ano` · `resumo` · `veiculos_consolidados` | 98/98 | 71/71 | 4 de 8 |
| `informe_pf_saldos_31_12` · `wise_fiscal_flags` | 78/98 | 71/71 | não |
| `payload_version` · `prompt_version` | 13/98 | 12/71 | não |
| `validation` | 9/98 | 8/71 | não |
| `pipeline_stage` · `data_processamento` | **0/98** | **71/71** | não (mortos no PR-A) |
| `anos_base` · `declarations` · `membros` · `properties` · `receipts` · `summary` | **0** | **0** | sim — fantasmas |

## Decisão

**D1 — Declarar as 14 chaves reais.** As 13 que os produtores emitem hoje, mais
`membros`, que o `BaselineNormalizer` **pode** emitir (alias de `membros_familia`).
`membros` é declarada por alcance de código, não por presença no corpus: sob
`additionalProperties: false` em `strict`, uma chave emitível e não declarada aborta
o write.

**D2 — Aposentar 5 fantasmas.** `anos_base`, `declarations`, `properties`,
`receipts`, `summary` — zero emissões e nenhum caminho de produção que as escreva.
`declarations` **continua sendo lida** (`consolidate_baseline.py:193`,
`analyze_finances.py:381`, `patrimonio_resolvers.py:82`), mas do payload de
**entrada** do E1.5, que este schema não governa. Aposentar a declaração de saída não
toca esses leitores.

**D3 — Colapsar o `oneOf` de raiz; `required: ["patrimonio_por_ano"]`.** O Format B
(`required: ["declarations"]`) nunca casou: `declarations` é 0/169 e
`patrimonio_por_ano` é 98/98 e 71/71. Ramo morto de contrato é pior que ausência —
publica uma forma alternativa que nenhum produtor produz e nenhum leitor espera.
Mesma classe que a [[ADR-427]] D4 consertou no E4.

**D4 — `additionalProperties: false`.** É o que torna o contrato detector: sem ele,
chave nova entra calada e a [[ADR-409]] §F volta a valer. Consequência **medida e
aceita** em D6.

**D5 — Completude por igualdade de conjunto, derivada do produtor.** Gate nos dois
sentidos ([[ADR-427]] D5): nenhuma chave emitida fica fora do schema, e nenhuma chave
declarada é fantasma. O conjunto emitido vem de rodar o produtor, não de lista à mão —
lista à mão é a fantasma da próxima vez.

**D6 — `_CONTRATO_NAO_DERIVADO` é levantado, e o resíduo passa a ser do número.** A
razão do bloqueio era *"contrato irreal"*, e ela morreu com D1-D5. O que resta é
corpus sujo, que o predicado normal da [[ADR-409]] §B já mede:

| produtor | drift pós-D1-D5 | causa |
| --- | --- | --- |
| E1.5c | **3/98** | `valores_31_12` negativo — [[ADR-431]], [[A40.l111]] |
| E4 `patrimonio` | **71/71** | os 2 fósseis, em artefato **histórico** |

Os 71 são artefatos escritos **antes** do PR-A. A validação é pós-**write**
([[ADR-212]]), então write novo não os carrega e nenhuma produção quebra. O flip
espera a **virada do corpus** — nenhuma run ocorreu desde 2026-08-30 19:07.

## Não-decisões (rejeitadas)

- **Declarar os 2 fósseis como tolerados** para zerar os 71 — ressuscita exatamente
  o que a [[A40.l110]] matou, e o contrato voltaria a descrever um payload que
  produtor nenhum escreve.
- **Adiar `additionalProperties` até a virada do corpus** — deixaria o detector
  desligado por tempo indeterminado, que é o estado que a [[ADR-409]] §F condenou.
  O bloqueio do flip é consequência honesta, não motivo para não fechar o contrato.
- **Deletar o `BaselineNormalizer`** — os 5 passos restantes são no-op no corpus
  (`membros_familia`, `resumo_patrimonial`, `bens_imoveis_consolidados`,
  `investimentos_financeiros_consolidados`, `dividas_consolidados`: 0/169), mas
  removê-los é decisão de compat v2→v1, não de contrato. Fica nomeado, sem dono
  atribuído aqui.

## Consequências

- `baseline_patrimonial` sai de 5 de 11 para **14 de 14** — o contrato passa a
  descrever o payload, e chave nova em E1.5c passa a ser detectada.
- O flip continua bloqueado, agora **pelo número e não pela prosa**, com os paths
  nomeando a causa. Some quando a l111 estiver refletida no corpus e as runs
  virarem.
- Quem for flipar lê `NO-GO` com `additionalProperties` em 71 artefatos e precisa
  saber que é história, não regressão — está escrito na §Consequências desta ADR e
  no §Deferimento da [[A40.l58]], que esta ADR **quita**.
