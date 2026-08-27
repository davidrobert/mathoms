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
  - "[[ADR-191]]"
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
5. **`trs_target_pct = 4.0` cai, junto com a regra que o lê.**
   [`suggestion_config.py:14`](../../../../pipeline/domain/services/suggestion_config.py) e
   [`rule_trs_desalinhada`](../../../../pipeline/domain/services/suggestion_rules.py)
   (`suggestion_rules.py:87-115`, `section_id="S7"`) são o alvo **determinístico** do plano
   de ação para `carteira_trs` — a chave que o catálogo declara **órfã por decisão**
   ([[ADR-191]] §D5). Forma: **emenda datada da [[ADR-191]] §D6** no PR1, não da
   [[ADR-399]] — ver §Acolhimento abaixo.
6. **A prosa do exec context deixa de afirmar limiar que o catálogo se recusa a arbitrar.**
   [`pontos_fortes_analyzer.py:121`](../../../../pipeline/domain/services/pontos_fortes_analyzer.py)
   entrega ao modelo `"acima da referência de 30%"` como afirmação da própria E5, na seção
   `sintese` do exec context (`eviction_priority: 1` — a última a sair do corpo).

## Acolhimento do §Deferimento datado 2026-08-27 da [[A40.l89]]

> **Escrito do lado que recebe.** A disposição já estava em **dois** lugares — a
> [[ADR-399]] §Emenda 2026-08-27 (*"o alvo determinístico do plano de ação
> (`suggestion_rules.trs_target_pct`) e a prosa da E5 que entrega limiar ao modelo são
> leitores isentos pela D4 e migram para a [[A40.l90]], sob emenda própria"*) e o
> §Deferimento datado da [[A40.l89]]. Faltava o lado que executa; sem ele a lane não sabia
> que ganhou superfície.

**Por que a [[ADR-191]] e não a [[ADR-399]].** A [[ADR-399]] §D4 já **renuncia** a estes
leitores — não há isenção a estreitar por este eixo (é o §7 do ataque, que segue valendo).
Quem eles contradizem é a [[ADR-191]] §D6, cujo **Aceite** diz *"nenhuma superfície do
relatório compara a TRS efetiva com um alvo de retorno … nos dois consumidores"*.
`rule_trs_desalinhada` é o **terceiro**, com `section_id="S7"` — dentro do escopo que o
aceite declarou, fora do que ele mediu. A emenda datada corrige a contagem, não a decisão.

**O veredito de domínio (`financial-planner`): são dois conceitos com o mesmo acrônimo.**
A **regra dos 4%** (SWR, estudo Trinity) é taxa de **decumulação** sobre patrimônio
investível;
`goals.taxa_retirada_efetiva_pct` (= `PassiveIncomeResult.trs_efetiva_pct`) é **yield
observado**. Prescrever *"reduzir a taxa de retirada"* sobre um yield é conselho
**inexecutável** — a família não escolhe quanto os ativos pagam. O órfão está certo; o que
cai é a regra, junto com a constante. Precedente de forma no **mesmo arquivo**: FP-010
removeu `rule_seguros_insuficientes` **com** `seguros_renda_pj_threshold_brl`
([[ADR-161]] §Emenda 2026-08-11) — constante sem a regra que a lê é o que sobra quando se
corta pela metade.

**A linha viva hoje é FÓSSIL, e corrigir o produtor não a apaga.** A regra não dispara no
dogfood (`if_pct` 35,76 < 50; `trs` 1,74 < 4,6 = 4,0 × 1,15); *"Reduzir taxa de retirada
para 4.0% ao ano"* persiste porque a `Decision` D01 foi aceita em 2026-05-06 e
[`_top5_decisions_stmt`](../../../../backend/app/services/pipeline/pipeline_adapter.py)
(`pipeline_adapter.py:136-155`) projeta **sem revalidar** contra o run corrente. O destino
das `Decision` já aceitas **não é desta lane** — a [[A40.l89]] o endereçou a *ciclo de vida
de `Decision`*, sem lane. Consequência aceita: o PR desta lane fecha o produtor e a linha
persistida continua no relatório de quem já aceitou.

### As duas prosas não são simétricas — medido

O §Deferimento da l89 nomeia `pontos_fortes_analyzer.py:121` **e** `:158`. Medidos, só um
contradiz o catálogo:

| linha | prosa entregue | chave lida (`scoring.json::thresholds_alertas`) | veredito |
|---|---|---|---|
| `:121` | *"acima da referência de 30%"* | `pontos_fortes_taxa_poupanca_min_pct` = **30** | **contradiz** — rival de `poupanca_referencia_pct` = **25**, e o catálogo se **recusa** a arbitrar ⇒ `taxa_poupanca_recorrente` é órfã |
| `:158` | *"abaixo do teto de 20%"* | `endividamento_maximo_pct` = **20** | **número-neutro** — é a **mesma chave** que `_endividamento` do catálogo lê (`kpi_target_catalog.py:352`) |

Então o `:158` **não cai**: ele já é o catálogo por outro caminho, e removê-lo custaria
informação sem resolver contradição nenhuma. O que ele exige é o **gate** que impede a
neutralidade de se desfazer em silêncio se as duas fontes divergirem — mesmo par do §9,
onde `endividamento_alto` é neutro e `reserva_insuficiente` é 3×.

Os predicados são **estritos** (`taxa_poup > 30`, `endiv < 20`, `pontos_fortes_analyzer.py:115,140`);
`≥ 30%` / `< 20%` na redação de origem é abreviação, não o operador.

**Residual herdado, já declarado pela [[A40.l89]]:** entre o merge dela e o desta lane o
relatório tem linha **sem comparador** para taxa de poupança e, no mesmo documento, prosa
afirmando 30%. É contradição menor que a de hoje (alvo fabricado **+** prosa), e ela fecha
aqui.

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
- **`rg trs_target_pct` devolve zero ocorrências** — a constante e a regra que a lê saem
  juntas (§Escopo 5). Constante órfã reprova: é o meio-corte que a [[ADR-161]] §Emenda
  2026-08-11 já teve de emendar uma vez. O `kind` `trs_desalinhada` permanece nos tipos
  sem produtor, com o registro datado — forma de [`suggestion.py`](../../../../pipeline/domain/types/suggestion.py) (`:38` o kind, `:44-46` a razão — *"kind sem produtor é inerte, kind removido é mudança de contrato"*).
- A emenda da [[ADR-191]] §D6 traz `amended_at` + blockquote de sinal, e **reescreve o
  Aceite** de *"nos dois consumidores"* para o número que ela passa a medir. Emenda que
  corrige a decisão sem corrigir a contagem do aceite deixa o mesmo gate falso.
- **Nenhuma prosa do exec context afirma limiar de KPI órfão** — prova por mutação sobre a
  seção `sintese` renderizada, não por leitura do analyzer: trocar
  `pontos_fortes_taxa_poupanca_min_pct` faz o texto entregue ao modelo mudar hoje, e não
  deve mudar depois (§Escopo 6).
- **`:158` fica, e ganha gate de neutralidade**: se `endividamento_maximo_pct` deixar de
  ser a chave que `_endividamento` lê, vermelho. Sem isso a neutralidade medida hoje se
  desfaz em silêncio.
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
| 4 | **§Escopo 2 é inimplementável para 2 das 4 regras.** `seguro_vida` ↔ `protecao_custo_premio` (a chave chamava-se `protecao_cobertura` até a [[ADR-399]] §Emenda 2026-08-27 E2 — **nome corrigido aqui em 2026-08-27**) e `rentabilidade_nao_medida` ↔ `carteira_trs` são **órfãos por decisão de domínio** ([[ADR-387]]; [[ADR-191]] §D5): o catálogo publica `limiar=None` de propósito, e o docstring do `kpi_target_catalog` diz que pôr número ali "seria **regressão**, não melhoria". Nenhuma das duas é threshold: uma é predicado booleano de gap ([[ADR-240]] KPI F), a outra é sentinela `== "N/D"`. Não há limiar a derivar. |
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

E a prova mais curta de que o classificador não descreve a grandeza: **o mesmo número, da
mesma fonte, aparece duas vezes no mesmo golden com valores diferentes.**

| campo | valor no golden |
|---|---|
| `reserva_emergencia.meses_alvo` | `18` |
| `kpi_targets.reserva_cobertura_meses.limiar` (= `$.reserva_emergencia.meses_alvo`) | `1800` |

`meses_alvo` está em `_NON_MONETARY_EXACT`; `limiar` não. Dezoito meses e mil e
oitocentos meses no mesmo arquivo.

### §9 — a metade implementável do §Escopo 2 **não** é número-neutro

Das duas regras que têm limiar no catálogo, só uma é neutra:

| regra | limiar hoje | limiar do catálogo | efeito |
|---|---|---|---|
| `endividamento_alto` | `scoring…endividamento_maximo_pct` = **20** | `taxa_endividamento` = **20** (mesma chave) | **neutro** |
| `reserva_insuficiente` | `scoring…reserva_minima_meses` = **6** | `reserva_cobertura_meses` = **18** (`goal_declarado`) | **3×** |

A precedência da [[ADR-399]] é *alvo da família vence doutrina do produto*, então derivar
do catálogo **é** a leitura certa — mas o piso do item de reserva vai de 6 para 18 meses,
e a polaridade dele é a que [[ADR-412]] §D7 protege (*"morre a magnitude, nunca o item"*):
ele passa a disparar onde hoje cala. Um workspace com 10 meses de cobertura hoje está
conforme e passaria a emitir "Reforçar reserva de emergência".

**No dogfood não aparece** (53,3 meses ≥ 18 nas duas leituras), então a taxa de disparo
que o PR1 tem de declarar **não pode ser medida nesse workspace** — ele é conforme sob as
duas regras e não discrimina. É o mesmo ponto cego do §3, noutro eixo.

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
6. **§Escopo ganhou os itens 5 e 6 em 2026-08-27** (§Acolhimento). O item 5 traz uma
   emenda da [[ADR-191]] §D6 para o PR1 — que passa a carregar **duas** emendas datadas se
   a da [[ADR-399]] sobreviver à correção 4. Elas têm ADRs, gates e provas distintos:
   avaliar **separar em PR1a/PR1b** antes de escrever.

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
