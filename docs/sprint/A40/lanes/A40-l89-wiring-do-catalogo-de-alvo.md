---
id: A40.l89
type: lane
title: "Wiring do catálogo de alvo: o produtor suprime o limiar por falta de procedência e o parecer o republica"
sprint: A40
plan: PLAN-deterministic-authority
status: shipped
ship_pr: 1779
ship_date: "2026-08-27"
priority: P0
branch_slug: a40-l89-wiring-do-catalogo-de-alvo
owner: prompt-engineer
depends_on:
  - "[[A40.l91]]"
adrs:
  - "[[ADR-399]]"
  - "[[ADR-416]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/llm
---

# A40.l89 — `wiring-do-catalogo-de-alvo` (RR5-02)

> **Origem:** rodada unificada **U1** 2026-08-26 ([[ADR-416]]) ·
> [[REPORT-REVIEWS-active]] §r5 — **RR5-02** (Crítico, P0).
> Cru + síntese: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).

> **Esta lane é a RETOMADA do §Deferimento D3, não um locus novo.** O braço do `target`
> de `PE-2` e de `FP-6` no [[PIPELINE-REVIEWS-active]] §r7 está deferido desde 2026-08-21
> com donos nomeados: o catálogo determinístico mergeou (#1557, [[ADR-399]]) e **não foi
> wired** — produção segue publicando alvo do LLM. Abrir lane com nome próprio forkaria
> uma decisão que já tem endereço. O escopo abaixo executa o que o deferimento escreveu.

> **Muta E5 + prompt ⇒ zera o contador de 2 re-runs** ([[A40.l2]], estendida à l34/l35).
> Serializada atrás da [[A40.l91]] numa janela única de rebaseline.

## O fato, medido (2026-08-26)

Quatro `kpi_targets` têm `procedencia: null` com motivo nomeado — a supressão é deliberada
e documentada:

| KPI | Motivo declarado da supressão |
|---|---|
| taxa de poupança recorrente | duas fontes divergentes para o mesmo limiar |
| progresso rumo à independência | acompanhado pelo cone, não por alvo pontual |
| cobertura de proteção | capital ideal exige inventário confirmado ([[ADR-387]]) |
| carteira TRS | sem alvo canônico ([[ADR-191]]) |

**Três das quatro vazaram.** A tabela "Métricas a observar" renderizada publica alvo para
duas delas, e o plano de ação renderiza uma decisão fixando **alvo pontual** para exatamente
a métrica que o produtor declara sem alvo canônico.

O produtor suprime porque a procedência falta; republicar pela prosa devolve à família a
autoridade que o registro recusou — em três eixos de decisão ao mesmo tempo.

## O que a medição já descartou

- ~~"isto é o mesmo defeito das notas metodológicas e cabe na mesma lane"~~ — **refutado**:
  não compartilha superfície, dono, blast radius nem gate com um `.map()` faltando num
  componente. É produtor + schema + `PROMPT_VERSION` + janela de rebaseline. Tese comum não
  é lane comum.
- ~~"o parecer alucina o alvo"~~ — não. Ele autora um alvo porque **nada** no exec context
  o proíbe: o catálogo existe e não é lido.

## Escopo (executa (a), (b) e (d) do §Deferimento D3 — o (c) já mergeou em #1591)

> **Reescrito em 2026-08-27**, com o item (d) transferido. O texto anterior prometia três
> superfícies e alcançava uma; critério inexequível não adia entrega, **esconde**.

1. **Fecha o canal de emissão.** `metrica_key` vira required com enum fechado; `nome`,
   `valor_atual` e `target` saem do tool schema (`SkipJsonSchema`) e passam a ser
   estampados pelo finalize a partir do `kpi_target_catalog`. Métrica fora do enum não é
   emitível — **não há chave de escape**, e é esse o cap estrutural da [[ADR-399]] D1.
2. **`target` sem procedência ⇒ o item perde o comparador**, e publica `motivo` no lugar
   — a linha sobrevive como observacional.
3. **Read-path subtrativo** nos pareceres persistidos: o `target` só é servido quando o
   artefato traz `metrica_key`. Sem backfill, sem recomputar catálogo, sem mutar artefato
   ([[ADR-204]] §D1). Cobre HTML e PDF pela mesma rota.
4. Bump **atômico** de `PROMPT_VERSION` **e** `_SCHEMA_VERSION` — os dois entram na chave
   de cache e **nenhum dos dois é gateado** para esta mudança.

## Fora de escopo

- Estender o leitor único à **superfície de risco** → [[A40.l90]]. A ordem é forçada: se as
  regras de risco lerem o catálogo antes do parecer, o ponto urgente passa a contradizer o
  alvo ainda autorado pelo LLM na tabela de métricas **do mesmo relatório**. Wiring primeiro.
- A base bruta/líquida da meta de independência → [[A40.l91]], que vai na frente.

### §Deferimento datado 2026-08-27 — o item (d) muda de endereço

**O alvo do plano de ação não vem do LLM.** "Reduzir taxa de retirada para 4,0% ao ano" tem
ocorrência **única** no repo: `pipeline/domain/services/suggestion_rules.py:103`, com a
constante `trs_target_pct = 4.0` em `suggestion_config.py:15`. É **regra determinística** — e
o catálogo declara `carteira_trs` órfã ("sem alvo canônico", [[ADR-191]] §D5). São duas fontes
determinísticas do próprio produto se contradizendo, o que é a tese da [[A40.l90]], não desta
lane. A justificativa de ordem acima diz *qual lane vai primeiro*, não *onde (d) mora*: a
redação original conflatou sequenciamento com propriedade.

Agrava: a linha é **fóssil**. A regra não dispara hoje (`if_pct` 35,76 < 50; `trs` 1,74 < 4,6
— par medido no **run da U1**, `storage/<uuid>/`, off-git; na fixture
`dogfood_view_model.json` a regra também não dispara, mas pela guarda **anterior**, com
`goals.taxa_retirada_efetiva_pct` ausente — re-medido no closeout de 2026-08-27, ver
[[A40.l90]] §Acolhimento);
o 4,0% persiste porque a `Decision` D01 foi aceita em 2026-05-06 e `_top5_decisions_stmt`
projeta sem revalidar. Corrigir o produtor **não apaga a linha já persistida**.

| item | casa | dono | condição de retomada |
|---|---|---|---|
| ~~`trs_target_pct = 4.0` na rota do plano de ação~~ | [[A40.l90]] | — | **ENTREGUE 2026-08-29** (#1815) |
| ~~prosa `≥ 30%` / `< 20%` no exec context~~ | [[A40.l90]] | — | **ENTREGUE 2026-08-29** (#1816) |
> **Nota de reconciliação 2026-08-29 — a forma prescrita nesta tabela era falsa.**
> As duas primeiras linhas mandavam *"emenda da [[ADR-399]] §D4 no PR1 da l90"*. A l90
> mediu que o §D4 **renuncia** escopo em vez de isentar (*"o escopo é essa rota, não o
> repo… não estão no escopo desta ADR"*), logo não havia isenção a estreitar — e emendá-la
> poria descrição falsa no registro permanente. A forma entregue foi outra: **[[ADR-419]]
> nova** (`Proposto`, #1812) para o canal de gatilho de risco, e **emenda da [[ADR-191]]
> §D6** (#1815) para o `trs_target_pct`, porque quem o alvo de TRS contradiz é o Aceite da
> 191 — que contava *"dois consumidores"* e eram **três**. A prosa do exec context saiu
> sem emenda: o limiar que ela afirmava já era órfão declarado.

| `Decision` aceita não revalida contra o run corrente | ciclo de vida de `Decision` | `financial-planner` | próxima lane que toque `Suggestion`/`Decision` |
| seleção do painel: piso determinístico das rompidas | `PLAN-deterministic-authority` §Onda 5 | `financial-planner` + `prompt-engineer` | stamping desta lane em `main` |

> ✅ **Acolhido do lado da l90 em 2026-08-27** — [[A40.l90]] §Escopo 5-6 + §Acolhimento. A
> ocupação que barrou a primeira tentativa (`agent/a40-l90-ataque-p2/…`) era **stale**: o
> único commit da branch é patch-idêntico ao `f91df375` já em `main` (#1767) e o worktree
> estava limpo. Duas correções que o lado que recebe mediu e este lado não: a emenda é da
> **[[ADR-191]] §D6** (a [[ADR-399]] §D4 *renuncia* a estes leitores — não há isenção a
> estreitar), e das duas prosas só a `:121` contradiz o catálogo — a `:158` lê a **mesma
> chave** que `_endividamento` lê, e fica.

**Residual declarado, para o próximo revisor não o achar sozinho:** entre o merge desta lane e
o da l90, o relatório terá linha **sem comparador** para taxa de poupança e, no mesmo
documento, prosa afirmando `≥ 30%`. É contradição menor que a de hoje (alvo fabricado **+**
prosa), mas é contradição.

## Forma canônica

Emenda datada à [[ADR-399]] **não** é necessária: o wiring é exatamente o que a D4 já decide.
Se o escopo exigir mudar o que a D4 isenta, a forma é emenda — e aí a lane é a [[A40.l90]].

## Critério de aceite

> **Reescrito em 2026-08-27** junto com a transferência do item (d) — o critério anterior
> prometia a **prosa** e o **plano de ação**, que esta lane não alcança: nenhum campo de prosa
> carrega `metrica_key`, e o produtor do plano de ação é determinístico.

- Nenhum `target` **nem** `valor_atual` publicado em `metricas[]` sem `metrica_key` no
  vocabulário fechado **e** `procedencia != null` no `kpi_targets` do E5 — no artefato novo,
  no artefato congelado e no PDF (mesma rota).
- O modelo **não pode emitir** `target`: prova por mutação sobre o **tool schema**, não por
  instrução de persona.
- Item órfão publica `motivo` na célula do comparador; **célula vazia reprova** (vazio o leitor
  lê como "não mediram", que é afirmação diferente de "não afirmamos um alvo").
- Todo `observado_path` do catálogo resolve para folha existente no payload do golden, pelo
  **resolver de produção**.
- Delta de golden declarado `↑`/`↓`/`=` **no corpo do PR**, com o diff inspecionado item a
  item. **Ressalva medida (2026-08-27):** "rebaseline silencioso reprova" **não é verdade
  para este arquivo**. `dev/check_golden_rebaseline_isolation.py` fixa
  `_GOLDEN_PREFIX = "tests/fixtures/pipeline_golden/"` e **não cobre**
  `backend/tests/snapshots/`; `golden_diff` não é invocado em workflow nenhum. Logo o
  delta viaja no mesmo commit do código sem violar gate — a declaração aqui é **editorial,
  não enforçada**. Estender o prefixo é da [[A40.l80]], dona assinada do `golden_diff.py`;
  não se duplica o gate deste lado.
- **Cap:** se a condição de retomada do D3 (*"nenhum rebaseline de golden em voo"*) não
  estiver satisfeita quando a janela abrir, esta lane e a [[A40.l90]] caem **juntas** para a
  A43 — não se separam.
- Concluído = PR mergeado em `main` com CI verde.

## Correção datada 2026-08-27 — o que a revisão adversarial pegou DEPOIS do merge

> Rodada sobre o diff já mergeado (#1770 + #1772), com 4 lentes independentes e uma
> passada de refutação. **Cinco defeitos confirmados por repro**, dois deles P0. Fica
> registrado porque o padrão importa mais que os itens: **o gate e o critério que teriam
> pego três deles fui eu que escrevi, e escrevi de um jeito que não pegava.**

| # | defeito | por que passou |
|---|---|---|
| 1 | `alvo["rotulo"]` derrubava o stage com `KeyError` sobre E5 gravado entre #1591 e #1770 — **depois** de pagar o LLM e **antes** do `_write_cache`, logo cada retry pagava de novo | o guard testava a entrada AUSENTE do catálogo, não o campo ausente DENTRO dela; `rotulo` nasceu no #1770 e `kpi_targets` existe desde o #1591 |
| 2 | o gate de `observado_path` construía a `section_whitelist` **a partir dos próprios paths que ia testar** ⇒ `path_not_whitelisted` inalcançável por construção | gate que fabrica a própria precondição mede a si mesmo; sob a whitelist real, **2 das 13** chaves não resolvem |
| 3 | 67 E5 do dogfood não publicam `kpi_targets` ⇒ ramo órfão com `nome=""` ⇒ até 10 linhas **anônimas** na tabela | `nome` perdeu `min_length` ao sair do tool schema; `""` valida e persiste |
| 4 | `5,6` renderizava `"6 meses"` contra `"≥ 6 meses"` — **violação lida como conformidade** | o hint `meses` do formatter compartilhado arredonda para inteiro, e o observado tem 1 casa |
| 5 | a leitura suprimia `target` e continuava servindo `valor_atual` autorado | o §Critério pedia os **dois**; o código entregou um. O observado fabricado ao lado de "Não afirmamos um alvo" LÊ como medido |

Todos corrigidos e provados por mutação. As duas chaves irresolvíveis do #2 viraram
**dívida declarada por igualdade de conjunto** em `tests/test_e5_golden_execution.py` —
consertar uma sem removê-la de lá reprova, e uma terceira reprova.

### Achados da sessão da [[A40.l90]] — dois eixos que o §Escopo 2 não cobria

O §Escopo 2 chaveia em `procedencia: null` para o item perder o comparador. Há **dois
jeitos de o comparador ser ilícito sem a procedência ser nula**, e os dois estavam vivos:

| eixo | o que estava errado | correção |
|---|---|---|
| **procedência mentida** | `reserva_cobertura_meses` carimbava `goal_declarado` sobre `meses_alvo`, que sai de `scoring.json::_base_calculo.meses_alvo_por_perfil_renda` chaveado por perfil de renda **observada** — e **não existe leitor de `Goal(RESERVA_EMERGENCIA)` no pipeline**. Doutrina usando o crachá da família, com a precedência da [[ADR-399]] D2 operando sobre isso na direção que **absolve** | vira `limiar_canonico` com `ref` na chave real; volta a `goal_declarado` quando o Goal for legível pelo pipeline |
| **medida suprimida** | `exposicao_cambial` publicava `limiar` + `limiar_canonico` mesmo com `tier: indeterminado` e `carteira_lastro_estrangeiro.cobertura: indeterminado` ([[ADR-403]]). Depois do wiring, o parecer afirmaria "0% contra ≥ 10%" **com o selo de autoridade do produto** sobre medida que o produtor se recusou a julgar — pior que o alvo autorado pelo LLM | sai da tabela estática e vira resolver com guarda de cobertura, no molde do `_renda_passiva_cobertura` |

**Predicado que fecha os dois, adotado:** nenhum `target` publicado quando o comparador
não é licenciado — seja por **procedência ausente**, seja por **medida suprimida**.

Ressalva ao enquadramento recebido: a analogia com a RV2-24 **não procede**.
`thresholds_alertas.reserva_minima_meses` (6) é lido por `pontos_urgentes_analyzer.py:251`
como **piso de alerta**; `meses_alvo` (12/18) é **alvo por perfil**. Piso e alvo são
conceitos distintos, não duas definições rivais do mesmo limiar. O defeito é a procedência
mentida, não a divergência de fontes.

**Delta de golden desta correção: `↓`** — o `dogfood_view_model.json` perde um alvo
publicado (`exposicao_cambial.limiar` 1000 → `null`). Como o `limiar` é classificado como
**dinheiro** pelo instrumento do snapshot ([[A40.l90]] §8), o diff aparece como delta
monetário; é artefato do classificador, não valor de dinheiro.

### Segue aberto — com dono E rota (painel de 2026-08-28)

| item | dono | por quê |
|---|---|---|
| `diagnostico_confianca` fora da whitelist de `get_e5_section` | `prompt-engineer` | ampliar a whitelist muda a superfície que o modelo lê; exige bump próprio |
| predicado `[classe=…]` não admitido por `_JSONPATH_RE` | `data-engineer` | ou o E5 publica a folha em ponto fixo, ou o subset de JSONPath cresce |
| `metrica_key` repetida (sem `uniqueItems` nem validator) | `prompt-engineer` | com o vocabulário fechado, duas linhas iguais ficam byte-idênticas exceto pela coluna Revisão |
| barra de progresso ignora a polaridade do operador | `product-designer` | pré-existente, mas agora sobre alvo autoritativo: para `<`/`<=` a barra **enche conforme piora** |
| `clt_estavel` (6 meses) é inalcançável — `_perfil_por_pct` nunca o retorna (exige contagem de fontes que o fluxo v1 não tem), então o piso real do alvo de reserva é 12 | `financial-planner` | se 6 meses deve ser alcançável é decisão de domínio, não de wiring |
| `Goal(RESERVA_EMERGENCIA)` não tem leitor no pipeline — a precedência "declarado vence doutrina" ([[ADR-399]] D2) não tem como operar para reserva | `data-engineer` | enquanto isso, a entrada é honestamente `limiar_canonico` |

**A casa decimal de `meses` é mudança visível ao usuário** e ficou nesta rota apenas (o
formatter compartilhado não mudou, porque os outros consumidores dele não comparam contra
nada). Se a preferência do domínio for outra forma, é decisão de `financial-planner`.

## Entregue em 3 PRs

`ship_pr` nomeia o **#1779** porque é o que deixou `main` no estado atual (o schema pede um;
os demais vivem aqui e na tabela do `_README`). Os três, em ordem:

| PR | commit | o que entregou |
|---|---|---|
| [#1770](https://github.com/davidrobert/mathoms/pull/1770) | `0f4ad12d` | catálogo correto e completo — invariante de forma, path da TRS, vocabulário 10→13, `rotulo`, `protecao_custo_premio`, gate de `observado_path` |
| [#1772](https://github.com/davidrobert/mathoms/pull/1772) | `78b06986` | o canal fecha — `metrica_key` required, `nome`/`valor_atual`/`target` fora do tool schema, estampagem no finalize, read-path subtrativo, bump atômico de `PROMPT_VERSION` + `_SCHEMA_VERSION` |
| [#1779](https://github.com/davidrobert/mathoms/pull/1779) | `4fbfb91b` | **hotfix de 7 defeitos** que os dois primeiros introduziram — 2 P0 do autor, 2 P0 achados pela sessão da [[A40.l90]], 3 P1 |

## Fecho — painel de 2026-08-28 (financial-planner · senior-cto · data-engineer)

**Veredito: FECHADO COM RESSALVA.** Os 3 PRs estão em `main` com CI verde e os três P0
foram verificados no `origin/main`, não pelo PR. `FECHADO` puro exigiria "nada aberto sem
dono"; aqui há dono **e** rota, mas R1/R2 não são estado de repouso — são KPI publicado
cujo observado o parecer **nunca** consegue ler.

### Decisões tomadas

**Render de `meses` — mantém 1 casa nos dois lados** (`53,3` / `≥ 18,0`). `pct` já rende
`≤ 20,0%` para limiar inteiro; fazer `meses` diferente seria a única unidade com alvo em
forma distinta do observado na mesma tabela, para corrigir uma falsa-precisão que o glifo
`≥` já neutraliza.

**Direção do arredondamento (P2, novo).** `cobertura_meses` usa `round(x, 1)` half-even e
`_classify` roda sobre o float cru: `5.96` publica `6,0 meses / ≥ 6,0 meses` **e**
`avaliacao_liquidity: "Insuficiente"` — o relatório se contradiz na mesma tela. Cobertura
em meses é medida de sobrevivência: `ROUND_FLOOR`. A janela é ~1,5 dia de custo essencial;
o motivo é coerência entre veredito e número exibido, não magnitude.

### Achados NOVOS do painel, que não estavam nos seis

| # | achado | consequência |
|---|---|---|
| N1 | **`_alocacao_renda_fixa` publica `operador="<="`** — afirma que **menos** RF que o alvo está conforme, falso nas três metodologias e na direção que machuca (família sub-protegida em drawdown) | está mascarado porque R2 impede o observado de resolver. **Consertar o path de R2 sem o operador ATIVA um comparador doutrinariamente errado com o selo do produto** — a classe que esta lane existe para fechar, a um commit de distância |
| N2 | **`check_prompt_version_bumped` não cobre `config/prompts/*.yaml`** — `manifest_version` sai do `version:` do YAML e entra na chave de cache com TTL de 7 dias | **terceira instância** da mesma classe nesta lane. Bloqueia R1, cujo remédio é edição de manifest |
| N3 | **`clt_unica_fonte` é rótulo factualmente falso** — o código o escolhe por *ausência de medição* de fontes, não por ter medido fonte única; publica "renda de fonte única" para casal com dois salários | mesmo modo de falha da ADR-399 (observado de uma base sob rótulo de outra), um andar acima |
| N4 | **R1 é mais barato do que este lado supôs** — a seção `diagnostico_confianca` **já é injetada** no exec context pelo manifest, com `narrative_hint` próprio. A whitelist só controla o **re-ler sob demanda**. Delta de superfície: **zero folhas novas** | ampliar o enum não é concessão de leitura, é **remoção de contradição** do manifest |
| N5 | **R6 é mais barato do que o registro sugere** — falta **uma entrada** em `_GOAL_TYPE_MAP` + um serializer; model, DTO, schema e ADR-263 já existem | quando executada, exige **emenda datada à ADR-399** (muda a procedência publicada da reserva) |

### Rota dos residuais (substitui a lista de donos soltos)

| item | rota decidida | dono |
|---|---|---|
| **R1** `diagnostico_confianca` fora da whitelist | acrescentar ao enum de `get_e5_section` + bump do `version:` do YAML. **Bloqueado por N2** | `prompt-engineer` |
| **R2** predicado `[classe=…]` | **folha em ponto fixo** (`rf_atual_pct` + `rf_alvo_pct` em `AlocacaoDerived`), não estender o `_JSONPATH_RE` — o subset é guardrail declarado, e alargá-lo dá filtro ao **modelo** para servir um consumidor interno. **Vai junto com N1** | `data-engineer` |
| **R3** `metrica_key` duplicada | **dedupe subtrativo no finalize, keep-first**, com contador. **Não** `uniqueItems` nem validator hard-fail: as linhas diferem em `frequencia_revisao`, e hard-fail reabre a reask storm ([[ADR-292]]/[[ADR-294]]). ≤30 linhas ⇒ bug fix, não lane | `prompt-engineer` decide, backend implementa |
| **R4** polaridade da barra | **lane própria** — o defeito é de **contrato**, não de CSS: `operador` existe no `KpiTarget` e **não viaja no wire**, então o front re-deriva por regex sobre a string renderizada. Mitigação imediata: suprimir a trilha quando o operador for de teto | `product-designer` + `data-engineer` |
| **R5** `clt_estavel` inalcançável | piso de 12 é **doutrina defensável e fica**. Mas a faixa inalcançável **sai do `scoring.json`** (config viva que ninguém seleciona convida o próximo a "consertar" `_perfil_por_pct` e afrouxar o piso de toda família CLT), e o rótulo N3 é renomeado | `financial-planner` |
| **R6** `Goal(RESERVA_EMERGENCIA)` sem leitor | lane própria. **E a ADR-399 D2 precisa de emenda ANTES**: "declarado vence doutrina" está certa para alocação e **errada para reserva** — declarado mais frouxo que o canônico não licencia. Regra correta: `limiar = max(declarado, canonico)` | `data-engineer` + `financial-planner` |

**Enquanto R6 não existir, `limiar_canonico` é a entrada honesta** — o hotfix acertou, e a
inércia da D2 para reserva é hoje proteção, não bug.

### Executado pela [[A40.l93]] em 2026-08-28 — o que saiu das duas tabelas acima

> As tabelas §Segue aberto e §Rota dos residuais são **painel datado de 2026-08-28** e
> ficam como estão — snapshot que alguém atualiza deixa de ser evidência. Esta subseção
> diz o que foi executado **depois** delas, e onde a execução **divergiu da rota
> decidida**: sem isso, quem ler a rota segue instrução que já não descreve o repo.

Entregue em [#1796](https://github.com/davidrobert/mathoms/pull/1796) (`64bd7a07`).
**Dois dos seis** itens do §Segue aberto fecharam; os outros quatro seguem, com a rota
inalterada.

| item das tabelas | desfecho |
|---|---|
| **N2** — gate de versão não cobre `config/prompts/*.yaml` | ✅ por **lista declarada**, não glob: o critério é *"a `version` entra em chave de cache que não hasheia o texto do prompt"*. Junto, o gate deixou de **falhar aberto** com ref irresolvível — ampliar cobertura de instrumento que pode estar desligado seria a mesma classe. [[ADR-233]] §Emenda 2026-08-28 |
| **R1** — `diagnostico_confianca` fora da whitelist | ✅ manifest `2.6.0`. **Mais barato do que "bloqueado por N2" sugeria por uma razão a mais:** o parecer é chamada **single-shot** (`LLMService.call` não tem parâmetro `tools`), então o bloco `tools:` é whitelist de **resolver server-side**, não superfície do modelo |
| **R2** — predicado `[classe=…]` | ✅ **com desvio de rota, em dois pontos.** A rota dizia `rf_atual_pct` **+** `rf_alvo_pct`; foi entregue **só** `renda_fixa_atual_pct`. (a) o prefixo `rf_` era colisão **medida** — `rf_pos_pct`/`rf_pre_pct`/`rf_ipca_pct` vivem um nível acima e somam **40** contra **44,44** renormalizado, que é o C14 da [[A40.l80]] nascendo de novo; (b) a folha do alvo não foi publicada porque, com N1 resolvido por órfão, `ref` é `null` e ela nasceria **sem leitor** |
| **N1** — `operador="<="` da alocação | ✅ **e a forma do remédio não estava decidida nesta tabela** — o painel nomeou o defeito, não a cura. `financial-planner` **recusou** `\|atual − alvo\|` contra 2pp: `SEVERITY_ALINHADO_MAX_PP` é piso de **acionabilidade** ([[ADR-400]] o reusa assim) e a [[ADR-141]] §Emenda item 10 difere a calibração relativa — publicá-lo como `limiar_canonico` promoveria limiar interno a doutrina. Virou **órfão por (b)**, a forma que `if_progresso`/`if_prazo_ano` já têm. [[ADR-399]] §Emenda 2026-08-28 |
| **R3 · R5 · R6** | seguem abertos, rota **inalterada** |
| **R4** — polaridade da barra | segue aberto na [[A40.l92]], mas o **escopo dela caiu de 4 para 3 chaves de teto**: sem alvo, `alocacao_renda_fixa` não tem trilha |

**Efeito que a tabela não previa:** sem comparador, dois estados que fabricariam
conformidade deixam de ser representáveis — denominador zero e supressão declarada
([[ADR-394]]/[[ADR-400]]). Os dois estavam **vivos na fixture do golden**.

### Remédio para o padrão dos gates auto-referentes

Quatro instâncias nesta sessão, um autor: whitelist derivada do alvo do teste; fixtures
`float` contra guard de `float`; critério keyado no único eixo pensado; teste com
`git show` morrendo em clone raso.

**Decidido: emenda datada à [[ADR-210]]** — *gate novo entra com prova de vermelho*: o PR
que introduz gate ou teste-de-invariante cola no corpo o caso que ele deve reprovar,
**reprovando**. Recusadas: ADR nova (a casa existe — a ADR-210 já é a de "teste que custa
CI sem dar sinal"), gate meta (indecidível, e seria escrito pelo mesmo autor com a mesma
premissa) e revisão adversarial pré-merge obrigatória (é o que pegou 5 dos 7, e é a mais
cara — vira imposto permanente; fica como prática opcional).

**Declarado junto com a regra, senão ela vira o próximo falso-verde:** ela teria pego o
gate de whitelist e as fixtures `float`; **não** teria pego os dois P0 achados pela sessão
da l90 (procedência mentida, medida suprimida) — esses são julgamento de domínio, e são o
que a revisão adversarial rende.

### Rotas que apontam para esta lane, agora que ela fechou

O `check_closure.py` levantou `CLOSE-BLOCK-05` em **3** linhas da [[A40.l90]]. Julgadas uma
a uma:

- **`:106` era rota real e está SATISFEITA — e a linha já não existe.** A l90 declarava uma
  regra inelegível "enquanto o catálogo não carregar o qualificador de cobertura (achado
  roteado à l89)". O #1779 o entregou: `_exposicao_cambial` devolve órfão com motivo quando
  `tier == "indeterminado"` ou qualquer componente tem `cobertura != "apurado"`. Avisada, a
  sessão dona removeu a linha no **#1789** — o predicado composto dela **colapsou** para
  `limiar is not None`, porque a cobertura virou condição de existência do limiar **no
  produtor**. **Re-medido em 2026-08-28, pós-merge: o gate levanta 2, não 3.**
- **`:161` e `:197` são falso-positivo do gate** — citam procedência ("herdado do
  §Deferimento da l89", "já declarado pela l89"), não rota futura. **Limite conhecido do
  `CLOSE-BLOCK-05`: ele não distingue "roteado PARA X" de "herdado DE X".** Fica
  registrado; não se muda texto correto para calar gate.

### Por que o flip da l90 vem neste PR

O predicado de `status` (`lane-status-predicate`) falha **nos dois sentidos** e lê o índice
**global** (`pass_filenames: false`). Em `origin/main` o par era consistente — l89
`in_progress` + l90 `blocked`. Flipar só um lado quebra o gate na árvore de quem flipou:
l89 `shipped` deixa a l90 "blocked com dep terminal"; l90 `open` sozinha vira "open com dep
pendente". **Deadlock: nenhuma das duas sessões commita o próprio flip isolado.**

Os dois vão juntos aqui para `main` ir de (l89 `in_progress`, l90 `blocked`) a
(l89 `shipped`, l90 `open`) **sem passar por estado inválido**. Da l90 mudou **só** o
frontmatter (2 linhas: `status` + a tag); corpo, §Escopo e o `:106` são da sessão dona e
ficaram intactos — combinado com ela antes do commit.
