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

> **Itens 1-4 reescritos em 2026-08-27** — a redação anterior era inexecutável em três
> pontos e falsa num quarto. O texto original está preservado em §Correção datada
> §C-5; o porquê de cada mudança, em §Ataque medido §1-§5.

1. **PR1 — ADR nova `Proposto`** (não emenda da [[ADR-399]]): a superfície determinística
   de risco deriva gatilho de **doutrina**, nunca de alvo declarado; aresta `kpi_key` em
   `PontoUrgenteItem`; gate de cobertura do vocabulário. A [[ADR-399]] §D4 **renuncia**
   escopo em vez de proibir (§7 do ataque, adotado pela §Emenda 2026-08-27 da própria
   ADR-399), então não há isenção a estreitar — e emendá-la para "estreitar uma isenção
   que ela não deu" poria descrição falsa no registro permanente. **O ID não é alocado
   aqui**; quem executar aloca na escrita (`ls docs/adr/ | tail`).
2. **Uma regra deriva do catálogo, não quatro:** `endividamento_alto`, que é
   **número-neutro** (já lê `scoring.json::thresholds_alertas.endividamento_maximo_pct`,
   a mesma chave que `_endividamento` usa). As outras três **não têm limiar a derivar**:
   `seguro_vida` e `rentabilidade_nao_medida` mapeiam órfãos por decisão de domínio
   ([[ADR-387]]; [[ADR-191]] §D5) e nem sequer são threshold (predicado booleano de gap e
   sentinela `== "N/D"`); e `reserva_insuficiente` vai para §Deferimento (abaixo). As duas
   órfãs ganham **registro** da decisão — docstring e `motivo` na copy, não número.
3. **As dimensões sem regra derivam de uma regra de enumeração, não de um número em
   prosa:** `METRICA_KEYS` menos as chaves com regra, menos as órfãs por decisão. Hoje dá
   **quatro** (a redação anterior dizia três e omitia `despesas_nao_categorizadas`), mas o
   número muda quando o catálogo mudar — e mudou: `METRICA_KEYS` foi de 10 para 13 chaves
   entre 26 e 27/08.
   **Elegibilidade voltou a ser `limiar` não-nulo — o produtor absorveu a cobertura
   (atualizado 2026-08-28).** O #1779 (`4fbfb91b`) entregou o achado roteado à
   [[A40.l89]]: `exposicao_cambial` saiu da tabela estática `_CANONICOS` e virou
   [`_exposicao_cambial(e5)`](../../../../pipeline/domain/services/kpi_target_catalog.py),
   que devolve **órfão com motivo** quando `tier == "indeterminado"` **ou** qualquer
   componente tem `cobertura != "apurado"`. Medido no golden depois do merge:
   `limiar: null`, `procedencia: null`, `motivo: "exposição cambial sem cobertura
   apurada"`.
   Consequência para esta lane: o predicado composto que eu tinha escrito (`limiar`
   não-nulo **e** cobertura apurada) **colapsa** — a cobertura passou a ser condição de
   existência do limiar, no produtor, que é onde devia estar. A regra desta lane lê
   `limiar is not None` e pronto. `exposicao_cambial` segue inelegível **hoje**, mas por
   ser órfã, não por falta de qualificador; volta a ser elegível sozinha no dia em que a
   cobertura for apurada, sem esta lane mudar nada.
   **Aberto e é desta lane: `_alocacao_renda_fixa` publica `operador="<="`** — afirma que
   ter **menos** renda fixa que o alvo é conforme, o que é falso nas três metodologias e
   erra na direção que machuca (família sub-protegida em drawdown). Está **mascarado**
   porque o `observado_path` carrega o predicado `[classe=renda_fixa]` e o `_JSONPATH_RE`
   do verificador não casa `=`. **Consertar o path sem consertar o operador ativa um
   comparador doutrinariamente errado com o selo do produto** — se o PR desta lane
   publicar `rf_atual_pct` em ponto fixo, os dois vão juntos. Origem: painel de fecho da
   [[A40.l89]] (2026-08-28).
4. **Invariante por chave, sobre o registro de gatilho — não sobre `kpi_targets[]`:** para
   todo limiar de doutrina que emite item, rompê-lo sem emitir o item correspondente ⇒
   vermelho. **Não** chaveia em `procedencia == "limiar_canonico"`: esse rótulo já está
   comprovadamente errado uma vez (`reserva_cobertura_meses` carimbada `goal_declarado`
   sobre número de `scoring.json`), e consertá-lo quebraria o invariante. A forma
   existencial anterior (`count(rompidos) > 0 ⟹ len(pontos_urgentes) > 0`) **não falha
   hoje** — passa com o defeito inteiro presente (§1-§3 do ataque).
   O invariante lê o **artefato E5**, nunca o snapshot do view-model: com a escala mista
   do §8, `taxa_endividamento` sai falso-conforme e `reserva_cobertura_meses` sai
   falso-rompido.
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

**A linha viva hoje é FÓSSIL, e corrigir o produtor não a apaga.** A regra não dispara —
**re-medido em 2026-08-27 no closeout**, rodando `rule_trs_desalinhada` sobre
`backend/tests/snapshots/dogfood_view_model.json` (a mesma fixture do §Ataque: `8219` e
`20.550000` reproduzem): retorno **`None`**, pela **primeira** guarda
(`goals.taxa_retirada_efetiva_pct` **ausente** no payload), não pelo limiar. O par
`if_pct` 35,76 / `trs` 1,74 herdado do §Deferimento da [[A40.l89]] **não é desta fixture** —
aqui `goals.if_pct` = **13,0** e `passive_income.trs_efetiva_pct` = **0,0**; aquele par vem
do run da U1 (`storage/<uuid>/`, off-git), outro estado de workspace. O limiar de disparo
**é** 4,6 (= 4,0 × 1,15, conferido no `SuggestionGeneratorConfig`) — o que estava errado era
a *variável*, não a aritmética, e a conclusão sobrevive por margem maior: falha na guarda
anterior. *"Reduzir taxa de retirada
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

A própria [[ADR-399]] §D4 corrobora a assimetria ao enumerar seus isentos: ela nomeia
*"`pontos_fortes_analyzer.py:66`"* — o leitor de `endividamento_maximo_pct`, que alimenta a
`:158` — e **não** nomeia a linha `:65` (`pontos_fortes_taxa_poupanca_min_pct`), que alimenta
a `:121`. A lista de isenção da D4 já separava as duas; ninguém tinha lido a lista.

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

## Deferimento datado 2026-08-27 — `reserva_insuficiente`

**Dono:** `financial-planner`. **Condição de retomada:** o merge do hotfix de estampagem
da [[A40.l89]] (branch `agent/a40-l89-hotfix-estampagem/20260827-1636`), que corrige a
procedência de `reserva_cobertura_meses` para `limiar_canonico`.

Sai do §Escopo 2 porque é **inexecutável hoje**, não porque é caro. O catálogo publica
`meses_alvo` com `procedencia: "goal_declarado"`, e o número vem de
`scoring.json::reserva_emergencia._base_calculo.meses_alvo_por_perfil_renda`, chaveado por
`_perfil_por_pct` sobre a renda **observada** — não há leitor de
`Goal(RESERVA_EMERGENCIA)` em `pipeline/`. Derivar dela hoje é herdar um carimbo falso:
doutrina usando o crachá da família, e a precedência da [[ADR-399]] §D2 passaria a operar
sobre isso na direção que **absolve** a família da própria meta.

> **Não é a forma da RV2-24** (correção da sessão da [[A40.l89]], 2026-08-27, aceita).
> Em `taxa_poupanca_recorrente` as duas chaves dizem "referência" e podem disparar no
> mesmo relatório — definições **rivais** do mesmo limiar, e por isso o resolver se recusa
> a arbitrar. Aqui não há rivalidade: `reserva_minima_meses` (6) é **piso de alerta**
> (`pontos_urgentes_analyzer.py:251`) e `meses_alvo` (12/18) é **alvo por perfil de
> risco** — papéis distintos, ambos legítimos. O defeito é a **procedência mentida**, não
> a divergência de fontes. Isso reforça o gatilho ficar em 6: não há o que arbitrar.

**Aberto, dono `financial-planner`:** `_perfil_por_pct` nunca retorna `clt_estavel`, então
o ramo de 6 meses do *alvo* é inalcançável e o piso efetivo dele é 12. Se 6 deve ser
alcançável é decisão de domínio — o remédio é contagem de fontes de renda, que o fluxo v1
não tem.

E quando for retomada, o gatilho **não** se move: a [[ADR-399]] §D2 fecha com *"publica-se
o declarado como `target` e **o limiar vira `risco`**"* — doutrina vai para o canal risco,
que é esta superfície. A [[ADR-367]] (`Proposto`) já decidiu no título: *"o alvo da reserva
gradua **sem mover o gatilho**"*. O alvo gradua `prioridade`/`prazo`; o piso decide
existência.

## Fora de escopo

- O alvo republicado pelo parecer → [[A40.l89]], que vai na frente.
- O denominador de cada limiar (que base cada número mede) → [[A40.l80]], que está `open`,
  **não entregue** — e que recebeu o §8 do ataque (`is_monetary`), **gate de entrada desta
  lane**: hoje `dev/check_golden_rebaseline_isolation.py` não cobre
  `backend/tests/snapshots/`, então "delta de golden declarado" é inexequível.
- A [[ADR-367]] (`Proposto`, gradação + tier de irreversibilidade) e a RULE note dela, que
  declarava enforcer inexistente — corrigida em 2026-08-27, fora desta lane.

## Critério de aceite

- O invariante do item 4 é teste **por chave** e falha por mutação **parametrizada sobre
  todas as chaves elegíveis** — não sobre uma. Romper um gatilho de doutrina sem emitir o
  item correspondente ⇒ vermelho. Prova de que discrimina: a mutação só-concentração, que
  hoje fica verde, tem de ficar vermelha.
- **Gate estático de cobertura:** toda chave elegível está coberta por regra **ou** por
  dispensa declarada com motivo. É ele — não o invariante de payload — que pega "o catálogo
  ganhou chave nova e ninguém leu", que é como este catálogo nasceu órfão.
- **Nenhuma regra emite sobre medida suprimida.** Mutação: `tier: "indeterminado"` com
  `pct = 0` ⇒ zero pontos urgentes de cambial.
- A ADR nova do item 1 está `Proposto` antes do PR de implementação e flippa no merge.
  **Não** há emenda da [[ADR-399]] por este eixo (§7 do ataque).
- Delta de golden declarado — **e só depois que a [[A40.l80]] puser
  `backend/tests/snapshots/` sob a disciplina de rebaseline**. Hoje o critério é
  inexequível: o golden que esta lane rebaselinaria não tem gate.
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
   **emenda datada da [[ADR-191]] §D6** para o PR1.
   > **Resolvido na mesma data, depois de escrito** (#1775, que reescreveu os itens 1-4):
   > a condicional original — *"duas emendas datadas **se** a da [[ADR-399]] sobreviver à
   > correção 4"* — **não sobreviveu**. A correção 4 se resolveu contra a emenda: o PR1
   > abre **ADR nova `Proposto`**, porque emendar a [[ADR-399]] para "estreitar uma isenção
   > que ela não deu" poria descrição falsa no registro permanente.
   Continuam sendo **dois artefatos de ADR** no mesmo PR (a nota `Proposto` nova + a emenda
   da [[ADR-191]]), com gates e provas distintos — a pergunta **PR1a/PR1b permanece**, com
   conteúdo outro. O ID da nota nova **não é alocado aqui**; quem executar aloca na escrita.

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

## Correção datada do §Ataque — 2026-08-27, pós-especialistas

> **Nada acima foi apagado.** Quatro afirmações que publiquei nos #1766/#1767 não se
> sustentam; ficam onde estão, anotadas aqui. Origem: co-design com `financial-planner`,
> `data-engineer`, `product-manager` e `senior-cto`, com **toda** refutação remedida por
> mim contra `main` `1647578f`.

### C-1 — `exposicao_cambial` **não** está rompido. São dois canônicos, não três.

`exposicao_cambial.tier == "indeterminado"` e
`componentes.carteira_lastro_estrangeiro.cobertura == "indeterminado"`. O produtor
**suprimiu o veredito**; o `0%` é piso de medida, não fato sobre o patrimônio. Comparar
`0 >= 10` e concluir "rompido" é fabricar veredito sobre medida que o produtor se recusou
a julgar.

Pior como processo: a [[A40.l80]] §C1 **já registrava o mecanismo desde 2026-08-25** —
`carteira_lastro_estrangeiro` é fixado `Cobertura.indeterminado` incondicionalmente desde
o #1568 ([[ADR-403]]), e `_tier_from_pct` é código morto em produção. O §Ataque re-derivou
como achado o que uma lane P0 viva da mesma sprint já havia refutado por escrito.

**Rompidos de fato: `concentracao_imobiliaria` (82,19% vs 50%) e `taxa_endividamento`
(20,55% vs ≤20%).** O §1 do ataque (o invariante passa com o defeito presente) **não muda**
— 2 > 0 e `len(pontos_urgentes) == 2`.

### C-2 — o §9 errou a magnitude e a natureza do número.

- **`meses_alvo` não é alvo da família.** Sai de `_meses_alvo_from_scoring`
  ([`reserva_emergencia_calculator.py:135-143`](../../../../pipeline/domain/services/reserva_emergencia_calculator.py)),
  que lê `scoring.json::reserva_emergencia._base_calculo.meses_alvo_por_perfil_renda`, com
  o perfil **derivado da composição de renda observada** (`:213-225`). Não há leitor de
  `Goal(RESERVA_EMERGENCIA)` no pipeline. O catálogo carimba `procedencia: "goal_declarado"`
  sobre `limiar_canonico` — **procedência falsa**, e é achado da [[A40.l89]], não desta lane:
  o §Escopo 2 dela chaveia em `procedencia: null`, então ela passa no próprio critério sobre
  entrada mentirosa.
- **O "3×" é falso no caso comum.** `_perfil_por_pct` (`:352-361`) **nunca retorna
  `clt_estavel`** — o comentário declara que a contagem de fontes não existe no fluxo v1.
  O ramo de 6 meses é inalcançável; o piso do alvo é **12**, e 18 só em `pj_dominante`.
  A magnitude é **2×** no caso alcançável comum.
- **A conclusão do §9 sobrevive por outra rota, mais forte.** A [[ADR-399]] §D2 fecha com
  *"publica-se o declarado como `target` e **o limiar vira `risco`**"* — a precedência
  "família vence doutrina" governa o canal `target`; o mesmo parágrafo roteia a doutrina
  para o canal **risco**, que é esta superfície. O piso de risco segue **6**. E a
  [[ADR-367]] (`Proposto`) já decidiu isso no título: *"o alvo da reserva gradua **sem mover
  o gatilho**"*.

### C-3 — o §8 mediu 5 de 26, e a consequência que lhe atribuí não é alcançável.

**A classe é 5× maior.** 26 de 198 classificações monetárias estão erradas (**13,1%**), em
9 famílias — medido com o `_monetary_paths` do próprio teste:

| path | grandeza real | golden publica |
|---|---|---|
| `kpi_targets.*.limiar` (5) | pct / meses | ×100 |
| `score.valor` (1) | nota 5,9/10 | `590` |
| `score.componentes[].valor` (5) | pct / meses | ×100 |
| `score.breakdown[].valor` (5) | nota 0-10 | ×100 |
| `score.breakdown[].contribuicao` (5) | pontos | `250` = 2,50 pts |
| `investimentos.top_ativos[].posicao` (2) | **ordinal** | rank 1 → `100` |
| `…instituicoes_por_membro[].n_posicoes` (1) | **contagem** | 1 → `100` |
| `ratios.concentracao_imobiliaria` (1) | pct | `8219` |
| `consumo_consciente.equivalente_meses_aporte` (1) | meses | ×100 |

**E o "over-gated" era falso.** Escrevi que `check_manifest` exigiria manifesto e gravaria
"50% → 45%" como `old_cents: 5000`. Medido: `golden_diff` **não é invocado em CI nenhum**,
`tests/fixtures/pipeline_golden/rebaseline_manifest.yaml` está **vazio (`[]`)**, e
`dev/check_golden_rebaseline_isolation.py:23` fixa
`_GOLDEN_PREFIX = "tests/fixtures/pipeline_golden/"` — que **não cobre**
`backend/tests/snapshots/dogfood_view_model.json`. O cenário era hipotético.

O que sobra é pior e é real: **o golden que esta lane vai rebaselinar não tem gate nenhum**,
e o delta pode viajar no mesmo commit do código que o produziu. E a [[A40.l80]] não pode
fechar por sufixo — `top_ativos[].posicao` e `n_posicoes` não têm irmão `unidade`, e
`score.componentes[].unidade` está no schema e **não é emitido** (`None` no payload).

### C-4 — duas afirmações de estado que envelheceram.

- **A [[A40.l80]] está `open`/P0**, não `shipped` — escrevi `shipped` no §Encaminhamento.
  Ela é dona viva de `dev/golden_diff.py` (o comentário do sufixo é assinado `# A40.l80:`),
  o que muda o roteamento do §8: é **item dela**, não lane nova.
- **A [[ADR-399]] agora tem `amended_at: ["2026-08-27"]`** — a [[A40.l89]] mergeou a §Emenda
  no #1773, que cita este ataque. A frase do §7 ("não tem `amended_at`") descrevia
  `f91df375` e vale só para aquele commit. **O argumento do §7 segue de pé** e a própria
  §Emenda o adota: o D4 renuncia escopo, não proíbe.

### C-5 — texto original dos §Escopo 1-4, preservado

Reescritos em 2026-08-27. O que estava escrito, verbatim:

> 1. **PR1 — emenda datada da [[ADR-399]]**, estreitando a isenção da D4 à superfície de
>    risco, com a taxa de disparo medida e escrita.
> 2. As quatro regras passam a derivar limiar do catálogo.
> 3. As três dimensões sem regra (concentração imobiliária, desvio de alocação, exposição
>    cambial) ganham regra que **lê** o catálogo, não que fixa número.
> 4. Invariante: `count(kpi_targets rompidos) > 0 ⟹ len(pontos_urgentes) > 0`. Falha hoje.

Por que cada um caiu: **1** — não há isenção a estreitar (§7), e a §Emenda 2026-08-27 da
[[ADR-399]] adotou essa leitura; **2** — 3 das 4 regras não têm limiar a derivar (§4) e
`reserva_insuficiente` está sob procedência falsa; **3** — eram quatro, não três (§5), e
"ter `limiar`" não basta como elegibilidade; **4** — não falha hoje (§1-§3), e chavear em
`procedencia` seria ancorar num rótulo comprovadamente falível.

### O que o ataque afirmou e **sobrevive** integralmente

§1, §2, §3 (o invariante passa com o defeito presente; a mutação do §Critério fica verde;
é infalsificável no dogfood), §4 (2 das 4 regras mapeiam órfãos por decisão), §5 (a
enumeração saiu do run, não do catálogo), §6 (a citação é a redação aposentada), §7 (o D4
renuncia escopo — adotado pela §Emenda da [[ADR-399]]), e o núcleo do §8 (`limiar` é
classificado como dinheiro; a unidade não é endereçável por nome).
