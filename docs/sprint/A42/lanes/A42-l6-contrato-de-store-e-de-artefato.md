---
id: A42.l6
type: lane
title: "Contrato do store: política de escopo, retenção de órfão e validação de artefato"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l6-contrato-do-store
adrs:
  - "[[ADR-291]]"
  - "[[ADR-212]]"
  - "[[ADR-278]]"
depends_on:
  - "[[A42.l5]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/dados
  - area/backend
---

# A42.l6 — `contrato-do-store` (LC08, RV4-21, RV4-23, RV4-48)

> **Origem:** [[LEDGER-CERTIFY-active]] §r4 2026-08-04 — LC08 (P1 contrato + P2 GC) ·
> [[PIPELINE-REVIEWS-active]] §r4 — RV4-21, RV4-23, RV4-48.

> **Split de 2026-08-04, por decisão do `senior-cto`.** Esta lane tinha 7 achados e era
> dois agregados empacotados. O corte não é estético — é por **arquivo, bloqueio e
> reversibilidade**: (a) formas de ADR distintas (emenda de política de escopo não pode
> ser o veículo de uma decisão de boundary `backend/` ↔ `pipeline/`); (b) esta metade
> **não está bloqueada** e a outra está, então empacotadas o trabalho livre esperava o
> bloqueado; (c) esta metade contém a única ação **irreversível** (coleta de órfão), que
> não pode ficar acoplada a um PR reversível. O predicado de extração e o registry de
> stages saíram para a [[A42.l12]]; o rótulo de período foi para a [[A42.l5]], que é a
> lane que decide período.

> **Depende de [[A42.l5]]:** o guard "por expectativa" desta lane conta **grupos que o
> run escreveu**, e é a l5 que muda o keying que define esse conjunto. Além disso o
> escopo da listagem muda o **conjunto de pernas** do merge — logo `stmts[0]`, logo o
> `titular` que vai ao hash (ver a cadeia declarada na l5). Ordem dura, não preferência.

## Problema

1. **Escopo divergente entre listagem e leitura.** A listagem de chaves é
   workspace-wide; a leitura é run-scoped em três degraus. É a assimetria que a
   [[ADR-291]] documenta como causa-raiz e consertou **só do lado da leitura**. Efeitos
   medidos: a validação de saída do razão reporta mais grupos do que o run escreveu; e
   órfão de *keying* nunca recebe prazo de retenção (a retenção é key-scoped) ⇒
   **imortal**.
2. **Coluna de lineage nunca populada** no caminho de escrita: as duas consultas
   reversas filtram por coluna 100% nula e devolvem lista vazia **em silêncio** —
   falso-negativo, não erro. E o teste passa porque a fixture semeia um shape que
   **nenhum produtor emite** — o falso-verde de fixture é a parte mais grave.
3. **Artefato persistido sem validação de schema** (dois stages sem entrada no
   mapeamento pós-write) e com versão de schema nula, embora o schema exista — e o
   artefato do run **viola** o próprio schema. Somado: um stage é gravado com nome
   legado que **escapa do gate anti-legado** por não estar no mapa que o gate deriva —
   ponto cego, não isenção declarada.

## Decisão

1. **Paridade de política de escopo** — mesma regra de três degraus na listagem e na
   leitura. **Armadilha declarada:** escopar a listagem ingenuamente torna o guard da
   [[ADR-291]] D5 dead code e reintroduz o defeito de saída vazia silenciosa; o guard tem
   de ser reescrito **por expectativa** no mesmo PR, e a expectativa depende do keying da
   [[A42.l5]] — se esta lane mergear depois dela, o número esperado **mudou** e precisa
   ser recalibrado, não copiado.
2. **Popular a coluna de lineage no write-path** e corrigir a fixture para o shape que
   os produtores realmente emitem.
3. **Validação de schema pós-write nos stages faltantes.** **Ordem obrigatória:
   corrigir o schema antes de gatear** — o artefato atual viola o schema, então ligar o
   gate primeiro derrubaria a geração. Incluir o nome de stage legado no mapa do gate ou
   declará-lo isento explicitamente.
4. **Coleta de órfãos por último**, em PR próprio: os órfãos são a **pré-imagem** de
   qualquer re-ancoragem de override, e apagá-los antes é irreversível.

Forma: **emenda [[ADR-291]]** (política de escopo) — a decisão existe, o lado da
listagem ficou de fora. Toca também [[ADR-278]] (coluna de lineage) e [[ADR-212]] (hook
pós-write).

## Critério de aceite

**Piso de DoD = decisões 1 a 3.** A coleta de órfãos (decisão 4) é trailing declarado e
irreversível — se a lane travar, queremos a política correta em `main` sem ter apagado
nada.

- Listagem e leitura devolvem o mesmo conjunto sob a mesma política; a validação de
  saída do razão reporta exatamente o que o run escreveu.
- Guard da [[ADR-291]] D5 **reescrito por expectativa** e provado por mutação: cenário
  de saída vazia ⇒ falha. Sem isso o fix de escopo mata o guard.
- Consulta reversa de lineage devolve resultado não-vazio no corpus, e a fixture usa
  shape emitido por **produtor real** — teste que falha se a fixture divergir do produtor.
- Schema corrigido **antes** do gate; validação pós-write ativa nos dois stages; o
  artefato do run passa em modo estrito.
- Nenhum artefato com prazo de retenção nulo por ser órfão de keying.
- Coleta de órfãos em PR **posterior**, com contagem antes/depois declarada e delta de
  override orfanado igual a zero.
