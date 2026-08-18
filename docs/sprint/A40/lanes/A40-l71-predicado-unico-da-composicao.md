---
id: A40.l71
type: lane
title: "Predicado único da composição patrimonial: o donut e a tabela decidem o negativo explicitamente"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1511
ship_date: "2026-08-18"
priority: P1
branch_slug: a40-l71-predicado-unico-da-composicao
owner: product-designer
adrs:
  - "[[ADR-145]]"
  - "[[ADR-215]]"
depends_on: []
parallel_with:
  - "[[A40.l66]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/frontend
---

# A40.l71 — `a40-l71-predicado-unico-da-composicao`

> Item **7e** da Onda 7 do [[PLAN-deterministic-authority]] (RV6-23), aberto como
> lane do [[PLAN-report-trust]] — a casa das lanes de render. É o **enabler sem
> copy** da onda: entrega o predicado único, e a decisão de texto dos estados
> fica com o 7a ([[A40.l72]]). Nasce `open` — não depende do seam nem de janela
> de rebaseline monetário.

## Problema

A mesma composição patrimonial é filtrada por **dois predicados diferentes**, um
em cada componente, e nenhum dos dois decide o negativo — ambos o resolvem por
efeito colateral:

`frontend/src/components/report/charts/PatrimonioDoughnutChart.tsx:23-25`

```tsx
const data = rows
  .filter((r) => r.valor > 0)
  .map((r) => ({ label: r.categoria, value: r.valor }));
```

`frontend/src/components/report/cards/PatrimonioCategoriasCard.tsx:21-23`

```tsx
const rows = allRows.filter(
  (row) => !(row.categoria === "Residência" && row.valor === 0),
);
```

Sobre o payload do r6 as duas divergem **na mesma tela**: o balde com valor
negativo (a dívida que o seam roteou para o ativo — RV6-01) **desaparece do
gráfico** e **é impresso na tabela**; o zero suspeito do cônjuge (RV6-04) some do
gráfico e a tabela o imprime como zero confirmado. O leitor vê duas respostas
para uma pergunta.

Dois agravantes do predicado da tabela:

1. Ele é **acoplado à copy** — casa a categoria pela string renderizada
   `"Residência"`. Mudança de rótulo (ou i18n) desliga o filtro sem que nada
   falhe, e a exceção do [[ADR-215]] P5 (esconder "Residência R$ 0,00" para não
   confundir "zero ≠ dado ausente") deixa de valer em silêncio.
2. Ele resolve **exatamente um** caso de zero — o de residência — e trata todo o
   resto (zero de qualquer outra categoria, negativo de qualquer categoria) por
   omissão, imprimindo. Não há decisão escrita para o negativo em lugar nenhum
   dos dois componentes.

## Escopo

`visibleCompositionRows()` — **um** predicado, exportado de módulo próprio em
`frontend/src/components/report/utils/`, consumido pelos **dois** componentes.
Ele decide os 3 casos **explicitamente**, cada um com nome:

| Caso | Predicado | Donut | Tabela |
|---|---|---|---|
| negativo | `valor < 0` | omite a fatia | imprime a linha, marcada |
| zero-confirmado | `valor === 0` com cobertura | omite a fatia | imprime `0,00` |
| ausente | zero sem cobertura, ou categoria sem dado | omite a fatia | `—` + nota |

A assimetria donut×tabela é **intencional e declarada** no módulo: fatia de área
zero ou negativa não é representável num donut, mas a linha da tabela é o lugar
onde o número presta contas. O que a lane elimina não é a assimetria — é ela
existir **por acidente**, escrita duas vezes e divergente.

A exceção [[ADR-215]] P5 (residência zero) migra para dentro do predicado.

> **Corrigido na execução (2026-08-17): a chave não trafega.** Esta linha dizia
> "passa a casar pela chave de categoria ([[ADR-145]])". Medido ao implementar:
> a [[ADR-145]] declara `template_key` estável e proíbe rename, mas o payload
> transmite **só o rótulo exibido** — `patrimonio_calculator.py:455` monta
> `{"categoria": "Residência", …}`, e dois dos seis rótulos interpolam nome de
> membro (`f"Investimentos {identity.titular_nome}"`). Não há campo de chave em
> `PatrimonioCategoria` nem bridge de codegen. Fazer a chave trafegar é mudança
> de contrato do E5 — fora desta lane, e na superfície da [[A40.l5]].
>
> Entregue no lugar, com a mesma intenção (rename não desliga o filtro em
> silêncio): constante única `CATEGORIA_RESIDENCIA_LABEL` no predicado + **gate
> de paridade Py↔TS** (`dev/check_composicao_predicate.py`), que falha no commit
> se o produtor renomear. Precedente da forma: `check_probabilidade_parity.py`
> ([[A40.l25]]) e `check_chart_conclusion_parity.py` ([[ADR-122]]).

**Interim declarado:** enquanto o RV6-04 estiver aberto ([[A40.l69]]), zero sem
cobertura renderiza `—` + nota, **não** `0,00` — a distinção `zero_apurado` ×
`nao_apurado` chega no payload com a l69, e até lá o render não tem como afirmar
qual dos dois é. Quando a l69 mergear, o caso `zero-confirmado` passa a ser
alimentado pelo campo `cobertura_investimentos[]` em vez do interim.

## Enforcement

Sem enforcement novo de pipeline — é lane de render. O que a lane trava é
**estrutural**: teste que reprova se algum dos dois componentes voltar a filtrar
`composicao`/`tabela_categorias` por conta própria (o predicado é fonte única, e
duplicá-lo é a regressão que esta lane fecha).

## Critério de aceite

- **Prova por mutação:** fixture com balde negativo ⇒ hoje o donut o omite e a
  tabela o imprime sem marca; pós-fix, os dois consomem o mesmo predicado e o
  caso é **nomeado** nos dois — a linha da tabela sai marcada e a fatia sai
  omitida **pela mesma decisão**, não por dois `filter` que por acaso divergem.
  Segunda mutação: renomear a categoria `"Residência"` no fixture ⇒ o filtro do
  [[ADR-215]] P5 desliga, **e continua desligando pós-fix** — o payload não
  carrega a chave (ver a caixa de correção acima). Quem impede o rename
  silencioso é o gate de paridade Py↔TS, que quebra no commit do **produtor**;
  o teste do fixture pina essa dependência para que mudá-la seja decisão, não
  deriva.
- Teste dos 3 casos com nome, um por caso — não um teste com 3 asserts (o
  primeiro a falhar esconderia os outros dois).
- Gate de duplicação: `filter` sobre `composicao`/`tabela_categorias` fora do
  predicado reprova.
- Contraste dos estados novos (marca do negativo, nota do `—`) nos **2 temas**,
  par `-on-tint` quando o texto for sobre tint da própria cor; `NAMED_PAIRS` se o
  gate não alcançar o par.
- Baseline visual: `frontend-print-visual` é **label-gated** — rodar
  explicitamente e **inspecionar o PNG no runner Linux** antes de commitar
  baseline. Baseline commitada sem olhar já custou uma sessão neste repo.
- Specs de a11y por seção cobrindo os estados novos.

> **Medido na execução (2026-08-17): o spec de axe não é gate do texto
> acessível.** Removido o par `sr-only` do travessão do `nao_apurado`,
> `tests/a11y/accessibility.test.tsx` seguiu **verde** — célula com travessão
> não é violação séria para o axe, e quem usa leitor de tela ouviria célula
> vazia (a mesma ambiguidade "zero ≠ não medido" que a lane fecha no visual).
> Daí `tests/components/report/PatrimonioCategoriasCard.test.tsx`, que afirma o
> texto e **reprova** sob a mesma mutação. O spec de axe continua — ele cobre
> outra classe (violação estrutural) — mas não é o que protege este par.

## Fora de escopo

- **Copy** dos estados de degradação e do banner → [[A40.l72]] (7a), que é quem
  detém a decisão de texto da onda. Esta lane entrega o predicado e usa texto
  mínimo (`—` + nota curta); reescrevê-lo é lá.
- Contagem `needs_review` server-side no payload + snapshot OpenAPI — passo (1)
  da sequência da Onda 7, PR de backend, fora desta lane.
- Distinguir `zero_apurado` de `nao_apurado` **no dado** → [[A40.l69]]. Aqui é só
  o render do que o payload já diz.
- Export/PDF com contagem indisponível → resíduo da [[A40.l22]] (RV6-22).
- 5º banner: **proibido** (§Anti-decisões do plano). Estado novo reusa o
  `ReportDataQualityBanner`.

## Entregue — 2026-08-18 (#1511 · `50033dae`)

`visibleCompositionRows()` é fonte única do donut e da tabela; os 4 estados
(`apurado`/`negativo`/`zero_apurado`/`nao_apurado`) usam o vocabulário da
[[A40.l69]], e o parâmetro `cobertura` já está na assinatura para ela ligar sem
mudar shape. Gate `dev/check_composicao_predicate.py` no pre-commit.

**Duas correções de rota, medidas na execução** (detalhe nas §Escopo/§Critério
acima): a chave da [[ADR-145]] não trafega — entregue constante única + gate de
paridade Py↔TS no lugar do match por `template_key`; e o spec de axe não protege
o texto acessível — daí `PatrimonioCategoriasCard.test.tsx`.

**O gate v1 era cego, e isso é o achado reutilizável.** A primeira versão casava
`composicao` e `.filter(` na **mesma linha**, e passou verde sobre a mutação que
reintroduz o bug em duas linhas — que é a forma do código original. Trocado por
*leitor único*, com allowlist declarada de 3 leitores. Ambos os braços
re-provados por mutação depois do refactor.

**Cobertura ausente, declarada:** os fixtures de e2e/visual têm
`patrimonio.categorias` — nem `composicao` nem `tabela_categorias` — então o card
renderiza estado vazio neles e o gate visual **não** exercita estas linhas. A
lacuna de fixture é real e fica aqui em vez de virar "baseline estável".

Verificado localmente o *report render gate* que o CI cancelou na primeira
tentativa (72 passed, 2 skipped), além de pipeline 6706, frontend 1789 e backend
3532.
