---
id: A40.l82
type: lane
title: "Um default de grupo RFB decide a classe de 13% da carteira, com confiança plena e sem sinal"
sprint: A40
plan: PLAN-deterministic-authority
status: shipped
ship_pr: 1698
ship_date: "2026-08-25"
priority: P0
branch_slug: a40-l82-tipo-default-decide-classe
adrs:
  - "[[ADR-400]]"
  - "[[ADR-410]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l82 — `tipo` default decide classe (RV8-01)

> **Origem: [[A40.l77]] §RV8-01.** Aquela lane **registra** a regressão; esta a
> **conserta**. A l77 está `shipped` e não reabre — brigar com o gate
> `lane-transition` que a [[A40.l59]] shipou destruiria o valor de auditoria do
> `shipped` (mesma doutrina do `_HISTORY`: snapshot datado que alguém atualiza
> deixa de ser evidência).

> **Não vai para a J5.** A J5 é a janela de rebaseline do denominador (DE-7, DE-8,
> D4-resto, D5 da [[ADR-410]]). Esta contenção **não exige rebaseline** — e os dois
> têm modos de falha **opostos**: o DE-7 *soma* valor a um denominador, então o
> total move por desenho; isto *redistribui* entre baldes, e `Σ preservado` é o
> critério de aceite mais forte do braço de classificação. Rodar junto queima o
> instrumento.

## Problema

O r8 (run `d0f6260a`, 2026-08-24) abriu como achado **nº 1, Crítico P0**:
**11 de 61 posições migram** de `Fundos` para `Renda Fixa` — **R$ 174.636,71,
13,1%** sobre a carteira **pós-resolver** (ano-base por membro, Σ 1.335.354,95) —
com `autoridade: "keyword"` (confiança plena), zero
`review_reason`, `nao_classificado_pct` parado e nenhum golden quebrado.

| | sem `tipo` | com `tipo` (produção hoje) |
| --- | --- | --- |
| Fundos | 12 | **2** |
| Renda Fixa | 21 | **32** |

> **Duas bases, ambas certas.** A tabela 61×3 do #1698 mede os **itens crus**
> (maior ano por item, Σ 1.946.473,20) e dá **R$ 323.936,08 · 16,6%**. Esta lane
> mede **pós-resolver** (ano-base por membro, Σ 1.335.354,95) e dá **R$ 174.636,71
> · 13,1%**. Quem cruzar os dois documentos vê dois percentuais para "a mesma
> coisa" — são recortes diferentes do mesmo fato, não divergência.

### Os itens são fundos de ações rotulados renda fixa

```
WESTERN ASSET FIA BDR NIVEL I       ← FIA = Fundo de Investimento em Ações
ALASKA BLACK INSTITUCIONAL FIA BDR  ← FIA
CONSTELLATION INSTITUCIONAL         ← fundo de ações
ALASKA BLACK FIC FIA - BDR          ← FIC FIA
SAFARI 30 FIC FIM II                ← FIM = multimercado
```

A `descricao` diz `FIA`/`FIM` e está **certa**; o `tipo` diz `renda_fixa` e está
**errado**. `_classify_investimento`
([`consolidate_baseline.py:711`](../../../../scripts/consolidate_baseline.py))
emite `return "renda_fixa"` como **default do grupo 04 da RFB**, indistinguível
de valor derivado de evidência — mesma família do `return "investimento"` que a
[[A40.l77]] já tratou como sentinela, e cuja generalização ninguém viu.

### O que a l77 mudou não foi o campo — foi quem o lê

`"tipo": inv.get("tipo", "")` está em `patrimonio_resolvers` desde `f2ea6dcd`
(A6d.3.3, [[ADR-100]]), meses antes. O #1677 flipou os consumidores do
`E5MemberResolver` — que **descartava** `tipo` — para o resolver canônico, que
sempre o emitiu. A célula do r8 diz que a linha *passou a incluir* `tipo`;
está errada e enganaria quem der `git blame`.

### O defeito que importa não são os 11 itens

**13% da carteira mudou de classe e todo instrumento do repo disse verde**:
golden (não tem `investimentos_consolidados`), snapshot (domicílio de 1 membro),
os invariantes de conservação (cegos por construção — valor migra *entre*
baldes), `nao_classificado_pct` (parado, porque a classe existe) e `autoridade`
(que reportou `keyword` para uma presunção). Mesmo o fix perfeito, sem gate,
deixa a próxima migração sem sinal.

## Decisão (co-design de 2026-08-25)

`financial-planner` + `data-engineer` em paralelo; divergiram na contenção e o
`senior-cto` fechou.

**Convergiram:** subjacente > veículo — unânime nos padrões consagrados de
planejamento patrimonial brasileiro, e por três razões independentes:
comparabilidade de risco entre classes, renda passiva ser propriedade do
subjacente e não do veículo, e o veto sobre o que entra na reserva. As 5 marcas
de gestora são dívida
a cortar; `PRESUNTIVO` precisa ficar **abaixo** de `KEYWORD`; proveniência vai em
**campo companheiro**, nunca mudando o valor de `tipo` (que entra no hash de
identidade — `_identity_key = (tipo, instituicao, descricao)` → `investment_id`,
publicado como `locator` durável).

**Arbitrado:**

1. **Reverter.** Não pelo placar 11×1, pela **assimetria de visibilidade**: 174k
   invisível-e-invertido contra 25k **declarado** (`SEM_MATCH` alimenta
   `nao_classificado_pct` e move o dial da supressão) e conservador na direção.
   É a tese "declarado > mudo" da própria [[ADR-400]].
2. **Forma:** apagar o campo da entry, **não** parar de passá-lo no call-site —
   senão `top_ativos` publica `nome="Renda fixa (Btgpactual)"` **dentro do balde
   Fundos**, contradição visível que o pré-l77 não tinha.
3. **As 5 marcas saem no mesmo PR** — são a **mesma decisão** ("sinal que parece
   evidência e não é"). `CONSTELLATION INSTITUCIONAL` cair em `SEM_MATCH` é o
   desfecho **correto**: o produto não sabe o que é aquela string e deve dizê-lo.
   Escopo estrito: só as 5 de `Fundos`; `picpay`/`nubank` em `Caixa` ficam,
   porque não foram medidas.
4. **Atribuibilidade por tabela, não por PR extra**: `com tipo` / `sem tipo` /
   `sem tipo e sem marca` sobre os mesmos 61 itens, em cents.

### Por que a alternativa foi recusada

O `financial-planner` propunha não reverter e reordenar `EVALUATION_ORDER`
(`Fundos` antes de `Renda Fixa`). O `senior-cto` apontou **contradição interna**:
isso é **fix por coincidência** — faz o input errado produzir a resposta certa
*neste corpus*, que é exatamente a "resposta acidentalmente certa por mecanismo
errado" que ele condena em outro ponto. E inverteria a racionalidade escrita no
comentário da `EVALUATION_ORDER`, mandando um "Fundo de Investimento em Renda
Fixa" legítimo para `Fundos` — errado sob subjacente > veículo.

## Escopo

1. **Contenção** — os dois edits, um PR, com a tabela 61×3 no corpo.
2. **Gate estrutural** — o caminho de classificação da E5 não lê `tipo`,
   falseável por mutação **nas duas direções**, com **expiração datada**
   apontando para o degrau 1.
3. **Emenda datada à [[ADR-400]]** — nomeando a causa, não o sintoma.

## Critério de aceite

- Tabela **61×3** em cents no corpo do PR, com o custo declarado — não omitido.
- `Σ` dos baldes **preservado** entre as três colunas. É o invariante mais forte
  deste braço: a contenção redistribui, nunca soma nem subtrai.
- Gate **estrutural** com chamador em CI, provado por **mutação executada nas
  duas direções** — re-injetar `tipo` deixa vermelho, remover deixa verde.
- A emenda à [[ADR-400]] diz que **presunção derivada de default ≠ presunção
  derivada de fato**, e que o degrau 1 **não pode ser construído** enquanto o
  produtor não separar os dois. `PRESUNTIVO` abaixo de `KEYWORD` é consequência,
  não a decisão.
- Sem rebaseline de golden ou snapshot — e o PR **diz que isso é falta de
  cobertura, não estabilidade**, citando a ⚠️ que a [[A40.l77]] já escreveu.

## Fora de escopo

- **`classify_asset_outcome` deixar de aceitar `tipo: str` posicional** (value
  object tipado, padrão [[ADR-089]]/[[ADR-097]] D2) — **dono: `data-engineer`**,
  janela J5. É a mudança que torna a classe irrepresentável em vez de corrigida
  uma vez, mas são 6 call-sites de produção e superfície de teste grande; sob
  contenção P0 a razão risco/benefício é proibitiva, e a l77 já errou uma
  estimativa dessas por 28×. Amarrado à emenda da [[ADR-400]] como
  **pré-condição do degrau 1**.
- **RV8-19 — identidade de posição é hash de campo de extração** — **dono:
  `data-engineer`**, janela **própria**, nem na J5 nem colada aqui: muda o hash e
  invalida locators publicados. Precede-o uma medição: taxa de sobrevivência de
  `investment_id` run-a-run sobre o mesmo corpus.
- **`tipo_proveniencia`** (campo companheiro, enum de quatro derivado
  mecanicamente de qual `return` de `_classify_investimento` disparou) —
  **dono: `data-engineer`**, aditivo, delta zero em cents, ~~sem janela~~ —
  **janela dada no fechamento** (ver o bullet retratado abaixo e [[ADR-400]]
  §"A contenção tem custo medido"): o campo passa a ter custo corrente de
  R$ 25.337,34 em KPI publicado.
- ~~**Reserva de emergência** — o RV8-01 **não** a contamina hoje.~~
  **Retratado no fechamento (2026-08-25): a conclusão estava invertida.** As duas
  premissas eram verdadeiras — o titular usa mesmo `_positions_for_member` (medido:
  `726.500,16 [posicoes]`, **idêntico** nos três cenários) e o item da cônjuge é
  mesmo uma `poupanca` genuinamente líquida. Mas é **por ser líquida** que tirá-la
  custa: sem `tipo` ela cai em `Outros`, sai de `_LIQUID_BUCKETS` e a reserva da
  cônjuge **cai R$ 25.337,34** (110.130,67 → 84.793,33, `fonte=irpf`). O movimento é
  **todo do `tipo`** — o corte das cinco marcas é **zero** na reserva, porque
  `Fundos` e `Outros` são ambos ilíquidos.
  **Por que importa:** `poupanca` sai do ramo `if "poupanca" in desc_lower` —
  **evidência**, não default de grupo — e a `descricao` armazenada (104 chars) *não*
  contém a palavra. `tipo` era o **único portador**. A contenção descartou o campo em
  bloco e levou junto o que era fato: a reserva agora **subavalia** com sinal e
  magnitude conhecidos. Não reabre a decisão (25k declarado < 174k mudo; banda
  "Excessiva" mantida, 43,9 → 42,8 meses), mas **dá janela** ao
  `tipo_proveniencia` — ver [[ADR-400]] §"A contenção tem custo medido".
- **RV8-04 — R$ 642.744,79 não-atribuídos** entrando na reserva do titular por
  `not membro → titular`: defeito **anterior** a esta lane e 25× maior que o de cima.
  **Dono: `data-engineer`**, janela própria.

## Entregue

`shipped` em 2026-08-25 via **#1698** (`2fd2e60e`), CI verde. Os três itens do
§Escopo saíram no mesmo PR:

| item | o quê |
|---|---|
| 1. Contenção | `tipo` sai da entry em `patrimonio_resolvers`; as 5 marcas saem de `_DEFAULT_KEYWORDS` **e** de `config/scoring.json` (só do default seria **no-op** — `merge_asset_keywords` deixa o scoring sobrescrever a classe inteira) |
| 2. Gate | `tests/unit/pipeline/test_classe_de_ativo_nao_le_tipo.py` — comportamental, parametrizado sobre as keywords **de produção**, com auto-falseabilidade e afirmação de direção |
| 3. Emenda | [[ADR-400]] §2026-08-25 — presunção derivada de *default* ≠ derivada de *fato*; o degrau 1 fica bloqueado até o produtor separar os dois |

**Σ preservado nas três colunas** (194.647.320 cents) — a contenção redistribui,
nunca soma. Mutação executada nas duas direções: re-injetar `tipo` deixa **7
vermelhos**; o campo voltar como `tipo_rfb` deixa **4 vermelhos** e o teste
*estrutural* **verde** — é por isso que ele ficou como diagnóstico nomeado, e não
como o gate.

Um quarto edit entrou por medição, não por desenho: o corte cruza
`INCERTEZA_APORTE_MIN_PCT` (1,18% → 3,08%) e **ativaria** um defeito latente do
`alocacao_narrator`, que publicaria *"Maior desvio: 30,3 pp. Carteira aderente ao
alvo."* — duas frases contraditórias. `next_aporte_classe` passa a `None` com
`motivo_supressao`.

⚠️ **Golden e snapshot intactos é falta de cobertura, não estabilidade** — o golden
não tem `investimentos_consolidados` e o dogfood é domicílio de um membro. É a mesma
cegueira que deixou a regressão entrar pela [[A40.l77]].
