---
id: A42.l3
type: lane
title: "Harness de certificação: falso-verde para dentro"
sprint: A42
status: shipped
ship_pr: 1949
ship_date: "2026-09-01"
priority: P1
branch_slug: a42-l3-harness-falso-verde-para-dentro
adrs:
  - "[[ADR-302]]"
  - "[[ADR-421]]"
depends_on: []
tags:
  - type/lane
  - sprint/a42
  - status/shipped
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
> é `_non_ledger_verdict`, que retorna `COBERTO_SEM_VALOR` com a glosa *"origem
> E2/baseline (fora do grão transacional)"*. Ele monta
> `cross_group = cross_group_summary(...)`, o numerador de **261** contra o
> qual a [[A40.l2]] prova o fix, e `dev/certify_ledger_local.py` importa
> `build_report` daqui. Nenhuma das duas lanes declarava a aresta, em nenhuma
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
proveniência — os quatro bullets que discriminam (troca de sujeitos, fixture de dois runs
em SQLite real, anti-amputação, drift exercitado em run não-recente) estão no §Critério de
aceite da [[A42.l14]].

> **Re-ancoragem 2026-08-31, no closeout da [[A42.l14]] (#1915).** As três âncoras de
> **linha** deste bloco caducaram e foram trocadas por âncoras de **símbolo**, que
> sobrevivem a refactor. Onde as coisas estão hoje: `_non_ledger_verdict` saiu de
> `ledger_certify_core.py` para **`dev/ledger_unit_verdicts.py:120`** (mudança da
> [[A42.l19]], não da l14); `cross_group_summary` é montado em
> **`ledger_certify_core.py:251`** (era "linha 300"); e o import de `build_report` está
> em **`certify_ledger_local.py:49`** (era `:40`). Some-se um arquivo novo ao raio do
> item 1: a leitura de DB saiu para **`dev/ledger_certify_db.py`**, e os nomes voltam ao
> harness por **re-export de binding** — chamada qualificada torna inertes os
> `monkeypatch` dos testes, provado por mutação no #1915. **Nada disto amplia o escopo
> desta lane**; a §Ordem obrigatória acima está **satisfeita** — a l14 shipou.

**A colisão com a [[A40.l2]] não muda de forma.** A correção do sujeito não toca
`cross_group`/`cross_group_entregue`: o numerador da KR-B lê só os baldes transacionais
(`_tx_rows`) e não é alcançado nem pela correção nem pela amputação do braço entregue.
Medido na sessão de ataque; registrado como bound no §r6.


---

## Entrega — 2026-09-01

> **Todos em `main` (2026-09-01).** `ship_pr: 1949` — o último PR que carregou item; o
> #1952 é o registro docs. A coluna de estado foi deliberadamente omitida da tabela:
> terminalidade é o campo `status` desta nota, que tem gate.

| PR | Itens |
| --- | --- |
| [#1944](https://github.com/davidrobert/mathoms/pull/1944) | 3 (PC13) + a cláusula de ratchet da [[A42.l2]] |
| [#1946](https://github.com/davidrobert/mathoms/pull/1946) | 6 (LC5-02) + residual do 1 (LC05/LC5-06) |
| [#1947](https://github.com/davidrobert/mathoms/pull/1947) | 7 (LC5-03) + 8 |
| [#1949](https://github.com/davidrobert/mathoms/pull/1949) | 4 (RV4-17) + 5 (RV4-45 + RV4-18) |
| [#1951](https://github.com/davidrobert/mathoms/pull/1951) | 2 (LC06) |

### O que a lane NÃO entregou, e por quê

**Metade do item 1 já era da [[A42.l19]].** O registry por chave com default
`não-verificável`, e o teste de balde fictício que o §Critério de aceite pede, entraram
em [#1871](https://github.com/davidrobert/mathoms/pull/1871). Esta lane entregou o que
sobrava: a **glosa**. Uma frase única — *"origem E2/baseline (fora do grão
transacional)"* — era carimbada nos quatro baldes e é **factualmente falsa** para
`fluxo_mensal_detalhado`, que sai do `CashFlowBuilder` sobre a mesma população
classificada. O registry passou a `{balde → NonLedgerChecker}`, com a proveniência
**daquele** balde ao lado de onde contar.

**O item 9 não procede como escrito.** O enunciado (`PV9-04`: *"severidade constante,
`info` em 17/17"*) foi **re-triado no §r10** como `PV10-03`, e a re-triagem procede —
medi: a severidade é **ternária condicional em todos os 17 checks**
(`"error" if … else "info"`, e variantes). `info` em 17/17 é **efeito** de tudo passar,
não constante estrutural. O remédio que o item prescrevia (*"pelo menos um check com
severidade capaz de reprovar"*) já é verdade no código.

A substância que sobrevive é outra, e está em `PV10-03`: **4 de 17 checks pausam o run**
(`_CONSERVATION_CHECKS = {CV1, CV2, CV3, CV6}`), os 13 restantes são advisory, e a linha
de resumo publica "17/17 OK" contando advisory como gate. Ela se parte em duas, e
**nenhuma das duas é órfã**:

- *"17/17 OK conta advisory como gate"* → já é o §Decisão 3 da [[A42.l4]]
  (*"parar de afirmar mais do que se mede"*), que é dona de `scripts/validate_cross.py`.
- *"os 4 que gateiam são recompute de produtor único"* (a classe que a [[ADR-418]] §D4
  condena) → **sem dono**: a [[A42.l16]] decidiu escopo "só o CV18" e a deixou
  explicitamente de fora. Roteada para a [[A42.l4]] como aresta declarada, e não para
  lane nova: o §Teste de corte previa lane irmã com `depends_on` **nesta**, mas isso foi
  escrito antes da refutação — o dono real é o do arquivo, não o deste harness.

### Deferimento datado — âncora do eixo E3 **entregue** (2026-09-01)

O item 7 ancora o veredito de grupo no resíduo da perna E2→E3, que cruza três produtores
— e o terceiro é o **log de execução do E3** (statements excluídos inteiros no load, que
`e3_load_report.StatementExclusion` declara pertencerem ao ledger run-level). Esse log é
o da **re-derivação**, não o do run pinado.

Consequência: a âncora só transfere ao eixo entregue quando o drift é zero. Com drift, o
eixo cai para `coberto` com o motivo escrito — honesto, e uma perda real de discriminação
no modo `--entregue`.

**Condição de retomada:** o `output_summary` do `PipelineStageLog` do run pinado já é
lido por `_entregue_evidence` para evidência de retenção. Se ele carregar a partição de
exclusões, a âncora passa a ser medível sobre o substrato entregue sem depender do drift.
**Dono:** quem pegar a [[A42.l6]] (contrato de store/artefato) ou uma lane de
observabilidade do E3 — não é trabalho deste harness sozinho.

### Nota de método

O §Critério de aceite pede *"remover o input do check ⇒ exit ≠ 0"*. Ele **não discrimina**
os itens 2 e 7: no item 7 o input está presente e o check roda — o que estava errado era a
**proveniência** dele (é a mesma cegueira que o §Aresta desta lane já registrava sobre a
[[A42.l14]]); e no item 2 remover o input produz `não-verificável`, que é o comportamento
correto. Nos dois casos a prova usada foi **mutação do mecanismo** (neutralizar o teto da
âncora, neutralizar os detectores de identidade), não mutação por ausência de input.

Dois falsos-verdes foram pegos **nos meus próprios testes** antes do merge, e ambos estão
registrados nos PRs: um guard de classe que comparava as glosas do dict e sobrevivia à
mutação que restaurava a frase única no veredito ([#1946]); e um teste de exit code que
comparava `main()` contra a **própria constante** e sobrevivia a `EXIT_INDETERMINADO = 0`
([#1949]).

---

## Rota recebida da [[A40.l32]] — deferida com dono, 2026-09-01

O closeout achou uma rota **para dentro** desta lane que ela nunca registrou. A
[[A40.l32]] (`shipped`, #1335) a nomeia duas vezes:

> *"**Isto não resolve o débito estrutural** de `.claude/skills/**` (segue com a
> [[A42.l3]])"* · *"Os scripts sob `.claude/skills/` têm cobertura zero — importam
> `backend` no topo e nenhuma suíte os alcança. (…) Gap estrutural, maior que esta lane;
> dono natural é a [[A42.l3]]."*

**Nenhum dos 9 itens a cobria, e nenhum PR a entregou.** Registrada aqui para não virar
rota-zumbi quando esta nota ficou terminal.

**Re-medido em 2026-09-01, e a afirmação mudou:** são **7** scripts em
`.claude/skills/*/scripts/`, e **1 já tem teste real** —
`tests/unit/test_capture_report_render.py` carrega
`capture_report_render.py` por `importlib.util.spec_from_file_location`, contornando o
import de `backend` no topo. "Cobertura zero" era verdade quando escrito; hoje é **1 de
7**, e o que interessa é que a **técnica está provada**: o resto é mecânico.
(`resolve_workspace` aparece em `tests/test_llm_calls_allowed_propagation.py`, mas é
`_resolve_workspace_id` de **outro** módulo — não conta.)

**Por que não entrou nesta lane.** A própria [[A40.l32]] a chama de *"gap estrutural,
maior que esta lane"*, e ela é de natureza diferente dos 9 itens: aqui cada item é um
falso-verde nomeado com prova por mutação; ali é cobertura ausente por acidente de
import. Absorvê-la no closeout seria ampliação silenciosa de escopo depois do merge.

**Condição de retomada e dono:** 6 scripts sem teste, técnica provada, custo mecânico.
Dono natural é quem pegar uma lane de instrumento na A42 — a [[A42.l4]] já é solo em
`scripts/validate_cross.py` e não serve. Se ninguém pegar, vira lane própria com o
enunciado **re-medido** acima, nunca com o "cobertura zero" original.

## Closeout — 2026-09-01

Camada 1 (`check_closure.py --lane A42.l3`) limpa, sem banner de substrato, rodada de
árvore em `origin/main`. Camada 2 releu os **12** citadores. Corrigidos neste PR:

- **3 afirmações falsas** na linha desta lane do §Âncora hoje do `_README` da A42
  (`_non_ledger_verdict` mudou de arquivo na [[A42.l19]]; o default deixou de ser
  `COBERTO_SEM_VALOR`; o `certify_parse_local.py` passou a ler `checksum_ok`), mais o
  carimbo `sobrevive`.
- **1 afirmação falsa** na linha da [[A42.l4]] do mesmo bloco
  (`compare_reviews.py` não busca mais `transacoes_total` — #1949 removeu a perna).
- A frase de pré-condição do **KR-B**, que dizia *"a perna de volume do gate
  anti-regressão está morta hoje"*.
- `RV5-10` na [[PIPELINE-REVIEWS-active]], cuja `Disposição` ainda apontava para esta
  lane embora o §r6 já a tenha **re-escopado** para `RV6-02` dizendo em letra que
  *"[[A42.l3]] não é sobre isso"*.
