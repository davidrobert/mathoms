---
id: A42.l3
type: lane
title: "Harness de certificação: falso-verde para dentro"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l3-harness-falso-verde-para-dentro
adrs:
  - "[[ADR-302]]"
  - "[[ADR-421]]"
depends_on: []
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/ci
  - area/pipeline
---

# A42.l3 — `harness-falso-verde-para-dentro` (LC05, LC06, PC13, RV4-17, RV4-18, RV4-45, + LC5-02, LC5-03, LC5-06, PV9-04)

> **Origem:** [[LEDGER-CERTIFY-active]] §r4 2026-08-04 — LC05, LC06 (ambos Alto,
> classe `[skill]`) · [[PARSE-CERTIFY-active]] §r2 — PC13 · [[PIPELINE-REVIEWS-active]]
> §r4 — RV4-17, RV4-18, RV4-45. Adota também o resíduo declarado da [[A39.l6]]
> (traço positivo do checksum, já emitido e nunca lido).

> 🔴 **Segunda colisão, medida 2026-08-05 — o item 1 desta lane reescreve o arquivo
> que produz a prova do KR-B da [[A40]].** O "classificador de balde do razão" do item 1
> é [`dev/ledger_certify_core.py:161`](../../../../dev/ledger_certify_core.py) —
> `_non_ledger_verdict`, que retorna `COBERTO_SEM_VALOR` com a glosa *"origem
> E2/baseline (fora do grão transacional)"*. **O mesmo arquivo**, na linha 300,
> monta `cross_group=cross_group_summary(...)`, que é o numerador de **261** contra o
> qual a [[A40.l2]] prova o fix (`dev/certify_ledger_local.py:40` importa
> `build_report` daqui). Nenhuma das duas lanes declarava a aresta, em nenhuma
> direção: o §Escopo abaixo nomeia só `dev/certify_parse_local.py`, e o critério de
> agrupamento por arquivo — que as duas sprints declaram — passou por cima dela.
>
> **Consequência se ignorada:** reescrever o veredito antes de a prova da [[A40.l2]]
> estar registrada não dá conflito de merge, dá **invalidação silenciosa de prova** —
> o `--compare` deixa de ser maçã-com-maçã e a l2 fecha verde sobre um instrumento
> diferente do que congelou o baseline. É a lição da [[A39]] que a própria
> [[A40.l1]] codificou (*baseline pós-mutação mede o próprio fix*), agora entre
> sprints.
>
> **Amarra quitada 2026-08-14.** A [[A40.l2]] shipou (#1368). `depends_on` saiu.
> Os cinco itens voltam a ser entregáveis juntos. **Cautela que sobrevive sem ser
> dep:** o residual da l2 declara que `ledger_certify_core.py` continua cego ao
> enforce e ainda reporta 261 na sombra. O item 1 desta lane reescreve esse
> arquivo — pinar comparabilidade do `cross_group` ou re-freeze; não tratar 261
> como denominador vigente. `_non_ledger_verdict` moveu para a linha 170.

> **Esta lane é dona de `dev/certify_parse_local.py`.** Colisão declarada com
> [[A42.l2]] (mesma onda): o critério da l2 exige que o ratchet aceite código de aviso
> estruturado como alternativa honesta à escalação, e o ratchet de des-certificação vive
> na **mesma função** que esta lane reescreve para ler os traços de checksum. Não são
> disjuntas — a onda paralelizava três lanes sob premissa falsa. Resolução: **esta lane
> entrega a mudança de ratchet**, incluindo a cláusula que a l2 precisa; a l2 consome e
> **não** edita este arquivo. Quem mergear primeiro avisa.

## Problema

As ferramentas de certificação — as que existem para provar que o pipeline fecha —
dão verde sem medir. Cinco instâncias da mesma classe:

1. **Veredito catch-all com default otimista.** O classificador de balde do razão é
   um catch-all cujo default é "coberto": conta containers que aqueles baldes não
   usam, imprime "0 itens · coberto" com o payload completo em mãos, e a glosa "fora
   do grão transacional" é **factualmente falsa** para um dos baldes. Carimba
   `coberto` sobre a dimensão que carrega **62,5% do peso do score**.
2. **A P0 nº 1 da própria rubrica nunca foi exercitada** em quatro rodadas: o check
   que roda varre um balde de população e vetor **diferentes** do agregado que a
   rubrica diz cobrir.
3. **Traço já emitido e nunca lido.** O sinal positivo de checksum de investimento é
   declarado no schema e escrito pelo produtor; o harness não o lê. Onze documentos
   ficam presos em `coberto-sem-verificação` por **observabilidade**, não por falta
   de checksum. E "sinal presente → ausente" é des-certificação invisível ao ratchet.
4. **Perna de volume do gate anti-regressão morta:** busca uma folha que não existe
   no view-model, recebe vazio, e o guard torna o check inalcançável.
5. **Auditoria de paridade fail-open** sem variável de ambiente, comparando dois
   sinks alimentados pelo **mesmo** hook — "não consegui medir" é indistinguível de
   "medi e passou". Mesma forma: o registro durável descarta o contexto estruturado
   do log, então avisos de drift chegam como eventos idênticos e cegos.

## Decisão

O princípio único: **"não consegui avaliar" é um estado, não um sucesso.**

- **Registry explícito** `{balde → checker | não-verificável(motivo)}` com default
  **`não-verificável`**. Balde novo sem checker declarado aparece como lacuna, não
  como aprovação. Estender o drift (hoje só na camada de reconciliação) para
  contagem por balde da camada de categorização — **guard que fecha a classe**, não a
  instância.
- **Invariantes de saída** para a P0 nº 1, não reimportação dos módulos de dedup
  (reimportar seria tautologia: o check passaria porque usa o mesmo código que
  deveria auditar). Invariantes sobre o agregado publicado, com **partição de
  julgabilidade** declarada e prova por mutação.
- **Ler os traços que já existem** (checksum de investimento) e dar-lhes rank no
  ratchet, para que "presente → ausente" falhe o `--compare`.
- **Reparar a perna de volume** do gate, ou removê-la declarando que a perna de
  drift de valor cobre o caso — o que não pode continuar é perna morta que parece viva.
- **Exit code próprio para indeterminado** na auditoria de paridade, e preservar o
  contexto estruturado no registro durável.

## Critério de aceite

- **Prova por mutação em cada um dos cinco:** remover o input do check ⇒ **exit
  ≠ 0**. Hoje quatro dos cinco produzem verde nessa condição (medido no §r4 e no §r2).
  Este é o critério central da lane; sem ele, "consertei o harness" não é verificável.
- Balde sem checker declarado ⇒ veredito `não-verificável(motivo)`, nunca `coberto`.
  Teste que adiciona um balde fictício e exige que ele **não** apareça como coberto.
- A P0 nº 1 da rubrica passa a ter check que a exercita sobre o agregado correto,
  com a partição de julgabilidade escrita.
- `--compare` falha quando o sinal positivo de checksum desaparece de um documento
  que o tinha.
- Nenhum check novo que dependa de variável de ambiente para morder: se a condição
  não está satisfeita, o resultado é `indeterminado` com exit próprio — não `pass`.
- **O ratchet aceita o enum de verificabilidade da [[A42.l2]]**, e des-certificação
  (`provada → nao_verificavel`) **falha** o `--compare`. Este bullet é a entrega de que a
  l2 depende: ela declara em prosa que consome esta cláusula, e sem o item estar no DoD
  **desta** lane a l3 poderia shipar verde deixando a l2 bloqueada — dependência cujo
  entregável não está no critério do provedor não é dependência, é esperança (correção do
  `senior-cto`, 2026-08-04).
- **KR-B da sprint só é mensurável depois desta lane.** É a razão pela qual ela está
  na Onda 1 e não depois dos fixes que ela deveria vigiar.
- **O item 1 pode mergear** — a [[A40.l2]] é terminal (#1368). O PR desta lane cita
  esse número e declara o que fez com o numerador `cross_group` (re-freeze ou
  pin de comparabilidade). Sem essa declaração o KR-B residual da A40 perde o
  referente.

---

## Ampliação de escopo — rodada unificada U1, 2026-08-26

> Os itens do §Escopo acima são a redação de 2026-08-04 e **não mudam**. A numeração
> continua daqui, porque o `_README` da sprint cita "o item 1 desta lane" nominalmente.
>
> **Origem dos itens novos:** rodada unificada **U1** ([[ADR-416]]) ·
> [[LEDGER-CERTIFY-active]] §r5 — **LC5-02**, **LC5-03**, **LC5-06** ·
> [[PIPELINE-REVIEWS-active]] §r9 — **PV9-04**.

A `U1` rodou o harness em modo entregue sobre um run real e achou **mais quatro**
falso-verdes na mesma família dos itens 1–5 — o instrumento afirmando verde onde não mediu:

6. **`layer_ok` sai verde com PONTO CEGO impresso duas linhas acima.** `paridade_fecha` é
   auto-identidade (partição do próprio conjunto do colapsador), não comparação com o
   detector; `sem_ponto_cego` existe e está **fora** do predicado agregado
   (`dev/ledger_collapse_layer.py`). O token que um gate leria é o verde.
7. **O checksum por grupo prova auto-consistência do produtor, não conservação E2→E3.**
   `_ledger_verdict` lê três campos escritos pelo mesmo produtor e nunca confronta
   `carregadas` com o input E2 (`dev/ledger_certify_core.py`). Saída medida: 97/97 grupos
   `conservado` impressos ao lado de *"E2→E3: count não fecha"*.
8. **O veredito E2→E3 afirma "resíduo = perda" sem computá-lo, e com o sinal invertido.**
   Aritmética sobre a própria saída: as exclusões declaradas **excedem** o gap em 13 rows, e
   há 23 rows entre "semeado" e "conservação" que nenhuma linha declara.
9. **A suíte de cross-validation tem severidade constante** (`info` em 17/17, `passed` em
   17/17), com dois passes por **isenção**. `falhas=[]` é tautologia — e a `U1` consumiu esse
   vazio como evidência de correção antes de medir a constante. (PV9-04; o destino é
   PIPELINE, mas o conserto mora no mesmo instrumento e por isso entra aqui.)

**Re-medição da colisão com a [[A40.l2]]** — o blockquote 🔴 de 2026-08-05 **não é editado**;
ele é evidência do que se sabia então. O que mudou no mundo: a `U1` mediu que o residual do
numerador da KR-B é **100% ponto cego do colapsador** (LC5-01), logo a prova que a colisão
protege **não pode fechar** enquanto a paridade de chave não for corrigida. A cautela segue
válida em forma mais forte: reescrever o veredito antes de a KR-B ser **re-declarada** na
[[A40]] invalida uma prova que já se sabe ter piso.

**Teste de corte aplicado:** os itens 6–8 tocam os mesmos arquivos e o mesmo predicado dos
itens 1–5 ⇒ ampliam esta lane. O item 9 toca outro arquivo, e entra por dono compartilhado
(instrumento de certificação) — se na execução ele se mostrar separável, vira lane irmã com
`depends_on` nesta, e não item órfão.

---

## Aresta declarada — [[A42.l14]], rodada unificada U2, 2026-08-29

> **Não é ampliação de escopo.** O `LC6-01` da `U2` ([[LEDGER-CERTIFY-active]] §r6) tem
> lane própria — a [[A42.l14]], criada pelo dono em #1821 — e a direção dele está
> decidida na [[ADR-421]] (`Proposto`). Esta seção registra só a **aresta**, porque as
> duas lanes reescrevem `dev/ledger_certify_core.py` e nenhuma declarava a outra.

**Ordem obrigatória: a [[A42.l14]] precede os itens 1–5 desta lane.** O registry de
checkers do item 1 reescreve `_non_ledger_verdict`; a l14 reescreve **de qual universo
vêm as peças** que todos aqueles vereditos leem. Aplicar o registry antes produz um
`não-verificável` corretamente tipado **sobre o universo errado** — pior que o `coberto`
de hoje, porque *parece* consertado e passaria no critério de mutação desta lane.

**Por que o §Critério de aceite acima não pega a classe da l14** — e isto vale como
aviso para esta lane, não como item novo: o critério central aqui é *"remover o input do
check ⇒ exit ≠ 0"*. No defeito da l14 o input **está presente** e o check **roda**; o que
está errado é a proveniência dele. Mutação que remove input continua reprovando enquanto
o defeito sobrevive intacto. Um critério de mutação por ausência não discrimina
proveniência — os três bullets que discriminam (troca de sujeitos, fixture de dois runs
em SQLite real, anti-amputação) estão no §Critério de aceite da [[A42.l14]].

**A colisão com a [[A40.l2]] não muda de forma.** A correção do sujeito não toca
`cross_group`/`cross_group_entregue`: o numerador da KR-B lê só os baldes transacionais
(`_tx_rows`) e não é alcançado nem pela correção nem pela amputação do braço entregue.
Medido na sessão de ataque; registrado como bound no §r6.
