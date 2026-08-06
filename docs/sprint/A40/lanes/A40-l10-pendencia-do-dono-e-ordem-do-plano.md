---
id: A40.l10
type: lane
title: "Ordem do plano com critério encodado + pendências acionáveis do dono"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l10-pendencia-do-dono-e-ordem-do-plano
adrs: []
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
