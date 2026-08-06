---
id: A40.l2
type: lane
title: "Identidade de lançamento cross-documento: tipo_conta com vocabulário divergente + titular vazio"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P0
branch_slug: a40-l2-identidade-lancamento-cross-doc
adrs: ["[[ADR-354]]"]
depends_on: ["[[A40.l1]]"]
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p0
  - area/pipeline
---

# A40.l2 — `identidade-lancamento-cross-doc` (RV3-01 · Crítico)

> ⚠️ **Leia a §Problema antes de codar.** O mecanismo publicado originalmente no
> [[REPORT-REVIEWS-active]] estava **errado** e foi corrigido pelo painel. A
> versão errada leva a um fix que é **no-op** e fecha verde.

> 🔴 **Segunda correção de mecanismo — 2026-08-05.** O [[LEDGER-CERTIFY-active]]
> §r4 (2026-08-04) **eliminou 4 dos 5 desenhos de fix** do §Escopo original. O
> defeito medido não mudou; o mecanismo mudou de *canonicalizar a montante* para
> *colapsar por transação antes do agrupamento*. O §Escopo abaixo foi reescrito e
> a decisão está na **§Emenda de [[ADR-354]]** (2026-08-05). O plano de 5 PRs
> que estava aqui até 2026-08-04 colapsaria ~48% do defeito **ou** apagaria dado
> legítimo — não o siga a partir de histórico de PR antigo.

## Medição herdada da [[A40.l1]] (instrumento pronto, baseline congelado)

O detector cross-grupo mediu o defeito desta lane no corpus dogfood. **Não
re-meça do zero — parta daqui:**

- **261 ocorrências**, Σ excesso 81.288.000 cents. `carrier-shaped=261`,
  `coincidence-shaped=0`.
- Composição **exaustiva**: `banco` preenchido e **idêntico** nas duas pernas ·
  `titular` **parcial** (preenchido numa, vazio na outra) · `tipo_conta` no par
  `('extrato','extratoconta')` · `(2 rows, 2 provs)` em 100%.
- **`banco` não diverge em nenhuma das 261** — confirma a decisão nº 1 do painel
  e sepulta o mecanismo original do achado.
- **Blast radius da re-ancoragem: 5 overrides** julgáveis (+7 quarentenados,
  inertes). O passo de re-ancoragem é muito mais barato que o desenho assumia.
- Baseline congelado off-git em `storage/<uuid>/ledger_certify/` (path e valores
  fora do git, [[ADR-343]]).

**Como provar o fix:** re-rodar `dev/certify_ledger_local.py <ws>` e comparar o
numerador contra 261. A l1 deixou **8 ratchets — 4 re-confirmados manualmente, 4
só com a prova do implementador** (ver [[A40.l1]] §Fechamento, residual 4) —,
então filtro ou cap silencioso **no numerador** quebra teste em CI (grupo
`dev_tools` no `ci.yml`).

> ⚠️ **Furo conhecido do instrumento que você vai usar como prova.** Os caps de
> **comprimento** do render não têm ratchet: `dev/ledger_cross_group_render.py:118`
> e `:124` (histogramas, 12), `:126` (`_fmt_occurrences(hits, 20)`) e `:137`
> (cap 8). Os ratchets existentes pinam o **numerador impresso**
> (`test_numerador_nao_tem_cap_constante`,
> `test_render_pina_o_numero_impresso_em_corpus_misto`), não o comprimento das
> listas — a lista de evidência pode encolher em silêncio enquanto o headline a
> contradiz. **Prove pelo numerador, não pela lista renderizada.** Detalhe em
> [[A40.l1]] §Fechamento, residuais 3 e 4.

**Residual que esta lane herda:** o predicado de carrier 1 aceita QUALQUER
divergência de `tipo_conta` (mais largo que o par variante). Par de tipos de
conta genuinamente distintos sai `carrier-shaped` e fica in-whitelistável no
**detector**. O PR1 fecha isso **do lado do colapsador** — a allow-list
(`extrato` ≡ `extratoconta`, com deny-list de sufixo de moeda) impede que o par
conta↔poupança colapse. O detector segue sobre-detectando rotulado, que é a
direção correta para instrumento ([[ADR-342]]); só o mutador precisa da
allow-list. Assimetria que **continua aberta**: variante de vocabulário em
`banco` com as duas pernas cheias não é carrier-shaped hoje, e o colapsador a
bloqueia por `banco_conflitante` — logo um alias de `banco` exigiria tratamento
próprio nos dois lados.

## Problema

O mesmo lançamento entra **duas vezes** no razão E4, vindo de dois documentos do
mesmo banco. As pernas diferem em `banco` (caixa), `tipo_conta` e `titular`, e o
`transaction_hash` diverge — então o dedup K4 não colapsa.

**O carrier NÃO é a caixa de `banco`.** `normalize_banco` (`_tx_identity.py:75`)
faz `_WHITESPACE_RE.sub("", _strip_accents(value).lower())` e é chamada dentro de
`_hash_v1` **e** `_hash_v2` (`:233`). `c6bank` e `C6Bank` produzem o mesmo
componente de hash. A caixa fura a **chave de grupo**, não o hash.

Os carriers reais, ambos sobrevivendo à normalização como strings distintas:

1. **`tipo_conta`** — `extrato` vs `extratoconta`. `normalize_tipo_conta` (`:84`)
   só faz casing/whitespace, **não vocabulário**.
2. **`titular`** vazio numa das pernas. Efeito de segunda ordem:
   `_has_discriminants` (`:169-171`) devolve `False`, então `natural_key` sai
   `None` — mas o `transaction_hash` **continua sendo computado** com titular
   vazio. A perna fica sem chave de re-ancoragem e com hash próprio.

## O que a medição de 2026-08-04 eliminou

Os 4 desenhos abaixo estavam no §Escopo desta lane e **morreram por medição**
([[LEDGER-CERTIFY-active]] §r4). Ficam registrados para que ninguém os
ressuscite achando que são escopo pendente:

| Desenho morto | Por que morreu |
| --- | --- |
| alias-map de `tipo_conta` como **canonicalização a montante** da chave de grupo | A chave que faz as duas pernas se encontrarem é **provenance-free** e não contém `tipo_conta`. Canonicalizar a montante não é pré-requisito de nada |
| **fail-closed** em vocabulário desconhecido | Cobertura de contraparte é **50,88%** ⇒ quarentenar apagaria ~252 rows de fonte única ou órfãs. Fail-closed aqui é destrutivo |
| **fail-closed** em `account_type_equivalences` (`account_grouper.py:181`) | Mesma medição |
| **fundir os grupos-fonte** | Colapsa só ~48% (teto 126/261, LC03) **e** é destrutivo: a perna LLM não tem saldo e o merge elege `closing_balance=stmts[-1].closing_balance` **posicional** (`e3_reconciler_adapter.py`) ⇒ apagaria o saldo da conta inteira (LC13) |

**Sobreviveu:** colapso **por transação**, pré-agrupamento — e o alias-map do dono
renasce como **allow-list do predicado de colapso**, não como canonicalização.

## Escopo — 5 PRs, nenhum toca `_hash_v2`

`_hash_v1` está **congelado** ([[ADR-278]] D1) e `_hash_v2` é a chave de dedup
**e** de re-ancoragem de `transaction_overrides`. O colapsador **seleciona rows**;
não toca input de hash — a §Não-decisão da [[ADR-354]] (nenhum `_hash_v3`) segue
integralmente válida.

- **PR0 (docs-only, feito)** — **§Emenda de [[ADR-354]]** em 2026-08-05, no PR #1195:
  revoga as duas primeiras §Consequências e registra o predicado de 4 cláusulas.
- **PR1 — colapsador measure-only** ✅ **PR #1195**. Domain service puro
  `CrossDocumentCollapser`, injetado com `default None` no `E3ReconcilerAdapter`
  **após** `reconcile_with_report` e **antes** do agrupamento. Chave = a do detector
  da [[A40.l1]]. Não remove row; emite **alvo com multiplicidade** (`RemovalTarget`).
  ⚠️ O contrato original — "emite os `_hash_v2` que removeria" — era **errado**: hash
  não endereça row (ver §P0 achado pela verificação). Corrigido no PR1b.
- **PR1b — correção do P0 de endereçamento** ✅ **PR #1208** (`c0c27a9b`). Troca a
  lista de hashes por `RemovalTarget(hash, remover, no_bucket)`; `hash_desaparece` é o
  predicado que o PR2 consome. Saiu **separado** do instrumento a pedido do
  `pr-size-labeler` — 97 linhas que mudam contrato merecem revisão isolada.
- **PR1d — cardinalidade por arquivo** ✅ (este PR). Revoga a cláusula 4 (§Emenda 2 da
  [[ADR-354]]) e **reordena o resto**: vem antes do gate, porque muda o alvo que o gate
  mede. Rebaseline 411 → **593**.
- **PR1c — instrumento de E3.** Promove a medição a parte do harness
  (`dev/ledger_collapse_layer.py`), com **4 identidades** e ratchet por mutação;
  injeta o colapsador **no harness** via kwarg do `_e3_build_adapter`, não em
  produção. **Bloqueia o PR3** por dois eixos medidos: `alvo_enderecavel=false` (411
  declaradas vs 453 resolvidas) e 113 das 411 rows fora do campo de visão do detector.
  Custo S, 0 LLM, read-only.
- **PR2 — re-ancoragem (backend), pré-condição do enforce.** Consome os
  `RemovalTarget` do PR1b (não "os hashes" — hash não endereça row), cruza com
  `transaction_overrides` ativos e produz o mapa
  removido→sobrevivente. Respeita o boundary (`pipeline/**` sem `sqlalchemy`): o
  pipeline **emite**, o backend **decide**. Enforce só liga se a interseção for
  vazia **ou** o mapa cobrir 100%.
  **Não construa do zero** — `backend/app/services/internal_ops/backfill_override_identity.py`
  ([[ADR-282]]) já tem a máquina: `ReanchorPlan`, `CollisionPlan` (N overrides
  colapsam numa chave ⇒ vencedor reancora, perdedores soft-delete),
  `BackfillReport`, revalidação TOCTOU entre plan e apply, e o filtro
  `orphaned_at IS NULL` que mantém override quarentenado inerte. O delta desta
  lane é a **fonte** dos candidatos (hashes do colapsador em vez de
  `natural_key_hash IS NULL`).
- **PR3 — enforce.** Colapsa de fato, com os 4 eixos de aceite abaixo.

**`titular` vazio deixa de ser PR próprio:** é a cláusula de unificabilidade do
predicado (perna vazia unifica, perna conflitante não colapsa) e já está no PR1
com teste. O débito de âncora estável de override que a [[A42]] §Fora do sprint
roteia para "l2 PR3" é atendido pelo **PR2** desta numeração.

## Medição do PR1 contra o corpus real (2026-08-05) — a banda estava errada

O PR1 shipou o instrumento; esta é a primeira vez que ele foi **apontado para o
corpus**. Detector e colapsador medidos na **mesma re-derivação** (`_rederive` do
`dev/certify_ledger_local.py`, ws dogfood, run `82b30303`, zero-write):

| | detector ([[A40.l1]], baldes E4) | colapsador (statements E3) |
|---|---|---|
| chaves colidentes | **261** (261 carrier, 0 coincidence) | **331** |
| rows removíveis | — | **411** |
| bloqueados pelo predicado | — | **0** |

**Paridade é EXATA, por digest.** Os dois instrumentos derivam a chave com
`sha256("|".join(str(p) for p in key))` sobre tuplas de conteúdo idêntico — o
detector trunca em 8, o colapsador em 12 —, então `det.key_digest ==
col.key_digest[:8]` é comparação exata, não aproximação:

| | chaves |
|---|---|
| em ambos | **261** |
| só no detector | **0** |
| só no colapsador | **70** |

`261 + 70 = 331` fecha. **O detector é subconjunto estrito do colapsador.**

> ⚠️ **Correção de método, mesma sessão.** A primeira medição publicada aqui usou
> paridade por `(mês, cents, moeda, direction)` — tupla **mais grossa que as duas
> chaves**, porque descarta a descrição — e reportou `225 / 0 / 66`. Ela colapsava
> eventos distintos na mesma tupla e **subcontava a interseção**. O número por
> digest (`261 / 0 / 70`) é o correto. Lição: paridade entre dois instrumentos exige
> a chave dos instrumentos, não uma projeção dela.

**A identidade que fecha o diagnóstico de camada.** Aplicando a fórmula **do
detector** (`(n_provenances − 1) × valor_cents`) aos grupos **do colapsador**,
restritos às 261 chaves compartilhadas, sai **81.288.000 — idêntico ao cent** ao
número do detector. Mesma chave, mesmo valor, mesma fórmula ⇒ mesmo número: não há
drift de normalização, de data nem de moeda entre as camadas. É prova mais forte que
qualquer paridade.

**Σ cents exige nomear a fórmula em cada célula** — três somas plausíveis diferem em
até 2,6× e a primeira versão desta seção comparou duas delas como se fossem a mesma
grandeza:

| soma | valor |
|---|---|
| detector: `Σ (n_prov − 1) × cents` | 81.288.000 |
| colapsador: `Σ cents` por chave | 186.132.700 |
| colapsador: `Σ cents × rows removíveis` | 216.980.850 |
| colapsador: `Σ cents × n_rows` | 490.090.665 |

> ⚠️ **O `excess_cents` do detector é PISO por construção, não medida do fenômeno.**
> Nas mesmas 261 chaves o E3 tem **733 rows** (`{2:111, 3:89, 4:61}`) e o E4 apenas
> **522** (`{2:261}`) — o dedup por `transaction_hash` do E4 já achatou a
> multiplicidade intra-proveniência antes do detector olhar. **O detector é incapaz
> de reportar multiplicidade ≥3.** Uma versão anterior desta seção atribuía o gap ao
> "efeito multiset", com o sinal invertido: o multiset **reduz** removable (593→411)
> e não pode explicar gap para cima.

Quatro leituras. A primeira invalida o critério que estava escrito aqui; a última
inverte uma conclusão que esta lane publicou como confirmada.

1. **A banda `[259,261]` é falsificada, e a causa é erro de camada** — instrumento em
   **E4**, mutador em **E3**, populações diferentes por construção (detector varre
   4.321 rows; o E3 tem 6.398 tx, e a [[A40.l1]] §SUB-detecção já declarava que
   transferência e par em baldes opostos não chegam aos baldes). **Mas "não é bug" era
   falso:** o artefato do PR1 carregava um P0 próprio (leitura 4).
2. **`0 só no detector` autoriza o detector como oráculo secundário** — o colapsador
   cobre tudo que o instrumento conta, sem ponto cego na direção perigosa. O gate
   "re-rodar e ver 0", porém, **é vácuo para 113 das 411 rows (27,5%)**: 89 das 70
   chaves exclusivas mais 24 dentro das compartilhadas, nenhuma existindo como
   `transaction_hash` em balde algum (comparador validado — 298 de 322 casam, logo o
   0/89 é ausência real).
   **Correção de materialidade:** dizer "58% dos cents" era enganoso. Desses cents,
   **99,7% são transferência interna** (64 chaves / 79 rows / 124.962.300), valor
   bruto **dinheiro-neutro** no fluxo, sem row em `receitas`/`despesas`, sem campo de
   relatório e sem âncora de override. O bloqueio do PR1b se sustenta pelo **grão row
   e pela ausência de instrumento**, não pela massa em cents — e a materialidade zero
   é **condicional** à classificação atual de transferência interna, que este repo já
   viu sobre-disparar.
3. **`0 bloqueados` ⇒ 6 de 6 ramos de rejeição inexercitados** (não "4 de 5"), medidos
   independentemente e sem short-circuit: `descricao_vazia`,
   `proveniencias_diferente_de_duas`, `banco_conflitante`, `titular_conflitante`,
   `tipo_conta_fora_da_allow_list`, `par_nao_e_nativo_mais_llm`. Duas nuances que
   mudam a leitura: a allow-list de `tipo_conta` é **331/331 no lado do PASS** —
   inexercitada no bloqueio, porém **load-bearing**, é o que separa colapsar de
   apagar; e `titular` é satisfeito **por vacuidade** em 331/331, com
   `account_number_norm` vazio em 117/117 statements. A evidência de identidade do
   predicado reduz-se a `banco` + a chave de colisão.
4. **A cláusula multiset NÃO salva 182 transações legítimas — ela preserva 182 rows de
   duplicação intra-proveniência.** A aritmética está certa (924 rows medidos direto,
   593 ingênuo − 411 multiset = 182); a **semântica está invertida**. Nas 262 legs com
   ≥2 rows: `source_document` difere em **262/262**, merge_key legado difere em
   **262/262**, mesmo objeto em **0/262**. A descrição bruta é **byte-idêntica em
   168** (onde `is_duplicate` retorna `True` em 168/168) e nas outras **94** a
   divergência é *exatamente* o sufixo de roteamento que `normalize_descricao`
   remove ([[ADR-255]] it.2, cujo docstring cita extratos sobrepostos do C6).
   **0/262 têm evidência de 2 eventos distintos.** Estrutural: as rows de um bucket
   são K4-idênticas **por construção**, então a cláusula não tem como distinguir "o
   evento ocorreu 2×" de "uma perna reportou 2×" — os campos que distinguiriam não
   estão na chave nem no hash.
   **Consequência dura:** 411 não é o lado conservador de um trade-off — é
   **insuficiente em 182 rows / Σ 86.977.115 cents**. Pós-enforce, **182 de 331 chaves
   (55%)** ficariam com 2 rows onde os predicados do próprio pipeline reconhecem 1
   evento. Só as 149 chaves `card=1` saem corretas. O número consistente com
   `is_duplicate` + [[ADR-255]] neste corpus é o **ingênuo 593**.

### P0 achado pela verificação: hash não endereça row

O §Escopo dizia que o PR1 "emite candidato com os `_hash_v2` que removeria" e que o
PR2 "consome os hashes do PR1". **Isso estava errado como contrato.** As 8 partes de
`_hash_v2` são a **união** da 5-tupla da chave de colapso com a tripla de
proveniência, logo **todas** as rows de um bucket compartilham o mesmo hash — 1 hash
endereça N rows.

Medido: alvo declarando **411** rows **resolve 453**. O excesso de **42** são
exatamente os sobreviventes que a cardinalidade multiset elegeu; um consumidor que
apagasse pelo conjunto de hashes apagaria o sobrevivente junto, e **nenhum
instrumento existente perceberia**. Aritmética por forma: `(1,1)×149` excesso 0 ·
`(1,2)×60` excesso 0 · `(2,1)×42` excesso **1** · `(2,2)×80` excesso 0.

**Contrato correto** (entregue junto do PR1b): o candidato emite
`RemovalTarget(hash, remover, no_bucket)` — alvo com **multiplicidade** —, e
`hash_desaparece` (`remover >= no_bucket`) é exatamente o predicado de que o PR2
precisa para saber se um override ancorado naquele hash órfãna. `alvo_ambiguo` marca
remoção parcial de bucket.

O teste que deixou o P0 passar assertia `len(removable_hashes) == removable_rows` —
**comprimento de lista, cego à resolução**. E o comentário adjacente declarava que as
formas assimétricas "não ocorrem no corpus": falso, `(2 llm, 1 nativo)` ocorre **42×**
e só 149 das 331 são `2 rows, 2 provs`. O comentário justificava como hipotético
exatamente o caso real.

### Três classes que nenhuma das leituras cobria

1. **Duplicação intra-proveniência cross-arquivo — 182 rows / Σ 86.977.115.**
   Nenhum dos três dedups a alcança: por statement (`reconciliation_service.py`,
   escopo = 1 statement) · `cross_file_dedup` (só roda com >1 statement no mesmo
   `output_key`, e a key legada carrega **período** — arquivos de período sobreposto da
   mesma conta nunca se encontram; 9 de 106 grupos têm >1 statement) · o colapsador
   (`_group_by_key` exige ≥2 proveniências, logo é cego a colisão dentro de uma).
   **Não é "o dedup pega isso depois".** É buraco estrutural, e é o que a cláusula
   multiset transforma de defeito em feature. Candidato a lane própria — sobrepõe-se à
   [[A42.l5]] (período na chave de grupo).
2. **Assimetria de `kind` entre pernas do mesmo evento — 6 chaves, Σ 388.300.** A perna
   nativa classifica receita/despesa (com row em balde) e a LLM classifica
   `transferencia` (sem row em balde nenhum), porque `InternalTransferDetector` recebe
   `banco`/`tipo_conta` — precisamente os campos que divergem. Defeito do razão
   **atual**, independente do colapsador, e nenhum dos dois instrumentos o reporta.
3. **O predicado é cego a período.** Duas pernas com períodos declarados **totalmente
   disjuntos** saem `blocked_reason=None`. Recomendação: **não** adicionar cláusula de
   período — o metadado não sustenta decisão (na perna LLM, **85,2%** das rows caem
   fora do próprio período declarado, contra 1,8% na nativa) — e sim corrigir o
   docstring, que justificava o mecanismo com uma premissa que nada verifica. Feito.

## Co-design de 2026-08-05 — seis premissas minhas morreram

`data-engineer` + `financial-planner` em paralelo (gatilho duplo: contrato entre stages
+ regra de domínio sobre dinheiro). **Não ressuscite nenhuma destas:**

| Premissa que eu escrevi | Por que é falsa |
| --- | --- |
| "a perna LLM não carrega âncora v2, logo remover row dela não órfãna override" | O gate `_has_discriminants` governa só o campo `natural_key` do **item E4**. O subsistema de override tem **hasher próprio, sem gate** (`override_identity.py:52-65` → `compute_natural_key`), e é esse valor que o read-path casa. Row de perna LLM **pode** ancorar override em v2, com hash degenerado. Gate construído sobre isso nasce cego na classe exata que o enforce apaga |
| "cruzar os alvos com `transaction_overrides.transaction_hash`" | Coluna é **namespace de versão mista**: row pré-cutover carrega `_hash_v1`, pós-cutover `_hash_v2`. Interseção contra conjunto v2 dá vazio **por incompatibilidade de versão**, não por corpus — foi exatamente o meu 0/5 |
| "o único sintoma do colapso não declarado é o valor degradar" | `e2_to_e3` monta `count_out = survivors + Σ transacoes_duplicadas_removidas`, e esse campo é **só cross-file**. Canal novo em `remocoes` **não entra no `count_out`** ⇒ dispara o check de *count* antes de qualquer check de valor. Corolário: a invariante 7 da [[ADR-347]] (`duplicadas == intra + cross_file`) **não é verdade hoje** e nada a testa |
| "reusar `candidate.valor_cents` no 5º canal" | `CollapseCandidate.valor_cents` é **magnitude** (`decimal_cents` faz `abs()`); o ledger grava **assinado** (débito negativo). Reusar faz `_declared_dedup_cents` nunca fechar contra `val_in − val_out` |
| "cardinalidade correta = eventos distintos por `is_duplicate` ou descrição normalizada" | Normalizada é **degenerada** (constante dentro da chave ⇒ `card=1` sempre = colapso ingênuo disfarçado). `is_duplicate` byte-idêntico é **o critério que já falhou** nas 94/262 legs com sufixo de roteamento. O discriminador é **`source_document`** |
| "`alvo_enderecavel` é pré-condição do enforce" | Mede se um consumidor **que apaga por conjunto de hash** removeria a mais — consumidor que a decisão de D2 garante nunca existir. E **degrada** de 42 para 140 sob a regra nova: evidência de que a métrica é errada, não de que a regra é |

**Sequenciamento decidido** (reordena a lane; D4 primeiro porque muda o alvo que o
gate mede — gate construído sobre 411 seria re-medido inteiro):

`PR1d` cardinalidade ✅ → `PR-D2/D3` (`collapse()` + 5º canal + `intra` autoritativo +
schema + patch do `count_out`) → `PR-D1` (gate + `AuditRecord` + flag) → `PR3` (flip
em produção).

### O que o PR-D2/D3 tem de trazer

- **`collapse(statements) -> (statements, candidates, removals)`** — mutação é
  **seleção sobre os objetos no mesmo passo**, cópias via `replace` (idioma de
  `_reconciled_copy`, que existe porque construtor campo-a-campo perdia campo).
  Identidade de row = identidade de objeto dentro da chamada. **Zero endereço
  serializado, zero `_hash_v3`.**
- **5º canal `cross_document_collapse`** com `count` **e** `valor_cents` **assinado**
  (somado das `Transaction` removidas), emitido **por statement** via `DedupRemoval`
  (o ledger é per-group; atribuição global não fecha).
- **`intra` deixa de ser inferido por diferença.** Motivo mais forte que "os canais
  competem pela mesma subtração": a inferência é **o mecanismo que converte remoção
  não-declarada em absorção silenciosa**. Com `intra` autoritativo, canal futuro
  não-instrumentado produz resíduo ≠ 0 ⇒ `PERDA_SILENCIOSA` **alto**. É a [[ADR-342]]
  aplicada ao próprio ledger.
- **Patch obrigatório no harness:** `e2_to_e3` passa a usar
  `count_out = survivors + Σ remocoes[*].count` quando `remocoes` existe, com fallback.
  Sem isso o PR3 fecha com veredito degradado por bookkeeping.
- **Schema:** `config/schemas/e3_reconciled.schema.json` tem `additionalProperties:
  false` em `remocoes` ⇒ editar **no mesmo PR do writer**, senão hard-fail no step
  `MATHOMS_PIPELINE_SCHEMA_MODE=strict`. Compat sem campo de versão: propriedade
  **opcional** + leitores channel-agnostic (`_ledger_verdict` e `_declared_dedup_cents`
  já iteram `.values()`), então artefato de 4 e de 5 canais coexistem sem branch.
- **Emenda datada na [[ADR-347]]**, não ADR nova — a §Dec-4 é dona da partição.
  **Antes** do flip HARD do PR3 dela, senão o teste de exaustividade nasce sobre uma
  partição de 4.
- **Bug adjacente:** `_intra_cents_by_source` é dict-comprehension keyed por `source`
  ⇒ dois statements com o mesmo `source_document` se **sobrescrevem** e
  `_ledger_totals` somaria o mesmo cents 2×. Ao promover a count+cents, **some**.
- **Classe nova declarável:** sob a regra nova um statement da perna LLM pode ficar com
  **0 transações** e ainda escrever artefato ⇒ E3 vazio, que `e3_group_verdict` rotula
  `COBERTO_SEM_VALOR`. Declare como esperado ou pule a escrita.

### O que o PR-D1 (gate) tem de trazer

- Interseção computada **sobre as colunas de snapshot da [[ADR-282]]**
  (`tx_data`, `tx_valor_cents`, `tx_moeda`, `tx_descricao`), recompondo o
  **`_key_digest`** da chave de colapso — **não** por igualdade de hash. Imune a versão
  de hash, imune ao gate de discriminantes, sem PII cruzando o boundary.
- **Polaridade:** gate que **bloqueia** deve **sobre-detectar** ⇒ o join **descarta
  `direction` e proveniência**. Over-match é adjudicável à mão em 5–12 rows;
  under-match é override órfão em produção. Isso também absorve a deriva medida E3↔E4
  (4282/4320 = 99,1%), que vem de `direction` (sinal vs balde).
- Override com `natural_key_hash IS NULL` **e** `orphaned_at IS NULL` (âncora
  indecidível) conta como **hit e bloqueia**. Hoje são 0.
- Mora em `backend/app/services/internal_ops/collapse_precondition.py`, read-only,
  devolvendo `OpResult`. **Não persiste tabela** ([[ADR-111]]): durabilidade é
  `AuditRecord` via `append_audit`. O enforce destrava por **feature flag** flipada
  pelo operador, **não** por leitura runtime do gate (acoplamento de estado + forçaria
  `pipeline/**` a consultar DB). Flag nova exige entry em `DEFAULTS` no mesmo PR.
- **Duas faces, e a segunda é obrigatória:** "vazio" é propriedade do corpus **e do
  tempo**; gate one-shot pré-flip caduca no dia seguinte. Face (b): por run, emitir
  `ReviewReason` informativo quando `hash_desaparece` casa override ativo — mantém o
  sinal vivo pós-flip sem bloquear (measure-then-emit, [[ADR-347]] §Dec-3).

### Salvaguardas de produto exigidas pelo `financial-planner` (bloqueantes no PR3)

O erro não é +19% na receita: é **+63% no superávit** (erro de diferença amplifica os
dois níveis), e ele entra na **janela 12m** que é denominador de todo headline —
score, reserva-alvo, patrimônio-alvo, taxa de poupança, folga. O modo de falha é
comportamental antes de numérico: a família compromete um aporte que não se sustenta, quebra no mês 3 e saca da
reserva, perdendo o **hábito**, que vale mais que o valor.

1. **Contador visível na S2** (Fluxo de Caixa), não a lista: *"N lançamentos
   consolidados por sobreposição de documentos, em M meses"*. Aterrissa em
   `analise_financeira` (metadata de `fluxo`). **Sem essa linha o PR3 não mergeia** — o
   agregado fica irreconciliável contra o extrato do banco, e para o planejador B2B2C,
   que responde profissionalmente pelo número, ledger irreconciliável é veto de adoção.
   Gatilho novo: mudança no que o relatório mostra ⇒ **`product-designer`** no slice de UI.
2. **`needs_review` cirúrgico, nunca em bloco** — só bucket com remoção parcial e chave
   com `kind` divergente. Review de 593 rows vira approve-all e o mecanismo morre.
3. **Sem limiar de valor.** Faz identidade depender de magnitude, que não é fato de
   domínio, e **preserva exatamente as maiores distorções** — as que movem receita 19%.
4. **Assimetria de tolerância documentada como escolha:** o colapsador é mais rígido que
   o dedup intra (sem ±3d/±R$0,01). Consequência aceita: par cross-documento com Δ1 dia
   **continua** dupla-contando. Sub-colapso limitado e nomeado > sobre-colapso ilimitado.
5. **Detalhe da remoção no ops/E7, não no relatório da família** — o planejador precisa
   da lista; a família precisa do fato.

> **O risco que o `financial-planner` recusa:** enforce que remove 593 rows sem que a
> remoção seja um número declarado que família e planejador possam **reconciliar**.
> Hoje o erro é visível como contradição ("folga confortável + reserva insuficiente");
> depois seria **invisível**. "Apagar dinheiro real não é a quebra de confiança pior —
> apagar sem dizer é."

## Decisões do dono — 2026-08-05, pós-verificação adversarial

Tomadas com o dado do dogfood declarado **descartável** (perda não é risco), logo o
critério foi **qual regra o produto quer a longo prazo**, não qual é segura de tentar.

### D5 — o enforce cobre as 453 de perna LLM; as 140 nativas ficam de fora

**Não é sobre risco. É sobre coerência.** A verificação mediu que o enforce **retém 576
rows da MESMA forma** que remove nas 140 — mesma chave, mesma proveniência, arquivos
distintos —, porque `_group_by_key` só retém chave viva em **≥2 proveniências**. O
discriminador entre remover e reter é, portanto, **se por acaso existia uma perna LLM
naquela chave**.

Isso é acidente, não regra. Consequências que reprovam:

- O razão pós-enforce fica **internamente inconsistente**: nenhum consumidor consegue
  afirmar "duplicação intra-proveniência foi removida" nem "foi preservada".
- É o mesmo vício que reprovou a opção A na decisão de cardinalidade — identidade de
  lançamento dependendo de circunstância do upload, não do fato.
- A premissa do D4 para essa classe **falha em 16/140 dias** (contagem diferente entre
  os dois arquivos) e em 61/140 (multiset de chaves diferente).
- O único oráculo externo — resíduo `saldo_final − (saldo_inicial + Σ tx)` — **piora em
  3/3** grupos mensuráveis, e cada delta é exatamente o cents do canal daquele grupo,
  somando as 140.
- A metade protetiva do D4 é **vácuo empírico**: `card {1: 331}`, 0/331 exercita a guarda.

**As 453** (remoção de perna LLM inteira) entram: **zero** sinal contrário, native-first
100%, `kind` de fluxo preservado em 6/6, e é o defeito para o qual a lane foi aberta.

**Implementação:** `keep_native = len(group.native_rows)` — row nativa **nunca** é
removida. A cardinalidade por arquivo (§Emenda 2 da [[ADR-354]]) **continua válida** e
segue governando quantas rows da perna LLM sobrevivem; o que muda é que ela deixa de
autorizar corte no bucket nativo.

**Medido pós-D5 (corpus dogfood, 2026-08-05):** rows removidas **593 → 453**;
declarado == removido == canal (`453`); rows nativas **5504 → 5504**, preservadas;
Σ cents assinado **12.001.051** (era 64.753.775 — a queda reflete que as 140 nativas,
que carregavam 80.528.182, saíram do escopo). Chaves colapsáveis seguem 331.

> ⚠️ **Bug que a primeira tentativa de D5 introduziu, e como ele passou verde.**
> `_targets` (que computa `removable_rows`) e `rows_to_drop` (que remove) derivavam o
> corte em **cópias separadas** da mesma fórmula. Mudei uma e não a outra: o measure
> passou a declarar **453** enquanto a mutação removia **593** — com a suíte **verde**,
> porque a fixture de 1 nativa + 1 LLM é justamente o caso onde as duas concordam.
> **Só a medição no corpus achou.** `keep_split` virou fonte única e o teste novo
> exercita 7 formas assimétricas. É a materialização do risco F2 que o `senior-cto`
> nomeou ao pedir que o eixo (i) fosse promovido ao corpus.

**As 140 + 576 = 716 rows viram uma classe só** — duplicação intra-proveniência
cross-arquivo — roteada para a [[A42.l5]] com **regra e instrumento próprios**. Não é
deferimento por medo: é recusa a shipar meia regra sem instrumento, que é o padrão que
esta lane passou o dia inteiro corrigindo.

### D6 — o caption da V0 é derivado do dado, não hardcoded

Sem ele, o primeiro relatório pós-flip renderiza **"Receitas ▼19% — avaliação ruim"**
(`VariacaoSection.deltaColor` + `deltaAriaLabel`), atribuído a nada. O produto passaria
a **afirmar** que a família ganhou 19% menos — falso-positivo mais caro que o número
que estamos corrigindo, porque o erro atual é otimista e este seria acusatório.

**Regra:** presença de `consolidacao_cross_documento` no relatório atual **+** ausência
no snapshot comparado ⇒ a base de comparação mudou ⇒ caption. **Derivado**, não flag de
migração — generaliza para qualquer campo futuro que marque mudança de método, e não
deixa resíduo a limpar depois do flip.

**Sem suprimir cor** — o delta de patrimônio é legítimo e suprimir tudo distorce.

**Débito registrado, não desta lane:** a V0 **julga** (`avaliação ruim`), o que é certo
para movimento real e errado para mudança de método. A noção de **base não-comparável**
pertence ao plano [SNAPSHOT_CHANGELOG_V3](../../../plan/SNAPSHOT_CHANGELOG_V3/_README.md); abrir item lá.

**Escopo que a l2 NÃO fecha (atualizado pela D5):** a classe **inteira** de duplicação intra-proveniência cross-arquivo — **716 rows** (140 que o D4 removia + 576 que o colapsador retém por não haver perna LLM na chave). Inclui a duplicação em chave de **proveniência
única** (buraco do `cross_file_dedup` com período na key) permanece aberta e é da
[[A42.l5]]. Diga isso no PR3, senão alguém conclui que a classe estrutural fechou.

## Critério de aceite

**Anti-Goodhart primeiro:** a chave do colapsador **contém** a do detector, logo
"o numerador cai a 0" é quase tautológico — o colapso zera o instrumento por
construção. Por isso o aceite exige eixos que **não derivam da mesma chave**.

- ✅ **`alvo_enderecavel` RETIRADO de `layer_ok` em 2026-08-05** — deixa de ser
  pré-condição do PR3. A pergunta certa não era *"posso retirar um eixo de gate?"*, mas
  **"posso desfazer uma fusão?"**: três eixos respondem *"os números que imprimo são
  legíveis?"* (propriedade do **instrumento**) e `alvo_enderecavel` responde *"um mutador
  causaria dano?"* (propriedade do **produto**). Fundidos, a legibilidade ficava **refém
  de uma decisão de produto** — [[ADR-342]] invertida. A desfusão seria correta **mesmo
  com o eixo verde**.

  **Os 4 critérios do `senior-cto`**, todos verificados antes de retirar:

  | | critério | evidência |
  |---|---|---|
  | **T1** | nomear o consumidor que a métrica prediz e provar que não existe | `grep` em `main`: nenhum consumidor de `removal_targets`/`hash_desaparece` fora de teste — `collapse()` remove por `id()` sobre a mesma lista |
  | **T2** | anti-hindsight: já estava vermelha antes da degradação? | **Sim** — `false` já no #1211 com 42 ambíguos, antes do D4 levá-la a 140. Quem move a trave não constrói o gate que o bloqueia nem publica o bloqueio |
  | **T3** | a substituição domina na classe de falha | `test_declarado_bate_com_removido_em_corpus_HETEROGENEO` mede **7 formas assimétricas** (promovido após o bug do D5, que a fixture simétrica não pegava) + o canal do ledger |
  | **T4** | o número continua visível **e** ratcheteado | segue no render com ⚠️, e o teste assere que o texto **não some** |

  🔴 **Falsificador a vigiar (F1):** se algum caminho futuro — face (b), re-ancoragem,
  console ops — resolver `RemovalTarget.hash` contra um conjunto de rows e **agir** por
  ele, a métrica volta a viver e a retirada vira trave movida retroativamente. **Encode,
  não confie:** o PR3 dá **consumidor legítimo** ao `RemovalTarget` (emitir o hash do
  **sobrevivente**, alimentando a re-ancoragem) **ou** o deleta. Estrutura órfã apodrece
  e depois é adotada errado por quem não leu a lane.

  **Registro histórico** — a forma dos ambíguos sob a métrica retirada:

  | forma | ocorrências | `remover` | `no_bucket` | ambíguo |
  |---|---|---|---|---|
  | 1 nativa + 2 LLM (`n_rows=3, card=2`) | **42** | 1 | 2 | **sim** |
  | 1 nativa + 1 LLM (`n_rows=2, card=1`) | 149 | 1 | 1 | não |
  | 2 nativas + 2 LLM (`n_rows=4, card=2`) | 80 | 2 | 2 | não |
  | 2 nativas + 1 LLM (`n_rows=3, card=2`) | 60 | 1 | 1 | não |

  `149+80+60+42 = 331`; `hash_desaparece=False` nos 42 (sobra 1 das 2).

  🔴 **Achado que aperta a decisão de cardinalidade.** Nos 42, a perna LLM viu o evento
  2× e a nativa 1×, então `card = max(1,2) = 2` e sobrevivem **1 nativa + 1 LLM** —
  exatamente o par duplicado **cross-documento** que esta lane existe para remover. Para
  essas 42 chaves o `411` não é "o lado conservador do trade-off": ele **preserva o
  defeito-alvo**. É a inversão da C4 (§Medição, leitura 4) aparecendo no **alvo**, não
  só na contagem — e é evidência direta a favor de recalcular `survivor_cardinality`
  sobre eventos distintos em vez de rows cruas.
- **Pré-condição 2 do PR3, bloqueante: paridade de camada.** O enforce não mergeia
  enquanto o número de E3 não tiver instrumento contado e ratcheteado — **113 das 411
  rows (27,5%)** não existem como `transaction_hash` em balde algum. Sem isso o gate
  de saída da lane é vácuo por construção. Baseline de E3 **sob a regra nova**
  (2026-08-05, pós-§Emenda 2): **331 chaves / 593 rows declaradas / 733 resolvidas /
  `card {1: 331}` / Σ(cents × rows removíveis) = 303.957.965 / 121 rows e 161.960.555
  cents fora do campo de visão do detector**. A fórmula faz parte do baseline, porque
  três somas plausíveis diferem em 2,6×. **Não pine o número como alvo** — o alvo é a
  regra; pinar 593 é Goodhart (esta lane já acumula três instâncias de identidade que
  fecha por construção e esconde o defeito).
- **Banda sobre o número de E3, não sobre 261.** O `[259,261]` que estava aqui era
  erro de camada (ver §Medição do PR1). A banda correta parte do baseline de E3
  acima; o numerador do detector E4 (261) passa a ser **oráculo secundário** que
  também tem de cair — nunca o alvo primário.
- ✅ **Cardinalidade = eventos por ARQUIVO** (§Emenda 2 da [[ADR-354]], feito no PR1d):
  sobrevivente = `max` de rows num mesmo `(proveniência, source_document)`. Duas guardas
  gêmeas, cada uma com prova por mutação: *um arquivo reportando 2× não colapsa para 1*
  e *dois arquivos reportando 1× cada colapsam para 1*.
  **Os dois critérios que eu havia proposto morreram no co-design:** descrição
  normalizada é **degenerada** (é constante dentro da chave por construção — devolveria
  `card=1` sempre, ou seja o colapso ingênuo disfarçado, apagando repetição legítima em
  80 chaves); e `is_duplicate` byte-idêntico é **o critério que já falhou** nas 94/262
  legs com sufixo de roteamento, reproduzindo o teto de ~48% que a §Emenda 1 sepultou.
- **Sobrevivente é a perna nativa em 100% dos casos**, incluindo as 6 chaves com `kind`
  assimétrico — eleger a perna LLM converteria receita em `transferencia`, **apagando
  renda em silêncio**, que é o pior falso-positivo possível neste produto.
- **Consistência com a regra vigente, testada:** par que o `is_duplicate` colapsaria
  **dentro** de um arquivo tem de colapsar também **entre** arquivos (2 rows idênticas
  em 1 vs 2 statements ⇒ mesmo resultado). É o argumento que autoriza a regra: ela é
  **estritamente mais rígida** que o dedup já vigente (±3 dias, ±R$ 0,01), logo **não
  abre classe nova de falso-positivo** — só remove a dependência de fronteira de
  arquivo de uma regra que o produto já aceitou.
- 🔴 **O PR3 precisa de um 5º canal declarado no ledger — medido 2026-08-05.** O
  `build_artifact_ledger` ([[ADR-347]]) infere o dedup intra por **diferença**
  (`intra = st.tx_loaded - len(s.transactions)`, `e3_load_report.py:120`), e o
  colapsador remove row de `s.transactions` **antes** do ledger. Consequência medida
  (fixture de 10 tx, 3 removidas): as 3 aparecem em `intra_statement_dedup`
  (`count=3, valor_cents=0`) e o **invariante do ledger FECHA** —
  `tx_carregadas == transacoes_total + Σ remocoes[*].count`. Ou seja, o enforce não
  quebra o ledger: ele **misatribui 411 rows a um canal que significa outra coisa**, e
  a partição de 4 canais (`undated_drop`, `anachronic`, `intra_statement_dedup`,
  `cross_file_dedup`) esconde isso porque é fechada e o count compensa.
  **Único sintoma:** em `e2_to_e3`, `val_out` cai mas `declared` não, então
  `value_ok = dups > 0 and (val_in − val_out) == declared` fica falso e o veredito
  degrada de `CONSERVADO` para `COBERTO_SEM_VALOR` — sinal fraco para 411 rows
  mal-atribuídas. **Ação:** o PR3 adiciona `cross_document_collapse` a `_remocoes`
  com `count` **e** `valor_cents`, e o `intra` deixa de ser inferido por diferença
  (senão os dois canais competem pela mesma subtração). Terceira instância nesta lane
  do mesmo padrão: identidade que fecha por construção esconde o defeito.
- **Continuidade de saldo** segue não medida sob remoção — abrir junto do PR3.
- **Invariante de saldo:** nenhum grupo perde `closing_balance`, a contagem de
  `saldo_final_unknown` não muda, e os 105 grupos seguem fechando em tol-0.
- **Oráculo a jusante:** queda de ~19% da receita e ~8% da despesa nos meses
  afetados, **e** desaparecimento da incoerência "folga confortável + reserva
  insuficiente" que o [[LEDGER-CERTIFY-active]] §r4 nomeia como sintoma visível.
- `COUNT(*) WHERE orphaned_at IS NOT NULL` em `transaction_overrides` **não sobe**
  entre antes e depois do backfill. Se subir → **abortar e restaurar**.
- Vetores-golden de hash em `tests/unit/pipeline/test_tx_identity_propagation.py`
  seguem verdes — o colapsador não altera nenhum hash.
- Declarar o **sinal esperado do delta** (§Decisões nº 5 do sprint) e conferir com
  `dev/golden_diff.py`.
- **Prova por mutação** em cada cláusula do predicado (8 mutações no PR1).

## Guarda anti-regressão

Duas, e nenhuma é o vetor-golden de hash (que segue válido mas agora é trivial —
o colapsador não toca hash):

1. **Equivalência com o carrier da [[A40.l1]]:** todo candidato colapsável tem de
   ser `carrier-shaped` pela definição **única** de `carrier_signatures`, com as
   tags derivadas do próprio candidato. Impede que uma cláusula relaxada faça o
   colapsador apagar a coincidência cross-conta que a l1 declara como
   sobre-detecção aceitável.
2. **Cardinalidade multiset:** impede que a chave day-exact transforme *2 eventos
   vistos 1× cada* em *1 evento*.

## Achado adjacente medido no PR1 (não é escopo desta lane)

`_reconciled_copy` (`reconciliation_service.py`) reconstrói `BankStatement`
campo-a-campo e **perde `account_number_raw`/`_norm`** — o "discriminador real
entre 2 membros no mesmo banco" da [[ADR-226]] PR2 nunca chega ao payload E3 nem
ao `account_number` por transação. Medido em 2026-08-05: presente após o load,
`None` após o reconcile. Está gateado por `xfail(strict=True)` em
`tests/unit/pipeline/test_cross_document_collapser.py::test_reconcile_preserva_todo_campo_de_identidade`;
corrigir muda output do E3 (golden), logo é **PR próprio com delta declarado**, e
o XPASS estrito força a remoção do marker. Candidato natural a dono: [[A42.l5]]
(já reescreve o keying de grupo do E3).
