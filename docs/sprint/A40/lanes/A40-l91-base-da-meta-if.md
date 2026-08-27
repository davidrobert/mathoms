---
id: A40.l91
type: lane
title: "A meta de independência é composta pela fórmula bruta e consumida nos slots líquidos"
sprint: A40
plan: PLAN-deterministic-authority
status: in_progress
priority: P0
branch_slug: a40-l91-base-da-meta-if
owner: financial-planner
depends_on: []
adrs:
  - "[[ADR-418]]"
  - "[[ADR-416]]"
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l91 — `base-da-meta-if` (PV9-16)

> **Origem:** rodada unificada **U1** 2026-08-26 ([[ADR-416]]) ·
> [[PIPELINE-REVIEWS-active]] §r9 — **PV9-16** (Alto, P0).
> Cru + síntese: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).

> **Muta E5 ⇒ zera o contador de 2 re-runs.** É a **cabeça** da janela única de rebaseline
> da onda 2: número errado com o maior peso do score, e não depende do catálogo de limiar.
> Ordem: esta → [[A40.l89]] → [[A40.l90]].

## O fato, medido (2026-08-26)

Três campos publicados fecham **ao centavo** a identidade da fórmula **bruta** documentada em
[FORMULAS.md](../../../reference/FORMULAS.md): a renda-alvo mensal, capitalizada pela taxa de
retirada, dá a meta publicada.

Mas os dois consumidores são as fórmulas **líquidas**: o gap é `meta − investível` e o
progresso é `investível ÷ meta` — as duas exigem descontar a renda passiva **observada**
(que o payload publica) antes de capitalizar.

Consequência aritmética entre campos já publicados, sem depender de nenhum balde: o
progresso sai **subdeclarado** e o gap **sobredeclarado**. E `progresso_if` carrega o
**maior peso do score**.

## O que a medição já descartou

- ~~"é defeito de balde ou de denominador amputado"~~ — **não**: a discrepância é entre
  campos já publicados e sobrevive a qualquer viés de base.
- **O que NÃO se afirma:** o valor corrigido do progresso. Se a meta for **declarada pelo
  dono** e não derivada, o número publicado é o frame da família e está certo — só que aí a
  coincidência ao centavo com a fórmula bruta precisa ser explicada.

## A pergunta que esta lane decide

**A meta é declarada ou derivada?** A medição de 1 comando está escrita no §Critério.

- **Declarada** ⇒ o defeito é de **rótulo**: os slots líquidos consomem uma meta bruta sem
  dizer. Fix = nomear a base em cada consumidor.
- **Derivada** ⇒ o defeito é de **fórmula**: a composição usa L24 e o consumo usa L26–27.
  Fix = uma base só, com delta de golden declarado.

Co-design `financial-planner` (a decisão de domínio) antes de escrever o fix.

## Escopo

1. Medir se a meta é declarada ou derivada (comando no §Critério).
2. Aplicar o fix da leitura que a medição selecionar.
3. O card de independência **nomeia o denominador** que a meta financia — hoje o relatório
   publica três custos mensais diferentes e nenhuma superfície diz qual deles a meta cobre
   (achado irmão `RR5-09`, mesmo eixo, dono `product-designer`).

## Fora de escopo

- O editorial do ano de independência (dois anos concorrentes) → [[A40.l29]].
- A honestidade do cone e o percentil → [[A40.l25]].

## O veredito da medição (2026-08-27) — **derivada**, e a pergunta era estreita

`dev/measure_if_base.py` (forma no §Como reproduzir) sobre o run da U1:

- **A meta é derivada.** Resíduo `|if_meta_brl − renda_passiva_mensal × 12 ÷ (trs/100)|` =
  **R$ 0,00** no `derived_json` do Goal, e **nenhum** dos 5 inputs a declara. Cai o ramo
  "declarada"; o defeito é do eixo da fórmula.
- **A identidade bruta fecha no E5 publicado** (resíduo R$ 0,00) e a líquida não (razão
  `if_meta ÷ meta_líquida` = **1,1307**). Os dois consumidores leem a bruta: `if_pct`
  publicado bate `investivel_efetivo ÷ meta_bruta` ao centésimo, e `if_gap` bate
  `meta_bruta − investivel_efetivo` ao centavo.

**Mas o ramo "derivada ⇒ defeito de fórmula" estava mal-especificado, e a medição mostra
por quê.** Descontar a renda passiva **observada** — a leitura literal da
[FORMULAS.md](../../../reference/FORMULAS.md) — seria **dupla-contagem**: o
`patrimonio_gerador` que produz aquela renda é **93,10%** de `investivel_efetivo`. O ganho
de 4,68 pp no progresso viria inteiro de contar o mesmo ativo duas vezes, uma no numerador
e outra reduzindo o denominador.

**O que decide não é a fórmula, é o par.** `investivel_efetivo × TRS = renda_alvo` ⟺
`investivel_efetivo = renda_alvo × 12 ÷ TRS`: a base bruta é a **certa** quando o numerador
contém todos os ativos geradores. E o numerador é governado por um toggle.

### O defeito vive no regime **default**

| Regime | cat_2 no numerador | Renda passiva fora dele | Publicado hoje |
| --- | --- | --- | --- |
| `imoveis_no_if = true` — **o run da U1** | sim | zero | **correto** |
| `imoveis_no_if = false` — **default** ([[ADR-223]]) | não | aluguéis (**75,45%** da renda passiva observada) | meta **+9,56%**; progresso **−1,74 pp**; gap **×1,119** |

Com o toggle em `false`, `investivel_efetivo` cai para `investivel_financeiro` (razão
**0,5092** no perfil medido) **e a meta não se move** — a família deixa de contar o imóvel
como patrimônio *e* segue tendo de acumular do zero a renda que ele já paga. A exclusão é
cobrada duas vezes.

É a imagem espelhada do invariante anti-dupla-contagem da [[ADR-142]], que existia só na
`description` de um campo do `goal.if.v2.schema.json` — schema **candidato**, nunca em
produção. O lado que produção exercita nunca teve enunciado nem gate.

**Ocupação do regime defeituoso:** 6 dos 7 workspaces do ambiente medido estão em `false`,
e `imoveis_no_if_set_at` é nulo em 7/7 — ninguém escolheu, é o default que caiu no DB.

### Por que a U1 não conseguiu fechar sozinha

`if_meta`, `if_pct` e `if_gap` saíam sem dizer de que base vinham, e `CV5` afirmava
`if_meta × TRS ÷ 12 == if_trs_monthly_value` sobre dois campos em que **o segundo deriva do
primeiro** — `info`/`passed` em todo run, sem poder falhar. Auditar a base exigia ler
código-fonte. É a terceira fuga que a §Consequências da [[ADR-412]] nomeia.

## Como reproduzir

A medição roda contra o DB local de dogfood e imprime **apenas resíduos e razões** — nenhum
valor monetário absoluto (§Regras críticas › dados sensíveis):

```bash
PYTHONPATH=. .venv/bin/python dev/measure_if_base.py c97b97c2-35d3-4bc3-afeb-e16f38fde658
```

## O que foi entregue

[[ADR-418]] — **uma base só**, e ela desconta exatamente a renda passiva produzida por ativo
que o numerador **não** conta:

```
if_meta = MAX(0, if_meta_bruta − renda_passiva_fora_do_investivel_mensal × 12 ÷ TRS)
```

- `compor_meta_if` é o produtor único; `if_pct`, `if_gap` e `solve_prazo_anos` leem a mesma
  base. O Monte Carlo e o `CenariosConjugeAnalyzer` herdam por já lerem `IFProjection.if_meta`.
- O termo é **ternário**: `None` = não medi (renda passiva degradada — a chave não sai),
  `0.0` = medi e não há nada fora, `>0` = desconta. Zero implícito afirmaria ausência que
  ninguém apurou; e `0` sem apuração seria campo mensalizado sem rótulo de janela
  ([[ADR-306]]) — o gate `test_e5_janela_labels` pegou.
- `goals` publica `if_meta_bruta` e `if_meta_base` (enum fechado `BaseDaMetaIF`, vocabulário
  próprio — interseção vazia com `BaseFinanceira` da [[ADR-412]]). Auditar a base passa a ser
  possível **só pelo payload**.
- `if_trs_monthly_value` segue sendo a renda-alvo **declarada** e passa a derivar
  explicitamente da bruta — mesmo valor, procedência dita.
- `CV5` deixa de ser tautologia: afirma a composição, cruzando três produtores independentes
  (o Goal, o toggle e o IRPF).

**Delta de golden: `=`.** O workspace de dogfood está em `imoveis_no_if = true`, onde o termo
é zero e a meta não se move ao centavo. O rebaseline é de **forma** — duas chaves novas em
`goals` —, não de valor. Workspaces em default com aluguel observado passam a ver progresso
maior e gap menor; é correção, e move o score (`progresso_if` tem peso 2,0 — o maior,
empatado com `taxa_poupanca_recorrente`; 25% da nota).

## Follow-up medido, fora do escopo desta lane (2026-08-27)

**`/plano` publica um segundo progresso de IF, e ele diverge do relatório em 14,91 pp
hoje** — no mesmo run, com a mesma meta. A causa é o numerador, não a base:

| Superfície | Numerador | Denominador | Progresso no run da U1 |
| --- | --- | --- | --- |
| Relatório S7 | `investivel_efetivo` | meta operacional | **35,76%** |
| `/plano` (`IFHeroCard`) | `patrimonio_liquido` | `derived.if_meta_brl` (bruta) | **50,68%** |

`patrimonio_liquido ÷ investivel_efetivo` = **1,4170** — o `/plano` conta residência e
veículos rumo à independência, que a [FORMULAS.md](../../../reference/FORMULAS.md) §Patrimônio
exclui explicitamente da métrica de `progresso_if`. Produtor:
`backend/app/application/goal/compute_if_projection.py:24`, alimentado por
`usePlanoOverview.loadLatestPatrimonioSnapshot` (que lê `reports[].patrimonio_liquido`).

**Não corrigido aqui, e a divergência é anterior a esta lane** — a [[ADR-418]] mexe no
denominador e este eixo é o numerador, com produtor em `backend/app/application/` e
contrato de API próprio (`IFGoalComputeResponse`). **Dono: `financial-planner`** (qual
patrimônio conta para IF é regra de domínio), com `senior-cto` no contrato. Condição de
retomada: qualquer lane que toque `compute_if_projection` ou o hero de `/plano`.

## Critério de aceite

- A medição do item 1 está escrita no PR, com o comando que a reproduz.
- Se o veredito for "derivada": a identidade `gap = meta_líquida − investível` fecha ao
  centavo, e o delta de golden é declarado `↑`/`↓`/`=`.
- Se for "declarada": nenhuma superfície publica gap ou progresso sem nomear a base.
- Prova por mutação: alterar a renda passiva observada move o progresso na direção certa.
- Concluído = PR mergeado em `main` com CI verde.
