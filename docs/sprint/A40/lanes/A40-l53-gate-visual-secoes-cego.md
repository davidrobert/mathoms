---
id: A40.l53
type: lane
title: "Gate visual de seções está cego: S2 varia 5–6% entre tentativas do mesmo commit e `main` puro reprova em 6 baselines"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: a40-l53-gate-visual-secoes-cego
adrs:
  - "[[ADR-210]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p1
  - area/frontend
  - area/ci
---

# A40.l53 — `gate-visual-secoes-cego`

> **Aberta em 2026-08-12**, no fecho da [[A40.l45]] (decisão do dono: os
> follow-ups sem dono viram lanes na A40). **Vizinha, não duplicata, da
> [[A40.l46]] item 1**: aquela cobre o job `frontend-print-visual` (página 1 do
> PDF, baseline única); esta cobre o job `Frontend visual snapshots`
> (`sections.snapshots.visual.spec.ts`, 28 baselines por seção × tema).

## Problema

O job `Frontend visual snapshots` não distingue regressão de ruído. São dois
defeitos independentes, medidos na execução da [[A40.l45]] (PR #1387):

### 1. O snapshot da S2 é flaky no próprio runner

As **três tentativas do mesmo job** — mesmo commit, mesmo runner Linux — diferem
**entre si** em 5,1%, 5,6% e 6,3% (S2-dark, run 31576243325). A tolerância do
spec é `maxDiffPixelRatio: 0.025`. O snapshot reprova sozinho, sempre, em
qualquer PR que aplique o label `visual`.

Causa provável, medida: `setupReport` captura após `waitForTimeout(500)`, e o
conteúdo do canvas do Chart.js só estabiliza entre **~900ms e ~1200ms** (hash de
`getImageData` em instantes crescentes). `animations: "disabled"` do Playwright
cobre CSS, não canvas.

**Tentativa que JÁ FALHOU** (não repetir): trocar o timeout por espera até o
hash do canvas estabilizar — o hash amostrado estabiliza antes de o desenho
terminar; a variação intra-run persistiu. Candidato seguinte: desligar a
animação do Chart.js no ambiente de teste (opção de chart, não de Playwright).

### 2. `main` puro já reprova em 6 baselines

Controle rodado **duas vezes** (branch cortada de `origin/main` + dispatch com
`run_visual=true`): `S2` ×2, `S3` ×2, `APP_A-light` e `S-parecer-retido-dark`
falham em `main` sem nenhum diff de PR. O job é **label-only** ([[ADR-210]]
§camada 1), então PRs sem o label envelhecem as baselines em silêncio — mesma
mecânica que deixou a baseline de print sendo um crash por 4 meses.

Consequência prática: o job é **fail-open por ruído** — vermelho permanente que
todo autor aprende a ignorar. Na l45 ele escondeu uma regressão real minha
(S2-light a 9,9%) atrás do próprio ruído; só a triagem manual separou.

## Método de triagem que funcionou (usar até o fix)

Nunca comparar captura local × baseline (macOS × Linux domina o diff), nem
comparar PNGs por bytes. Comparar **`actual` × `actual` de dois runs no mesmo
runner** — o do PR e o de um controle cortado de `origin/main` — por pixel,
limiar ~8/255. Foi isso que provou que 5 das 6 falhas eram herdadas (0 px de
diferença) e uma era da lane.

## Escopo

1. **Matar a variação na fonte** — animação do Chart.js desligada (ou concluída
   de forma determinística) no ambiente de teste. Prova: 3 execuções do job no
   **mesmo commit** com diffs intra-run < 0,5% em todas as seções.
2. **Rebaseline das 6 baselines podres**, em runner Linux, **com os PNGs
   olhados** um a um antes do commit (a lição da baseline que era um error
   boundary) — só depois do item 1, senão congela um frame arbitrário.
3. Registrar em `TESTING.md` o método de triagem `actual`×`actual`.

## Critério de aceite

- [ ] 3 runs consecutivos do job `Frontend visual snapshots` no mesmo commit de
      `main`: 0 falhas, e nenhum par de tentativas difere > 0,5% em pixel.
- [ ] As 6 baselines regeneradas têm justificativa individual (o que mudou e por
      quê), com inspeção visual registrada no PR.
- [ ] Provado por mutação: uma mudança real de layout numa seção (ex.: retirar o
      `grid-cols-1` da [[A40.l45]]) deixa o job vermelho.

---

## Ataque — medição de 2026-08-14

Sonda local (worktree, `next dev` + Playwright, fixture `medium`, S2 dark) +
run de controle em `main` (`chore/visual-control-l53-20260814`, run
`31805984578`). O que a medição **muda** no diagnóstico acima:

### 1. A causa não é "a animação leva 900–1200ms". É a captura que reinicia o desenho

Amostrando `getImageData` dos 4 canvas da S2 a cada 250ms, **sem** throttle: o
canvas para de mudar em ~770ms e fica **bit-idêntico por 13s** seguidos. Doze
screenshots consecutivos da seção inteira (976×2960) dão **0,000%** de pixel
diferente em todos os 11 pares. Ou seja: numa máquina ociosa não existe flake —
o número de 900–1200ms descreve a animação, não o defeito.

O defeito aparece quando se instrumenta **o que a própria captura faz**. Um
`ResizeObserver` nos canvas registra, a cada `locator.screenshot()`:

```
0x256 / 0x250 / 0x288 / 0x256   @16889ms   ← durante a captura
924x256 / 924x250 / 924x288 / 924x256 @17101ms  ← 212ms depois
```

**Toda captura zera a largura dos 4 canvas e a devolve em seguida** — 8 eventos
de resize por screenshot, zero enquanto a página está ociosa. Com
`responsive: true`, o Chart.js redesenha **com animação** a cada restauração. O
gate de estabilidade do Playwright vira então um laço que se auto-alimenta:
cada tentativa de capturar provoca o redesenho que a tentativa seguinte flagra.

Sob `Emulation.setCPUThrottlingRate: 8` (runner carregado), na cadência real do
Playwright (0/100/250/500/1000ms), os pares consecutivos da S2 dão
**8,2% · 10,5% · 4,7% · 3,8% · 1,5% · 3,2% · 3,8%** e **não convergem em 19s** —
mesma ordem de grandeza e mesma assinatura decrescente-porém-instável dos
262940px/235142px vistos no CI. O limiar é 2,5%; o orçamento é
`expect.timeout: 5000`.

Consequências para o escopo:

- **Aumentar a espera não resolve.** O tempo de acomodação não é 1s; é função da
  carga do runner e cada retry o reinicia.
- Confirmado o "JÁ FALHOU" do diagnóstico: esperar o hash estabilizar não podia
  funcionar — o hash é amostrado entre capturas, e é a captura que move o
  desenho.
- **O gate de estabilidade não é governado por `maxDiffPixelRatio` da forma
  descrita.** Lendo `page.js` do `playwright-core`: a **primeira** captura é
  comparada direto com a baseline e, se casar, passa na hora; só a partir da
  segunda o comparador roda captura-contra-captura — com as *mesmas* opções
  (2,5% aqui). Por isso o `actual.png` que sobra fica a 0,8% da baseline: o
  conteúdo estava certo, o desenho é que não parava.

### 2. Fix medido nas duas direções

`prefers-reduced-motion` desliga a animação do Chart.js
(`ChartRegistry.ensureChartRegistered`, mesmo padrão que `ChartGaugeScore` já
usa para a agulha) + `reducedMotion: "reduce"` no projeto `visual` do Playwright:

| Cenário (throttle 8×, cadência do Playwright) | Pior par consecutivo |
| --- | --- |
| sem fix | **10,485%** |
| com fix (media query verificada em `matchMedia`) | **0,000%** (7/7 pares) |

Não cega o gate: com o fix, trocar um `md:col-span-2` por `md:col-span-1` na S2
reprova com **398100px (ratio 0,14)** e altura 2960 → 3008.

> Erro de método que quase virou conclusão: a primeira rodada usou
> `test.use({ reducedMotion })` e mediu 2,4–4,4%, o que parecia refutar o fix.
> `matchMedia` no navegador dizia `false` — a alavanca não chegou na página.
> Só `page.emulateMedia({ reducedMotion: "reduce" })` funcionou. Verifique a
> alavanca antes de julgar o fix.

### 3. O item 2 do escopo mira uma lista que não existe mais

As 6 baselines de 2026-08-12 foram **rebaselinadas pelo #1384**, mergeado
`2026-08-12 08:45` — uma hora depois do controle citado neste documento. O
controle de `2026-08-13` (run `31690085263`, commit `35f15270`, ancestral de
`main`) fechou **28/28 verde**.

Só que a lista se refez em dois dias. Controle de hoje em `main`
(`31805984578`): **7 reprovados, 1 flaky, 30 passaram** —

| Baseline | Modo de falha |
| --- | --- |
| S7 light + dark | altura **580 → 408px** |
| S8 light + dark | altura **909 → 928px** |
| S2 dark, APP_A light, S_parecer-retido dark | diff de pixel |
| S2 light | `Failed to take two consecutive stable screenshots` (passou no retry) |

S7/S8 são do **#1448** (`A40.l34` PR3b), mergeado **22 minutos antes** do
controle, tocando `S7IndependenciaSection.tsx`, `S7PgblLocationNote.tsx` e
`S8PrevidenciaSection.tsx` — mudança de layout deliberada, **sem o label
`visual`**, logo sem rebaseline. O passivo não é um lote a limpar; ele se
regenera em horas. Rebaselinar "as 6" é perseguir um retrato vencido.

> **A esteira, medida dentro do próprio PR de conserto.** As 6 baselines foram
> regeradas no runner (run `31817219064`) e commitadas. Antes de o CI reavaliar,
> o `auto-update-prs` mergeou `main` na branch trazendo o **#1452** (`A40.l47`
> PR1), que toca `ApendiceASection.tsx` e `RentabilidadeCard.tsx`. Resultado da
> reavaliação: **36 passed, 2 failed** — as 4 estruturais passaram, e a
> `APP_A` (light **e** dark) reprovou com altura `2042 → 2119px`. **As baselines
> de APP_A nasceram vencidas em ~20 minutos**, por um terceiro PR, no mesmo dia
> dos outros dois. Três PRs em ~24h mudaram o render sem o label. Qualquer
> critério de aceite que fale em "as N baselines podres" descreve um retrato,
> não um estado — o que o gate precisa é de sinal que não dependa de baseline
> (§5) e de um caminho em que quem muda o render refaça a baseline no próprio
> PR.

### 4. A consequência prática mudou de sinal desde que a lane foi escrita

"Fail-open por ruído — vermelho permanente que todo autor aprende a ignorar"
valia até o **#1428**, que pôs `frontend-visual` em `all-green.needs`. Hoje o
job **gateia merge**. Aplicar o label `visual` — a coisa certa a fazer ao mexer
no relatório — passou a ser o que **bloqueia** o PR, por um defeito que não é do
autor. O comentário de `ci.yml:1287-1290` ainda afirma o contrário do que o
mesmo arquivo faz em `ci.yml:1567`.

### 5. O critério de aceite 1 não é mensurável como o job está hoje

"nenhum par de tentativas difere > 0,5%" não tem instrumento: em run verde o
Playwright não emite `actual.png`, e o upload de artefato é `if: failure()`.
Só dá para evidenciar o critério quando o job **falha**. A sonda do §1
(N capturas + diff par-a-par, sob throttle) é o instrumento que falta — e vale
mais como **teste permanente** do que como triagem manual: ele não depende de
baseline, e reprova alto se a animação voltar por qualquer caminho.

### 6. Achado adjacente — o PDF imprime o gráfico no meio da animação

Mesma raiz, vítima em produção. `ChartCanvas` captura o fallback de impressão
com `setTimeout(…, 300)` sobre uma animação de ~1s, uma única vez
(`useEffect(…, [data])`), e `report-print.css` esconde o `<canvas>` e mostra
esse `<img>` em `@media print`. O `pdf_renderer` esperar 2s não ajuda: a imagem
foi congelada aos 300ms e nunca é refeita.

Medido comparando o `src` do `<img>` com `canvas.toDataURL()` aos 6s (sem
throttle, tudo dentro da página — sem captura do Playwright no meio):

| Gráfico | Diferença | O que sai no papel |
| --- | --- | --- |
| Receita/Despesa mensal | 41,4% dos pixels | barras mais curtas |
| Receita por Fonte | 32,5% | barra "Salário" com **678px de 837px = 81%** do comprimento — o texto ao lado diz 76% de R$ 248.500 (R$ 188.860) e a barra aponta ~R$ 155.000 no eixo impresso logo abaixo |
| Despesas por Categoria | 14,7% | rosca **aberta**: 10 de 72 setores de 5° sem anel (50° de vão); no canvas final, 0 |
| Fluxo mensal empilhado | 17,5% | barras mais curtas |

Os 81% batem com `easeOutQuart` em t≈0,33 — a assinatura de uma captura aos
300ms. Cobertura hoje: **zero**. O `frontend-print-visual` compara só a **página
1** do PDF (`report.print.pdf.png` = capa + KPIs, sem gráfico algum).

Isto **inverte a prioridade do item 1 do escopo**: desligar a animação só no
ambiente de teste deixaria o gate verde renderizando um caminho que nenhum
usuário recebe, e o defeito do PDF passaria a ser invisível **para o próprio
gate criado para vê-lo**. Por isso o fix medido no §2 é a media query (um só
caminho de render, e a11y de brinde) e não uma flag de teste — mas ela **não**
cobre o PDF, porque o `pdf_renderer` não emula `reduced-motion`: a captura do
`printSrc` precisa acontecer no fim da animação (`animation.onComplete`), não
num timer cego.

### Escopo revisado — decidido pelo dono em 2026-08-14

O §6 fica **dentro** desta lane: a raiz é a mesma, e fechar só o gate deixaria
o defeito do PDF invisível para o próprio gate criado para vê-lo.

1. `prefers-reduced-motion` desliga a animação do Chart.js + `reducedMotion` no
   projeto `visual` (§2). **Sem** flag de ambiente de teste.
2. `ChartCanvas` serializa o fallback de impressão quando o Chart.js **para de
   emitir render** (plugin `mathomsRenderSignal` + debounce), não num timer
   cego de 300ms (§6).
3. Gate permanente **sem baseline e sem label** —
   `chart-determinismo.@critical.spec.ts`, no `Report render gate` que
   `all-green` exige. Prova as duas coisas, e ambas foram verificadas por
   mutação:
   - voltar ao timer de 300ms ⇒ *"a imagem de impressão difere do canvas"*;
   - tirar o `reduced-motion` do `ChartRegistry` ⇒ *"capturas 0 e 1 diferem sob
     throttle 6×"*.
4. Comentário de `ci.yml:1287-1290` corrigido: o job **gateia** merge (§4).
5. `TESTING.md` §"Antes de culpar a sua mudança" — método `actual`×`actual`,
   o mecanismo do resize e o fato de o gate de estabilidade ser um erro
   distinto do diff de baseline (§1, §5).
6. Rebaseline **do que estiver vermelho no dia do PR**, com PNG olhado um a um
   — não da lista de 2026-08-12 (§3).

O critério de aceite 1 permanece sem instrumento em run verde (§5); o item 3
acima o substitui por uma prova que roda em todo PR de frontend, em vez de 3
execuções manuais no mesmo commit.
