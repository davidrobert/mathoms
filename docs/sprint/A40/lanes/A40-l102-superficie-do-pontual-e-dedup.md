---
id: A40.l102
type: lane
title: "Superfície do gasto pontual: dedup do par publicado sob promessa de unicidade + o que cada superfície declara excluir"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l102-superficie-do-pontual-e-dedup
owner: data-engineer
depends_on: []
adrs:
  - "[[ADR-422]]"
  - "[[ADR-425]]"
  - "[[ADR-347]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/pipeline
  - area/frontend
---

# A40.l102 — `superficie-do-pontual-e-dedup`

> **Origem:** split da [[A40.l98]] no co-design de 2026-08-30 (`financial-planner` +
> `data-engineer` + `senior-cto`). O corte é pelo eixo **muta E5 × não muta**: a l98
> pertence à janela de mutação que precede o próximo re-run e disputa a cláusula de
> reinício do contador de saída; esta não, e pode ir em paralelo.

## Escopo

1. **`LC6-07` — dedup do par publicado.** Ver §Formulação corrigida abaixo.
2. **Declaração impressa do que cada superfície exclui** — o output da política única
   que a [[A40.l98]] entrega. Sem produtor único, três declarações são três
   oportunidades de mentir; com ele, a declaração é derivada.
3. **Os dois cards de S2 herdados da [[A40.l15]]** (texto de conclusão do donut e do
   chart mês a mês).

> ⚠️ **Obrigação que não pode se perder:** a [[A40.l15]] é dona do `CARDS_DA_L15`, que
> exclui nominalmente dois cards de `janelaCanonica.contract.test.tsx` e de
> `janela-canonica.@critical.spec.ts`. **Remover as duas exclusões é critério de aceite
> desta lane.** O assert de "exclusão não é vácuo" fica **verde depois** de removida —
> ninguém será avisado automaticamente se isso for esquecido, e a guarda fica cega para
> sempre.

## `LC6-07` — formulação corrigida (2026-08-30)

O registro do `LEDGER` diz *"dois pares duplicados (mesma data, mesma categoria, mesmo
valor)"*. **As duas metades estão erradas**, medido nos itens do report `c011c40c`:

- **Não é mesma data.** O par difere em 1 dia: `2025-10-26` em `C6Bank (extratoconta)`
  e `2025-10-27` em `c6bank (extrato)` — mesmo banco, **documentos-fonte distintos**,
  mesmo valor (R$ 3.000), mesmo beneficiário. Assinatura de D+1 entre dois documentos.
- **Não são dois pares.** Chaveando por `(data, categoria, valor)` dá **0** grupos; por
  `(mês, categoria, valor)` dá **1**; por `(mês, valor)` dá 2, mas o segundo é falso —
  beneficiários distintos. E o grupo verdadeiro traz um **terceiro** item legítimo
  (`PDV*BARA CLINICA`, outro documento, outra natureza): chave por mês+valor colapsaria
  os três.

### A medição inicial foi sobre CÓDIGO MORTO — registrado para não se repetir

A primeira análise mediu `transaction_signature`/`deduplicate_transactions`
(`scripts/reconcile_transactions.py:464-537`) e concluiu que *"a descrição já colapsa,
só a data separa"*. **Essa função não roda.** Seu único chamador é `reconcile_account`
(:877), que **não tem chamador nenhum** no repo; o caminho vivo é `main_with_store` →
`_e3_build_adapter` → `E3ReconcilerAdapter.reconcile_via_store`. `tests/test_e3_dedup.py`
a chama direto — é o teste que a mantém verde e a fez parecer viva.

**Consequência:** consertar a assinatura ali deixaria o teste verde, o dogfood parado e o
defeito publicado — um conserto que mede a si mesmo.

### No caminho vivo, o par falha em CINCO cláusulas, em dois mecanismos

| mecanismo | cláusula | por que o par não passa |
| --- | --- | --- |
| `ReconciliationService.is_duplicate` | `a.description != b.description` | descrição difere byte a byte (o sufixo está lá) |
| idem | escopo do grupo | dedup cross-file roda dentro de `{banco}_{tipo_conta}_{MOEDA}_...` ⇒ `extrato` e `extratoconta` são grupos **diferentes** |
| `CrossDocumentCollapser._collapse_key` | `tx.date.isoformat()` | **day-exact** — D+1 nunca vira candidato |
| `_extraction_reason` | `par_nao_e_nativo_mais_llm` | exige 1 nativa + 1 LLM; dois nativos é **bloqueado** |
| `cross_document_collapse_enforce_enabled` | default `False` | measure-only: nada é removido |

A tolerância de ±3 dias **já existe** — em `is_duplicate`, que em compensação exige
descrição idêntica. A normalização que resolve a descrição (`_ROUTING_SUFFIX_RE` já tira
`TRANSF ENVIADA PIX`) vive só no colapsador, que é day-exact. **As cegueiras são
exatamente complementares e o par cai no vão.**

### Decisão: measure-first, sem enforce

**D±1 é aceitável como classe de candidato, inaceitável como critério de remoção — hoje.**

- **Direção do erro.** Sub-dedup publica duplicata **visível e auditável**, conservação
  intacta. Super-dedup **destrói** row, órfã override ancorado no `transaction_hash` dela,
  e é **silencioso**. Sob [[ADR-347]] + `ReportPublication` pinado com `RESTRICT`, um erro
  é recuperável e o outro não.
- **Não há discriminante positivo.** `saldo_apos` é emitido por **0 dos 13** parsers;
  `nr_doc` por 1 (Caixa); `Transaction.from_dict` **descarta os dois**; não há hora. D±1
  hoje decide por prior, não por evidência — e taxa de falso-positivo não-verificável não
  é taxa aceitável.
- **Escala:** 1 par em 89 itens (0,76% da janela) contra 63,2% de base não classificada.
  Duas ordens de grandeza menor, e é o único item do lote que **destrói dado**.

**PR-0 é produzir o número:** hoje a classe D±1 **não é sequer contável** — o par nunca
vira candidato, logo nunca ganha `blocked_reason`. Segunda passada no **colapsador** (não
na assinatura), classe própria `proximidade_d1`, measure-only, artefatos byte-idênticos
antes/depois (molde: `dev/probe_collapse_rollback.py`).

**Quando D±1 vira seguro:** quando houver teste **positivo** por candidato. O árbitro já
existe e não é heurística — a **cadeia de saldo** (`continuity_chain.py`,
`ledger_saldo_oracle.py`): duplicata genuína quebra a cadeia em exatamente o valor
duplicado; duas transações genuínas não quebram. Critério: *remove-se o candidato se e
somente se a remoção **repara** a cadeia*. Habilitador: fazer o parser C6 **emitir** o
saldo diário que ele já lê (`day_last_saldo`) e hoje descarta.

⚠️ **`_extraction_reason` é bloqueio maior que a data**, e mexer nele é território da
[[ADR-354]] §D5. **Não fazer dentro desta lane** sem emenda datada.

### A promessa de unicidade não está sendo quebrada — verificado

`_le_consolidacao` só emite `consolidacao_cross_documento` quando `count > 0`, e com
enforce desligado a chave é omitida ⇒ a nota *"contamos cada um uma vez só"* **não
aparece**. Não há P0 de copy. O que existe é uma promessa que a peça **não faz** sobre
uma classe que ela **não conta** — e o objeto `base_pontuais` da [[A40.l98]] fecha isso
sem tocar no E3: o par continua na lista, e a lista passa a declarar o critério.

## Critério de aceite

- `CARDS_DA_L15` removido das **duas** guardas, com o assert de não-vácuo verificado
  antes e depois.
- Classe `proximidade_d1` contável, com `blocked_reason` por candidato; **zero** rows
  removidas; artefatos byte-idênticos antes/depois.
- Se algum dia houver enforce: prova nos **dois substratos** — o par some da lista
  (`backend/tests`) **e** de `total_pontuais`/`total_pontuais_janela` (`tests`), com a
  mesma constante de delta compartilhada entre os dois arquivos.
