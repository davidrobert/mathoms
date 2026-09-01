---
id: A40.l110
type: lane
title: "O baseline grava `date.today()` no artefato e o §F da ADR-409 nomeia o produtor errado: matar o fóssil nas duas pontas"
sprint: A40
status: shipped
priority: P1
branch_slug: a40-l110-fossil-do-baseline-e-idempotencia
owner: data-engineer
ship_pr: 1914
ship_date: "2026-09-01"
depends_on: []
adrs: ["[[ADR-432]]", "[[ADR-409]]", "[[ADR-427]]", "[[ADR-093]]", "[[ADR-212]]"]
tags: [type/lane, sprint/a40, status/shipped, priority/p1, area/dados, area/pipeline]
---

# A40.l110 — `fossil-do-baseline-e-idempotencia`

> ✅ **Entregue em 2026-09-01 nos dois PRs.** **PR-A** —
> [#1914](https://github.com/davidrobert/mathoms/pull/1914) (`f8cbf94d`): o fóssil morre
> nas duas pontas e o `date.today()` sai do artefato. **PR-B** — [#1933](https://github.com/davidrobert/mathoms/pull/1933),
> [[ADR-432]]: o contrato é re-derivado do produtor (**5 de 11 → 14 de 14**), o `oneOf` de raiz colapsa e
> `additionalProperties: false` entra. Closeout do PR-A em
> [#1929](https://github.com/davidrobert/mathoms/pull/1929), que corrigiu 3 números meus.
>
> **O flip deste schema continua bloqueado — agora pelo número, não pela prosa.** Medido
> pós-PR-B: E1.5c 3/98 (valor negativo, [[A40.l111]]) e E4 **71/71**
> `additionalProperties`, de artefato **histórico** que carrega os 2 fósseis. Some quando
> as runs virarem o corpus; nenhuma ocorreu desde 2026-08-30 19:07.

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

- [x] **Mecanismo — é este que discrimina.** Zero leitura de relógio de parede durante
      a construção do balde `patrimonio`, via `sys.setprofile`
      (`tests/test_baseline_sem_relogio_gate.py`). Controle negativo medido: com o passo
      do `date.today()` reinstalado, **4 dos 5 testes reprovam**.
- [x] **Efeito** — dois builds do mesmo input → `sha256` idêntico do balde. **Declarado
      inerte sozinho contra este defeito, e medido como tal:** no mesmo dia civil o hash
      bate mesmo com o `date.today()` de volta. Vale contra outras fontes de
      não-determinismo, não como prova de idempotência entre dias.
- **Não medido, e por quê** (sem checkbox de propósito — caixa vazia que ninguém pretende
      fechar vira pendência zumbi): dois runs em **dias civis distintos** pós-fix. Não há
      congelamento de relógio no repo (sem `freezegun`). Os `sha256` divergentes de
      2026-08-12 e 2026-08-16 no §O defeito são **pré-fix** — provam que o defeito existiu,
      nunca que sumiu. Substituídos, por decisão desta lane, pelo gate de mecanismo acima.
- [x] `measure_schema_drift --schema baseline_patrimonial.schema.json --all` com o
      número **antes e depois** no corpo do PR, para os dois produtores.
- [x] Controle negativo: reinserir `pipeline_stage` na fixture **reprova**.
- [x] PR-B: `additionalProperties: false` com gate de completude por **igualdade de
      conjunto** entre chaves declaradas e emitidas, nos dois sentidos ([[ADR-427]] D5),
      nos dois produtores — `tests/test_baseline_contrato_completo_gate.py`, com o
      conjunto emitido vindo de **rodar o produtor**, nunca de lista à mão. Controles
      negativos medidos: fantasma de volta reprova, chave emitida fora do schema reprova,
      `oneOf` de volta reprova.

      > **Re-corte 2026-09-01 — o critério anterior era insatisfazível.** Ele exigia *"os
      > dois produtores em 0 de drift no corpus"*. Os 6 residuais são violação de
      > `minimum: 0` — domínio de **valor** —, e `additionalProperties` é sobre **forma**:
      > o critério acoplava ao PR-B um drift que a própria §Fora de escopo desta lane
      > declarou de outra dona. Pior, o desbloqueio não tinha data: a [[A40.l111]] já
      > mergeou (#1917) e os 6 continuam. Medido: sobreposição hoje é **5 de 11**
      > (declaradas 11, emitidas 15) — é esse número que o PR-B move, e ele não depende
      > do drift de valor.
      >
      > O drift de valor sai **declarado fora, com dono**: [[A40.l111]] `shipped`, e o
      > corpus só o reflete quando as runs virarem — nenhuma ocorreu desde o merge
      > (artefato mais novo: 2026-08-30 19:07).
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

Os 2 `required` respondiam por **196 das 202** ocorrências (97,0%). As 6 restantes são o
`valores_31_12` negativo — [[A40.l111]], fora de escopo por decisão da lane.

> **Correção 2026-09-01 — eu publiquei `392 das 398`, e era do instrumento.**
> `jsonschema` já emite **um erro por campo faltante**, e `_validation_paths`
> ([`schema_drift_telemetry.py`](../../../../scripts/schema_drift_telemetry.py))
> **re-expande cada erro sobre todos os campos faltantes** — contagem quadrática.
> Medido: 1 campo → 1 ocorrência, 2 → 4, 3 → 9. Com 98 artefatos × 2 campos o real é
> **196**, e o tool reportava 392. O defeito do instrumento é anterior ao PR-A; o que
> este PR fez foi fossilizá-lo na lane e na emenda da [[ADR-409]]. A conclusão não muda
> (97,0% contra 98,5%); o número, sim. Quem re-medir hoje encontra 202 e concluiria que
> o corpus mudou.

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
o §F vivendo em prosa. Hoje o schema ainda mede `NO-GO` por causa dos 6 residuais.

> **Correção 2026-08-31, medida.** Eu escrevera *"quando a [[A40.l111]] fechar, o
> drift vai a 0"*. Ela fechou ([#1917](https://github.com/davidrobert/mathoms/pull/1917))
> e **não foi a 0**: os 6 continuam. O fix dela vale para run **nova**; o corpus
> histórico guarda os negativos já persistidos, e o `minimum: 0` segue reprovando-os.
> O verde chega quando as runs virarem o corpus — data que ninguém agenda.
>
> **Emenda 2026-09-01 — o fato é mais duro que o mecanismo que eu declarei.** Não é só
> que "vale para run nova": **nenhuma run ocorreu desde o merge**. Artefato mais novo do
> corpus é de `2026-08-30 19:07`; artefatos em/após 2026-08-31 são **0**, e
> `valores_31_12` com `null` são **0** nos dois produtores. O `sanear_baseline` do #1917
> ainda não executou em produção nem uma vez.

Quando chegar, **o predicado do §B diria `GO`** para um contrato que descreve **5 de 11**
do payload (medido 2026-08-31: declaradas 11, emitidas 15; era 5/13 antes do PR-A). A prosa não seguraria — e a data em que ela deixaria de segurar não é
previsível, que é justamente o que torna o enforcement necessário.

`baseline_patrimonial` entra em `_CONTRATO_NAO_DERIVADO` no
`dev/measure_schema_drift.py`: veredito `NO-GO` **independente do drift**, com a
razão e a lane que o levanta (o PR-B) na mensagem. É o que o §F pedia, enforçado.

## Execução PR-B (2026-09-01) — o contrato passa a descrever o payload

**[[ADR-432]] `Decidido`.** Censo do corpus por produtor, e o schema re-derivado do que
os dois de fato emitem:

| | antes | depois |
| --- | --- | --- |
| properties declaradas | 11 | **14** |
| sobreposição declarada×emitida | 5 de 11 | **14 de 14** |
| `oneOf` de raiz | Format A ∪ Format B | colapsado — `required: ["patrimonio_por_ano"]` |
| `additionalProperties` | sem setar | **`false`** |

**+8 emitidas que não eram declaradas** (`itens`/`resumo` em 98/98 e 71/71; `_meta`,
`informe_pf_saldos_31_12`, `wise_fiscal_flags`, `payload_version`, `prompt_version`,
`validation`). **−5 fantasmas** (`anos_base`, `declarations`, `properties`, `receipts`,
`summary`). `membros` fica **por alcance de código** — o normalizer a emite por alias de
`membros_familia`, e sob `strict` chave emitível não declarada abortaria o write.

O Format B exigia `declarations`, que é **0/169**; `patrimonio_por_ano` é 98/98 e 71/71.
Ramo morto de contrato é pior que ausência: publica forma que produtor nenhum produz.

### O preço, medido e aceito

`additionalProperties: false` leva o agregado de 6/169 a **74/169 (43,8%)**:

| produtor | drift | causa |
| --- | --- | --- |
| E1.5c | **3/98** | `valores_31_12` negativo — [[ADR-431]], [[A40.l111]] |
| E4 `patrimonio` | **71/71** | os 2 fósseis, em artefato **histórico** |

Os 71 são anteriores ao PR-A e a validação é pós-**write** ([[ADR-212]]) — write novo não
os carrega, produção nenhuma quebra. Foi decisão explícita da [[ADR-432]] §Não-decisões
**não** declarar os fósseis para zerar o número: seria ressuscitar o que esta lane matou.

### `_CONTRATO_NAO_DERIVADO` levantado

A razão do bloqueio era *"contrato irreal"*, e ela morreu. O dicionário fica **vazio, não
deletado** — é onde a recusa da [[ADR-409]] §F se encoda para o próximo schema —, e os
testes do mecanismo passam a usar entrada sintética, senão morreriam calados.

O que bloqueia o flip agora é o número, e ele **nomeia o path**. Era esse o ponto.

## Fora de escopo

O `valores_31_12` negativo (3/71) é defeito de **dado** com regra de domínio própria —
vive na [[A40.l111]], dono `financial-planner`. Mantê-lo fora é o que permite a medição
do PR-B ser honesta.
