---
id: A42.l16
type: lane
title: "O check de cobertura cambial converte 'não sei o tier' em 'passou'"
sprint: A42
status: shipped
ship_pr: 1827
ship_date: "2026-08-29"
priority: P0
branch_slug: a42-l16-check-cambial-converte-nao-sei-em-passou
owner: senior-cto
depends_on: []
adrs:
  - "[[ADR-403]]"
  - "[[ADR-418]]"
tags:
  - type/lane
  - sprint/a42
  - status/shipped
  - priority/p0
  - area/pipeline
---

# A42.l16 — `check-cambial-converte-nao-sei-em-passou`

> **Origem:** `PV10-01` da rodada unificada **U2** ([[PIPELINE-REVIEWS-active]] §r10,
> merge `47970706`). Verificado literalmente no código.

## O defeito

`scripts/validate_cross.py:640`:

```python
coberto = len(apurados) == len(componentes) or tier == "indeterminado"
```

A disjunção é uma **escotilha de sinal invertido**: quanto **menos** o sistema sabe, mais
fácil o check passa. No run medido o CV18 saiu `passed: true, severity: info` com
`não apurados=[…]; tier=indeterminado` — um componente não apurado e o tier desconhecido, e o
resultado publicado é verde.

**A política correta está no mesmo módulo, 400 linhas acima** (`:227-229`, CV5):
*"ausência é 'não sei', nunca 'bate'"*. E `_cv18` **já sabe** devolver `None`
(`:628-630`, `if not componentes: return None`).

## Distinga de dois vizinhos

- `PV9-14` é *"definição impressa ≠ implementada"* — produtor é a **calculadora**.
- `PV9-15` foi **REFUTADO** na U2: o tier nunca trocou de sinal;
  `carteira_lastro_estrangeiro` é fixado `Cobertura.indeterminado` **incondicionalmente**
  desde `6c546d7b` (2026-08-21), e `_tier_from_pct` é **código morto em produção** — a
  [[A40.l80]] §C1 já mediu isso em `main`.

Aqui o produtor do defeito é o **validador**.

## Não medido — a lane deve medir

Se `indeterminado` é o tier **default** do dogfood, a escotilha está aberta **sempre**, não
só neste run. Isso muda a severidade.

## Contexto que amplia o alvo — decida o escopo

O mesmo arquivo tem 17 checks e apenas **4** podem pausar o run (`_CONSERVATION_CHECKS`,
`:681`), e os 4 são **recompute de produtor único** (leem componentes **e** total do mesmo
payload E5) — a classe que a [[ADR-418]] §D4 já condenou **no mesmo arquivo**. O CV5 recebeu o
remédio; CV1/CV2/CV3/CV6 não. Ver `PV10-03`. Decida se a lane cobre só o CV18 ou a classe.

## Critério de aceite

- Ausência devolve `None`, nunca `True`.
- **Prove que o check reprova no cenário certo** com `tests/test_e7_conservation_gate.py` — a
  U2 leu o gate no código e **nunca o observou disparando**, e isso está declarado como
  evidência fraca no §r10.

---

## Medição (2026-08-29) — o enunciado de origem não sobreviveu inteiro

> **Tudo abaixo é medido, não lido.** A U2 declarou evidência fraca por ter lido o gate no
> código sem observá-lo disparar; esta seção é o que o disparo mostrou.

### A tabela-verdade completa do termo, sobre o payload do run real

| cobertura | `tier` | `coberto` | leitura |
| --- | --- | --- | --- |
| completa | afirma faixa | ✅ passa | correto |
| completa | `indeterminado` | ⚠️ **passava** | **o buraco real** — veredito fraco demais |
| incompleta | afirma faixa | ✅ **reprova** | o caso perigoso — **já reprovava** |
| incompleta | `indeterminado` | ✅ passa | estado **sancionado** da v1 ([[ADR-403]]) |

**A linha 3 refuta o enunciado.** *"Quanto menos o sistema sabe, mais fácil o check passa"*
descreve um efeito real do `or`, mas o caso que ele deixa passar é a linha 4 — cobertura
incompleta **com o veredito suprimido**, que é exatamente o que a [[ADR-403]] decidiu que o
produto deve fazer (*"cobertura incompleta suprime o VEREDITO, não a medida"*). A banda
afirmada sobre numerador que o run não fechou — o dano assimétrico que motivou a ADR — **já
reprovava**, com teste desde o #1568 (`test_cv18_pega_veredito_forte_demais_para_a_cobertura`).

### O defeito que sobra, e é de outro sinal

`_tier` define `indeterminado` como **exatamente** "algum componente não apurado". Logo os
dois disjuntos são `P` e `¬P` para todo artefato que o produtor emite: `coberto` era
`P ∨ ¬P` — um termo que **não discriminava nada**. Não é escotilha; é decoração. Mesma
família que a [[ADR-418]] §D4 condenou neste arquivo, na forma de disjunção absorvente em
vez de recompute de produtor único.

### A pergunta que a lane mandava medir

> *"Se `indeterminado` é o tier default do dogfood, a escotilha está aberta SEMPRE — não só
> neste run. Isso muda a severidade."*

Varridas **60 combinações dos inputs de `compute_exposicao_cambial`** (caixa vazio / 1 moeda
/ 2 moedas × posições ausentes / vazias / ETF / custódia estrangeira × 5 denominadores):

- o produtor emite **uma única** forma — `caixa_fx=apurado`,
  `carteira_lastro_estrangeiro=indeterminado`, `tier=indeterminado`;
- **CV18 reprovou em 0 das 60**;
- as outras duas pernas são igualmente constantes sob o produtor: `Σ(apurados)` soma só
  `caixa_fx`, que **é** `total_brl` por construção; `_carteira_reconcilia` devolve `True`
  sem medir enquanto a carteira não se declara apurada.

Não é que a escotilha esteja sempre aberta escondendo veredito errado: **CV18 inteiro é
inerte fim-a-fim** desde `6c546d7b` (2026-08-21) e publicou `passed: true` em todo run
porque não podia fazer diferente. Seus únicos contraexemplos são dicts editados à mão nos
próprios testes. A [[ADR-403]] afirma *"os gates aqui são provados por mutação"*: as
mutações existiam e eram todas de **payload** — nenhuma de **produtor**. É a distinção entre
"o predicado está certo" e "o predicado pode pegar uma regressão".

### O critério de aceite de origem está refutado

> *"Ausência devolve `None`, nunca `True`."*

`None` é a resposta certa quando o check **não é avaliável** — é o que `_cv18` já faz sem
`componentes` (artefato pré-#1568). Com `tier == indeterminado` **não há ausência**: o run
sabe que a cobertura é incompleta e sabe qual é o tier. Devolver `None` ali apagaria o check
de **100% dos runs** — trocaria um termo inerte por um **check** inerte, perdendo junto a
conservação e a reconciliação. A política do CV5 citada na origem (*"ausência é 'não sei',
nunca 'bate'"*) continua certa e **não se aplica a este ponto**.

### Escopo decidido: só o CV18

A classe (`PV10-03` — 4 de 17 checks gateiam e são recompute de produtor único) **não** entra:
promover ou recompor `_CONSERVATION_CHECKS` muda comportamento de pausa de run e pede
decisão própria. Fica um insumo medido para ela, abaixo.

## Entregue

1. **`or` → equivalência** (`_tier_concorda_com_cobertura`): o veredito publicado diz o
   mesmo que a cobertura publicada, **nos dois sentidos**. Preserva as linhas 1, 3 e 4 e
   fecha a 2 — uma v2 que reconcilie os universos e esqueça de destravar `_tier` pararia de
   publicar banda em silêncio, e o check dizia verde.
2. **Tripwire de produtor** (`test_produtor_v1_emite_uma_unica_forma_de_cobertura`): pina a
   inertidão medida. No dia em que a v2 destravar a carteira, ele reprova e obriga quem
   fizer isso a reler CV18 em vez de herdar um check que nunca disparou.
3. **CV18 observado disparando**, em `tests/test_e7_conservation_gate.py`: atravessa
   `stage.run()`, chega ao payload como `errors_count` — **e não pausa**.
4. **[[ADR-403]] §D7 emendada** (2026-08-29). Nenhum ID de ADR novo alocado.

## Insumo medido para o `PV10-03`

A nota de *"evidência fraca"* daquela linha diz que a prova barata existe e **não foi
usada**. Ela existe **e estava em uso**: `test_stage_pausa_em_conservacao_violada` observa
CV2 reprovando e pausando via `stage.run()` desde o **#941** (`67e4f2b9`, 2026-07-10,
[[A36.l3]]), no arquivo que a linha nomeia. O que **não** era observado é o outro lado, e
agora está: CV18 emite `severity="error"`, reprova no stage e **não pausa**, por estar fora
de `_CONSERVATION_CHECKS`. Um `error` que não gateia é exatamente o que a linha de resumo
"17/17 OK" conflaciona com gate. A substância do `PV10-03` não é afetada.

## Verificação

- `pytest tests -q` — 7912 passed, 38 skipped, 2 xfailed
- A/B contra o `or` original: **um** teste discrimina o fix
  (`test_cv18_pega_veredito_fraco_demais_para_a_cobertura` reprova sem, passa com); os
  outros 26 passam nos dois lados — a fixture de reconciliação foi tornada internamente
  consistente para deixar de testar dois eixos ao mesmo tempo.
- **Não muta E5** ⇒ fora de qualquer janela de rebaseline.

## Fecho — PR [#1827](https://github.com/davidrobert/mathoms/pull/1827), merge `221534e8` (2026-08-29)

**O título e a §O defeito acima preservam o enunciado como ele foi REGISTRADO pela U2, não
como ele terminou.** A §Medição os refuta; nada aqui foi reescrito, porque o enunciado de
origem é evidência do que a rodada concluiu.

Re-medido **contra o código mergeado** (o número não foi relido, foi re-rodado): a varredura
de 60 combinações de input do produtor continua em **0 reprovações** — a equivalência não
introduziu falso-positivo no estado sancionado da v1, que é o regime de 100% dos runs.

`pytest tests -q` = **7912 passed** é medição do commit desta lane. Em `main` com o #1828
dentro são **7918** — a diferença são os 6 testes daquele PR, nenhum meu.

## Aberto, com dono

- **Prioridade re-triada de P0 para P1 — recomendação, não decisão.** O motivo do P0 era a
  escotilha que esconderia veredito errado, e ele não sobreviveu à medição; o que resta é
  inertidão de check, que não alcança o leitor. Frontmatter e tabela do `_README` continuam
  **P0** de propósito: re-priorizar linha de registro de rodada é do dono da sprint.
  **Dono: quem triar o `r11`**, junto com a re-triagem já pendente de `PV9-09`/`PV9-19`/`PV9-14`.
- **`PV10-03` (recompor `_CONSERVATION_CHECKS`) segue aberto** e recebeu insumo medido desta
  lane — ver §Insumo. Dono: a linha `PV10-03` do §r10, sem lane ainda.
