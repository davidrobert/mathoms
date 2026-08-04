---
id: A42.l6
type: lane
title: "Contrato de store e de artefato: escopo, predicado único de extração e registry de stage"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l6-contrato-de-store-e-de-artefato
adrs:
  - "[[ADR-291]]"
  - "[[ADR-212]]"
  - "[[ADR-093]]"
depends_on: []
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/dados
  - area/backend
---

# A42.l6 — `contrato-de-store-e-de-artefato` (LC08, LC09, RV4-15, RV4-19, RV4-21, RV4-23, RV4-48)

> **Origem:** [[LEDGER-CERTIFY-active]] §r4 2026-08-04 — LC08 (P1 contrato + P2 GC),
> LC09 · [[PIPELINE-REVIEWS-active]] §r4 — RV4-15, RV4-19, RV4-21, RV4-23, RV4-48.
> Sete achados, um contrato.

## Problema

O contrato do store de artefatos e o do registro de stage estão inconsistentes em
cinco pontos que se sobrepõem:

1. **Escopo divergente entre leitura e listagem.** A listagem de chaves é
   workspace-wide; a leitura é run-scoped em três degraus. É a assimetria que a
   [[ADR-291]] documenta como causa-raiz e consertou **só do lado da leitura**.
   Efeitos: a validação de saída do razão reporta mais grupos do que o run escreveu; e
   órfão de *keying* nunca recebe prazo de retenção (a retenção é key-scoped) ⇒
   **imortal**.
2. **Predicado de "extraído" que aceita stub.** Um consumidor considera o documento
   extraído sem inspecionar o payload, então o stub de escalação satisfaz a condição:
   limpa a marca de revisão e liga o selo. Os outros dois consumidores do mesmo fato
   **inspecionam** o payload. Três leitores, duas semânticas.
3. **Lista de stages de extração hardcoded.** O sincronizador conhece três stages e
   desconhece os criados depois de três ADRs: documentos efetivamente extraídos ficam
   marcados como sem extrato, e o status é promovido incondicionalmente.
4. **Coluna de lineage nunca populada** no caminho de escrita: as duas consultas
   reversas filtram por coluna 100% nula e devolvem lista vazia **em silêncio** —
   falso-negativo, não erro. E o teste passa porque a fixture semeia um shape que
   nenhum produtor emite.
5. **Artefato persistido sem validação de schema** (dois stages sem entrada no
   mapeamento pós-write) e com versão de schema nula, embora o schema exista — e o
   artefato do run **viola** o próprio schema. Somado: um stage é gravado com nome
   legado que escapa do gate anti-legado por não estar no mapa que o gate deriva —
   ponto cego, não isenção declarada.
6. **Rótulo de período que subrepresenta o span real** — chave de um mês
   transportando treze, porque o período vem de um valor único expandido enquanto os
   lançamentos carregam o documento inteiro.

## Decisão

1. **Paridade de política de escopo** — mesma regra de três degraus na listagem e na
   leitura. **Armadilha:** escopar a listagem ingenuamente torna o guard da
   [[ADR-291]] D5 dead code e reintroduz o defeito de saída vazia silenciosa; o guard
   tem de ser reescrito **por expectativa** no mesmo PR.
2. **Predicado único** `documento_foi_extraido(payload)`, extraído para um só lugar e
   consumido pelos três leitores. Um stub nunca satisfaz.
3. **Derivar a lista de stages do registry**, mais teste de completude que **falhe na
   próxima ADR** que adicionar stage de extração. O teste é o ponto: sem ele o defeito
   volta na próxima adição.
4. **Popular a coluna de lineage no write-path** e corrigir a fixture para o shape
   que os produtores realmente emitem — a fixture falsa é a parte mais grave, porque é
   o que fez o defeito passar por testado.
5. **Validação de schema pós-write nos stages faltantes.** **Ordem obrigatória:
   corrigir o schema antes de gatear** — o artefato atual viola o schema, então
   ligar o gate primeiro derrubaria a geração. Incluir o nome de stage legado no mapa
   do gate ou declará-lo isento explicitamente.
6. **Derivar o período do span real** dos lançamentos.
7. **Coleta de órfãos depois** do resto: os órfãos são a pré-imagem de qualquer
   re-ancoragem de override e apagá-los antes é irreversível.

Forma: **emenda [[ADR-291]]** (política de escopo) — a decisão existe, o lado da
listagem ficou de fora.

## Critério de aceite

- Listagem e leitura devolvem o mesmo conjunto sob a mesma política; a validação de
  saída do razão reporta exatamente o que o run escreveu.
- Guard da [[ADR-291]] D5 **reescrito por expectativa** e provado por mutação:
  cenário de saída vazia ⇒ falha. Sem isso o fix de escopo mata o guard.
- Um único predicado de extração no repo (grep prova a unicidade); stub **nunca**
  limpa marca de revisão nem liga selo. Teste com stub explícito.
- Teste de completude de stages que **falha** se um stage de extração novo não for
  registrado — verificado adicionando um stage fictício.
- Consulta reversa de lineage devolve resultado não-vazio no corpus, e a fixture usa
  shape emitido por produtor real (não o inventado).
- Schema corrigido **antes** do gate; validação pós-write ativa nos dois stages; o
  artefato do run passa em modo estrito.
- Nenhum artefato com prazo de retenção nulo por ser órfão de keying.
- Coleta de órfãos em PR **posterior**, com contagem antes/depois declarada.
