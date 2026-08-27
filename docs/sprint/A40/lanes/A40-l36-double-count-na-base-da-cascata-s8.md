---
id: A40.l36
type: lane
title: "Double-count potencial na base da cascata fiscal da S8: pró-labore pode entrar duas vezes"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1491
ship_date: "2026-08-18"
priority: P1
branch_slug: a40-l36-double-count-base-cascata-s8
adrs:
  - "[[ADR-236]]"
  - "[[ADR-375]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l36 — `double-count-base-cascata-s8`

> **Aberta em 2026-08-11**, achado do co-design da [[A40.l34]] (`senior-cto`).
> Registrada como §Não-objetivo da [[ADR-375]] para não inchar aquela lane.
> **Não medida ainda** — o achado é de leitura de código, e a lane começa
> confirmando ou refutando.

## Problema (a confirmar)

`cascata_calculator.py:383` compõe a base PF como
`cargas.bruto_anual` (pró-labore anualizado) `+ outras_rendas_tributaveis_pf_anual`.
O segundo termo é preenchido por `tributario_input_builder._assemble_input` a
partir de `_load_irpf_renda_tributavel`, que é o **total** de rendimentos
tributáveis do IRPF.

**Se o total do IRPF já contém o pró-labore, a base da S8 soma duas vezes.**

Isto importa mais depois da [[ADR-375]], não menos: aquela ADR faz da S8 a
**dona única** do limite PGBL publicado. Um defeito na base da S8 deixa de ter
uma segunda opinião no documento para contradizê-lo.

## Escopo

1. **Medir primeiro.** Confirmar se `_load_irpf_renda_tributavel` inclui a ficha
   de pró-labore. O achado é de leitura; pode não reproduzir.
2. Se reproduzir: decidir quem é a fonte do pró-labore quando as duas existem —
   é regra de domínio, gatilho de `financial-planner`.
3. O defeito é do produtor da S8 e cai **dentro** da [[ADR-236]]: emenda datada,
   não ADR nova, salvo se a decisão mudar a base declarada.

## Critério de aceite

- Medição registrada, com o caso que reproduz **ou** a refutação datada.
- Se reproduzir: teste com pró-labore presente nas duas fontes, provando a
  contagem única.
- ~~Delta declarado e conferido por `dev/golden_diff.py` — a base cairia, então o
  sinal é `↓`.~~ **Retirado em 2026-08-27, por medição, não por conveniência:** o
  instrumento não tem sinal sobre este campo. `rg -c pgbl_base_anual tests/fixtures/`
  → exit 1 (o campo não existe no corpus de golden, que tem e2/e3/e4/dogfood e
  nenhum E5 com a cascata), e `git show a04fb00f --stat | grep -iE 'golden|snapshot|baseline'`
  → exit 1 (o #1491 não tocou golden nenhum). Cobrir E5/cascata no corpus é lane
  de substrato, não desta. O delta foi conferido pelo caminho que **tem** sinal:
  mutação sobre `_compute_layers` (§Fecho).

## Colisão declarada

Toca `cascata_calculator.py`, que a [[A40.l34]] **não** modifica (a l34 só
consome a base). Sem colisão de conteúdo; quem mergear depois rebaseia.

## Entregue — 2026-08-18 · PR [#1491](https://github.com/davidrobert/mathoms/pull/1491) · `a04fb00f`

Confirmado, medido e corrigido. Base 318.000 → 174.000 e teto PGBL
38.160 → 20.880 — a soma inflava a base em **+82,8%** (a queda, no outro
denominador, é de −45,3%; o `−82,8%` da redação original prendia o número ao
denominador errado). Decisão de domínio em [[ADR-236]] §Emenda 2026-08-17
(`financial-planner`, duas rodadas).

**A ADR-236 se contradizia**: o §D3 mandava somar pró-labore + outras, a §Riscos
proibia inferir base de pró-labore só. Sobreviveu a §Riscos — só o IRPF tem o
*total* que o RIR/2018 art. 68 manda usar.

### O delta tem DUAS dimensões — declarar só a monetária engana o revisor

| dimensão | direção |
|---|---|
| monetária (`pgbl_base_anual`, `renda_pf_tributavel_total`) | **↓** sempre: a base cai o pró-labore anualizado **inteiro** (144.000 na fixture); só o `pgbl_limite_anual` cai 12% disso (17.280) |
| conjunto de triggers | **não-monótona**: T3 apaga sem IRPF; T1 **acende** com IRPF |

T1 é *prescritivo* ("subir pró-labore", com custo real de INSS) e sua guarda de
elegibilidade (`base/(base+delta) ≥ 0,80`) é **monotônica na base** — baixar a
base só pode ligá-lo. *(Corrigido em 2026-08-27: falso na borda. Há uma guarda
**anterior** à da razão — `if not pgbl_aplicavel`, `cascata_triggers.py:74-80` —
e baixar a base até a **ausência** apaga o T1. Re-medido sobre `_input_simples_v`:
base 174k → `[T3]`; 96k → `[T1,T3]`; 40k e 1k → `[T1]`; base 0 → `pgbl_aplicavel
False`, motivo `renda_tributavel_pf_zerada`, `triggers []`. A borda não é
hipotética: é o caso "sem IRPF" que a §Emenda 2026-08-17 §3 criou.)* Quem olhar o `golden_diff` e vir só o dinheiro cair não vê
a prescrição aparecer.

### Achados que não estavam no escopo

- **Dois testes que PASSAVAM** asseveram ausência de T1/T3 e passariam por
  construção com base zero — verde sem cobertura. Ganharam guarda anti-vacuidade.
- **O gate LGPD pegou regressão real do rename**: a denylist de `redaction.py`
  casa por prefixo, e `outras_rendas` deixou de cobrir o campo — ele vazaria em
  log. Foi o único gate que viu.
- **A fixture do T1 precisou de dimensionamento medido**: com 174k a razão passa
  de 0,80 (alvo = teto INSS 8.157,41) e o trigger DESLIGA, deixando o teste verde
  sem exercitar o que existe para exercitar. Ficou em 96k.
- **O gate `test_pgbl_base_...` foi reescrito em pé e ficou mais forte**: passou a
  discriminar quatro grandezas (canônica, `receita×32%`, pró-labore-only,
  double-count) em vez de uma. Com IRPF = 0 coincidiam a **1ª e a 3ª**
  (canônica e pró-labore-only, ambas 60.000); a `receita×32%` valia 192.000 e
  nunca coincidiu com nada. *(Par corrigido em 2026-08-27 — a redação dizia
  "as duas primeiras"; o comentário do próprio teste, `:164-166`, acerta.)*

> ## ⚠️ Status possivelmente vencido — medido em 2026-08-26
>
> Anotado pelo closeout da [[A40.l65]], **sem tocar §Escopo nem §Critério**: esta
> lane está `status: open` sem `ship_pr`, mas **o código que ela descreve está em
> `main`**.
>
> Medido em `pipeline/domain/services/tributario/cascata_calculator.py`:
> `outras_rendas_tributaveis_pf_anual` **não existe mais** e
> `renda_tributavel_pf_irpf_anual` aparece 2×. O pró-labore não entra mais na base
> do PGBL — que é o defeito nomeado no título.
>
> **Não flipei o status**: o rename é *uma* parte do escopo, e só quem conhece a
> lane sabe se o resto entrou. Mas quem consultar o frontmatter hoje conclui que o
> defeito segue vivo, e ele não segue. Precedente do risco: o §Problema da
> [[A40.l65]] afirmava a entrega desta lane no passado enquanto o `status` dizia o
> contrário.

### Follow-up P1 que esta lane destravou — [[A40.l65]]

Com o pró-labore fora, **a base perdeu a âncora do titular**.
~~`_read_latest_workspace_artifact` pega o IRPF mais recente por `created_at`, sem
resolver ano-base e sem dedup~~ — e o artifact é **por declarante**. Numa família
de dois, a base do PGBL vira a declaração de quem foi processado por último, e o
teto de 12% é por CPF, não por família.

> **Metade fechou em 2026-08-24 (#1672).** O eixo do **ano** já não depende da
> ordem de processamento: `_read_latest_workspace_artifact` deixou de existir, e
> a S8 passa por `resolve_ano_base_fiscal` com a mesma partição e dedup do E5
> ([[A40.l65]] §Escopo 1). **Segue aberto** o eixo do **declarante** — com dois
> declarantes no ano eleito a escolha ainda é por recência, e o teto de 12%
> continua sendo por CPF ([[A40.l65]] §Escopo 2).

> **A outra metade fechou em 2026-08-25 (#1711), e com ela a lane.** Medido no
> fecho: `pipeline/domain/services/tributario/irpf_titular_anchor.py` existe em
> `main`, com o enum `AncoraTitular` (`resolvida` / `ambigua` /
> `sem_declaracao_no_ano`), consumido por `tributario_irpf_reader.py:17,104,117`;
> `tributario_input_builder.py:170::_cpf_do_titular` resolve o titular contra
> `family_members` e devolve `None` quando há ≠1 titular ou falta CPF — sem
> identidade a base é **ausente**, não a de quem sobrou. A [[A40.l65]] está
> `shipped`. Não reescrevi o texto de 08-24 acima: é snapshot datado.

## Fecho — 2026-08-27 · `shipped` em #1491

Lane fechada pela skill `lane-closeout`. **O trabalho estava feito e provado
desde 2026-08-18; o registro é que ficou 9 dias atrás** — a lane seguia `open`
sem `ship_pr`, aparecia em `SPRINT_CURRENT.md` como trabalho disponível e o
`lane_pickup` a dava como `LIVRE`. É o ponto cego declarado do
`dev/check_lane_transition.py`: a checagem `C1` só alcança lane que **declara**
`ship_pr`, e transição ausente não produz diff nenhum.

O flip foi roteado explicitamente pela lane vizinha e nunca executado:
[[A40.l65]] §Ataque item 5 — *"O item 5 é da [[A40.l36]] — flip de `status` +
`ship_pr`, não desta lane."*

### O que foi re-exercitado (não relido)

| critério | prova |
| --- | --- |
| a medição reproduz | mutação em cópia isolada, sem editar arquivo de produto: revertendo `renda_pf = inp.renda_tributavel_pf_irpf_anual` para a soma pré-fix, `compute(_input_pro_labore_tambem_no_irpf())` dá base 318.000 / teto 38.160; em `main`, 174.000 / 20.880 |
| o teste morde | `pytest tests/test_cascata_renda_pf_base.py -q` → **12 passed**; sob a mutação, **8 failed / 4 passed**. Não há `xfail` no arquivo em `main` |
| pró-labore nas duas fontes | a fixture `_input_pro_labore_tambem_no_irpf` tem `pro_labore_mensal=12000` no fluxo E4 **e** os mesmos 144k dentro de `renda_tributavel_pf_irpf_anual=174000` |

### O que o fecho corrigiu fora da lane

- **[`FAQ_cascata_fiscal_pj.md`](../../../reference/FAQ_cascata_fiscal_pj.md)
  publicava a fórmula do double-count**, em bloco cercado e no presente
  (`base_pgbl_anual = pro_labore_anual_tributavel + outras_rendas_…`), 9 dias
  depois do fix. É a página que o usuário lê para conferir o número — a
  superfície de maior dano do defeito —, é `type: doc` indexado, e **nenhuma
  lane viva a nomeava**. O exemplo numérico também derivava a base de um
  pró-labore de fluxo (R$ 18k), que é o impostor *"pró-labore-only"* que o gate
  desta lane rejeita. Corrigida com a correção datada.
- **[[ADR-236]] §Emenda 2026-08-27** — o §D2 (tabela de inputs), o §D3
  (`dataclass CascataInput`) e o §D5 (spec de render do card) ainda prescreviam
  o nome e a composição que a §Emenda 2026-08-17 revogou. São seções vigentes,
  não snapshot: re-derivar dali reintroduz o defeito.

## Aberto — 2026-08-27 · dono: David Robert

Dois achados do fecho, ambos de **gate ausente**, não de número errado. Nenhum
bloqueia o fecho — o comportamento em `main` está correto; o que falta é o que
impede a volta.

1. **A junção real das duas fontes não tem teste.** O teste entregue monta
   `CascataInput` à mão e prova a contagem única dentro de `_compute_layers`;
   mas o único ponto de produção onde a fonte E4 e a fonte IRPF se encontram é
   `backend/app/services/tributario_input_builder.py:287::_assemble_input`, e
   ali o double-count pode ser reescrito sem nada ficar vermelho. Medido por
   mutação no call-site (injeção via plugin pytest, sem editar arquivo):
   trocando `renda_tributavel_pf_irpf_anual=irpf.total` pela soma com o
   pró-labore, os 4 arquivos que importam o builder passam inteiros —
   `38 passed`. Braço de controle: a mesma injeção zerando a base derruba
   `8 failed`, então o verde é medição, não no-op. Causa: as fixtures do builder
   semeiam IRPF sem fluxo E4 (`pro_labore = 0`), e a única que semeia
   `pro_labore: 120000.0` não afirma nada sobre a base.
   *Retomar quando:* alguém tocar `_assemble_input` — ou antes, se o ICP PJ
   entrar em dogfood com as duas fontes preenchidas.
2. **A frase que o card entrega ao leitor não tem gate.** O #1491 trocou o copy
   para *"Base = total dos rendimentos tributáveis declarados no IRPF"*, e
   nenhum teste afirma essa string: `rg -n "total dos rendimentos tributáveis"
   frontend/tests/` → nada; `CascataFiscalCard.test.tsx:110` afirma só o rótulo
   do bloco (*"Base para dedução PGBL"*), idêntico antes e depois do fix. Com o
   §D5 já corrigido (acima), a spec deixou de mandar escrever errado — mas a
   saída do produto segue sem tranca, e os 12 casos desta lane medem
   aritmética, não prosa.
