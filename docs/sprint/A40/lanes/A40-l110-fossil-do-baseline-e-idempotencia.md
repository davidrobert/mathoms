---
id: A40.l110
type: lane
title: "O baseline grava `date.today()` no artefato e o §F da ADR-409 nomeia o produtor errado: matar o fóssil nas duas pontas"
sprint: A40
status: in_progress
priority: P1
branch_slug: a40-l110-fossil-do-baseline-e-idempotencia
owner: data-engineer
depends_on: []
adrs: ["[[ADR-409]]", "[[ADR-427]]", "[[ADR-093]]", "[[ADR-212]]"]
tags: [type/lane, sprint/a40, status/in-progress, priority/p1, area/dados, area/pipeline]
---

# A40.l110 — `fossil-do-baseline-e-idempotencia`

> **Origem:** tratamento dos achados da [[A42.l19]]. Co-design `data-engineer`,
> 2026-08-31. **Origem** do escopo: o §Deferimento datado da [[A40.l58]] (§F da
> [[ADR-409]]) — que está `shipped` e **não é rota**: lane terminal não executa
> trabalho. Esta lane é auto-contida; a l58 se lê como histórico, não como dono.

## O defeito, em três camadas

**1. `date.today()` é gravado em artefato persistido — quebra de idempotência.**
`BaselineNormalizer` passo 2 cai em `self._resolve_today()` quando
`data_consolidacao` não existe — e `consolidate_baseline` **não emite** essa chave.
Medido, mesmo input em dois dias civis:

```
dia 2026-08-12  sha256[:12]=77467dd93aca
dia 2026-08-16  sha256[:12]=69cd9157bdc4   ⇒ NÃO idempotente
```

Envenena qualquer métrica de massa por conteúdo (o balde `patrimonio` conta 1
evidência nova por dia civil) e viola a idempotência radical do CLAUDE.md.

**2. Os 2 `required` fósseis não têm leitor.** `pipeline_stage` e
`data_processamento` só aparecem, no payload de baseline, no normalizer, nos testes
dele, na fixture e no schema. Zero consumidores de produção — verificado por `rg` em
`pipeline/`, `backend/app`, `scripts/`. O `pipeline_stage` chega a exigir
`const: "E1.5_Baseline_Patrimonial"`, nome que a [[ADR-093]] não reconhece.

**3. A premissa do §F da [[ADR-409]] está errada.** Ele manda re-derivar o contrato
*"do produtor E1.5c"* — mas a `description` do próprio schema declara outro:
*"A normalização em E4 converte v2 → v1 canonical **antes da validação**"*. Executar
o §F ao pé da letra escolhe o shape errado.

**A divergência entre os dois produtores é de exatamente 2 campos** — os mesmos 2
fósseis. Não são "duas formas do mesmo payload": é uma forma e um enxerto.

## O circuito que escondeu isso

O normalizer **sintetiza** os campos e a fixture
`tests/fixtures/pipeline_golden/e2/dois-membros-anos-disjuntos-1.5_consolidated.json`
os **hardcoda** no topo — três campos que `consolidate_baseline` nunca emite. Produtor
e teste concordando na crença errada. É a segunda instância, na mesma família de
schema e na mesma sprint, da patologia que a [[ADR-427]] §Consequências pegou em
`minimal-receitas-4_unified.json`.

## Ordem dura (o dilema evapora se as pontas caírem juntas)

**PR-A — matar o fóssil nas duas pontas, atômico.** Remove os 2 `required` + as 2
`properties` do schema; deleta os passos 1 e 2 do `BaselineNormalizer` (**o
`date.today()` sai aqui**); deleta `normalize_baseline` + `load_patrimonio` de
`scripts/categorize_transactions.py` (dead code de disco pós-[[ADR-212]], zero
call-sites, e único outro sítio do repo com a string do `const`); reescreve a fixture
para espelhar o produtor. `additionalProperties` **fica sem setar**. Medir os dois
produtores de novo — não presumir.

**PR-B — re-derivar do shape único.** Declarar as chaves reais, aposentar as
fantasmas restantes, colapsar o `oneOf` de raiz (o Format B `declarations` é ramo
morto pela medição do próprio §F — mesma classe que a [[ADR-427]] D4 consertou no E4)
e **então** decidir `additionalProperties`.

## Critério de aceite

- [x] Dois runs em dias civis distintos, mesmo input → `sha256` **idêntico** do balde
      `patrimonio`. Gate mede o **efeito** (hash), nunca o relógio — e mede também o
      **mecanismo**, porque só o hash é inerte contra este defeito (§Os gates).
- [x] `measure_schema_drift --schema baseline_patrimonial.schema.json --all` com o
      número **antes e depois** no corpo do PR, para os dois produtores.
- [x] Controle negativo: reinserir `pipeline_stage` na fixture **reprova**.
- [ ] PR-B: `additionalProperties: false` com os dois produtores em 0 de drift no
      corpus, medido. Gate de completude por **igualdade de conjunto** entre chaves
      declaradas e emitidas, nos dois sentidos ([[ADR-427]] D5).
- [x] §Deferimento da [[A40.l58]] corrigido — **feito** em
      [#1897](https://github.com/davidrobert/mathoms/pull/1897) (`3086b149`), de forma
      aditiva: o produtor declarado é o E4 pós-normalização; são dois produtores desde
      a [[ADR-427]] D3; e `additionalProperties` não se decide antes do PR-A.

## Execução PR-A (2026-08-31) — o fóssil morreu nas duas pontas

> `open` → `in_progress`. O PR-B (re-derivar o shape único) continua aberto e é
> pré-requisito de qualquer flip deste schema.

### O que caiu

- **Schema** — os 2 `required` e as 2 `properties`. A `description` também estava
  errada: declarava um produtor só. Agora nomeia os dois ([[ADR-427]] D3).
  `additionalProperties` segue **sem setar**, como a ordem dura manda.
- **`BaselineNormalizer`** — passos 1 e 2, e com eles o `date.today()`. O ctor
  existia só para injetar relógio em teste; saiu junto.
- **Dead code de disco** — `normalize_baseline` + `load_patrimonio` +
  `validate_baseline_schema` em `scripts/categorize_transactions.py` (216 linhas,
  zero call-site desde a [[ADR-212]]).
- **6 fixtures** — a lane nomeava 1; são 6. As 5 `*1.5_consolidated.json` e a
  `dogfood/baseline-1.5.json`.

### O que a medição disse, e onde ela corrigiu o enunciado

**1. O §F da [[ADR-409]] erra um fato, não só o produtor.** Ele afirma que o
normalizer roda *"em memória, nunca reescrito no artefato"*. Medido no corpus
inteiro (0 ilegíveis): **71/71** artefatos `patrimonio` do E4 carregam os 2 campos,
**persistidos**; 0/98 do lado E1.5c. É por esse caminho que o `date.today()`
chegava ao disco. Emenda datada na ADR.

**2. A medição só é legível com a chave de decriptação.** Sem
`MATHOMS_FERNET_KEY`/`_KEYS` no env, `measure_schema_drift` reporta
`drift 0.0% · NO-GO` com **169/169 ilegíveis** — a tabela em texto não mostra a
coluna `unreadable`, e `0.0%` lê-se como limpo. Quem protege é o `NO-GO` e o
`paylds 0`. Números desta lane vêm todos do run com a chave.

**3. A divergência entre os dois produtores era exatamente os 2 campos** — a tese
da lane, agora medida dos dois lados: depois do PR-A os dois produtores drifta no
**mesmo path, no mesmo item**.

| produtor | antes | depois |
| --- | --- | --- |
| `consolidate_baseline` (E1.5c) | 98/98 · 100% | **3/98 · 3,1%** |
| E4 `patrimonio` (pós-normalização) | 3/71 · 4,2% | **3/71 · 4,2%** |
| agregado | 101/169 · 59,8% | **6/169 · 3,6%** |

Os 2 `required` respondiam por 392 das 398 ocorrências. As 6 restantes são o
`valores_31_12` negativo — [[A40.l111]], fora de escopo por decisão da lane.

### Os gates, e por que são dois

`tests/test_baseline_sem_relogio_gate.py` — **o teste de efeito sozinho é inerte
contra este defeito**, e isso foi medido: com o `date.today()` reinstalado, os dois
builds caem no mesmo dia civil e o `sha256` bate. Quem reprova é o **mecanismo**
(nenhuma chamada de relógio de parede durante a construção, via `sys.setprofile`),
e ele reprova hoje, não em algum dia futuro. Controle negativo: 4 dos 5 testes
falham com o passo reinstalado.

`tests/test_fixture_baseline_espelha_produtor_gate.py` — controle negativo da lane
(*"reinserir `pipeline_stage` na fixture reprova"*), medido. A primeira versão da
medição do produtor era **circular**: `consolidate` copia as chaves do input para o
output, então medir com a fixture já limpa provava apenas a passagem. A entrada é
limpa antes, e `test_a_medicao_do_produtor_discrimina` prova que o instrumento
enxerga a presença quando ela existe.

### O que o PR-A cria, e que não estava no enunciado

A [[ADR-409]] §F recusa *"tirar só os 2 `required`"* porque isso **torna o número
verde sem tornar o contrato real** — e a elegibilidade do flip é só a medição, com
o §F vivendo em prosa. Hoje o schema ainda mede `NO-GO` por causa dos 6 residuais;
**quando a [[A40.l111]] fechar, o drift vai a 0 e o predicado do §B diria `GO`**
para um contrato que descreve 5/13 do payload. A prosa não seguraria.

`baseline_patrimonial` entra em `_CONTRATO_NAO_DERIVADO` no
`dev/measure_schema_drift.py`: veredito `NO-GO` **independente do drift**, com a
razão e a lane que o levanta (o PR-B) na mensagem. É o que o §F pedia, enforçado.

## Fora de escopo

O `valores_31_12` negativo (3/71) é defeito de **dado** com regra de domínio própria —
vive na [[A40.l111]], dono `financial-planner`. Mantê-lo fora é o que permite a medição
do PR-B ser honesta.
