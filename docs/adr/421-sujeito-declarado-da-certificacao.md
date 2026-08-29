---
id: ADR-421
type: adr
title: "Sujeito declarado da certificação: o veredito descreve o artefato entregue, e diz qual"
status: Proposto
date: "2026-08-29"
relates_to:
  - "[[ADR-302]]"
  - "[[ADR-343]]"
  - "[[ADR-241]]"
  - "[[ADR-271]]"
  - "[[ADR-354]]"
aliases:
  - "ADR 421"
  - "sujeito da certificação"
  - "LC6-01"
tags:
  - type/adr
  - status/proposto
  - area/tooling
  - area/dados
---

# ADR-421 — Sujeito declarado da certificação

**Status:** Proposto · **Data:** 2026-08-29 · **Origem:** [[LEDGER-CERTIFY-active]] §r6 `LC6-01` (rodada unificada U2, [[ADR-416]])

## Contexto

`dev/certify_ledger_local.py` imprime `# ledger-certify — ws <x> run <id>` e emite
cinco eixos de rubrica. **Nenhum deles descreve o run nomeado.**
`build_report` computa `conservation`, `e3_groups`, `e4_buckets`,
`investment_collisions`, `natural_key` e `cross_group` a partir das peças
**re-derivadas in-process**; o `persisted_e3` entra na assinatura e é consumido
só em `_drift`.

Prova por mutação sobre o núcleo puro: trocando `persisted_e3` por um universo
grosseiramente diferente, os oito campos de rubrica e sumário saem **idênticos**;
só `drift` reage. O artefato entregue pode ser qualquer coisa e o relatório não
muda.

Por que sobreviveu quatro rodadas: `tests/dev/test_ledger_certify_core.py:201`
passa `persisted_e3=fresh_e3` — o **mesmo objeto**. Nenhum teste sobre
`build_report` consegue discriminar os dois universos. A fixture compartilha a
crença errada.

**A mesma classe já ocorreu no instrumento irmão.** [[ADR-343]] §Emenda
2026-08-05 item 2 registra *"O parecer não era run-scoped: o coletor buscava por
`workspace_id` com `ORDER BY id DESC LIMIT 1`"*. Duas ocorrências independentes,
dois instrumentos, mesma causa — é invariante de classe, não conserto local.

### O que se mediu (dogfood `ws-1b9f2cf5`, run `79a61e33`)

| # | Medição |
|---|---|
| M1 | Os 31 grupos "só no persistido" são **31/31 sobra de 7 outros runs** (2026-05-29 → 2026-07-31); o run pinado escreveu zero deles. A glosa impressa *"keying antigo não reproduzido"* é **atribuição falsa de causa** |
| M4 | Dos **61 runs `completed` com E3, 60** teriam todas as próprias keys comparadas contra artefato de outro run. Só o pinado escapa — por ser o mais novo, não por desenho |
| M13 | O braço entregue está **amputado**: 6 baldes (falta `patrimonio`), `investimentos` = 0 contra 18 na sombra. `investment_double_count` devolve 0 sobre **zero posições** — falso-negativo do detector da [[ADR-271]], indistinguível de um 0 verdadeiro |
| M14 | O **E4 persistido do run carrega o sinal inteiro** — 7 baldes, `investimentos` = 18 |
| M15 | Só **10 dos 61** runs têm evidência de enforce; 51 seriam recusados se o predicado de certificar herdasse o de pontuar KR-B |

**Bound que protege a [[A40]]:** o numerador da KR-B lê só os baldes transacionais
(`_tx_rows`) e `transferencias_count` — não lê `investimentos`/`patrimonio`. A
amputação do M13 **não** o contamina; a KR-B continua de pé.

## Decisão

**D1 — Um sujeito por certificação, e ele é o artefato entregue.** A rubrica é
emitida uma vez, sobre o que o run publicou. A re-derivação **não some**: vira
bloco diagnóstico **normativo** (`sombra — o que o código de hoje produziria`),
e o gate reprova se ela desaparecer. Blocos que só existem em execução
(`e3_exec`, `collapse_layer`, `drift`) ficam sob esse rótulo.

*Rejeitadas:* **duas colunas simétricas** — o registro durável keya por
`(dimensão, âncora, regra)`, **sem eixo de braço**, então duas colunas obrigam
todo citador a carregar um qualificador que a chave não guarda, que é a
causa-raiz deste próprio achado. **Flip cego** — três blocos não existem no
artefato e ficariam órfãos.

**D2 — Auto-rotulagem por linha.** Todo veredito emite `[entregue]` / `[sombra]`
no próprio texto, não só no cabeçalho. Copy-paste para o MOC não pode perder o
sujeito. Esta cláusula ataca a causa de citação independentemente da topologia.

**D3 — Escopo por stage, assimétrico, conforme à [[ADR-241]].** E2 é lido pela
**política do run** (workspace-scoped com fallback — é o read-path de produção),
com corte temporal descartando row criada depois do run. E3/E4 são **run-scoped**.
Não reimplementar a política: compor o `DBArtifactStore` real, com teste de
paridade. Proveniência sai impressa como censo (`do run` / `herdado` /
`descartado pós-run`), nunca rótulo genérico.

> Run-escopar o E2 seria **regressão**: reintroduziria o universo subdimensionado
> da [[ADR-241]] §Contexto e fabricaria falsa perda na conservação E2→E3.

**D4 — Vereditos de balde e colisão de investimento vêm do E4 persistido**, não
da re-derivação amputada (M13/M14). As três métricas que o artefato não
serializa — `natural_key`, `_classified_cents`, `transferencias_count` — vêm da
re-derivação e só são emitidas se ela reproduzir o publicado ao centavo; senão,
`não-verificável` com o Δ impresso.

**D5 — Predicado de certificar ≠ predicado de pontuar KR-B.** Certificar exige
run existente com E3. Pontuar KR-B mantém a evidência de enforce. Sem a
separação, o default recusaria 51 dos 61 runs (M15).

**D6 — Eixo sem insumo no sujeito ⇒ `não-verificável(motivo)`.** Nunca omissão,
nunca herança silenciosa do outro braço. Princípio já decidido na [[A42.l3]]
§Decisão; esta ADR o estende ao eixo do sujeito.

## Consequências

- §r1–§r6 do [[LEDGER-CERTIFY-active]] **não são reescritos** — snapshot datado é
  evidência ([[ADR-343]]). Entra **uma** nota de cabeçalho no MOC: linha anterior
  a esta ADR descreve a **sombra**, salvo o `[numerador KR-B]` do §r5/§r6, que já
  vinha do entregue.
- Runs antigos passam a exibir `não-verificável` explícito onde hoje há verde
  silencioso. **Isso é o instrumento melhorando, não regredindo** — e precisa
  estar escrito, porque será lido ao contrário.
- `_persisted_e3_by_key` não morre: é rebaixado a bloco de **acreção de
  workspace** (diagnóstico de retenção/GC). Apagá-lo perderia sinal vivo.
- A ordem de `_e2e3_checks` (**LC-07**) **não é tocada**. Esta ADR muda os
  *inputs* daquele veredito, nunca a ordem.

## Lane e arestas declaradas

**Dona da execução: [[A42.l14]]** (`planned`, P0) — criada pelo dono em #1821 no mesmo
dia desta ADR. Esta ADR responde as três perguntas que o §Critério de aceite da lane
deixou abertas: os 31 são **sobra** (31/31, 7 runs), o modo entregue **cobre a
conservação inteira**, e a rota é **sujeito único auto-rotulado** — não duas colunas.

A [[A42.l3]] é dona de `dev/ledger_certify_core.py` para os itens 1–9 dela e **reescreve
o mesmo arquivo**. Ordem obrigatória: **a l14 precede os itens 1–5 da l3** — aplicar o
registry de checkers sobre o sujeito errado produz `não-verificável` corretamente tipado
sobre o universo errado, que é pior que o `coberto` de hoje porque *parece* consertado.

A [[A42.l6]] escolheu **emenda [[ADR-291]]** como veículo da paridade de política
de escopo no *store de produção* (`list_keys` vs `read`). Esta ADR **não** invade
isso: decide o **sujeito do veredito** do instrumento, não a política do store.
O lado de escopo aqui é **conformidade** à [[ADR-241]], já Decidida — não decisão
nova. Quem mergear primeiro avisa; a l6 consome o leitor run-scoped que o PR1
desta rota entrega.

## Critério de aceite

- **Teste de troca** sobre `format_report`: dois sujeitos construídos para render
  vereditos **opostos** em todos os eixos; trocá-los troca os blocos
  integralmente. Eixo que ignore o argumento quebra a simetria. Falha hoje.
- **Fixture de dois runs** em `tests/dev/`: mesma `artifact_key`, runs distintos,
  a do outro run mais recente. Certificar o run A reporta os grupos de **A**.
  Tem de ser SQLite real — o defeito mora na cláusula `WHERE`, e sessão fake
  seria o mock/prod drift que a §Testes do CLAUDE.md proíbe.
- **Duas mutações escritas antes do gate:** reintroduzir workspace-latest no
  substrato **reprova**; remover o corte temporal **reprova**.
- **Anti-amputação:** `investimentos` do sujeito entregue tem `len(dados) > 0` e
  `patrimonio` presente no run pinado — prova de que não é o `e4_e` amputado.
- **Não-regressão da sombra:** golden do texto do bloco sombra idêntico ao HEAD.
- **Drift honesto:** certificar qualquer um dos 61 runs não produz
  `persisted_only` originado de outro run. Exercitar em ≥3 runs **não** mais
  recentes — é o cenário do M4, onde o instrumento mente hoje.
