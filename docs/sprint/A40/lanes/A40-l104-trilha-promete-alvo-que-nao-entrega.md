---
id: A40.l104
type: lane
title: "A trilha sticky promete 20 alvos e entrega 10 em 1280px, 0 no telefone — e não há sinal de que falte algo"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_date: "2026-08-30"
ship_pr: 1860
priority: P2
branch_slug: a40-l102-trilha-promete-alvo-que-nao-entrega
owner: product-designer
depends_on: []
adrs:
  - "[[ADR-117]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p2
  - area/frontend
  - area/relatorio
  - area/a11y
---

# A40.l104 — `trilha-promete-alvo-que-nao-entrega`

> **Origem:** achado colateral da investigação da drift das baselines visuais da
> capa (PR [#1850](https://github.com/davidrobert/mathoms/pull/1850), que **só
> rebaselina** e não toca nisto). É **pré-existente e independente** — não é
> regressão da [[A40.l88]]; o chip `2.5` que ela reinseriu só piorou ~48px de um
> transbordo que já existia.

> [!WARNING] **Correção 2026-08-30 — a premissa mais forte desta lane era falsa.**
> Escrevi acima e propaguei a dois especialistas que "no telefone o relatório
> fica sem navegação nenhuma". **Falso, e medido.** `FloatingNav` está montado
> (`ReportShell.tsx:477`) e renderiza um terceiro FAB — "Abrir índice do
> relatório" — sob `isMobile = matchMedia("(max-width: 1023px)")`. Medido a 320,
> 390, 768, 1000 e 1023px: 44×44, `visibility:visible`, `pointer-events:auto`,
> dentro da viewport, e abre um `<dialog>` **modal** (`:modal` true) com **os 20
> alvos**, rótulos completos, Esc fechando. A ≥1024px o FAB some e o
> toggle→`aside` funciona.
>
> **Logo não existe largura sem rota de navegação.** O erro foi de escopo de
> instrumento: medi a trilha, o `aside` e o botão de índice, e nunca varri a
> página por outras superfícies. Uma afirmação de ausência exigia varredura, e
> eu fiz sondagem dirigida.
>
> O que **sobrevive** à correção está marcado ✅ abaixo; o que cai, ❌.

## O fato

✅ `ReportTopNav` declara **20 alvos de navegação** e, na largura do spec visual
(1280px), o usuário vê **10**. No telefone a trilha mostra **zero** — e nada
*nela* diz que existe mais. ❌ Isso **não** deixa o relatório sem navegação: o
FAB de índice cobre ≤1023px (ver correção acima). A trilha é uma faixa de
**orientação incompleta que não se declara incompleta**, não a única rota.

O container dos grupos ([`ReportTopNav.tsx:121-128`](../../../../frontend/src/components/report/shell/ReportTopNav.tsx))
é `display:flex; flex:1; overflowX:auto; minWidth:0; scrollbarWidth:"none"`. O
`scrollbarWidth:"none"` remove a única pista visual de que há conteúdo à direita,
e não há fade, seta nem indicador que a substitua.

Isso importa porque a trilha **é a navegação primária por decisão declarada**:
`useReportTocOpen.ts` tem `DEFAULT_OPEN = false` e o docstring diz textualmente
que "a `ReportTopNav` sticky é a navegação primária do relatório premium; o TOC
lateral é affordance opt-in". Por default, em qualquer largura, o índice lateral
**não está montado**. Entre os alvos que somem em 1280px estão os entregáveis
centrais: `S10` (Síntese Estratégica), `S_parecer` (10.1) e `plano_de_acao` (11).

## Por que importa — o corte não é aleatório

Veredito de domínio (`financial-planner`, via a sessão que abriu o chip,
2026-08-30). A trilha numera **diagnóstico → síntese → prescrição →
referência**, e o transbordo corta exatamente na dobra:

- **em campo (1→9)**: `S1` Patrimônio, `S2` Fluxo, `2.5` Seguros, `S3`
  Investimentos, `S4` Imóveis, `S7` IF, `S8`/`8.1`/`8.2` Tributário, `S9`
  Riscos — **diagnóstico 100% intacto**;
- **fora (10→E)**: `S10` Síntese, `10.1` Parecer, `11` Plano de Ação, `APP_A`–`E`
  — **prescrição e premissas 100% ausentes**.

No estado default a 1280px o produto entrega o artefato inerte do planejamento
patrimonial: o cliente que conhece os próprios números e não muda nada.

❌ **A análise de "segunda porta" caiu com a correção.** Ela pesava porque eu
supunha a trilha como rota única. Com o FAB medido, **todo alvo tem segunda
porta em ≤1023px** e o `aside` cobre ≥1024px. Sobrevive só o registro de fato:
`/plano` é rota independente do Plano de Ação (verificado), e
`SParecerSection.tsx` é o único componente do frontend que renderiza
`PlannerReview` (verificado) — relevante para outras lanes, inerte para esta.

✅ **O que sobrevive do veredito** é o enquadramento do corte: quem lê a trilha
como sumário conclui que o relatório termina na 9. Não é atrito (nunca há
resistência, então ninguém insiste nem reporta) — é **crença falsa** sobre a
extensão do documento, em cima de um controle que não se declara parcial.

**Severidade rebaixada de P1 para P2** nesta revisão. Não é P1 porque existe
rota alternativa medida em toda largura, e nenhum número está errado. Não é P3
porque a falha de **2.4.7 Focus Visible** abaixo de 455px é AA e é real (ver
abaixo), e porque o controle mentiroso da faixa 768–1023 é defeito objetivo.

## Medição

Chromium, dev server local, fixture `medium`, tema light. **A trilha é
data-independente**: `buildNavGroups` lê `LAYOUT.navigation` do
`config/report_layout.yaml` e só remove seção com `enabled:false` — o mesmo
relatório em qualquer workspace produz a mesma trilha. Logo o transbordo é função
**só** da largura disponível.

**A trilha tem largura de conteúdo constante: 873px.** Composição: 18 chips de
28px + 2 chips de 12px + 4 rótulos de grupo + 3 divisores + gaps. Os rótulos de
grupo e divisores custam ~313px — **36% da trilha**.

**Chrome fixo dentro da nav** = 505px em ≥768px (padding 40 + brand 269 + margem
8 + actions 176 + margem 12 + padding 12); 454px abaixo de 768px, onde o botão
de índice é `hidden md:inline-flex` e `actions` cai para 125. Em ≥1024px a nav
ainda perde **224px** para o sidebar do `AppShell`.

| viewport | trilha útil | alvos com tinta (de 20) | fora de campo |
| --- | --- | --- | --- |
| 320–430 | **0px** | **0** | os 20 + os 4 rótulos de grupo |
| 480 | 26px | 0 | 20 |
| 600 | 146px | 1 | 17 |
| 703 (caixa A4, [[ADR-381]]) | 249px | 4 | 14 |
| 768 | 263px | 4 | 14 |
| 960 | 455px | 9 | 9 |
| **1024** | **295px** | **4** | **14** |
| 1280 | 551px | **10** | **8** (`S10`, `S_parecer`, `plano_de_acao`, `APP_A`–`APP_E`) |
| 1366 | 637px | 12 | 6 |
| 1440 | 711px | 13 | 5 |
| 1512 | 783px | 15 | 3 |
| **1602** | 873px | **18** | 0 |

Quatro coisas que a tabela diz e o enunciado do achado não previa:

1. **Não existe largura abaixo de 1602px em que os 20 caibam** — e o máximo
   alcançável é **18, nunca 20**. Os chips `V0` ("O que mudou") e `perfil`
   ("Perfil da Família") não têm `num` no YAML, e o modo compacto colapsa o
   label (`maxWidth:0; opacity:0`): renderizam como **alvos de 12px em branco em
   toda largura**. Têm `aria-label`/`title`, então o leitor de tela os anuncia —
   quem enxerga vê dois buracos.
2. **Alargar a janela de 960 → 1024 REMOVE 5 alvos** (9 → 4). O sidebar do
   `AppShell` expande em `lg:` e come 224px. A curva não é monotônica na largura.
3. **Em ≤454px a trilha tem 0px de caixa** ✅. Não há o que rolar; a página não
   rola horizontalmente (`documentElement.scrollWidth == innerWidth`). ❌ Mas
   **não** é perda de funcionalidade: o FAB de índice serve toda essa faixa, o
   que **derruba o enquadramento 1.4.10 Reflow** (existe mecanismo alternativo).
   O que sobra, e é pior de defender contra, é que a trilha mantém **20 alvos
   focáveis dentro de uma caixa de 0px** — ver 2.4.7 abaixo.
4. **Achado colateral** ✅ **— e a correção o torna mais nítido, não menos.**
   Entre **768px e 1023px** o botão "Mostrar índice" é visível, clicável e
   **no-op**: monta o `<aside>` no DOM com largura 0, porque o wrapper e o botão
   são `md:` e o aside é `lg:`. Nessa mesma faixa o FAB de índice **funciona**.
   Ou seja: duas afordâncias de índice convivendo, **uma que entrega e uma que
   mente**. E o desenho pretendido está escrito no docstring do próprio
   `FloatingNav`: *"Botão 'Índice' (3º FAB) só aparece em `<lg` (≤1023px), onde a
   sidebar `ReportToc` está escondida"*. A divisão pretendida é `lg`; o `md:` do
   toggle é **desalinhamento de breakpoint de uma linha**, não feature faltando.

## Quem alcança o que está fora

| canal | resultado medido |
| --- | --- |
| Teclado (Tab) | **funciona** — percorre os 20, o browser rola o container (`scrollLeft` 0 → 292 → 322). WCAG 2.1.1 satisfeito. |
| Trackpad, gesto horizontal | **funciona** (`scrollLeft` 0 → 300) |
| Mouse comum, roda vertical sobre a trilha | **não rola a trilha** — rola a página (`scrollLeft` fica 0, `pageY` vai a 300) |

Mas **a linha do teclado só vale onde há caixa**. Re-medido a 320px e 375px: o
Tab percorre os chips e o browser tenta rolá-los (`scrollLeft` 89 → 103 → 125 →
155 → 185 → 215), e a interseção do alvo focado com a caixa de recorte é **0px²
em todos**. O foco pousa em 20 paradas com zero pixel pintado.

Logo o enquadramento correto de SC é **2.4.7 Focus Visible (AA)**, não 1.4.10:
2.1.1 se sustenta (ativar o link navega), o que falha é o indicador de foco. É o
gancho limpo — 1.4.10 exigiria litigar "perda de funcionalidade" contra um
mecanismo alternativo que o plano canônico *diz* existir (ver abaixo).

✅ O 2.4.7 **sobrevive inteiro** à correção: o FAB dá rota, não dá indicador de
foco para os 20 alvos que a trilha mantém focáveis dentro de uma caixa de 0px.
❌ Cai a palavra "inalcançabilidade": há rota. O defeito é de **descoberta e de
ponteiro** no desktop, e de **foco invisível** em ≤454px.

## Por que nenhum gate viu

- `overflow-horizontal.@critical.spec.ts` é cego por **dois** motivos
  independentes: (a) escopo — varre `article[data-report-mode]`, e a nav é irmã
  do `<article>`, não filha; (b) regra — `dentroDeRolavel()` pula contêiner
  rolável na tela, sob a premissa declarada "o usuário alcança com gesto", que é
  exatamente o que aqui não se sustenta.
- `validate_nav_targets` (`dev/report_layout_nav_targets.py`) tem exatamente
  `_dead_links` e `_unlinked`: ambos afirmam que o **grafo** está completo.
  Nenhum afirma que o link é **perceptível**.
- **E há uma catraca.** Nada mede capacidade da trilha contra contagem de
  seções, então toda seção nova piora o transbordo monotonicamente, sem freio —
  a `S_PROTECAO` custou ~48px e ninguém detectou. Consertar só a afordância
  reabre o mesmo bug na próxima seção. O invariante que falta, em termos de
  domínio: *nenhum alvo declarado em `navigation:` é indescobrível no estado
  default* — e **estado default inclui ToC fechada**.
- O baseline visual `cover-{light,dark}` **contém** a trilha truncada (o `clip`
  page-level `y=0..720` engole a nav sticky) e a congela como esperada.

**Print/PDF não é afetado**: `[data-report-topnav] { display:none !important }`
em `report-print.css`.

## O plano canônico já decidiu isto — e a metade de baixo está refutada

[`docs/plan/REPORT_PREMIUM/_README.md:103-105`](../../../plan/REPORT_PREMIUM/_README.md)
(Q7) decide: *"≥1024 sidebar+topnav; 768–1023 sidebar vira drawer; ≤767 só
topnav. `<ReportToc>` vira `<ReportTocDrawer>` em tela média."*

**`ReportTocDrawer` não existe em código** — o identificador aparece só nessa
linha do plano (verificado: zero ocorrências em `.ts`/`.tsx`). O
`<div className="hidden md:block">` de `ReportShell.tsx:329` é o **fóssil** dessa
decisão: o wrapper foi escrito em `md:` esperando o drawer, e o `<aside>` ficou
em `lg:block`. O achado 4 acima não é bug de breakpoint — é **decisão canônica
pendente de implementação**, com a justificativa errada já fossilizada no
docstring de `ReportActions.tsx:38` ("a sidebar é `hidden md:block`" — é
`lg:block`).

**E a metade de baixo da Q7 está refutada por medição.** "≤767 só topnav" é
exatamente o estado de 0px, e a linha 417 do mesmo plano (`nav-scroll` —
horizontal scroll em mobile") descreve um scrollport que não existe. Executar a
Q7 fielmente produz zero navegação no telefone. **Isso exige emenda datada à
Q7**, e a emenda é decisão de escopo em plano canônico — dono `product-manager`,
não `information-architect`.

## Vizinhança — o que esta lane NÃO é

O deferimento 1 da [[A40.l88]] ("índice runtime-aware", dono
`information-architect`) trata de **âncora morta**: entrada de nav que aponta
para seção que não montou. Esta lane trata do inverso — **alvo vivo
inalcançável**. São vizinhos e não se substituem.

## Decisão — `product-designer`, 2026-08-30

> [!IMPORTANT] **Esta decisão foi tomada sob a premissa falsificada acima** (que
> não havia rota abaixo de 768px). **A reconsulta ao mesmo dono aconteceu, com o
> FAB medido em mãos, e o veredito abaixo é o REVISADO** — a decisão original
> ficou registrada no histórico do PR, não aqui.

### Veredito revisado

**A camada 1 ("rota garantida do índice") foi retirada.** Em ≤1023px a rota já
existe, com focus-trap nativo e os 20 alvos com rótulo completo; nada disso é PR
novo, e some com ela todo o trabalho de `Sheet`/`aria-modal`/trap de foco que a
decisão original listava como não-diferível.

**A pergunta que restou — onde os chips saem — foi reposta.** As três opções que
eu tinha formulado (`md`, `lg`, `xl`) assumiam que o valor dos chips é função de
**quantos** têm tinta. É função de **quais**, e faltava uma variável: a faixa
**nunca rolava o chip ativo para dentro do campo**, e no compacto só o ativo
expande o rótulo. Lendo a seção 9 a 1024px, o rail mostrava "1 · 2 · 2.5 · 3" —
quatro números do começo do documento, nenhum ativo, nenhum rótulo. **O emprego
de orientação estava quebrado em toda largura abaixo de ~1500, independentemente
de onde se cortasse.** Com auto-scroll, 295px deixam de ser "4 de 20" e passam a
ser "o ativo com rótulo expandido + vizinhos".

Decidido: **chips fora abaixo de `md`** — onde o rail não comporta ativo-expandido
mais um vizinho de cada lado (~250px; a 703/768 há 249–263px, a 600 há 146px).
`lg` seria **regressão**, apagando a orientação justo em 768–1023, onde o `aside`
está escondido e nada mais responde "onde estou". E **a costura 1024–1279
dissolve**: com auto-scroll o rail a 1024 está no mesmo estado que a 768, e o
defeito real daquela banda era o `md:inline-flex` do toggle — uma linha.

**O fade sobe de prioridade e fica acoplado ao auto-scroll**: com o conteúdo se
movendo sozinho sob o usuário, corte duro nas bordas lê como bug, não como janela.

**Honestidade sobre o SC:** 2.4.7 exige um corte em algum ponto ≥455px e **não
escolhe qual** — `md`, `lg` e `xl` o satisfazem igualmente. Quem escolhe `md` é o
argumento de orientação, não a norma.


A medição eliminou duas opções do enunciado antes do painel: `density` mais
agressivo (já está no máximo, só o `num` aparece) e colapsar rótulos de grupo
(recupera ~313px → os 20 caberiam a partir de ~1290px em vez de 1602px; **não
muda nada abaixo de 1024, nem no telefone**).

**Overflow menu na própria trilha: rejeitado.** Quatro motivos, o primeiro
decisivo: qual item cai no menu depende da largura, e a curva não é monotônica
(achado 2) — "Plano de Ação" seria chip a 1440 e item de menu a 1024.
*Priority+* funciona quando o conjunto primário é estável e a cauda é curta;
aqui a cauda é 14 de 20 a 1024px, ou seja **o menu é a navegação, fantasiada de
chip**. Somam-se: triplicaria a renderização da mesma árvore YAML (dois
`IntersectionObserver` independentes já existem), não resolve ≤454px, e exige
`ResizeObserver` num elemento sticky para resultado pior.

**Decidido, em ordem de prioridade:**

1. **Rota garantida do índice.** `ReportToc` como overlay (`fixed` + backdrop),
   `xl:static` para o modo push; botão de índice visível em **toda** largura;
   chips saem abaixo de `md`. A fronteira push/overlay é **`xl`, não `lg`**:
   abrir em fluxo a 1024px deixa o artigo com ~560px (1024 − 224 do AppShell −
   240 do aside) para um grid de 4 KPIs.
2. **Tinta nos 2 chips sem `num`.** Badge 16×16 com glifo neutro — o precedente
   está na mesma feature: `ReportToc.tsx:203-208` já usa `<ChevronRight>` para
   entrada sem número. **Não numerar**: o YAML declara `V0`/`perfil` como
   shell-level não numeradas ("padrão do Sumário Executivo"), e numerar na
   trilha sem numerar o corpo cria mentira entre chip e heading. **Não
   remover**: "O que mudou" é o maior valor de entrada numa visita recorrente.
   Regra generalizável: *no modo compacto, nenhum chip pode renderizar com zero
   tinta.*
3. **Fade de borda** via `mask-image` (não gradiente de cor — o fundo é
   `var(--report-gradient-nav-sticky)` e cor bandearia, exigindo token novo),
   condicionado a `scrollWidth > clientWidth` por borda, `pointer-events:none`.

**Abaixo de 768px a barra fica e muda de função:** `[← Relatórios] · [título
truncado] · [Índice] · [ações]`, sem chips. Mesmo cortando brand (269px) e
actions (176px) sobrariam ~300px num telefone de 375 — 3-4 quadradinhos sem
rótulo de 20, custando 52px do recurso vertical escasso. E o scroll-spy morre
junto: com 4 de 20 visíveis, o `data-active` marca elemento fora de campo na
maior parte do documento. Encurtar o breadcrumb serve para caber **índice e
ações**, não chips (o título é redundante com o H1 da capa).

**Rejeitado explicitamente:** mapear roda vertical para scroll horizontal
(sequestra o scroll da página numa faixa sticky, exatamente onde o usuário está
descendo para dentro do relatório). E **nenhuma ação sobre a curva não-monotônica
do achado 2** — a resposta a "o orçamento da minha nav é controlado por chrome
que não é meu" é "então minha nav não pode ser o índice".

### Itens que entram no mesmo PR (não diferíveis)

- **`TocButton` vira `<a href="#id">`** com `preventDefault` para o smooth
  scroll. Promover o ToC a navegação primária promove hoje um `<button>` +
  `scrollIntoView`: perde copiar-link-da-seção e abrir-em-nova-aba, e o leitor de
  tela anuncia "botão" onde a trilha anuncia "link".
- **Semântica de drawer**: `aria-expanded` + `aria-controls` no trigger,
  `aria-modal`, Esc, trap de foco, retorno de foco ao trigger, fechar ao navegar.
  Hoje o toggle tem só `aria-label`.
- **O estado do drawer (< `xl`) não persiste.** `useReportTocOpen` grava em
  localStorage; abrir o índice uma vez no telefone deixaria o relatório do
  laptop 240px mais estreito para sempre. Só o estado de push persiste.
- **Trocar o ícone.** `Eye`/`EyeOff` em fintech é *o* affordance de mascarar
  saldo; usá-lo para índice é colisão semântica que piora quanto mais central o
  botão fica. `List` (ou `PanelLeft`/`Menu` conforme push/drawer), rótulo
  "Índice".
- **Reescrever o docstring de `useReportTocOpen.ts:8-10`**, que hoje afirma o
  contrário do que passa a valer: a trilha é **orientação**, o índice é
  **navegação**, e o default fechado existe porque a coluna de leitura ganha por
  default. Este componente já tem dois defeitos documentados por um comentário
  que afirma o oposto do código — não deixar um terceiro.

## O que a implementação achou — 3 dos 5 defeitos não estavam no achado

O achado original descrevia **afordância**. Ao implementar, o instrumento
encontrou três defeitos que ninguém tinha visto, e um deles é maior que o
achado que abriu a lane.

**1. O scroll-spy da faixa nunca funcionou.** Varrendo 12 pontos do documento a
1600px — largura em que os 20 chips cabem — **nenhum chip ficava `data-active`**.
Controle que isolou a causa: abrindo a página com `mathoms:report:toc-open` já
`true`, o índice monta junto com a faixa e **o spy dele morre igual**, embora
rastreie normalmente quando aberto depois do load. Não é defeito da faixa, é do
padrão compartilhado: os dois montam antes de o fetch resolver, o efeito chama
`getElementById` para todos os ids, recebe `null` em todos, sai no
`elements.length === 0` — e nunca mais roda, porque as deps (`groups`,
`flatEntries`, `mode`) não mudam quando o dado chega.

Consequência que muda o enquadramento da lane inteira: como o modo compacto só
expande o rótulo do chip **ativo**, e nunca havia ativo, **a faixa era 18 números
sem palavra alguma, sempre**. A escapatória do compacto nunca disparou. E o
índice ficava mudo **para o usuário que volta**, porque `toc-open` é persistido —
o recurso funcionava só na visita em que você o ligava.

**2. A eleição do ativo lia o conjunto errado.** O callback escolhia sobre
`entries`, que traz só quem **mudou** de interseção no disparo. Medido: no mesmo
scroll, a faixa dizia `S2` e o índice dizia `S8`. Duas superfícies do mesmo
relatório respondendo coisas diferentes para "onde estou".

**3. `scrollIntoView({block:"nearest"})` não serve em container `position:
sticky`.** O Chromium rola o **documento** até a posição de fluxo do sticky.
Medido: `window.scrollTo(1500)` voltava para **7px**, e o FAB "voltar ao topo"
nunca aparecia — `report-layout.@critical` reprovou. O índice tinha o mesmo
defeito **desde sempre**, inerte porque o spy dele estava morto; consertar o spy
o tornou alcançável, e sem este terceiro conserto o relatório saltaria para o
topo sozinho enquanto o usuário lê.

> **O meu próprio conserto nasceu com defeito, e o teste pegou.** A primeira
> versão da eleição exigia `ratio > 0`; com `rootMargin` encolhendo o root a ~30%
> da viewport, uma seção alta cruza o threshold 0 com `intersectionRatio` ≈ 0 (a
> razão é relativa ao TARGET). E o índice debouncia a **eleição**, não só o
> `replaceState`: num scroll longo a seção entra e sai da banda em disparos
> consecutivos, o segundo cancelava o timer do primeiro, e sobrava "nada
> intersecta" para avaliar. A faixa, síncrona, acertava — a assimetria era o bug.

## Entregue

| # | mudança | fecha |
| --- | --- | --- |
| 1 | `useMountedSectionIds` re-registra o spy quando as seções montam | achado 1 |
| 2 | `scrollSpy.ts` elege sobre o conjunto observado; os dois consomem o mesmo módulo | achado 2 |
| 3 | O índice só debouncia o `replaceState`; a eleição é síncrona | achado 2 |
| 4 | `keepInView` rola só o container, nunca o documento | achado 3 |
| 5 | A faixa rola o chip ativo para dentro do campo | orientação abaixo de ~1500px |
| 6 | Badge com glifo neutro em chip sem `num` | os 2 alvos sem tinta |
| 7 | Máscara de borda por `mask-image`, por borda, só sob transbordo | faixa não se declarava parcial |
| 8 | Chips saem abaixo de `md` | **2.4.7** — some a caixa de 0px com focáveis dentro |
| 9 | Toggle do índice nasce em `lg`, onde o `aside` existe | no-op de 768–1023 |
| 10 | `TocButton` vira `<a href>` | copiar-link, nova aba, "link" no leitor de tela |
| 11 | Ícone deixa de ser `Eye`/`EyeOff` | colisão com mascarar-saldo em fintech |
| 12 | Docstring de `useReportTocOpen` para de afirmar o contrário do código | terceiro comentário falso do componente |

`nav-scroll-spy.@critical.spec.ts` tem **uma asserção por defeito**, porque cada
um passava escondido atrás dos outros — contrafactual por subconjunto, não pelo
conjunto.

> **O gate quase nasceu decorativo, e o CI mostrou.** Escrevi o spec **sem**
> `@critical` de propósito, para evitar divergência de timing em Firefox/WebKit,
> e anotei no docstring que "assim roda só no chromium, que não filtra por tag —
> continua gateando todo PR". **Falso.** O step default (`Report render gate`)
> filtra `--grep @critical --project=chromium`, e o job "Frontend E2E" é opt-in
> por label `e2e`. Spec sem tag cai no vão entre os dois e **não roda em PR
> nenhum** — o mesmo modo de falha que esta lane existe para consertar. Corrigido
> com a tag; verificado rodando o comando **exato** do CI, que agora seleciona os
> 6 testes.
>
> No mesmo movimento caiu uma fragilidade do teste: enquanto a faixa media
> `rootMargin: -120px 0px -50% 0px` e o índice `-15% 0% -55% 0%`, "os dois
> concordam" passava por **coincidência de amostra**, não por invariante — bandas
> diferentes podem eleger seções diferentes no mesmo scroll. A banda agora é
> constante compartilhada em `scrollSpy.ts`, e a concordância virou exigível.

**Não entregue, e por quê:** a linha em que os chips saem ficou em `md` por
argumento de **orientação**, não por norma — 2.4.7 exige um corte em algum ponto
≥455px e não escolhe qual. A costura 1024–1279 (faixa no pior orçamento, sem
FAB) dissolve com o auto-scroll: o rail deixa de ser "4 de 20" e passa a ser "o
ativo com rótulo + vizinhos".

## Critério de aceite

1. Em 320, 375, 768, 1024, 1280 e 1602px: existe caminho **visível** (não só por
   teclado) de qualquer ponto do relatório até `plano_de_acao` (11),
   `S_parecer` (10.1) e `S10`, em no máximo 2 interações. **Este critério já
   passa hoje** — via FAB em ≤1023px e via toggle→`aside` em ≥1024px. Entra como
   **teste de não-regressão**, não como alvo: era o que eu supunha quebrado.
2. Em 768–1023px: clicar "Índice" mostra o índice. Hoje é no-op em 256px de
   faixa de viewport.
3. **Nenhum chip renderiza com 0px de tinta em largura alguma** — asserção sobre
   os 20 alvos, não sobre `V0`/`perfil` nominalmente.
4. Foco visível em todo alvo alcançável por Tab, **a 320px inclusive** (2.4.7).
   Hoje a interseção do alvo focado com a caixa de recorte é 0px² a 320 e 375.
5. **Uma só afordância de índice por largura.** Hoje a faixa 768–1023px tem
   duas, e a que o usuário encontra primeiro no chrome do topo é a que mente.
   (O drawer nativo do `FloatingNav` já entrega Esc, `:modal` e retorno de foco —
   medido; não é preciso reconstruí-lo.)
6. Existe gate que reprova **hoje** e passa depois, sem herdar a cegueira do
   `overflow-horizontal` (escopo fora do `<article>` + contêiner rolável não
   isenta quando não há afordância). Ele afirma o invariante contra a catraca:
   *nenhum alvo declarado em `navigation:` é indescobrível no estado default,
   ToC fechada* — de forma que seção nova caia nele sozinha.
7. Print/PDF inalterado — a baseline de `report-print.css` não se move. Se
   mover, o diff está errado.

## Roteamento

`information-architect` **não entra neste PR**: nada toca árvore de seções, ids,
âncoras, numeração ou o bloco `navigation:` do YAML — trilha e ToC derivam da
mesma árvore via `buildNavGroups`/`buildTitleMap`. Dois gatilhos o trariam, e
nenhum está na decisão: numerar `V0`/`perfil` (rejeitado) e dar ao drawer uma
árvore diferente da trilha (hierarquia, apêndices colapsados) — **diferido**: o
drawer entra plano, e só se reabre se testar mal.

> **O custo do segundo deferimento tem nome** (`financial-planner`, 2026-08-30):
> "Apêndices A–E" não é um bloco homogêneo de referência. `APP_B` (premissas
> econômicas — sustentam o número de IF da `S7`), `APP_C` (cenários de estresse;
> `hide-when-empty`, logo renderiza exatamente quando os dados o justificam e
> fica invisível justamente aí) e `APP_E` (próximos ciclos + disclaimers) são
> decision-grade. Só `APP_A` (glossário) e, com ressalva, `APP_D` (fontes /
> lineage — superfície de confiança) toleram rebaixamento. O rótulo do grupo faz
> **três seções decision-grade herdarem afordância de rodapé**. Isso não bloqueia
> o drawer plano; é a condição de retomada do gatilho de `information-architect`.

> **Prioridade sob truncamento, se algum mecanismo futuro precisar escolher**
> (`financial-planner`): 1º `S10`, 2º `plano_de_acao`, 3º `S_parecer` (máximo em
> unicidade, mas Premium-condicional e `hide-when-empty` — slot às vezes vazio é
> pior candidato à posição garantida), 4º `S9` (assimetria catastrófica;
> `hero_gap_protecao` é `variant:"critical"`, está visível hoje e deve
> permanecer). **Explicitamente não é reordenar a trilha** — ordem diferente do
> scroll quebra a semântica do `data-active` do `IntersectionObserver`. Sob a
> decisão acima a lista fica inerte, porque o índice passa a ser alcançável em
> toda largura e nada precisa ser sacrificado; ela existe para o caso de o
> desenho mudar.

`product-manager` entra para a **emenda datada à Q7** do plano canônico.

## Atenção operacional

Qualquer mudança aqui move as baselines `cover-{light,dark}` e provavelmente
outras. Rebaseline exige `workflow_dispatch` em `ci.yml` com `run_visual=true` +
`update_visual_baselines=true`, e o PR precisa da label `visual` para o gate
rodar e provar verde.
