---
id: A40.l90
type: lane
title: "A superfície determinística de risco tem quatro regras hard-coded e não lê o catálogo canônico de limiar"
sprint: A40
plan: PLAN-deterministic-authority
status: blocked
priority: P0
branch_slug: a40-l90-limiar-de-risco-le-o-catalogo
owner: financial-planner
depends_on:
  - "[[A40.l89]]"
adrs:
  - "[[ADR-399]]"
  - "[[ADR-416]]"
tags:
  - type/lane
  - sprint/a40
  - status/blocked
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l90 — `limiar-de-risco-le-o-catalogo` (PV9-06)

> **Origem:** rodada unificada **U1** 2026-08-26 ([[ADR-416]]) ·
> [[PIPELINE-REVIEWS-active]] §r9 — **PV9-06** (Alto, P0).
> Cru + síntese: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).

> **Muta E5 ⇒ zera o contador de 2 re-runs.** Serializada atrás da [[A40.l89]]; a ordem é
> forçada, não preferência — ver §Fora de escopo lá.

## O fato, medido (2026-08-26)

[`PontosUrgentesAnalyzer.analyze`](../../../../pipeline/domain/services/pontos_urgentes_analyzer.py)
é a superfície determinística de risco e tem **quatro regras hard-coded**: reserva abaixo do
mínimo, endividamento acima do máximo, gap de seguro de vida, rentabilidade não apurada.
**Nenhuma consulta `kpi_targets`.**

Concentração imobiliária, desvio de alocação-alvo e exposição cambial **não têm regra**. No
run da rodada, três limiares com procedência `limiar_canonico` estavam rompidos e a
superfície publicou **um** ponto urgente — o de proteção, que é uma das quatro regras fixas.

E o catálogo canônico ([[ADR-399]], declarado *"leitor único de cada limiar"*) é **órfão**:
existe no tipo gerado e em **nenhum** componente. O limiar existe, é versionado, tem
procedência declarada — e não chega a superfície nenhuma.

## O que a medição já descartou

- ~~"`alertas` é a superfície determinística de risco e está vazia com três limiares
  rompidos"~~ — **refutado pelo cético**: [`build_alertas`](../../../../pipeline/domain/services/e5_serialization.py)
  tem três condições e **nunca** carregou limiar de KPI; o docstring declara que lista vazia
  é *empty state honesto*, por curadoria da [[A40.l7]]. **Alvo errado.** O alvo certo é
  `pontos_urgentes`.
- ~~"o tier esconde o parecer do Free, então o Free não vê risco nenhum"~~ — **refutado**: o
  Free recebe diagnóstico + 3 pontos fortes + **1 risco** (o de severidade máxima).

## A pergunta que esta lane decide

A [[ADR-399]] §D4 **isenta explicitamente** os leitores pré-existentes (*"os leitores
pré-existentes citados em D4 permanecem"*). Estender o leitor único à superfície de risco é
mudança de escopo de ADR `Decidido`.

**Duas leituras:**

| | Leitura | Consequência |
|---|---|---|
| **A** | As regras de risco passam a derivar do catálogo; a isenção da D4 é estreitada | Um limiar, um lugar. Muda o que dispara ponto urgente ⇒ delta de golden |
| **B** | A isenção permanece e as regras ganham as três dimensões faltantes hard-coded | Não mexe na ADR, e reintroduz o problema que a D4 existe para resolver |

**Defendo A**, e a forma é **emenda datada à [[ADR-399]] no PR1**, com a taxa de disparo
medida sobre os runs de referência **declarada antes do flip** (doutrina WARN-first de
[[ADR-357]]/[[ADR-358]]). Sem a emenda, a lane viola por omissão uma decisão vigente.

## Escopo

1. **PR1 — emenda datada da [[ADR-399]]**, estreitando a isenção da D4 à superfície de risco,
   com a taxa de disparo medida e escrita.
2. As quatro regras passam a derivar limiar do catálogo.
3. As três dimensões sem regra (concentração imobiliária, desvio de alocação, exposição
   cambial) ganham regra que **lê** o catálogo, não que fixa número.
4. Invariante: `count(kpi_targets rompidos) > 0 ⟹ len(pontos_urgentes) > 0`. Falha hoje.

## Fora de escopo

- O alvo republicado pelo parecer → [[A40.l89]], que vai na frente.
- O denominador de cada limiar (que base cada número mede) → [[A40.l80]], entregue, com
  resíduo declarado.

## Critério de aceite

- O invariante do item 4 é teste e falha por mutação: romper um limiar canônico sem emitir
  ponto urgente ⇒ vermelho.
- A emenda da [[ADR-399]] traz `amended_at` e blockquote de sinal (gate
  `check_adr_amendment_signal`).
- Delta de golden declarado; a taxa de disparo pós-flip bate com a medida no PR1.
- Concluído = PR mergeado em `main` com CI verde.

## Ataque medido (2026-08-27)

> Docs-only, sobre `main` em `4f5e238b`. **Nenhum código tocado.** Estado de partida:
> **64 testes verdes** (`test_kpi_target_catalog` + `test_pontos_urgentes_analyzer` +
> `test_golden_diff` = 59; `test_report_view_model_snapshot` = 5). Nada aqui é "está
> quebrado": é "está verde, o diagnóstico da lane procede, e o **instrumento** que ela
> propõe não pega o defeito que ela descreve".

O §O fato **reproduz**. Medido no `dogfood_view_model.json` — fixture independente do run
da rodada — os limiares rompidos são exatamente **três, todos `limiar_canonico`**:

| kpi | procedência | observado | limiar | op | veredito |
|---|---|---|---|---|---|
| `concentracao_imobiliaria` | `limiar_canonico` | 82,19% | 50% | `<` | **ROMPIDO** |
| `exposicao_cambial` | `limiar_canonico` | 0% | 10% | `>=` | **ROMPIDO** |
| `taxa_endividamento` | `limiar_canonico` | 20,55% | 20% | `<=` | **ROMPIDO** |
| `despesas_nao_categorizadas` | `limiar_canonico` | 0% | 10% | `<` | conforme |
| `reserva_cobertura_meses` | `goal_declarado` | 53,3 m | 18 m | `>=` | conforme |

E o catálogo é órfão de **tudo**, não só de componente: `rg kpi_targets` devolve **um
produtor** (`analyze_finances.py:1954`) e **zero leitores** — nem parecer, nem backend,
nem componente React.

### Os oito achados

| § | achado |
| --- | --- |
| 1 | **O invariante do §Escopo 4 não falha hoje — ele passa com o defeito inteiro presente.** No snapshot: 3 limiares canônicos rompidos, `pontos_urgentes` publica 2 itens ⇒ `count>0 ⟹ len>0` é **`True`**. A lane afirma "Falha hoje". Não falha. |
| 2 | **A mutação que o §Critério 1 exige que fique vermelha fica verde.** Rodado o produtor real com concentração rompida (82,19% vs 50%) e todo o resto conforme: `pontos_urgentes = ['rentabilidade_nao_medida']`, `len=1` ⇒ invariante **verde**. O §Escopo 4 é uma implicação **existencial**; o §Critério 1 descreve uma implicação **por chave**. Os dois textos não são o mesmo predicado. |
| 3 | **E no workspace de referência o invariante é infalsificável.** Ele só discrimina quando as quatro regras fixas estão *todas* caladas — o que exige `rentabilidade_pct != "N/D"`. No dogfood, `ratios.rentabilidade_pct == "N/D"`, então `rentabilidade_nao_medida` dispara sempre e o consequente é satisfeito por uma regra que não compara limiar nenhum. |
| 4 | **§Escopo 2 é inimplementável para 2 das 4 regras.** `seguro_vida` ↔ `protecao_cobertura` e `rentabilidade_nao_medida` ↔ `carteira_trs` são **órfãos por decisão de domínio** ([[ADR-387]]; [[ADR-191]] §D5): o catálogo publica `limiar=None` de propósito, e o docstring do `kpi_target_catalog` diz que pôr número ali "seria **regressão**, não melhoria". Nenhuma das duas é threshold: uma é predicado booleano de gap ([[ADR-240]] KPI F), a outra é sentinela `== "N/D"`. Não há limiar a derivar. |
| 5 | **São quatro dimensões sem regra, não três.** O §Escopo 3 lista concentração, alocação e cambial; falta `despesas_nao_categorizadas` (`limiar_canonico`, 10%, `<`, ref `NAO_IDENTIFICADO_PARCIAL_PCT`). Ela não aparece porque a enumeração foi feita a partir do que estava **rompido** no run, não a partir do **catálogo** — e ela estava conforme. |
| 6 | **A citação da [[ADR-399]] é a redação aposentada.** A lane cita a ADR como declarada *"leitor único de cada limiar"*. A linha 115 da própria ADR diz: *"Redação anterior dizia 'leitor único de cada constante', o que a medição refuta"*. O D4 vigente é **Leitor único do limiar _na rota do `target` publicado_**, e o parágrafo seguinte abre com **"O escopo é essa rota, não o repo."** |
| 7 | **Não há isenção a estreitar, logo não há violação por omissão.** O D4 diz que os leitores pré-existentes *"permanecem — não foram unificados e **não estão no escopo desta ADR**"*. Isso é **renúncia de escopo**, não proibição. A [[ADR-399]] não tem `amended_at`, e o §Estado de implementação (2026-08-21) se declara *"Registro de fato, **não** emenda"*. A frase da lane — "sem a emenda, a lane viola por omissão uma decisão vigente" — é falsa. |
| 8 | **`kpi_targets[].limiar` é classificado como DINHEIRO, e o golden o publica ×100.** Medido com o instrumento do próprio gate (`_monetary_paths` do `test_report_view_model_snapshot`): os **5** limiares não-nulos são certificados monetários. 50% → `5000`, 20% → `2000`, 18 meses → `1800`, 10% → `1000`. |

### §8 em detalhe — por que sufixo não conserta

`is_monetary` chaveia no **leaf** (`limiar`); a unidade vive no campo **irmão**
`unidade` (`pct`, `meses`, `pct_aa`). Nenhuma regra de sufixo alcança isso — e sufixo
foi exatamente a forma que a [[A40.l80]] escolheu ao instalar `_versao`/`_version`
(*"Sufixo, e não entrada exata, porque … fechar por instância deixaria o próximo campo
de versão nascer com o mesmo bug"*). Este é o próximo campo, e ele nasceu com o bug.

Consequência **para esta lane**: `check_manifest` só exige entrada de manifesto para
delta **monetário**. Então o §Critério "delta de golden declarado" será produzido por um
instrumento que mede errado o campo central da lane — `diff_golden` sobre 50%→45% devolve
`delta_cents=-500`, e sobre 18→12 meses devolve `delta_cents=-600`. O registro permanente
do rebaseline escreve "50% → 45%" como **R$ 50,00 → R$ 45,00**.

E o mesmo classificador trata duas razões **irmãs** de formas opostas no snapshot:

| campo | tipo no golden | valor |
|---|---|---|
| `ratios.concentracao_imobiliaria` | `int` (cents) | `8219` |
| `ratios.taxa_endividamento_pct` | `str` | `"20.550000"` |

Mesmo bloco, mesma unidade; a diferença é o sufixo `_pct` no nome. E
`concentracao_imobiliaria` é justamente a primeira dimensão do §Escopo 3 — o número que
esta lane vai mover.

### O que se confirma da lane

- A refutação já registrada de `build_alertas` **procede**: três condições
  (`rentabilidade_pct == "N/D"`, TRS suspeita, warnings de classificação), nenhuma
  carrega limiar de KPI. O alvo `pontos_urgentes` é o certo.
- "Nenhuma consulta `kpi_targets`" em `PontosUrgentesAnalyzer` **procede**.
- A **Leitura A** segue sendo a recomendação certa — o que cai é a justificativa
  *procedimental* (§7), não a decisão de produto.

### Correções que a lane precisa antes de executar

1. **O invariante vira por-chave**: para todo `k` em `kpi_targets` com limiar não-nulo e rompido, existe ponto urgente cujo `code` mapeia `k`. A forma existencial não discrimina (§1–§3).
2. **§Escopo 2 se restringe às 2 regras que têm limiar** (`reserva_insuficiente`, `endividamento_alto`); as outras duas ganham o registro de que o catálogo as declara órfãs por decisão (§4). Note que `endividamento_alto` já lê `scoring.json::thresholds_alertas.endividamento_maximo_pct` — a **mesma** chave que `_endividamento` do catálogo usa —, então derivar do catálogo ali é **número-neutro**.
3. **§Escopo 3 passa de três para quatro dimensões** (§5).
4. **PR1 deixa de se justificar como "emenda que estreita isenção"** (§6–§7). Se a emenda for feita, o texto tem de descrever o que o D4 realmente diz.
5. **§8 precede o §Critério "delta de golden declarado"** — ou o delta será declarado por um instrumento que lê o campo da lane como dinheiro.

### Encaminhamento

- §1–§5 são **escopo desta lane** (`blocked`), a corrigir no próprio arquivo antes do PR1.
- §6–§7 tocam a [[ADR-399]], cujo §Estado de implementação e o **§Deferimento D3
  (2026-08-21)** em [[PIPELINE-REVIEWS-active]] já nomeiam donos vivos: `prompt-engineer`
  + `data-engineer`. A faltante **(c)** desse deferimento (`kpi_targets` publicado no
  payload E5) **já foi entregue** (#1591, `472a7c48`); (a), (b) e (d) são a
  [[A40.l89]] (`open`), que vai na frente desta.
- §8 **não** é desta lane nem da [[A40.l89]]: é a classe de `is_monetary` fechada pela
  [[A40.l80]] (`shipped`) com sufixo, e o campo novo não é endereçável por sufixo.
  Precisa de dono próprio — o remédio provável é o classificador ler `unidade` quando o
  irmão existir, o que é decisão de contrato, não remendo de lista.
- **Condição de retomada do §Deferimento D3 medida hoje: satisfeita.** `gh pr list
  --state open` devolve **zero** PRs — nenhum rebaseline de golden em voo.
