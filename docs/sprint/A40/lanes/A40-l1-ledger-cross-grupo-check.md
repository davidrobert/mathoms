---
id: A40.l1
type: lane
title: "Instrumento: detector de duplicação cross-grupo + baseline congelado"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1118
ship_date: "2026-07-30"
priority: P0
branch_slug: a40-l1-ledger-cross-grupo-check
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/dx
---

# A40.l1 — `ledger-cross-grupo-check` (instrumento)

## Problema

A conservação do razão fecha em **tol-zero (105/105 grupos-fonte)** e ainda assim
há duplicação material medida no corpus dogfood. Conservação é medida **por
grupo**; a duplicação é **entre** grupos, e cada grupo individualmente fecha.
`dev/certify_ledger_local.py` não tem check cross-grupo — é o furo de método nº 4
da rodada r3.

Esta lane é o **instrumento de medição de toda a A40**: sem ela, KR-B não é
verificável e a [[A40.l2]] fecha verde sem prova. Vem **primeiro** e congela o
baseline **sobre `origin/main`**, antes de qualquer mutação (lição A39 — baseline
pós-mutação mede o próprio fix).

## Escopo

- Detector puro `cross_group_double_count(buckets_e4) -> list[...]` em
  `dev/ledger_conservation.py`, irmão de `investment_double_count`.
- **Chave provenance-free:** `(data, valor_cents, moeda, direction,
  descricao_normalizada)`. Deliberadamente **sem** `banco`/`titular`/`tipo_conta`
  — são justamente os campos que variam entre as pernas do mesmo evento.
- Acoplar ao harness `dev/certify_ledger_local.py`: **reporta, não dedupa**, e
  emite ocorrências whitelisted em **linha separada** (anti-Goodhart do KR-B).
- Medir o blast radius do backfill: contar `transaction_overrides` ancorados em
  row com `titular` vazio (via `override_dual_read.py`). Esse número dimensiona o
  risco da [[A40.l2]].
- **Congelar baseline** do corpus dogfood em `storage/<uuid>/certify/` sobre
  `origin/main`.

## Critério de aceite

- Detector reporta **> 0** no corpus dogfood hoje (se reportar 0, o detector está
  errado — a duplicação foi medida e existe).
- 4 casos em `tests/unit/pipeline/test_cross_group_double_count.py` (fixture
  sintética PII-zero): **(a)** duas pernas do mesmo evento com `tipo_conta`
  variante e `titular` vazio ⇒ **detecta**; **(b)** transferência interna legítima
  (débito na origem + crédito no destino, `direction` oposto) ⇒ **não** detecta;
  **(c)** duas compras idênticas no mesmo dia, mesmo valor, mesma descrição, mesma
  conta ⇒ **não** detecta (duplicata legítima); **(d)** mesmo valor, moedas
  distintas ⇒ **não** detecta.
- Baseline congelado documentado no corpo do PR (path mascarado, fora do git).
- **Zero mudança de comportamento** — nenhum dedup novo, nenhuma escrita.

## Guarda anti-regressão

O caso **(b)** é a guarda que importa: sem `direction` na chave, toda
transferência interna vira falso-positivo em massa e enterra o sinal verdadeiro no
primeiro run. O teste tem de falhar se alguém remover `direction` ou `moeda` da
chave.

## Onde o código mora

Três módulos, um DAG sem ciclo:

- `dev/ledger_cross_group.py` — **detecção** (chave, proveniência, carrier,
  partição, cobertura). Não importa o render.
- `dev/ledger_cross_group_render.py` — **render** (boundary de PII do bloco).
  Consome o summary por duck-typing; a anotação do dataclass é `TYPE_CHECKING`,
  logo não há import em runtime nos dois sentidos.
- `dev/ledger_conservation.py` — **re-exporta** os dois, porque continua sendo o
  ponto de entrada documentado do ledger.

O split é o que mantém cada arquivo sob o teto de 500 linhas do CLAUDE.md — a
detecção estava em 499 e qualquer ratchet novo estourava.

## Limites declarados do detector

Rationale que **não** vive no código (CLAUDE.md: docstring de uma linha;
[[ADR-343]]: número de instância é off-git).

**Chave.** `(data, valor_cents, moeda, direction, descricao_normalizada)` —
provenance-free de propósito: `banco`/`titular`/`tipo_conta` são exatamente os
campos que variam entre as pernas do mesmo evento. A proveniência entra no
**critério de flag** (≥2 triplas distintas), nunca na chave. `direction` **não** é
campo do item E4: vem do BALDE, porque o `abs` da despesa destrói o sinal
(mesma regra já escrita no read-path de produção).

**SOBRE-detecção — 1 classe, declarada.** Coincidência legítima cross-conta
(mesma assinatura/tarifa/rendimento, mesmo dia, mesmo valor, em contas distintas
com **ambas** as pernas preenchidas) **entra** no numerador. Não é filtrada:
filtrar por assinatura derivada do corpus tornaria o instrumento um
detector-do-defeito-conhecido, incapaz de achar o próximo carrier (terceiro campo,
outro vazio, alias novo pós-[[A40.l2]]). A defesa é a **partição por fill-state**,
que é linha de relatório, nunca predicado de entrada. Se `coincidence-shaped`
crescer, o discriminante barato é prefixo da descrição CRUA entre as pernas.

**SUB-detecção — 4 limites.**

1. Conversão de **câmbio** é invisível: as pernas têm moedas distintas — o mesmo
   campo que evita o falso-positivo multimoeda.
2. O caminho de label PJ decide o kind pelo LABEL, então a direction-do-balde pode
   discordar da direction-do-hash — sub-detecta nesse corner, nunca super.
3. Par cujas extrações discordam do sinal/kind cai em baldes OPOSTOS ⇒ `direction`
   difere ⇒ chaves distintas ⇒ invisível por construção. É o MESMO mecanismo que
   dá o "não detecta" correto do caso (b).
4. A chave é subconjunto ESTRITO da do dedup K4, logo só acha divergência
   CONFINADA à proveniência — divergência em formato de data, descrição truncada
   ou centavo é invisível. Um número baixo lê-se "pouca duplicação
   **provenance-only**", não "pouca duplicação".

**Massa não-varrida — 2 canais.** A descrição entra normalizada
(`normalize_descricao`, [[ADR-255]] it.2/it.3), que remove o sufixo final de
roteamento — dois pagamentos DISTINTOS que diferem só nesse sufixo colidem. E o
kind `transferencia` não vai a balde nenhum, sendo o match bank-specific keyado em
`banco` (campo que diverge na classe medida), logo assimetria de detecção entre as
pernas tira o par inteiro dos baldes varridos. Por isso o contador de
transferências é impresso AO LADO do numerador: **queda de numerador com essa
massa subindo não é progresso.**

## Partição carrier × coincidência — UMA definição de carrier

A [[ADR-354]] tem **dois** carriers: (1) `tipo_conta` divergente entre as pernas e
(2) campo de proveniência **assimétrico** (vazio numa perna, preenchido na outra).
Os dois entram em `carrier_signatures(divergentes, parciais)` — **fonte única**,
consumida pela partição do relatório (`CrossGroupCollision.defect_shaped`) **e**
pelo validador de whitelist (`_validate_entry`). O token impresso é
`carrier-shaped`, e o valor de `carriers=` usa sufixo curto (`titular:c2`,
`tipo_conta:c1`) porque fica ao lado de campos `key=value` na linha de ocorrência —
`=`, espaço ou `+` dentro do valor quebrariam qualquer parse do relatório off-git.
A glosa longa sai **uma vez** por bloco, no render.

**Carrier 1 é mais largo que o declarado na ADR — de propósito.** O predicado
implementado é **QUALQUER** divergência de `tipo_conta`, não só o par variante que
motivou a decisão (`extrato` vs `extratoconta` nomeando o mesmo tipo de conta):
distinguir variante-de-vocabulário de tipo de conta REALMENTE distinto exige o
alias-map versionado que a [[ADR-354]] §Consequências joga para a [[A40.l2]]. Sob
[[ADR-342]] um instrumento erra para **sobre-detecção rotulada**, nunca para
sub-detecção silenciosa — então a declaração se alinha ao predicado, não o
contrário.

**Residual declarado:** coincidência legítima intra-banco entre tipos de conta
genuinamente distintos (tarifa/rendimento de mesmo valor no mesmo dia em conta e
poupança) sai `carrier-shaped`, escala a P0 **e é estruturalmente in-whitelistável**
— o validador rejeita o shape justamente por ser carrier. Não há escape barato: o
único discriminante possível ("este par de `tipo_conta` é variante de vocabulário ou
são tipos distintos?") **é** o alias-map da [[A40.l2]], e inventá-lo aqui seria
derivar whitelist do corpus — o eixo errado que a r1 mediu. Até lá, o antídoto é a
triagem por classe (histograma), não a whitelist.

A r3 mediu o defeito de ter **duas** leituras: `defect_shaped = bool(parciais)`
capturava só o carrier 2, então um par com `titular` simétrico e `tipo_conta`
variante saía `coincidence-shaped` (não escala a P0) enquanto o validador no MESMO
módulo se recusava a whitelistá-lo chamando-o de carrier 1. O ratchet que trava é
a **equivalência**: para cada classe medida, "é carrier-shaped na partição" e "é
rejeitado como carrier pela whitelist" têm de concordar.

O fill-state por campo continua sendo o eixo do carrier 2, em três estados:
`preenchido` · `parcial` (vazio numa perna, preenchido na outra) · `vazio` (vazio
em todas). "Vazio em ≥1 perna" **não** serve: rotula como defeito o par simétrico
(campo vazio nas DUAS pernas), onde não há nada a canonicalizar — a classe de
falso-positivo medida na r1. Sentinela de vazio ao lado de valor real num campo de
vocabulário é a **mesma** assimetria escrita em valores, logo também é carrier 2;
vazio em TODAS as pernas é rejeitado por eixo próprio (sentinela), não por carrier.

**Zero efeito no numerador:** a partição é linha de relatório. O fingerprint do
detector (colisões, digests, ordem, Σ excesso, cobertura) é idêntico antes e depois
— só a contagem impressa `carrier-shaped` sobe.

## Eixo de whitelist e o validador

A whitelist opera em **shape de VALOR**, não em nome de campo:
`banco=<valores>|tipo_conta=<valores>|titular=<fill-state>`. `banco`/`tipo_conta`
vêm de vocabulário fechado (`institution_catalog` / doc-types) e o mesmo relatório
já imprime `<banco>_<tipo_conta>_<MOEDA>_<periodo>` como unit de grupo E3 — os
valores podem sair. `titular` **nunca**: só o fill-state.

Isso conserta o eixo errado da r1: uma whitelist em nome de campo (`tipo_conta`)
apagava o falso-positivo **e** o verdadeiro-positivo juntos.

`validate_explained` **rejeita** (erro, não warning) entrada com assinatura de
carrier: `titular=parcial`, sentinela de vazio em campo de vocabulário, e
`tipo_conta` divergente (qualquer par de valores — ver §carrier 1 mais largo).
**Residual declarado:** divergência de valor em `banco` com as duas pernas
preenchidas é aceita — é a coincidência cross-instituição —, logo um carrier de
vocabulário em `banco` seria whitelistável. Quem cobre esse resto é o ratchet
contra a fixture carrier fixa, não o validador.

**Não existe segunda rota de whitelist.** `_assert_explicadas_declaradas` exige que
toda ocorrência na linha `explicadas` tenha shape ∈ whitelist declarada. Sem essa
invariante, um predicado alternativo dentro de `_collision` (medido:
`whitelisted = shape in explained or not descricao`) move ocorrências do numerador
para `explicadas` **sem tocar em `EXPLAINED_DIVERGENCE`** — as 3 identidades
continuam fechando, `coverage_ok` continua OK, e todo o aparato anti-Goodhart é
contornado em silêncio. Com ela, `explicadas` não-vazia sob whitelist vazia é
**impossível por construção**.

## As 3 identidades de cobertura

`coverage_ok` é o token grepável; falso ⇒ o numerador **não** é legível como 0.

1. **Interna:** `rows_scanned − rows_keyed == Σ unkeyable`. É auto-consistente
   (toda row excluída é contada como excluída), logo fecha com **qualquer** piso de
   materialidade — não travar a alavanca. Quem trava é o teste de **predicado**:
   row de valor não-zero abaixo de qualquer piso plausível segue chaveável.
2. **Externa:** `rows_scanned == Σ total_transacoes` — campo que o detector NÃO lê.
3. **Partição:** `keys_multiprov == len(numerador) + len(explicadas)`. Pega filtro
   silencioso entre o que o detector achou e o que saiu particionado (piso de
   materialidade, cap, dedupe de shape) — mudança que as duas primeiras não veem.

Mais: nenhum balde ilegível e ≥2 triplas de proveniência no corpus (com 1 tripla o
critério "≥2 triplas" é vacuoso, e o detector **não pode** flagar).

## O número IMPRESSO também é pinado

O numerador estava travado no grão de **dados** (`len(cg.numerador)`), mas o número
**impresso** — o que a skill manda grepar no Passo 4 e o que alimenta o baseline
off-git — não tinha asserção nenhuma: `len(hits)` → `sum(... if c.defect_shaped)` e
`_sum_excess → 0` passavam a suíte inteira verde. Fechado com asserção sobre a
string exata (`não-explicada: N ocorrência(s)` + `Σ excesso <N> cents`) em corpus
**misto** — com só carrier, filtrar por `defect_shaped` é indistinguível de `len`.

**Cap constante** dentro do numerador é a mesma classe de furo: `[:100]` sobrevivia
porque a fixture mais densa tinha 5 colisões (só `[:1]` era pego). Em produção o cap
PEGA — a 3ª identidade reprova a cobertura —, logo o furo era no gate pré-merge, não
no runtime. `corpus_denso(150)` (~300 rows sintéticas, ~0,05s) fecha qualquer cap
constante plausível de uma vez.

## `zero_write_ok` só prova algo se a contagem vier antes do rollback

Escrita pendente é visível a `SELECT` na mesma sessão — é **assim** que a prova de
zero-write funciona. O ramo degradado do blast radius chama `session.rollback()`
(necessário: em PostgreSQL o statement falho aborta a transação, 25P02). Com a
medição secundária ANTES de `counts_after`, o rollback apagava a escrita pendente
antes da segunda contagem ⇒ `counts_before == counts_after`, `rolled_back=1` e
`zero_write_ok=True` **com escrita tendo existido**. A ordem em `certify` é
invariante: `counts_before` → re-derivação → `counts_after` (a prova) → blast radius
(medição secundária).

## Gate de CI do ratchet

`dev/**` não estava em nenhum filtro de path do `ci.yml`, então PR que só tocava
`dev/**` **não rodava** `pytest tests/` — o ratchet nasceria sem gate pré-merge.
Fechado com um output novo (`dev_tools`) que gateia **só** `pipeline-tests`;
`backend-tests` fica de fora de propósito (o custo do job não se justifica para
`dev/**`). O controle compensatório declarado (`main-smoke` em `nightly.yml`) está
com o workflow `disabled_manually` — **P0 operacional a escalar ao owner**:
re-habilitar e isolar `main-smoke` dos jobs pesados que causaram as falhas.
