---
id: A40.l1
type: lane
title: "Instrumento: detector de duplicação cross-grupo + baseline congelado"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l1-ledger-cross-grupo-check
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
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

O detector é `dev/ledger_cross_group.py` (módulo irmão, para manter
`dev/ledger_conservation.py` sob o teto de 500 linhas), **re-exportado** por
`dev/ledger_conservation.py` — que continua sendo o ponto de entrada documentado
do ledger. O bloco de render vive junto do detector: quem é dono do concern é dono
do boundary que decide o que pode sair.

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

## Partição defeito × coincidência (fill-state por campo)

A partição correta é por **fill-state por campo**, em três estados:
`preenchido` · `parcial` (vazio numa perna, preenchido na outra) · `vazio` (vazio
em todas). `parcial` é a assinatura do carrier — e, por construção, implica
divergência no mesmo eixo (um campo vazio de um lado e cheio do outro tem 2 valores
distintos). Logo `defect_shaped` significa **assimetria no eixo divergente**, sem
precisar de um segundo predicado.

"Vazio em ≥1 perna" **não** serve: rotula como defeito o par simétrico (campo vazio
nas DUAS pernas), onde não há nada a canonicalizar. Essa era a classe de
falso-positivo medida na r1.

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
`tipo_conta` divergente (carrier 1 da [[ADR-354]] é vocabulário de tipo de conta).
**Residual declarado:** divergência de valor em `banco` com as duas pernas
preenchidas é aceita — é a coincidência cross-instituição —, logo um carrier de
vocabulário em `banco` seria whitelistável. Quem cobre esse resto é o ratchet
contra a fixture carrier fixa, não o validador.

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

## Gate de CI do ratchet

`dev/**` não estava em nenhum filtro de path do `ci.yml`, então PR que só tocava
`dev/**` **não rodava** `pytest tests/` — o ratchet nasceria sem gate pré-merge.
Fechado com um output novo (`dev_tools`) que gateia **só** `pipeline-tests`;
`backend-tests` fica de fora de propósito (o custo do job não se justifica para
`dev/**`). O controle compensatório declarado (`main-smoke` em `nightly.yml`) está
com o workflow `disabled_manually` — **P0 operacional a escalar ao owner**:
re-habilitar e isolar `main-smoke` dos jobs pesados que causaram as falhas.
