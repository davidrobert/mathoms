---
id: A40.l116
type: lane
title: "O guard de autocontradição do parecer erra a seção pela terceira vez, e o teste que o cobre importa a própria constante — cego por construção"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l116-guard-de-liquidez-erra-a-secao-e-o-teste-e-cego
owner: prompt-engineer
depends_on: []
adrs: ["[[ADR-412]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/backend]
---

# A40.l116 — `guard-de-liquidez-erra-a-secao-e-o-teste-e-cego`

> **Origem:** `RR9-09` + `RR9-22` da rodada unificada **U5**
> ([[PIPELINE-REVIEWS-active]] §r13). **Reincidência medida** da [[A40.l80]].

## O que reincide

O parecer **elogia** *"Reserva Robusta"* e **alerta** *"Reserva Excessiva — Capital
Ocioso"* sobre o mesmo objeto, na mesma página, com `autocontradicao_removidos: 0`.

`backend/app/services/parecer_guardrails_divida.py:165` — `_SECAO_LIQUIDEZ = "S1"`. O
modelo rotula a reserva com **outra** seção. A [[A40.l80]] fechou este mesmo defeito
(#1800) quando a constante valia um **terceiro** valor: o conserto **trocou o literal** em
vez de derivar o alvo do layout, então o guard voltou a errar assim que o rótulo do modelo
mudou. **É a terceira posição em que o alvo não casa.**

## O achado novo, e ele é o que mantém o defeito vivo

`tests/test_parecer_guardrails_divida.py` **importa `_SECAO_LIQUIDEZ`** e constrói a
fixture com ele (`_risco(section=_SECAO_LIQUIDEZ)`). O teste é **invariante ao valor da
constante**: qualquer literal passa, inclusive um que o modelo nunca emite. O gate que
deveria proteger a correção da [[A40.l80]] **não pode falhar** — mesma classe dos achados
de instrumento desta rodada ([[A42.l24]]).

O contador `autocontradicao_removidos: 0` não é falso: o **detector** não alcança o par
elogio × alerta, só pares dentro da mesma lista.

## A medição, e o que ela refutou no próprio enunciado

14 runs do dogfood (artefatos `parecer_planejador` decriptados do DB), mesmo corpus,
`temperature=0` — a variância não é amostragem:

| `section_id` do item de liquidez | runs |
| --- | --- |
| `S3` | 9 |
| `S4` | 5 |
| `S1` (valor de hoje, posto pelo #1800) | **0** |

`avaliacao_liquidity == "Excessiva"` em **10/10** runs checados: o gate do E5 está vivo, e
é o guardrail que não alcança. Pós-#1800, `autocontradicao_removidos == 0` em 5/5.

**⚠️ O critério 1 original está REFUTADO.** Ele mandava o alvo *derivar do layout*. O bloco
da reserva vive em `saude_balanco`, que é `aligned_with_layout: "S1"` — derivar do layout
produz exatamente `S1`, o valor 0/14. O remédio prescrito **reproduz o defeito**.
`section_id` não é propriedade do objeto: é rótulo que o modelo re-sorteia a cada run, e
nenhum literal — derivado ou não — sobrevive.

**⚠️ Refutada também a premissa do teste da [[A40.l80]]** (`test_guardrail_arma_em_secao_que_o_manifest_projeta`): *"seção que o manifest não projeta
é seção que o modelo não rotula"*. O modelo emite `S4`, `S_parecer`, `S_IRPF_RENDA` e `S_IRPF_OTIMIZACAO`, **nenhuma
projetada** pelo manifest. E o teste era fraco de todo modo — pertinência num conjunto de 8
deixa 7 literais errados passarem.

**O teste era cego, e isso foi medido, não inferido:** o HEAD passa **23 de 23** com
`_SECAO_LIQUIDEZ` mutada para `"S9"`, uma seção que o modelo nunca dá ao item de liquidez.

**⚠️ O critério 4 original é insustentável como invariante.** `PONTOS_FORTES_MIN = 3`
([[ADR-202]] §D5): com 3 pontos fortes o guard **não pode remover**, só ressalvar, e
`removidos: 0` é a saída *correta*. Distribuição medida de `len(pontos_fortes)` nos 14 runs:
**5 em 9 runs, 4 em 4, 3 em 1**. O tripwire passa a medir `removidos + ressalvados > 0`.

## Critério de aceite (revisado pela medição)

1. ~~O alvo do guard deriva do layout~~ → **`section_id` sai do match por completo.** A
   âncora é `tema_canonico` + o sinal do E5. Zero literal de seção em
   `parecer_guardrails_divida.py`.
2. O teste monta a fixture com a seção que o **modelo** emite (`SECAO_LIQUIDEZ_OBSERVADA`,
   não a constante do módulo) e o gate de não-inércia varre **os 12 valores do enum
   `SectionId`**. Contrafactual rodado: reintroduzir `p.section_id == <literal>` reprova
   **18 testes com `S1`** e **11 com `S3`** — o melhor literal possível.
3. O detector cobre par elogio × alerta sobre o mesmo assunto. ⚠️ Correção do enunciado: o
   detector nunca foi "só intra-lista" — `_pares_secao_tema_colididos` já cruzava pontos
   fortes × riscos. O que faltava era **agir** sobre o par.
4. Tripwire com a forma medida no U5: `removidos + ressalvados > 0` (não `removidos > 0` —
   ver acima). Mora em `tests/test_parecer_guardrails_divida.py`, **não** no golden mensal:
   aquele skipa sem `ANTHROPIC_API_KEY` e só roda pelo `planner-golden-monthly.yml`.

## Desenho entregue — dois braços separados por QUEM arbitra

| braço | gatilho | árbitro | desfecho |
| --- | --- | --- | --- |
| (a) | `avaliacao_liquidity == "Excessiva"` no E5 | determinístico | **remove** (o piso de 3 degrada para ressalva) |
| (b) | o parecer levanta `Liquidez` como risco | LLM sobre LLM | **ressalva, nunca remove** |

O braço (b) **não reabre a R1 refutada no r7**: aquela deletava por co-ocorrência de rótulos
do próprio LLM, e o falso-positivo que a derrubou era `"Equilíbrio presente-futuro"`. Manter
(b) em ressalva preserva a refutação — e (b) dispara justamente quando o E5 **cala**, isto é,
quando a reserva não é excessiva, que é onde o elogio tem mais chance de ser sobre outro
objeto. Medido, (b) é redundante no corpus (E5 falou em 10/10); existe para o caso em que
não fala.

Telemetria nova (`autocontradicao_fonte`, `autocontradicao_tema_ausente`) em
`config/schemas/parecer_planejador.schema.json`: sem discriminador, `removidos`/`ressalvados`
não dizem qual braço disparou — e embarcar dois braços inobserváveis repetiria a classe que
esta lane existe para consertar.

**Sem bump de `manifest_version`** — nada em `config/prompts/parecer_planejador.yaml` mudou.

## Follow-ups que esta lane NÃO fecha

- **O elogio tem dois produtores, e o guard alcança um.**
  `pontos_fortes_analyzer.py:186` emite `"Reserva de Emergência Robusta"` deterministicamente
  sob `avaliacao == "excessiva"` (por desenho — a `descricao` já carrega a ressalva do
  excedente) e renderiza em **S10**, fora do alcance de qualquer regra pós-LLM. E
  `parecer_planejador.yaml:699` projeta `$.pontos_fortes` **cru** no exec context: o título
  que o U5 flagrou é idêntico ao determinístico, isto é, o modelo ecoa o que o prompt lhe
  deu — e descarta a ressalva da descrição. Fechar isso mexe no manifesto (bump + re-eval), e
  o golden mensal do parecer não roda por default. **Lane própria.**
- **A ressalva preserva o `titulo`.** `_com_ressalva` reescreve só a `descricao`, então no
  regime em que o piso amarra (1 dos 14 runs) o título *"…Robusta"* sobrevive ao lado do
  risco *"…Excessiva — Capital Ocioso"*. O contraste visual persiste.
- **`tema_canonico` é opcional em `PontoForte`** (obrigatório em `Risco`): um elogio com o
  campo nulo escapa dos dois braços. Medido **0 em 64** pontos fortes — buraco de contrato,
  não observado. Fica **contado** (`autocontradicao_tema_ausente`) em vez de virar regra:
  torná-lo obrigatório empurraria o output para reask, e esse custo já foi pago na
  [[ADR-292]].
