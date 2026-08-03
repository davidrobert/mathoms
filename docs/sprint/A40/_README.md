---
id: MOC-sprint-a40
type: moc
title: "Sprint A40 — Report trust: o dado que entrou tem de chegar ao usuário"
aliases: ["A40", "Sprint A40"]
sprint_status: current
date: "2026-07-30"
theme: "report-trust"
---

# Sprint A40 — Report trust (revisão do relatório entregue, 2026-07-30)

> **Status:** `current` (aberta 2026-07-30; **Onda 0 em `open`** desde 2026-08-03 — ver §Ondas). **Continuação declarada** de [[PLAN-report-trust]]
> (`sprint_origem: A28`) — não é plano novo. A tese daquele plano ("o relatório
> não pode afirmar precisão que os dados não sustentam") é exatamente o que esta
> rodada mediu; as lanes daqui entram lá com `sprint_atual: A40`.

> **Origem:** skill `report-review` sobre o report `7a7e9333` (run `573a54a7`,
> pré-existente) do workspace dogfood, 2026-07-29 — registro em
> [[REPORT-REVIEWS-active]] §r3, 33 achados sistêmicos. **Nenhum stage foi
> re-executado**: o objeto é o artefato entregue. Cru + valores off-git em
> `storage/<uuid>/reviews/2026-07-29-573a54a7/`.

> **Revisão do sprint (painel 2026-07-30 — pm, senior-cto, data-engineer,
> product-designer, prompt-engineer, financial-planner):** 39 decisões, **33
> objeções**, 41 guardas. O painel **corrigiu o achado P0 antes da lane abrir** e
> reordenou duas prioridades. Correções incorporadas abaixo (§Decisões do painel).

## Tese

A A39 provou que o dado **entra** certo. A A40 prova que o dado que entrou
**chega ao usuário** — sem duplicar, sem sumir na renderização, e sem afirmar
mais do que a cobertura sustenta.

26 dos 33 achados são defeitos de **entrega**, não de cálculo: consumidor lê
chave que o emissor não emite, janela trocada, seção que colapsa depois de
prometer conteúdo, PII interpolada no render. O sinal decisivo é que a
conservação do razão fecha em **tol-zero (105/105 grupos)** e ainda assim existe
duplicação material medida — **o gate vigente mede a camada errada**.

## KRs

| KR | Métrica | Como se mede |
|---|---|---|
| **KR-A · Contrato de leitura** | Leituras órfãs conhecidas **5 → 0** *e* existe gate que hard-falha quando a sexta aparece | `dev/check_view_model_contract.py` (novo) cruzando schema E5 × tipos do frontend × readers Python. Prova do gate: fixture com chave órfã ⇒ EXIT≠0 |
| **KR-B · Não-duplicação do razão** | Duplicação cross-grupo **não-explicada = 0** no corpus dogfood | Check cross-grupo em `dev/certify_ledger_local.py`. Baseline congelado pela [[A40.l1]] **antes** de qualquer fix. Anti-Goodhart: ocorrências whitelisted contadas em **linha separada**, nunca somadas ao numerador |
| **KR-C · Entrega visível** | Nº de seções que **renderizam** parágrafo == nº de seções com narrativa **emitida** (hoje **0 de 16**) *e* 0 âncoras de nav sem alvo | Teste de render (Vitest/RTL) sobre payload golden + assert bidirecional nav↔seções em `ReportShell.tsx`. CV9 redefinido para medir **entrega**, não geração |
| **KR-D · PII zero no entregue** | 0 violações no view-model; critério 4 da [[ADR-337]] existe e é executável | Gate de PII sobre o view-model. Fixture sintética com identificador de terceiro + matrícula + endereço ⇒ bloqueio no CI |
| **KR-E · Honestidade da recomendação** | 0 recomendações no topo do plano cuja premissa o próprio payload contesta, sem pendência pareada | Predicado determinístico `premissa → campo E5` em teste sobre payload golden |

**KR rejeitado deliberadamente:** cobertura (`N% dos achados fechados`) — mede
burn-down, não valor, e trataria abreviação `k`/`M` como equivalente a dupla
contagem. Também rejeitado KR de percepção: em dogfood com N=1 o time É o
usuário, e viraria carimbo.

## Lanes (23)

Critério de agrupamento: **arquivo compartilhado** (evita merge-hell entre
branches `agent/*` paralelas) **e** risco compartilhado.

| Lane | Título | Prio | depends_on | Achados |
|---|---|---|---|---|
| [[A40.l1]] | Instrumento: detector de duplicação cross-grupo + baseline congelado | P0 | — | débito de método r3 #4 (habilita l2) |
| [[A40.l2]] | Identidade de lançamento cross-documento (`tipo_conta` + `titular`) | **P0 Crítico** | l1 | RV3-01, RV3-30 · **[[ADR-354]]** |
| [[A40.l3]] | Janela canônica: todo número rotulado 12m lê `janela_12m` | P0 | — | RV3-02, RV3-16, RV3-17 |
| [[A40.l4]] | Entrega de narrativas de seção + re-triagem do que passa a aparecer | P0 | — | RV3-03, **RV3-33 (7 inertes)** |
| [[A40.l5]] | Codegen do view-model + gate de contrato (mata a classe) | P1 | — | RV3-09, RV3-26, RV3-12, RV3-22 |
| [[A40.l6]] | Cards de imóvel e dívida: PII cartorial + contrato + zero-como-valor | P1 | l5 | RV3-06, RV3-12, RV3-27 |
| [[A40.l7]] | Navegação e ponteiros: âncora sem alvo, seção que colapsa, mapa incoerente | P1 | — | RV3-04, RV3-05, RV3-15, RV3-28 |
| [[A40.l8]] | Cobertura do manifest do parecer (dado renderizado inalcançável) | P1 | — | RV3-08 |
| [[A40.l9]] | Materialização de config run-scoped (input zerado silenciosamente) | **P1** | — | RV3-11 |
| [[A40.l10]] | Ordem do plano + pendências do dono | P2 | l9 | RV3-07, RV3-10 |
| [[A40.l11]] | Cobertura e incerteza na tela | P2 | l3, l4 | RV3-13, RV3-14, RV3-29 · flip [[ADR-353]] |
| [[A40.l12]] | Classificação incompleta distorce KPI | P1 | l1 | RV3-20, RV3-21 · flip [[ADR-351]] |
| [[A40.l13]] | Copy e design system | P3 | l4 | RV3-23, RV3-24, RV3-25 |
| [[A40.l14]] | Limpeza de órfãos e schema morto | P3 | — | RV3-32 + handoff A39 |
| [[A40.l15]] | Consumo Consciente: KPI de pontuais na base da janela (+3 co-changes E5) + base do texto do donut e do chart mês a mês | P2 | l3 | spun off da l3 (mudança de domínio; exige rebaseline de snapshot) |
| [[A40.l16]] | Desescalar `number_in_prose`: defeito de forma para de apagar conselho e de derrubar o run | **P0** | — | incidente `2ded7aab` · emenda **[[ADR-304]]** + **[[ADR-358]]** |
| [[A40.l17]] | Custo e cache no caminho `needs_review` do parecer | P1 | — | incidente `2ded7aab` |
| [[A40.l18]] | Criticidade de stage: add-on advisory não veta o entregável | **P0** | l21 | incidente `2ded7aab` · **[[ADR-357]]** |
| [[A40.l19]] | Migration do drift de enum de status (4 valores) | P1 + gate de deploy | — | **[[ADR-357]]** §7 |
| [[A40.l20]] | `PlannerReview` representa gerado-e-retido (destrava a UI) | **P0** | l18 (**decisão**, não merge) | emenda provável **[[ADR-204]]** |
| [[A40.l21]] | Leitores tolerantes a `partial_failure` (reader-first) | **P0** | — | **[[ADR-357]]** §Consequências |
| [[A40.l22]] | Superfície de degradação no relatório + PDF | **P0** | l20 | fatia premium da F11.5 · **bloqueador do beta** (6ª classe do gate de saída) |
| [[A40.l23]] | Gate: ADR citada em prosa resolve para arquivo (reserva de ID é invisível) | P2 | — | classe exposta pela **[[ADR-345]]** |

## Ondas

**Onda 0 — parar a sangria** ([[A40.l16]], [[A40.l17]]), aberta 2026-08-03 pelo
incidente do run `2ded7aab`. **Precede a Onda 1 e não é negociável**, por um
motivo estrutural e não de gravidade: a Onda 1 é "medir antes de mexer", e medir
exige **run que completa**. Com 89% dos runs perdendo conselho e uma fração
falhando, o baseline da l1 e a re-rodada de gate de toda onda posterior medem um
pipeline que não entrega — e o §Gate de saída do dogfood de [[PLAN-report-trust]],
que exige 2 re-runs completos consecutivos, **não pode nem iniciar o contador**.
A l16 é XS (uma linha em `_HARD_LAYERS` + bump de versão de verificação) e
independente. A l17 é cortável.

**Onda 1 — medir antes de mexer** ([[A40.l1]], [[A40.l3]], [[A40.l4]], [[A40.l9]]).
A l1 é instrumento: congela o baseline **sobre `origin/main`** antes de qualquer
mutação — lição da A39 (baseline pós-mutação mede o próprio fix). A l3 fecha três
achados com esforço S e risco baixo. A l9 sobe para cá porque é **pré-requisito de
RV3-07** e porque é reincidência de um "FIXADO" falso.

**Onda 2 — corrigir com o instrumento pronto** ([[A40.l2]], [[A40.l5]], [[A40.l7]],
[[A40.l8]], [[A40.l12]]). A l2 só abre depois da l1: sem detector, o fix fecha
verde sem prova. A l5 vem **antes** das lanes de correção individual de contrato —
senão cada uma é fixada uma vez e volta a divergir.

**Onda 3 — degradação honesta** ([[A40.l18]]…[[A40.l22]]). Fecha a classe que o
incidente expôs: contrato de criticidade de stage, `partial_failure` alcançável, e
o retido declarado na tela. É a §Frente 4 de [[PLAN-report-trust]] — leia lá a
tese, os KRs (KR-0..KR-3), o tripwire T1 e os guardrails G1/G2.

**Ordem interna, e nenhuma das três é estética:**

- **[[A40.l21]] antes de [[A40.l18]]** (reader-first). Os 5 read sites de
  `partial_failure` no frontend são código morto hoje — o status existe no union
  type e no `format.ts`, mas nenhum writer o emite. Corrigi-los primeiro é PR
  coeso e de risco zero. Shipar o writer primeiro entregaria um run que produziu
  relatório com banner vermelho de falha e botão de reprocessar: **pior que hoje**.
  Amarra: se a l18 escorregar >1 sprint, **reverta a l21** — é dead code pelos
  nossos próprios critérios.
- **[[A40.l20]] depende da *decisão* da [[A40.l18]]**, não do merge. O vocabulário
  de status é fixado pela [[ADR-357]] `Proposto`; implementar contra a ADR permite
  mergear em paralelo em vez de serializar duas semanas.
- **[[A40.l19]] em PR próprio** — migration não mistura com feature.

**Esta onda precede a Onda 4 por conflito de arquivo, não por prioridade.** A
[[A40.l22]] toca as mesmas superfícies do relatório que [[A40.l11]] e
[[A40.l13]]; pelo critério de agrupamento desta sprint ("arquivo compartilhado,
evita merge-hell"), a l22 vai primeiro e as duas rebaseiam sobre ela.

**Onda 4 — o que depende das anteriores** ([[A40.l6]], [[A40.l10]], [[A40.l11]],
[[A40.l13]], [[A40.l14]], [[A40.l23]]).

**Precedência de corte:** nunca cortar [[A40.l16]] nem [[A40.l18]]. Cortáveis, em
ordem: [[A40.l17]], marcador em `/reports` (já fora de escopo), dead-letter (já
fora, por gatilho). **Nada sai da A40** — decisão do dono, 2026-08-03: a onda 0 e
a onda 3 entram por cima do escopo existente, sem despejar lane P2/P3 para A41.

**A ordem não segue a coluna de severidade, e isso é deliberado.** O painel
apontou que a severidade desta rodada não é insumo confiável de sequenciamento: os
7 `CONFIRMADO` são confiáveis, os **37 `PARCIAL` carregam inflação desconhecida**
(débito de método #3 da própria r3 — zero refutado em 36 clusters). A ordem aqui é
por **"alcança o usuário na configuração atual"**, e começa pelo que foi **medido**.

## Decisões do painel (correções incorporadas)

**1. O mecanismo do P0 estava errado — corrigido antes de abrir a lane.**
Três especialistas, independentemente: `normalize_banco` (`_tx_identity.py:75`) já
faz lowercase + strip-accents **antes** do hash, em `_hash_v1` e `_hash_v2`. A
caixa de `banco` **não** fura o `transaction_hash` — fura a chave de grupo. Os
carriers reais são `tipo_conta` (vocabulário `extrato` vs `extratoconta`, que
`normalize_tipo_conta` só lowercaseia) e `titular` vazio. **A duplicação medida não
muda; a causa sim.** Escrita como estava, a lane shiparia um no-op e fecharia
verde. Âncora corrigida no [[REPORT-REVIEWS-active]].

**2. O fix não pode morar na fórmula do hash.** `_hash_v1` está **congelado**
([[ADR-278]] D1) e `_hash_v2` é a chave de dedup **e** de re-ancoragem de override.
Mudar os inputs de v2 órfãna override do usuário — regressão user-facing pior que a
duplicação. Daí a sequência da [[A40.l2]]: **medir → conter → corrigir a montante →
re-ancorar → quarentenar**, sem tocar `_hash_v2`.

**3. Os 7 achados "inertes" eram um evento de embarque de regressão.** Estavam
`não-acionável`, mas são inertes **porque a [[A40.l4]] os bloqueia** — e a l4 é P0
desta sprint. No instante em que fechar, sete defeitos chegam ao usuário de uma vez,
por um PR correto. Reclassificados para `procede-bloqueado · depends_on A40.l4`, com
re-triagem item-a-item como **critério de aceite bloqueante** da l4.

**4. Padrão transversal não registrado: os gates do repo medem produção, não
consumo.** Três instâncias na mesma rodada — RV3-04 (ADR entregue sem registro do
flip), RV3-03 (CV9 verde medindo geração), RV3-13 (campo sem consumidor). É o
invariante violado por trás da metade dos achados, e a razão de a [[A40.l5]]
(codegen + gate de contrato) ser a alavanca estrutural da sprint.

**5. Viés direcional agregado.** Quatro defeitos independentes empurram o relatório
na **mesma direção otimista**: principal como renda recorrente, cobertura na janela
mais lisonjeira, dupla contagem inflando receita, prazo de IF impresso como fato.
Erro aleatório se distribui; erro sistemático numa direção é assinatura de
mecanismo. **Cada PR que altera número exibido declara o sinal esperado do delta**
(`↑`/`↓`/`=`) e `dev/golden_diff.py` confere — divergência entre declarado e medido
bloqueia o merge.

**6. Prioridade invertida, corrigida.** RV3-11 (l9) era P2 abaixo de RV3-07 (P1) que
**depende dele**: o gatilho do CTA que RV3-07 quer construir depende de
`receita_pj_anual > 0`, que RV3-11 zera. Promovido a P1 e ordenado à frente.

**7. Aceitação indevida na revisão original.** Eu havia fechado RV3-31 (duas taxas
de retirada) como refutado, "aceite cumprido nas duas superfícies". O
`financial-planner` mostrou que RV3-31 e RV3-26 se contradizem na mesma tabela: uma
das superfícies lê chave inexistente e cai em **default hardcoded** — o aceite foi
verificado contra uma constante, não contra o payload. Os números coincidem **por
acidente**. RV3-31 vira `procede-fechado-em RV3-26` ([[A40.l5]]).

**8. Os "3 dados que faltam" eram 1.** O `regime` já é derivável de documento
ingerido (`FinanceiroPJSnapshot.regime_declarado` é computado e nunca consultado), e
`dependentes.count = 0` é **observação**, não ausência. Só a taxa da dívida é ask
genuíno. Tratar os três como iguais produziria um wizard perguntando o que o sistema
já sabe — queimando a única janela de atenção do dono no item de menor valor.

## Fora do sprint (disposição explícita)

- **RV3-19** (métrica do parecer fabricável) — já tem dono ativo com co-design em
  [[PLAN-pipeline-review-r2]] §Onda C; a medição da r3 mostra **10/10 valores
  conferindo** (fabricação *possível*, não *realizada*). Abrir lane paralela criaria
  duas fontes de verdade no mesmo arquivo. **Nota do `prompt-engineer`:** o bloqueio
  declarado lá (dep. catálogo KPI curado) é artefato da enforcement escolhida — com
  *drop-field* em vez de *drop-item* (padrão que o repo já adotou em [[ADR-294]]) a
  fabricabilidade fecha sem o catálogo. Isso **destrava** a fila serializada atrás
  dele; registrar no plano r2, não aqui.
- **Raízes de RV3-18** ([[ADR-246]], identidade de imóvel) e **RV3-22**
  ([[ADR-090]], string em campo numérico) — permanecem em [[PLAN-pipeline-review-r2]];
  a A40 absorve só as facetas user-facing ([[A40.l6]], [[A40.l5]]).
- **RV3-31** — refutado; sem gatilho próprio (ver §Decisões nº 7).

## Achado novo do painel (fora dos 33)

`max_total_input_tokens` e `max_tool_iterations` no manifest do parecer são **teto
declarativo**: parseados e nunca enforçados. Qualquer raciocínio de custo/latência
apoiado neles é infundado — o único teto vivo é `max_exec_context_bytes`. Manter um
teto que não trava é pior que não ter, porque induz revisão a assumir proteção
inexistente. Severidade Médio/P2, owner `prompt-engineer` → entra na [[A40.l8]].

## Achados da construção do harness de captura (2026-07-30)

Ao instrumentar a verificação renderizada, o caminho de produção de PDF revelou
**dois defeitos independentes que quebravam o download do cliente** — ambos com
prova vermelho/verde contra o frontend real, ambos **corrigidos** na mesma passada:

1. **`token_version` não propagava** em `download_pdf.py`. `create_access_token`
   nasce na versão 0; todo usuário que já invalidou sessões está em ≥ 1, então o
   token efêmero era rejeitado com 401 e o endpoint devolvia **HTTP 500**.
2. **Header `Authorization` não passa pelo gate client-side.** O gate de
   `/reports/[id]` lê o token de `localStorage`; `render_pdf` só injetava o header,
   então a página redirecionava para `/login` e o `wait_for_function` estourava —
   **mesmo com token válido**. Confirmado isoladamente: com token válido e sem
   semear `localStorage`, `ready=false`; semeando, `ready=true`.

Regressão coberta por `backend/tests/test_pdf_auth_contract.py`, incluindo um teste
de contrato que falha se alguém renomear a chave de auth no cliente.

**Efeito colateral útil:** o harness confirmou o **RV3-04 por medição** — 31 âncoras
de navegação, 1 sem alvo (`found: false, height: 0`). O achado deixou de ser
inferência de código. A [[A40.l7]] mantém o gate; a ferramenta só observa.

## ADRs

| ADR | Estado | Escopo |
|---|---|---|
| **[[ADR-354]]** | a abrir `Proposto` na [[A40.l2]] | Identidade de transação (K4) exclui atributos de proveniência do documento |
| [[ADR-337]] | emenda na [[A40.l6]] | Critério 4 (gate de PII no view-model) não existe |
| [[ADR-351]] | flip na [[A40.l12]] | Retorno de principal não é renda recorrente |
| [[ADR-353]] | flip na [[A40.l11]] | Confiança do diagnóstico — **bloqueado** até o campo-portador ter consumidor |
| [[ADR-278]] | **não** superseded | `_hash_v1` congelado; a A40 não cria `_hash_v3` |

## Débito de método herdado da r3

A própria rodada que originou este sprint registrou 5 furos de processo. Três já
viraram regra na skill `report-review`; dois viram trabalho aqui:

- **Conservação por grupo não detecta duplicação entre grupos** → [[A40.l1]].
- **Ninguém renderizou tela nem PDF** → toda lane de `clareza-ux` desta sprint
  exige **uma passada de verificação renderizada** (navegador ou `pdftotext`) no
  critério de aceite. Sem isso, a lane fecha sobre inferência de código.
