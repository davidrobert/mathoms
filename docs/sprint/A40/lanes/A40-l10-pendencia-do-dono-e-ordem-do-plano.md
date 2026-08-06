---
id: A40.l10
type: lane
title: "Ordem do plano com critério encodado + pendências acionáveis do dono"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l10-pendencia-do-dono-e-ordem-do-plano
adrs: ["[[ADR-365]]"]
depends_on: ["[[A40.l9]]"]
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/produto
---

# A40.l10 — `pendencia-do-dono-e-ordem-do-plano` (RV3-07, RV3-10, RV4-02)

## Problema

A revisão concluiu, para "a principal recomendação é a certa?": **direção sim,
ordenação indeterminada**. Três causas:

1. **A maior alavanca declarada está fora do ranking** — bloqueada por perfil
   tributário incompleto, e **sem nenhuma pendência acionável** que peça o dado.
2. **Nenhum critério de ordenação está encodado.** A ordem sai do julgamento de
   dois braços que compartilham a mesma persona. Sob "prazo legal primeiro", outro
   item venceria.
3. **A premissa da recomendação nº 1 é contestada pelo próprio payload** (RV3-10):
   o gap cita dependentes menores enquanto o bloco estruturado conta zero. A
   narrativa nomeia um filho; nenhum campo o conta.

**Correção do painel (§Decisões nº 8):** os "3 dados que faltam" eram **1**. O
regime já é derivável de documento ingerido (`FinanceiroPJSnapshot.regime_declarado`
é computado e nunca consultado) e a contagem de dependentes zero é **observação**,
não ausência. Só a taxa da dívida é ask genuíno. Um wizard perguntando os três
queimaria a única janela de atenção do dono no item de menor valor.

## Escopo

> **Item P0 admitido em 2026-08-04 (RV4-02, [[PIPELINE-REVIEWS-active]] §r4).** A
> primeira decisão da fila é **descartada** da única seção que responde "o que fazer":
> o cabeçalho de aporte ocupa "Prioridade 1" incondicionalmente e a fila é enumerada a
> partir do segundo item, então a decisão registrada pelo dono não chega ao leitor — e
> duplica quando outra decisão da fila também é de aporte. Âncoras:
> `charts_narrator.py:417-433` (descarte) e `S10SinteseSection.tsx:16-17` (render
> confirmado). Entra **como item desta lane, não como lane nova**: é a mesma superfície
> (ordenação do plano + S10) e o mesmo dono, e o critério de aceite abaixo já exige que
> recomendação não-computável nunca desapareça sem rastro. Admissão pela cláusula 1 do
> §Critério de admissão da [[A42]] (destino é quem já possui a superfície).
> **Nota de execução:** ler o diff de #1188 antes de começar — a [[A40.l9]] mexeu na
> materialização adjacente. Esta lane flipou `planned → open` e `P2 → P1` na mesma
> admissão, já que a dependência [[A40.l9]] shipou.


- Enum `elegibilidade` no item do plano de ação, avaliado no builder, com docstring
  co-localizado (methodology-as-code).
- ~~Consultar o regime declarado em vez de perguntar.~~ → **reformulado em
  2026-08-05:** declarar o regime como pendência de **confirmação**
  (pré-preenchida com o indício + proveniência rotulada), **nunca** como input
  da cascata. O texto original autorizava literalmente a promoção que a medição
  recusa — ver §Fora de escopo.
- Pendência acionável **só** para a taxa da dívida.
- ~~Critério de ordenação **encodado e auditável**.~~ → **desambiguado em
  2026-08-05:** encodado no ranking de `pontos_urgentes` (hoje a ordem literal
  dos `out.append` do analyzer). A fila de `Decision` fica **fora** — é
  governada pela [[ADR-179]], com a garantia estreitada pela §Emenda
  2026-08-05 dela. Sem essa desambiguação o próximo revisor reabre RV3-07
  sobre a superfície errada.

> **Correção de escopo — 2026-08-05.** Dois dos quatro bullets acima partiam de
> premissa medida como falsa. `elegibilidade` continua, mas **avaliado no
> `PontosUrgentesAnalyzer`** — não no `E5NarrativasBuilder`: a projeção é
> achatada para `list[str]` de títulos antes de chegar ao narrador
> (`generate_narratives._decisoes_titles_from_bundle`), então enum posto ali
> nasce inerte.

## Critério de aceite

> **Correção de premissa — 2026-08-05** (painel `financial-planner`,
> `senior-cto`, `product-designer`, `data-engineer`, `product-manager`,
> `information-architect`; 6/6 aprovaram com ressalva). O primeiro critério
> abaixo **encodava uma regra falsa** e foi substituído. O texto original fica
> preservado logo abaixo, tachado — reescrever sem preservar transformaria
> "corrigimos um critério mal-escrito" em "afrouxamos o critério para caber no
> entregue", acusação barata de fazer e cara de defender num gate de saída
> declaradamente adversarial.
>
> ~~KR-E: fixture com contagem de dependentes zero + regra que cita dependentes
> menores ⇒ item marcado `refutada_por_payload` e **ausente** do plano
> renderizado.~~
>
> **Por que cai:** `dependentes_menores_18` e `irpf_kpis.dependentes.count`
> medem **populações diferentes** — cadastro da família (`protecao_wiring.py`,
> `papel ∉ {titular, conjuge}` + idade) versus ficha da declaração do ano-base
> ([[ADR-305]], último ano **completo**, defasado 1-2 anos). Divergem nos dois
> sentidos sem que nenhuma esteja errada. Detalhe e âncoras no re-veredito de
> RV3-10 em [[REPORT-REVIEWS-active]] §r3 (`procede` → **refutado**).
>
> **Governa o KR-E da [[A40]], não este arquivo.** O KR admite **duas** saídas
> ("...no topo do plano ... **sem pendência pareada**") e o critério antigo
> admitia uma só (remover) — media, portanto, um critério mais **forte** que o
> KR, engessando o desenho e virando falso-vermelho para quem escolher a saída
> legítima de parear. E "ausente do plano renderizado" colidia com a **6ª
> classe** do §Critério de done do [[PLAN-report-trust]] ("nenhuma retenção de
> conselho sem declaração por classe de motivo no artefato entregue").

- **KR-E** ([[A40]] §KRs — *honestidade da recomendação*, não a sigla
  homônima de anti-regressão das sprints A37-A39): toda recomendação suprimida
  do **ranking** carrega, no artefato E5, a classe de motivo que a suprimiu
  **e** uma declaração na narrativa já renderizada. Nenhuma sai sem as duas —
  ausente do ranking, presente no artefato.
- A taxonomia é de **proveniência da premissa**, não de concordância entre dois
  campos: fixture com `conjuge_sem_renda_propria` (tautológico enquanto
  `protecao_wiring.py` fixa `renda_propria_brl = 0`) ⇒ item fora do ranking com
  motivo declarado.
- Fixture com regime ausente ⇒ item não some em silêncio: vira pendência com
  CTA. **Nota de medição (2026-08-05):** a pendência de regime **já existe
  renderizada** — `CascataFiscalCard.tsx::PerfilPendenteState` (S8) nomeia os 4
  campos que faltam e diz a quem pedir; veio com o card da cascata ([[ADR-236]],
  Sprint A16 L2 P5, #395), **não** com o CTO-05 (#973), que entregou a CTA no
  narrador (`tributario_narrator._narrate_perfil_pendente`). O que falta é
  âncora e posição no plano, não superfície.
- Recomendação não-computável **nunca** desaparece sem rastro.
- **Anti-falso-verde (decisão do `senior-cto`):** nenhum critério desta lane tem
  como alvo de asserção um campo de payload sozinho. Toda asserção é sobre a
  **string narrada**, na mesma fixture, com prova de mutação — inverter o input
  tem de mudar o **texto**, não só o payload.

## Entregue

**PR1 — RV4-02 (P0), 2026-08-05.** A primeira decisão do dono chega às duas
superfícies da S10. O defeito era **duplo** e a lane citava só metade:
`charts.top5_decisoes` enumerava `decisoes[1:5]` e `summaries.s10` enumerava
`decisoes[1:4]` — este último derrubando também tudo a partir da quinta e, com
≤3 decisões, afirmando a contagem **sem listar nenhuma**. Como
`report_layout.yaml` declara `S10.summary_source: "s10"`, o mesmo descarte
aparecia 2× na mesma seção.

O aporte saiu da numeração e virou enquadramento (`fmt_aporte_contexto`, produtor
único em `format_helpers` — o comentário "mesma guard do charts.top5_decisoes"
que existia no `s10` descrevia uma **segunda cópia**). Decisão de domínio do
`financial-planner`: aporte é um `Goal`, não uma `Decision`, e como é a única
linha que o motor sempre consegue calcular, ocupar "Prioridade 1"
incondicionalmente fazia o item mais fácil de computar ser sistematicamente o
mais importante — inversão dos padrões consagrados de planejamento patrimonial
brasileiro, que põem quitar dívida onerosa e formar reserva **antes** de aportar
e de assumir risco.

**Por que a suíte não pegava:** toda fixture do repo põe um título de aporte no
índice 0, então descartar `decisoes[0]` e reimprimi-lo como "Prioridade 1:
Aporte mensal" produzia texto plausível. `tests/test_e5n_entrega_da_fila_de_decisoes.py`
abre com uma decisão que **não** é de aporte; prova de mutação em 3 rodadas
(slice original, guard de meta zerada, guard de fila vazia) mata as asserções.

**Verificação adversarial do próprio PR (2026-08-05) — 7 achados, 1 deles P1.**
A 1ª rodada do fix corrigiu só o **início** do slice do `s10` (`[1:4]` → `[:4]`)
e deixou o teto em 4: com a fila cheia — que é **5**, o
`_TOP5_DECISION_LIMIT` — a frase afirmava "5 decisões" e listava 4, ao lado de
um card que listava as 5. Era a mesma classe de defeito que esta lane existe
para fechar, reintroduzida no fix. Escapou porque o teste de cauda do `s10`
usava fila **curta** (3 itens) — exatamente o recorte que evita o caso que
falha. Corrigido com teto compartilhado (`TOP_DECISOES_RENDER`) e asserção de
que as duas superfícies cortam no mesmo ponto.

Os outros 6: frase de aporte **repetida verbatim** nas duas superfícies da
mesma seção (resumo e card renderizam juntos — o enquadramento passou a viver
só no `s10`); `..` no `s10` quando o título do dono termina em ponto; `?.` no
card quando o título é interrogativo; `context` do estado vazio ainda
enunciando propósito sobre conjunto vazio; e 2 imprecisões de citação nas notas
de doc (`irpf_analyzer.py::_dependentes` não existe; `PerfilPendenteState` não
veio do #973). Refutados: 5, entre eles a alegação de que a mudança no
`chart_conclusions.yaml` seria fix inerte não declarado — o corpo do commit já
a declara.

**PR2 — elegibilidade (#1243), 2026-08-06.** Implementa a [[ADR-365]] + a nota
[[RULE-elegibilidade-da-recomendacao]].

O defeito que virou o coração do PR **não estava nos 3 achados que originaram a
lane**: `pontos_urgentes` não consultava `gap_qualitativo`, então *"Contratar
seguro de vida e invalidez / Alta / Imediato"* era emitido para **100% dos
workspaces sem apólice de pessoa** — inclusive titular solteiro sem dependente
econômico. Seguro de vida protege dependente econômico; sem dependente é custo
puro. Passa a mapear o predicado canônico da [[ADR-240]] (KPI F), derrubando de
**2 para 1** os produtores dele; `_has_apolice_vida_vigente` sai como código
morto. O canônico é mais **estreito** (exige cobertura de `vida`, não qualquer
bem `pessoa`): apólice de acidentes deixa de suprimir o item — verdadeiro-positivo
antes oculto.

`PontoUrgenteItem` ganha `code` estável + os dois eixos + `dado_faltante`.
`analyze()` devolve **uma** lista; a partição em ranqueados × retidos é projeção,
na serialização. O leitor que legitima o array de retidos é a frase por classe de
motivo no `s10` — `PontosUrgentesCard.tsx` fica **intocado**, porque a copy de
`degenerada` é decisão de superfície da [[A40.l22]].

**Delta é de população, não de valor** — o gate mecânico de golden é cego a
"quem recebe a recomendação". Medido nos dois substratos, que exercitam braços
opostos: no `dogfood_view_model` (dois adultos, sem dependente) o gap é
`sem gatilho` e o item **não é produzido** — não é retenção, é conselho que não
existe ([[ADR-167]]); no `e5n_delivery` (família com cônjuge) o gap é
`conjuge_sem_renda_propria`, o item sai do ranking como `degenerada` e o `s10`
**declara**: *"1 recomendação não entrou na lista: Contratar seguro de vida e
invalidez (a regra atual não distingue o seu caso)."*

**Dois erros meus, pegos por medição e não por revisão:**

1. O campo novo atravessa **três** construtores campo-a-campo e o
   `E5OutputInputs` o engoliu — com a suíte **verde** e a chave ausente do
   payload. Só apareceu rodando o substrato golden e imprimindo o E5. As provas
   de travessia passaram a derivar de `dataclasses.fields()`.
2. Marquei `rentabilidade_nao_medida` como `pendente_de_dado` e reverti: a
   premissa **é** verificável (o item dispara *porque* o dado falta) e o conselho
   é supri-lo — esconderia do ranking o item mais acionável. `pendente_de_dado`
   significa "não consigo avaliar se o conselho se aplica", não "o conselho é
   sobre um dado que falta".

Verificação: `pytest tests` 5855 · `pytest backend/tests` 3175 · TS 22/22 ·
prova de mutação em 4 rodadas matando 12 asserções · schema com
`additionalProperties: false` no item, que **compra gate hoje**
(`test_e5_golden_execution` valida um E5 gerado de verdade, fora do modo `warn`).

> **Nota de execução, 2026-08-06:** o merge do #1243 ficou bloqueado por
> **degradação do GitHub Actions** — `Service Unavailable` + `Failed to resolve
> action download info`, com o job de validação de título (que só lê uma string)
> falhando em 9m28s e 15m01s no `Set up job`, e o de pipeline estourando o
> timeout de 5m contra ~30-40s históricos. Não é o diff; a suíte está verde
> localmente. Re-run pendente.

## Estratégia decidida para PR2 e PR3 (painel 2026-08-06)

Segundo painel de 6 especialistas, com **22 objeções sustentadas** contra o
código e 2 caídas. **Substitui o §Desenho fixado de 2026-08-05** — três
premissas daquele registro não sobreviveram à medição, e estão corrigidas
abaixo. PR1 shipou (#1230); PR2 e PR3 seguem abertos.

### O achado que reordena a lane

**`pontos_urgentes` não lê `gap_qualitativo`.** `_seguro_vida_item` decide só por
"existe apólice com `tipos_bem` contendo `pessoa`" — não lê `flag_vida`, não lê
dependentes, não lê passivo. Consequência medida: **"Contratar seguro de vida e
invalidez / Alta / Imediato" dispara para 100% dos workspaces sem apólice,
inclusive solteiro sem dependente econômico.** Sob as três metodologias, seguro
de vida protege dependente econômico; sem dependente é custo puro. Não é
conservadorismo, é conselho errado — e é o item mais vendável do card, na frente
do cliente.

Isto **é** o caso de estreia da taxonomia, não um vizinho dela: é uma
recomendação no topo do plano cuja premissa o payload não sustenta, que é
literalmente o KR-E. Vai no PR2. `protecao` **já é parâmetro** de `analyze()` —
zero wiring novo.

### Três premissas minhas que a medição derrubou

1. **O fix "barato" da reserva não é barato — e a versão crua dele é
   regressão.** `_perfil_por_pct` **nunca retorna `clt_estavel`** (o comentário
   no próprio código diz que a contagem de fontes CLT não existe no fluxo v1 e
   assume a variante conservadora). Logo o **piso** de `meses_alvo` é **12**,
   não 6. Trocar `reserva_minima_meses` por `meses_alvo` cru faria toda família
   com 6-12 meses receber "Alta / Imediato" — enquanto `avaliacao_liquidity`, no
   **mesmo payload**, rotula essa faixa "Adequada", e o `HeroKpiGrid` pinta 8
   meses de **verde** com "Meta 18m (perfil de renda)". Alerta vermelho ao lado
   de KPI verde na mesma página é exatamente o que a sprint existe para impedir.
2. **`prazo` não é órfã.** Tem 2 leitores vivos: `dashboard_service` (serve
   `GET /dashboard`) e o manifest do parecer, que injeta `$.pontos_urgentes`
   raw. Declarar o shape no schema exige `description` nomeando os dois
   consumidores — senão a [[A40.l5]] mira o campo errado no cleanup.
3. **"O schema não é gate" é falso para este bloco.**
   `tests/test_e5_golden_execution.py` valida um E5 **gerado de verdade**, hard,
   fora do modo `warn`. Declarar `pontos_urgentes.items` com
   `additionalProperties: false` **compra gate hoje** e custa 1 fixture.

### Decisões que fecham os conflitos da rodada anterior

- **`Literal`, não `str, Enum`** (tie-break `senior-cto`, revendo a própria
  resposta anterior com evidência melhor): `ReviewReasonCode` é Enum por ter 3
  produtores, comportamento anexado e versionamento em schema próprio —
  `elegibilidade` não tem nenhum dos três. O precedente exato é `PctRendaSinal`,
  `Literal` **no mesmo módulo de proteção**. Vocabulário versionado **inline** em
  `e5_analysis.schema.json`, sem schema standalone.
- **`code` estável por regra é pré-condição, não enfeite.** Sem ele:
  `build_default_tarefas` numera `n = i + 1` sobre `pontos_urgentes` e
  `build_default_tarefas_status` chaveia por essa posição — **reordenar remapeia
  o status do dono para outra tarefa**, que é a mesma classe do RV4-02 que o PR1
  acabou de fechar. E `dev/golden_diff.py` cai em diff posicional sem chave
  natural. `code` entra no PR2 e destrava o PR3.
- **O Conflito 2 era falso.** [[ADR-167]] governa elegibilidade de **bloco
  irrelevante** ("este cenário não existe para esta família") — não há conselho
  a declarar. Aqui o conselho existe e a **premissa** é que não se sustenta.
  Três especialistas chegaram nisso independentemente. Emite-com-flag, e a
  metade que importa da ADR-167 (uma camada decide, o TS confia) sobrevive.
- **O leitor é a sentença narrada no `s10`, não o card.** `PontosUrgentesCard`
  fica **intocado** no PR2 — a copy de `degenerada`/`nao_verificavel` é decisão
  de superfície da [[A40.l22]], e leitor sem copy decidida é meia-superfície. A
  sentença por classe no `s10` já renderiza na mesma seção e sai no PDF: fecha o
  par produtor↔leitor sem antecipar a l22.
- **`conjuge_sem_renda_propria` fica em `protecao_analyzer`** e é marcado
  `degenerada` na camada de conselho. Remover o gatilho mudaria o payload
  `protecao_patrimonial` para outros consumidores; marcar é contido. Condição de
  deleção vai na ADR.
- **PR3 não estava bloqueado pelo que eu achei que bloqueava.** A má medição
  atinge os thresholds que decidem se o item **existe**, não o tier que ele
  **ocupa** — tier é constante por regra e é encodável hoje sem consumir nenhuma
  variável suspeita. O que gateava o PR3 era o `code`.

### Sequência

1. **ADR-365 `Proposto`** (docs-only, antes do código). Fixa os 2 eixos
   ortogonais com o contraexemplo que prova a ortogonalidade, `Literal` com
   condição escrita de promoção a Enum, `code` como identidade, os dois arrays
   como **projeção de uma lista única** (colapsar depois é deletar um ramo de
   serializer, não migrar dado), `degenerada` como valor **transitório** com
   condição de deleção, e o **§Estado-alvo** de convergência em ≤5 linhas.
   Alocar o ID **na escrita** (`ls docs/adr/ | tail`), nunca reservando em prosa.
   `adrs: []` da lane deixa de estar vazio no mesmo commit.
2. **PR2 — código.** `code` + `origem_premissa` + `elegibilidade` + `dado_faltante`
   em `PontoUrgenteItem`; `_seguro_vida_item` passa a mapear `gap_qualitativo`;
   `conjuge_sem_renda_propria` → `degenerada`; partição em `pontos_urgentes` (só
   `computavel`) + `pontos_urgentes_retidos`; sentença por classe no `s10`;
   `items` declarado no schema com `additionalProperties: false`. Prova derivada
   de `dataclasses.fields()` — não lista à mão. Asserção sobre a **string
   narrada**, com mutação nos dois sentidos.
3. **PR3 — ordenação + reserva.** Tier constante por regra, extraído para **um**
   helper puro compartilhado com `suggestion_rules` (não a terceira ordenação do
   mesmo domínio). Reserva: **piso 6 decide existência; `meses_alvo` gradua a
   prioridade dentro do item** (Alta se cobertura < piso; Média se piso ≤
   cobertura < alvo), copy nomeando o perfil — e `HeroKpiGrid.reservaTone`
   ancorado em `meses_alvo` no mesmo PR, senão nasce a contradição KPI×alerta.
   T0 de dívida **declarado inerte** no artefato, nunca encodado vazio: tier que
   nunca dispara ensina que "não apareceu dívida cara" = "não há dívida cara".
4. **Fecho da lane** (docs-only): RV3-07 parcialmente fechado, residual com
   §Deferimento datado.

**Forma dos docs (medida, não suposta):** o molde `rule-cenario-conjuge-estresse.md`
é **bloqueado pelo hook `sigilo-terms`** num arquivo novo — inclusive no campo
`methodology:` do frontmatter e na tag `methodology/<m>`; os 11 existentes só
passam por baseline. A RULE nova nasce **sem** esses dois. O fix da reserva não
vira ADR: é **emenda datada em [[ADR-218]]** + linha em `FORMULAS.md`.

### Fora da lane, com destino

- **Fórmula de `taxa_endividamento_pct`.** `scoring.json` declara unidade
  "% renda mensal comprometida"; o código calcula `dividas / patrimonio.bruto`.
  Mover a fórmula move o **score de todo workspace**, mais pontos fortes,
  alertas, red lines e a prosa do `s1`. **Lane única no sprint seguinte**, sob
  [[PLAN-report-trust]], **fundida** com o pipe `debts → E5` e o fix do parser da
  RL2 — são a mesma lane, porque `parcela_mensal` é o segundo campo morto do
  `DividaItem` e sem ele o endividamento por renda é **incomputável**. Exige ADR
  `Proposto` + baseline congelado antes do fix (padrão [[A40.l1]]).
  **No PR3, o ganho de maior ROI é de rótulo, não de fórmula:** trocar
  "Taxa de endividamento em 25% — meta < 20%" por "Dívidas equivalem a 25% do
  patrimônio bruto — referência < 20%". Zero mudança de cálculo.
- **Convergência das representações.** O painel mediu **cinco**, não três, e
  divergiu sobre o alvo: `senior-cto` e `product-designer` apontam `Suggestion`
  (que já tem `code`/`severity`/`kind`/`dedup_key` e ponte para `Decision`);
  `data-engineer` e `financial-planner` querem `pontos_urgentes` e `Decision`
  **separados** por serem agregados de donos diferentes (motor × dono). O que é
  consenso: `tarefas` não é conceito, é alias com perda; e a l10 **não funde**.
  O passo que a l10 dá é **o campo, não o store** — e a ADR-365 **tem** de nomear
  o alvo, senão o próximo agente reinventa `elegibilidade` dentro de
  `suggestion_rules` e passamos de cinco representações para seis.
- **Achados novos a registrar no fecho:** `rule_seguros_insuficientes` emite
  título **byte-idêntico** ao do analyzer (dois caminhos, mesma frase, mesmo
  usuário); `rule_reserva_insuficiente` está **morta** (`meses_cobertura` ×
  `cobertura_meses`, RV3-09, dona é a [[A40.l5]]); `dedupeBySemanticKey` é
  supressor não-declarado no frontend.

## Residual medido — achado novo, sem lane

**A fixture compartilhada Py↔TS muda sem disparar o job que a consome.**
`frontend/tests/components/report/sectionSummaryDelivery.test.tsx` lê
`../../../../tests/fixtures/narrativas/e5n_delivery.json` — **fora** de
`frontend/`. O filtro de path do job *Frontend checks* (`.github/workflows/ci.yml`
§`filter.frontend`) casa `frontend/**`, `design-tokens/**`,
`config/report_layout.yaml` e o próprio workflow; **não** casa
`tests/fixtures/narrativas/**`. Medido neste PR: o job saiu `skipping` num diff
que regravou a fixture duas vezes. Consequência: quebrar o contrato cross-stack
deixaria o CI **verde** — o par Py↔TS existe, o gate dele não fecha. Aqui o lado
TS foi rodado localmente (22/22), então o PR está coberto; o buraco é sistêmico.

**Não corrigido nesta lane, e a razão é custo, não esquecimento.** Acrescentar o
path ao filtro faz o *Frontend checks* (ESLint + tsc + Vitest + report render)
rodar em todo diff de fixture do pipeline, e a A40 já tem histórico de orçamento
de Actions estourado por contagem de jobs. É decisão de CI/CD com gatilho
`sre-devops`, não carona de PR de narrativa. **Destino:** [[A40.l5]] — é a lane
do contrato de view-model e do gate que cruza schema × tipos TS × readers Python;
este é o mesmo defeito na camada de disparo. Se a l5 não o adotar, vira item de
[[A42]] pela cláusula de camada (instrumento de certificação).

## Fora de escopo — com destino, não como cauda

Cada item abaixo saiu por medição, não por conveniência. A convenção do repo é
que **handoff só existe quando o destino o registra**; onde o destino ainda não
registrou, isto aqui é o emissor e está nomeado.

- **Promover `regime_declarado` a `CascataInput.regime`** — recusado. O nome
  engana: o valor é **inferido pelo LLM** quando o informe não declara
  (`pipeline/llm/prompts/informe_pj.py` manda deduzir por retenções e **chutar
  `simples_nacional`** no ambíguo, e mapear **Lucro Real → `lucro_presumido`**
  com `needs_review`), e `needs_review`/`confidence` são **descartados** em
  `fiscal_source._build_pj_summary`. Promover publicaria a cascata inteira sobre
  regime chutado, ferindo o invariante da emenda CTO-05 da [[ADR-236]]
  ("nenhum número tributário derivado quando o regime é desconhecido"). Há ainda
  3 obstáculos mecânicos: vocabulário incompatível (`simples_nacional` vs
  `simples`), 2º guard `anexo_simples is None` que mantém o Simples suprimido de
  todo modo, e o default morto `anexo_simples or "V"` — Anexo V é a tabela mais
  cara, e relaxar o guard inflaria a carga publicada ~2,5× na 1ª faixa.
  **§Deferimento datado (2026-08-05), condição de retomada:** quando
  `needs_review`/`confidence` do informe PJ deixarem de ser descartados **e** o
  prompt parar de chutar regime em ambiguidade.
- **Pipe `debts → E5.endividamento.taxa_juros`** — `debts.taxa_juros_aa` já tem
  coluna, DTO e formulário; falta o consumo (o E5 hardcoda `taxa_juros: None`).
  **Amarra escrita:** não popular a taxa sem corrigir, no mesmo PR, o parser da
  red line RL2 — ele exige o caractere `%` numa string contra um schema que
  obriga `number|null`, e compara contra `> 1.5` assumindo taxa **mensal**
  enquanto a coluna é **anual**. Popular sem isso troca um silêncio por erro de
  ordem de grandeza.
- **Os 4 predicados de "dependente"** — `protection_bundle_populator` filtra
  `role == "dependente"` e **exclui `role == "filho"`**, zerando o fator de
  cobertura de vida justamente para quem tem filho: o hero e o chip da S9 se
  contradizem para o mesmo cadastro. É defeito de **cálculo**, não de narrativa,
  e não tem código de rodada por ter sido achado em co-design.
- **Ordenação da fila de `Decision`** — não tocada de propósito: mudar
  `_top5_decisions_stmt` altera o payload de S10 de todo workspace e a causa
  raiz está a montante (o produtor não popula `priority`/`impact_1y`). O estado
  real ficou registrado em [[ADR-179]] §Emenda 2026-08-05.
