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

## Lanes (26)

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
| [[A40.l24]] | Asserção "0 LLM" do gate F2 passa a medir no boundary do SDK | P1 | — | promovida da [[A41]] · [[ADR-355]] · [[PLAN-go-shell]] |
| [[A40.l25]] | Honestidade do cone de IF: precisão de exibição + `sigma` como premissa auditada | P1 | — | residual de [[ADR-360]] §Def. 1 + `ADR-361` §Def. 5 · KR-E |
| [[A40.l26]] | Cobertura do solver de prazo IF (aporte 0 com retorno > 0 converge) | P2 | — | [[ADR-360]] §Def. 6-7, abertos *pelo* #1158 · co-design `financial-planner` |

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

**Onda 3 — degradação honesta** (na ordem reader-first que esta seção declara:
[[A40.l21]], [[A40.l18]], [[A40.l19]], [[A40.l20]], [[A40.l22]]). Fecha a classe que o
incidente expôs: contrato de criticidade de stage, `partial_failure` alcançável, e
o retido declarado na tela. É a §Frente 4 de [[PLAN-report-trust]] — leia lá a
tese, os KRs (KR-0..KR-3), o tripwire T1 e os guardrails G1/G2.

**Ordem interna, e nenhuma das três é estética:**

- **[[A40.l21]] antes de [[A40.l18]]** (reader-first). Os **7** read sites de
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

**Fora de onda — [[A40.l24]] · ✅ `9b7d330e` (#1157), 2026-08-03.** Promovida da
[[A41]] pelo critério de **consumidor datado**: o [[TRACK-f2-cutover]] declara que
nada mais avança sem o dono rodar `make go-parity`, e a asserção "0 invocação
LLM" do Tier-1 era vacuamente verde. Não é tema report-trust e não compartilhou
arquivo com nenhuma lane daqui — não deslocou escopo.

O que ficou medido: a asserção tinha sido **invertida** por #1151 —
`requires_llm_fallback` só é escrito quando a visão da Caixa **falha**, então o
gate reprovava o braço sem credencial (zero chamada) e aprovava o que fez chamada
paga; como o `_go-on-native` injeta a key só no braço Go, o veredito ficava
invertido **entre os braços**. Trocado por **impedir** em vez de detectar
(`LLM_FREE=1` apaga a credencial dos dois braços, marcador verificado na saída do
`make`), com prova de mutação nos dois sentidos. Detalhe e a correção de premissa
da lane (medir no boundary do SDK é inalcançável no harness) no §Entregue dela.

> **Pendência com o dono, não fechada pelo PR:** o critério "run com
> `skip_llm=True` sobre o corpus do dogfood ⇒ 0 chamadas ao SDK e 0 rows novas em
> `LLMCallLog`" exige a stack local e **não foi executado** — a lane subiu a
> `shipped` com a prova de mutação (unit) e sem a prova ao vivo. Registrado em
> [`OWNER-GATED-active.md`](../../_MOC/OWNER-GATED-active.md) §1; a asserção
> mordendo de verdade só se confirma no 1º `make go-parity` do dono.

**Onda 4 — o que depende das anteriores** ([[A40.l6]], [[A40.l10]], [[A40.l11]],
[[A40.l13]], [[A40.l14]], [[A40.l15]], [[A40.l23]]). A l15 entra aqui — estava na
tabela e fora das ondas desde que nasceu (spun off da l3, 2026-07-31): depende da
l3 (shipada), é P2, e toca as mesmas superfícies de relatório que l11/l13, logo
rebaseia sobre a [[A40.l22]] pela mesma regra de arquivo-compartilhado. **Mover é
decisão do dono** — coloquei onde o critério declarado da sprint a coloca, não por
preferência.

**[[A40.l26]] também fica fora das ondas** (aberta 2026-08-03): carrega o
residual determinístico que o #1158 abriu ao fechar o §Def. 5 — `_solve_prazo`
não implementa os ramos `aporte == 0, r > 0` e `r == 0, aporte > 0`, que
convergem (~35 anos no dogfood). É P2 e não P0 porque o custo é **informação
retida**, não falsa: o #1158 já trocou a sentinela por ausência. Toca
`if_projector.py`, disjunto da l25 (`if_monte_carlo.py`) — paralelas.

**[[A40.l25]] fica fora das ondas, por definição** (aberta 2026-08-03): é o
residual das §Entregas fora de lane, cujo código já está em `main` ou em PR
aberta. Não compartilha arquivo com nenhuma onda — `if_monte_carlo.py` +
superfícies de exibição de S7 — e depende só de #1162 aterrissar. Sequenciá-la
dentro de uma onda seria acoplar sem motivo. Como l24: roda em paralelo.

**Precedência de corte:** nunca cortar [[A40.l16]] nem [[A40.l18]]. Cortáveis, em
ordem: [[A40.l17]], marcador em `/reports` (já fora de escopo), dead-letter (já
fora, por gatilho). **Nada sai da A40** — decisão do dono, 2026-08-03: a onda 0 e
a onda 3 entram por cima do escopo existente, sem despejar lane P2/P3 para A41.

**A ordem não segue a coluna de severidade, e isso é deliberado.** O painel
apontou que a severidade desta rodada não é insumo confiável de sequenciamento: os
7 `CONFIRMADO` são confiáveis, os **37 `PARCIAL` carregam inflação desconhecida**
(débito de método #3 da própria r3 — zero refutado em 36 clusters). A ordem aqui é
por **"alcança o usuário na configuração atual"**, e começa pelo que foi **medido**.

## Estado da Onda 1 (2026-08-03) — o que shipou e o que a Onda 0 não invalida

Três lanes da Onda 1 estão em `main`, entregues **antes** da Onda 0 existir
(ela nasceu em 2026-08-03, do incidente `2ded7aab`):

| Lane | Commit | O que ficou medido |
|---|---|---|
| [[A40.l1]] | `92a91884` (#1118) | 261 colisões cross-grupo · Σ 81.288.000 cents · baseline congelado off-git · 8 ratchets provados por mutação |
| [[A40.l3]] | `b12aff30` (#1124) | `janela_12m` passa de 0 consumidores a leitura por seletor único; rótulo impresso (tooltip não sai no PDF) |
| [[A40.l4]] | `6c5d9814` (#1139) | precedência de 3 fontes declarada ([[ADR-356]]); 7 → 12 seções entregando parágrafo |


**A precedência da Onda 0 sobre a Onda 1 é real, e não retroage sobre o baseline
da l1.** O argumento da Onda 0 é que medir exige run que completa. Isso vale para
todo gate que dependa de **run com parecer** — inclusive o §Gate de saída do
dogfood de [[PLAN-report-trust]], que não pode iniciar o contador de 2 re-runs
consecutivos antes da [[A40.l16]]. Mas a medição da l1 é
`dev/certify_ledger_local.py`, que é **read-only, sem Celery e sem LLM**: re-deriva
E3+E4 in-process sobre o E2 persistido. O caminho que o incidente quebrou (parecer
→ `needs_review` → `success: False` → zero linha em `reports`) **não participa**
dessa medição. As 261 seguem válidas como baseline de KR-B.

O que **não** foi cumprido nas três: a re-triagem bloqueante da l4 (os 7 achados
inertes verificados contra output renderizado) morreu por limite de gasto e a lane
mergeou sem ela. O risco ficou delimitado — s4 entrega sem contagem, s8 sem DAS,
s9 suprimido, e o `s3` foi desligado depois (#1144) — mas não verificado.

> **Imprecisão do parágrafo acima, nomeada e não corrigida (2026-08-03).** "Morreu
> por limite de gasto e a lane mergeou sem ela" descreve a **3ª passada**, não a
> re-triagem: ela rodou **duas vezes e bloqueou nas duas**. A cronologia precisa
> está em [[A40.l4]] §Fechamento; a pergunta que sobra está na §Pendências de
> decisão nº 4. Reescrever este parágrafo ficou fora do escopo fechado da passada
> que corrigiu a lane.

## Entregas fora de lane (2026-08-03)

Trabalho que **shipou dentro da janela desta sprint sem lane própria** — nasceu de
gate/achado, não do backlog dos 33. Registrado aqui porque a §Lanes não o cobre e
sem isso a sprint fecharia dizendo menos do que entregou.

| Entrega | Commit | ADR | O que ficou medido |
|---|---|---|---|
| Determinismo do cone de IF | `35acc75e` (#1156) | **[[ADR-360]]** `Proposto` | Cone era sorteado da entropia do SO (0,7% de diferença entre runs com input idêntico). Seed passa a ser constante de modelo + guard de boundary; `n` 10k→50k (dispersão 2,4%→1,2% a 85 ms); proveniência (`mc_version`/`seed_usado`/`n_simulacoes_usado`) no artefato; schema do bloco fechado. Mediu que **subir `n` não compra reprodutibilidade** (0,2% sobra a 1 M) |
| Sentinela de não-convergência | `7107b956` (#1158) | — | `prazo_anos_realista` não projetável emitia 999, somado à idade virava `idade_meta_usada: 1040` em path citável formatado como "anos". Passa a emitir ausência com motivo. Fecha o item 5 do §Deferimento da [[ADR-360]] |
| Percentil censurado do cone | #1162 (**aberta**) | **`ADR-361`** | `Pk` do ano de IF saía da base **dos sobreviventes** (otimista, e mais otimista quanto pior o plano) enquanto `prob` usava `n` cheio. Passa a quantil na base cheia com censura declarada por percentil; corrige também o truncamento de `int(np.percentile)`. `mc_version` → `3.0` |

**O que sobra dos três** está na [[A40.l25]] e na [[A40.l26]] — não em §Deferimento de ADR, que é
invisível ao `SPRINT_CURRENT`.

**Owner-gated destas entregas** (também em [[OWNER-GATED]]): flip da [[ADR-360]] e
da `ADR-361` `Proposto` → `Decidido`; **nota one-shot de recalibração** no
primeiro relatório pós-merge (seed + `n` + censura deslocam todo o bloco de IF, e
sem a nota a leitura racional de "IF em 2040" virar 2041 é "meu plano piorou");
**re-rodar o Tier-1** do gate F2 (`make go-parity WS=<dogfood> RUNS=2`) para
confirmar 0 diff residual no controle Py↔Py sem allowlist para o cone.

## Pendências de decisão (2026-08-03)

Nove perguntas de **higiene interna desta sprint**. Deliberadamente **não** entram
em [[OWNER-GATED]]: aquele registro é de gates estratégicos entre planos
(licença, flip de cutover, LGPD), e misturar higiene de sprint diluiria o sinal
dele. Cada item traz o que foi **medido** sobre `origin/main` (`a1e70223`) e
termina em pergunta — nenhuma decisão embutida.

**1. Qual é o predicado do campo `status` de lane?**

O campo não deriva de regra declarada e está **anti-correlacionado** com dependência
satisfeita. Medido no frontmatter das 24 lanes:

- **Mesma onda, mesmo `depends_on`, `status` diferente** — [[A40.l2]] (`open`) e
  [[A40.l12]] (`planned`) estão as duas na Onda 2 e dependem as duas só de
  [[A40.l1]], que está `shipped`. Segundo par: [[A40.l14]] (`planned`) e
  [[A40.l23]] (`open`), as duas na Onda 4, as duas sem `depends_on`.
- **8 lanes com todas as deps satisfeitas estão `planned`** (l5, l7, l8, l11, l12,
  l13, l14, l15) enquanto **3 lanes com dep não satisfeita estão `open`** (l18
  depende de l21 `open`; l20 de l18 `open`; l22 de l20 `open`).
- O enum do schema admite `planned` · `open` · `in_progress` · `blocked` ·
  `shipped` · `cancelled`. **`blocked` não é usado por nenhuma das 24.**

`status` significa "dep satisfeita", "onda aberta", "alguém pegou", ou nada
verificável? Se houver predicado, quem o deriva e quando?

**2. A [[A40.l20]] pode abrir PR antes de a [[A40.l18]] mergear?**

A prosa afirma que sim em **3 lugares** (`_README` linha da l20 na tabela de lanes ·
`_README` §Ondas ordem interna · [[A40.l20]] blockquote de abertura, e um 4º em
[[PLAN-report-trust]]), sempre na forma "depende da *decisão*, não do *merge*". O
frontmatter da l20 declara `depends_on: ["[[A40.l18]]"]`, que é a única relação de
dependência do schema — `parallel_with` existe e é usado por 2 das 25 ([[A40.l24]] →
[[TRACK-f2-cutover]] e [[A40.l25]] → [[A40.l11]]), mas não expressa "depende da
decisão". Qual das duas leituras
vale para quem pega a lane: a prosa ou o frontmatter?

**3. A tabela de evidência da emenda da [[ADR-304]] tem 8 linhas — o denominador 9 é
o quê?**

Medido na tabela (linhas 127-134 do arquivo da ADR): **8 linhas de dado**; **7 de 8
(87,5%)** têm `number_in_prose` > 0; **6 de 8 (75%)** tiveram item apagado (a linha
de 2026-07-31 é o run que falhou, com `—` na coluna de apagados). E **7 documentos**
afirmam "9 runs" / "8 de 9" / "89%": [[ADR-304]], [[ADR-296]], [[ADR-358]],
[[PLAN-report-trust]], este `_README`, [[A40.l16]] e [[A40.l22]]. O run do incidente
`2ded7aab` **já é** a 1ª linha da tabela. Falta uma 9ª linha que existe e não foi
tabulada, ou o denominador 9 — e os 89% derivados dele — está errado?

**4. A re-triagem bloqueante da [[A40.l4]] conta como critério cumprido?**

Cronologia medida e agora escrita na lane: rodou **2×** e **bloqueou nas 2**; a 1ª
achou C29 e C32 `agora-visível-e-errado`; a 2ª achou C32 resolvido e provado por
mutação, C29 ainda errado (o DAS *recolhido* que substituiu a estimativa também era
falso) e **2 contradições novas** (`s4` com 6 imóveis contra 4 na seção; CV9 contando
7 de 7 com o render entregando 6); a **3ª passada, pós-remediação final, não rodou**
(limite de gasto). "Rodou 2×, bloqueou 2×, corrigido, 3ª passada não rodou" satisfaz
o critério de aceite, ou a lane precisa da passada final antes de fechar de fato?

**5. A [[ADR-356]] flippa para `Decidido (A40.l4)` ou fica `Proposto` com o motivo
escrito?**

Medido: `status: Proposto` no arquivo; [[A40.l4]] (a lane que a implementa) está
`shipped` em `6c5d9814` (#1139). O CLAUDE.md §"Política operacional" diz que o PR de
implementação flippa a ADR no merge — mas o critério de aceite da lane não foi
integralmente cumprido (nº 4 acima). Flip agora, ou `Proposto` com o motivo do
não-flip registrado no próprio arquivo?

**6. Os 4 residuais que a [[A40.l4]] roteou para "lane própria" ficam na A40?**

Medido na §Residual da lane — 14 linhas, das quais **4** têm `Dono` = "lane própria":

1. **`s3` contradiz a tabela da própria S3** — 3 categorias no parágrafo, 2 classes
   na tabela (`lane própria (gate financial-planner)`).
2. **`perfil_familia.right` publica `n_imoveis`** — a contagem que o `s4` deixou de
   afirmar; contradição cross-seção com a tabela da S4.
3. **PD-20 — a meta de TRS não é configurável** — `PassiveIncomeConfig.trs_meta_pct`
   nunca é lido pelo `RatiosCalculator`.
4. **Base da cascata** — `receita_bruta = receita_pj_anual` em vez de
   `FinanceiroPJSnapshot.receita_bruta_total_anual` ([[ADR-238]]).

Uma 5ª linha tem disposição distinta ("lane pós-re-medição do balde": reintroduzir
DAS no `s8` e `das_simples` em `despesas_impostos` depois de re-medir o balde com o
matcher de `69a2fad4`). Esses ficam na A40 — e então precisam de lane, contra as 24
atuais — ou viram disposição explícita de não-fazer na §Fora do sprint?

**7. Onde mora o tripwire de revert da [[A40.l21]], e quem é o owner?**

A amarra "se a [[A40.l18]] escorregar >1 sprint, reverta a [[A40.l21]]" está em **3
lugares de prosa** (`_README` §Ondas · [[A40.l21]] §Decisão · [[PLAN-report-trust]])
e em **nenhum mecanismo**: este `_README` não tem seção própria de gate de saída nem
de DoD — todas as menções a "gate de saída" fora desta seção (tabela de lanes,
§Ondas, §Estado da Onda 1) são ponteiro para [[PLAN-report-trust]] §Gate de saída do
dogfood — e o frontmatter da sprint declara `date: "2026-07-30"` sem data de fim. Sem
data de fim, "escorregar >1 sprint" não é avaliável. Qual artefato hospeda o
tripwire, com que gatilho, e sob qual owner?

**8. Vale acrescentar o path off-git ao lado de cada número medido?**

Três números circulam na sprint sem caminho de re-medição para o próximo agente:

- **"261 colisões · Σ 81.288.000 cents"** (§Estado da Onda 1 e [[A40.l2]]) — a
  [[A40.l1]] declara o destino genérico `storage/<uuid>/certify/`, não o dump.
- **"105/105 grupos"** (§Tese, [[A40.l1]], [[ADR-354]], [[REPORT-REVIEWS-active]],
  [[SPRINTS-active]]).
- **"25m23s e US$ 1,5655"** do run `2ded7aab` ([[A40.l16]], [[PLAN-report-trust]]).

Número sem path força o próximo agente a re-medir do zero ou a confiar. Anexar o
path off-git virá convenção da sprint, ou fica caso a caso?

**9. A precedência não-negociável da Onda 0 bloqueia a [[A40.l9]]?**

A [[A40.l9]] é a única lane da Onda 1 que não shipou (`status: open`, sem
`depends_on`). O §Estado da Onda 1 escreveu a isenção **só para a medição da
[[A40.l1]]** — `dev/certify_ledger_local.py` é read-only, sem Celery e sem LLM. O
critério de aceite da l9 são 3 casos em
`backend/tests/test_tributario_run_scoped_inputs.py` **mais** conferência de delta
`↑` por `dev/golden_diff.py`. A l9 está isenta pelo mesmo argumento da l1, ou o
golden_diff a amarra a um run completo — e portanto à [[A40.l16]]?

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
- **Rota alternativa ao choke-point LLM** ([[A41.l2]] E0 · [[A41.l3]] Caixa ·
  [[A41.l4]] gate de ausência de rota) — deferida na [[A41]] `candidate` por
  decisão da [[ADR-355]] §Escopo, **não** é para atacar antes do fim da A40. Só a
  [[A40.l24]] veio para cá, pelo consumidor datado. A l3 exige ADR `Proposto`
  (`senior-cto` + `prompt-engineer`) antes de dimensionar, e carrega uma
  **restrição de ordem** achada em 2026-08-03: `extract_with_llm` pula PDF
  escaneado sem entrar em `processed` **nem** em `errors` (stage reporta
  `success: True`), então deletar o call-site da Caixa antes de fechar esse gap
  troca "conta some no Tier-1" por "conta some em todo tier, sem sinal".

## Infra de CI tocada durante a sprint (não são lanes)

Duas correções de CI achadas ao entregar a [[A40.l24]]. Não têm lane porque não
são escopo report-trust e não competem por capacidade — mas ficam registradas
para não virarem mudança órfã de política:

| O que | Estado | Por quê |
|---|---|---|
| `backend-tests` `timeout-minutes` 12 → 20 | ✅ `9b7d330e` (#1157) | A política declarada no job ("2× tempo observado", de maio a ~7:30) erodiu para **1,15×**: medido nos 6 PRs de 2026-08-03, 9m02s–10m21s contra teto de 12. Reprovou o #1157 duas vezes por variância de runner, com diff que não alcança o job. Teto não muda custo de Actions (cobrança é por minuto consumido). |
| Investigação "por que a suíte dobrou" (5-8min em maio → 9-10min) | ⏳ **#1160 aberto** — emenda [[ADR-210]] | O bump acima para o falso-vermelho mas não explica o crescimento. **Se a sprint fechar com #1160 aberto, a baseline e a regra de dimensionamento não ficam registradas.** |
| Label cosmético fora do caminho de merge | ✅ `76b32d3a` (#1161) | `Apply size label` (action Docker) vivia no mesmo job que `Validate PR title`, que é required check, sem `continue-on-error` — i/o timeout do Docker Hub em `alpine:3.15` bloqueava merge do repo inteiro. O pin por SHA da action não cobre a imagem base dela, e o hook de pin do repo não alcança Dockerfile de terceiro. |

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

Estado lido do campo `status:` de cada arquivo em `docs/adr/` em **2026-08-03** —
não do que a lane prometeu. A tabela cobre as ADRs que o frontmatter `adrs:` das
26 lanes referencia, mais a [[ADR-278]] (que nenhuma lane referencia: é a nota de
que ela **não** é superseded) e as abertas por §Entregas fora de lane.

| ADR | Estado | Lane | Escopo |
|---|---|---|---|
| **[[ADR-354]]** | `Proposto` (aberta em #1114) · flip a `Decidido` no merge da [[A40.l2]] | [[A40.l2]] | Identidade de transação (K4) exclui atributos de proveniência do documento |
| [[ADR-337]] | `Decidido` · emenda na [[A40.l6]] | [[A40.l6]] | Critério 4 (gate de PII no view-model) não existe |
| [[ADR-351]] | `Proposto` · flip na [[A40.l12]] | [[A40.l12]] | Retorno de principal não é renda recorrente |
| [[ADR-353]] | `Proposto` · flip na [[A40.l11]] | [[A40.l11]] | Confiança do diagnóstico — **bloqueado** até o campo-portador ter consumidor |
| [[ADR-357]] | `Proposto` · flip no merge da [[A40.l18]] | [[A40.l18]], [[A40.l19]], [[A40.l20]], [[A40.l21]] | Criticidade de stage e degradação do run — add-on advisory não veta o entregável. **A mais carregada da sprint: 4 lanes** |
| [[ADR-358]] | `Proposto` | [[A40.l16]] | Enforcement em produção exige budget de produção — e KR no plano onde ele age |
| [[ADR-356]] | `Proposto` | [[A40.l4]] (`shipped`) | Precedência declarada do parágrafo de seção e CV9 como medida de entrega. **Flip pendente** — ver §Pendências de decisão nº 5 |
| [[ADR-355]] | `Decidido` | [[A40.l24]] | Intenção "sem LLM" do run é propagada até o stage, não só até a lista de stages |
| **[[ADR-360]]** | `Proposto` · flip pendente no dono | — (fora de lane, #1156) · residual em [[A40.l25]] e [[A40.l26]] | Seed do cone Monte Carlo é constante de modelo versionada, não entropia do SO. Rejeita seed derivado do input por quebrar monotonicidade em patrimônio/aporte |
| **`ADR-361`** | `Proposto` · PR **aberta** (#1162) | — (fora de lane) · residual em [[A40.l25]] | Percentil de tempo-até-o-evento só é publicável como ano se a taxa de sucesso o define — censura declarada na base cheia |
| [[ADR-359]] | `Decidido` | — (fora de lane, #1154/#1155) | Dispatch assíncrono falha alto e quem cria estado pendente compensa |
| [[ADR-304]] | `Decidido` · emendada 2026-08-03 | [[A40.l16]] | Pureza monetária da prosa do parecer; a emenda revoga a doutrina `==0` da §2 |
| [[ADR-345]] | `Roadmap` | [[A40.l23]] | Propagação do taint E2→E5 e selo de qualidade no read-path — adoção deferida; expôs a classe de reserva-de-ID invisível |
| [[ADR-306]] | `Decidido` | [[A40.l15]] | Base temporal de mensalização no E5 — janela canônica 12m + rótulo por bloco |
| [[ADR-240]] | `Decidido` | [[A40.l7]] | Card `S_PROTECAO` no relatório (pilar de proteção patrimonial) |
| [[ADR-204]] | `Decidido` · emenda provável na [[A40.l20]] | [[A40.l20]] | Imutabilidade do parecer pós-publicação; §D1 é quem fixa o vocabulário de `PlannerReview.status` |
| [[ADR-278]] | `Decidido` · **não** superseded | — | `_hash_v1` congelado; a A40 não cria `_hash_v3` |

## Débito de método herdado da r3

A própria rodada que originou este sprint registrou 5 furos de processo. Três já
viraram regra na skill `report-review`; dois viram trabalho aqui:

- **Conservação por grupo não detecta duplicação entre grupos** → [[A40.l1]].
- **Ninguém renderizou tela nem PDF** → toda lane de `clareza-ux` desta sprint
  exige **uma passada de verificação renderizada** (navegador ou `pdftotext`) no
  critério de aceite. Sem isso, a lane fecha sobre inferência de código.
