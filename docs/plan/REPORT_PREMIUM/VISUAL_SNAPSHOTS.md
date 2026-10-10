# Visual snapshots do relatório — operação

> Lane `report-a11y-finalize` item 3. Snapshots por seção × tema light/dark
> em [`frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts`](../../../frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts).

## Por que existe

Detectar regressão visual estrutural — mudança em token de cor, sumiço de
componente, layout shift — em cada seção do relatório nativo. Cobre o
buraco que axe-core (semântica) e Lighthouse (perfis agregados) não
pegam.

## Por que é opt-in (label `visual` ou `workflow_dispatch`)

- 35 testes neste spec (13 seções + cover + sumário executivo + 2 estados de
  `S_parecer`, × 2 temas, mais a tabela de métricas do parecer no papel, só
  light), dos quais 31 produzem baseline — `S4` e `APP_C` não montam com a
  fixture `medium`. O projeto `visual` roda 50 no total, em 3 arquivos: este, o
  `sections.fixtures.smoke.visual.spec.ts` (10) e o
  `visual-regression.visual.spec.ts` (5). ~2 min (medido: 1m57s no run
  `33326297663`), mas não vale bloquear todo PR por isso: a maioria não toca o
  renderer. <!-- re-medido 2026-08-30 no closeout da A40.l103 (#1859), que
  somou as 2 baselines de `sumario-executivo`: 32→34, 28→30, 42→44. -->
  <!-- re-medido 2026-10-08 no closeout da A40.l92 (#2065) com
       `npx playwright test --project=visual --list`: +1 teste e +1 baseline
       (`parecer-metricas-print`), 34→35 e 30→31. O total do projeto deu 50, não
       45: os 5 testes do `visual-regression.visual.spec.ts` não estavam na conta
       anterior (44 = 34 + 10). -->
  <!-- O "~50 testes (24 seções)" que estava aqui era da era Tático+USA
       (ADR-151 / ADR-168) e ficou stale por ~4 meses. Contagem em doc
       envelhece — confira no spec antes de citar. -->
- Baselines são **OS-específicas** (chromium em Linux ≠ macOS por
  font hinting + sub-pixel antialiasing). Comitar baselines macOS em
  PR de dev quebra o CI Linux.

## Fluxo de baseline (primeira vez OU após mudança visual aprovada)

1. Na branch, **apague** as baselines que a mudança pode tocar — na dúvida, as
   26 de seção (todas as de `sections.snapshots.visual.spec.ts-snapshots/` menos
   `cover-*`, `sumario-executivo-*` e `parecer-metricas-print-*`).
2. Dispare `gh workflow run CI --ref <branch> -f run_visual=true -f update_visual_baselines=true`.
3. Baixe o artefato `report-visual-baselines-generated` e copie os PNGs para
   `sections.snapshots.visual.spec.ts-snapshots/`. O render é determinístico
   (ruído 0 px, §Tolerância): a baseline que não mudou volta byte-idêntica e
   some do diff do git.
4. Abra cada PNG que o git acusa e **atribua** cada diferença a uma mudança do
   PR, ou à deriva de um PR anterior, nomeando-o. Diferença sem dono é
   regressão até prova em contrário — se for, corrija o código.
5. Commite no mesmo PR, com o label `visual`: o run do label compara contra o
   que você commitou.

> ⚠️ **Apagar não é opcional.** `--update-snapshots` sem valor usa o preset
> `changed`, que reescreve só a baseline que **reprova**; a irmã com diff sob a
> tolerância fica velha, sem sinal. Medido em 2026-10-09: 19 das 26 baselines de
> seção eram de render antigo. O #1569 reescreveu `APP-A` light (acima de 2,5%)
> e deixou a dark (2,37%); `APP-D` não era regenerada desde o #174 (maio). No
> mesmo dia o #2206 reescreveu `APP-A` dark, `APP-B` e `APP-D` e deixou `APP-A`
> light e `S1` com a copy antiga. O conserto na origem seria
> `--update-snapshots=all` no `ci.yml`.

> **Nunca** rode `--update-snapshots` localmente em macOS/Windows e
> commite o resultado. `.gitignore` já bloqueia `*-darwin.png`/`*-win32.png`,
> mas o gate humano é leitura visual: arquivos em `__snapshots__/` devem
> ter sufixo `-linux`.

## Tolerância

**Não existe mais tolerância absoluta neste spec.** O `maxDiffPixels: 200` que
esta seção descrevia saiu em duas etapas: a [[A40.l53]] (#1453) migrou as 26
baselines de seção para razão, e a [[A40.l103]] (#1859) tirou as 2 últimas (a
capa). Combinar os dois é armadilha — Playwright usa `Math.min(absoluto,
ratio×área)`, então o piso absoluto **anula** o ratio em imagem grande.

Três alvos, todos **medidos nos dois extremos** — piso de ruído e menor mudança
que precisa reprovar:

| Alvo | Valor | Par medido |
| --- | --- | --- |
| Seções (helper) | `maxDiffPixelRatio: 0.00003` | Ruído **0 px**: dois `workflow_dispatch` do mesmo SHA devolveram as 31 baselines byte-idênticas (runs 38001880308 / 38001884617 no Playwright 1.63; 37913203304 / 37913206241 no 1.60; 37878128246 / 37878130334 no 1.59). Menor mudança **262 px**: `"XX"` ao fim do `<h2>`, a classe em que o `<h2>` da S9 mudou e o gate ficou verde — 262–265 px nas 26 baselines (run 37917805709). Quem limita é a maior seção, S2 (2,9 Mpx): 86 px de folga, 3× abaixo. A barra cheia na linha de teto da [[A40.l92]] dá 1.135 px e reprova em `S_parecer-parcial` (run 37917727206); sob o `0.025` anterior, passava |
| `cover` e `sumario-executivo` | `maxDiffPixelRatio: 0.0003` | [[A40.l103]]: ruído 0 px; `"XX"` no `subtitle` = 304 px (~0,076%); 0.0003 ≈ 120 px na capa. Nenhum dos dois tem canvas |
| `parecer-metricas-print` (papel, só light) | `maxDiffPixelRatio: 0.0003` | [[A40.l92]]: ruído 0 px; a barra cheia na linha de teto = 1.135 px, ~11× acima do teto (~105 px em 703×500). É a única baseline da tabela no papel |

> ⚠️ **O par é em px; a tolerância é razão.** A folga em px cresce com a área,
> então uma razão para imagens de 0,2 a 2,9 Mpx é limitada pela MAIOR. Seção
> que passar de ~8,7 Mpx deixa de pegar o `<h2>` trocado — re-meça antes de
> aceitá-la. É por isso que a capa (0,4 Mpx) tem razão 10× maior que a do
> helper: em px, 120 contra os 86 da S2.

> ⚠️ **O que a tolerância das seções NÃO pega, declarado.** Trocar 2
> caracteres de texto de 12px muda 29–87 px (run 37882160857) e passa nas
> seções grandes; o separador decimal `42.8%` → `42,8%` do #2091 mudou 13 px.
> Isso é escopo de gate de texto (`print-text.@critical`, ESLint de
> `formatPercent`), não de pixel.

> ⚠️ **O custo: reflow de 1px reprova.** Mudança que desloca uma seção em
> fração de px marca milhares de px nela — a `APP-B` light marcava 18.813 pelo
> pixelmatch. A folga de 2,5% engolia isso, e junto engolia a deriva. O preço
> agora é rebaseline atribuída no PR que causou o reflow; o candidato para
> baixá-lo é comparar com realinhamento `dy=±1` antes de reprovar
> ([[PLAN-report-trust]] §Deferimentos do closeout da [[A40.l103]]).

> ⚠️ **`--update-snapshots` só reescreve quando a comparação FALHA.** Mutação
> sob a tolerância devolve o arquivo antigo intacto e o diff acusa `0px` — que
> é o arquivo comparado consigo mesmo, não medição. Para medir de verdade,
> apague a baseline na branch de sonda. Para ler o tamanho de uma mudança com
> o contador do próprio gate, rode a sonda com `maxDiffPixelRatio: 0`: todo
> snapshot que muda reprova e o log diz quantos pixels.

## Mascarar elementos voláteis

O spec respeita `[data-mask-snapshot]`. Se um componente legitimamente
muda em cada render (ex.: timestamp "Gerado em ${now}"), adicionar o
atributo evita falsos-positivos:

```tsx
<span data-mask-snapshot>{generatedAt}</span>
```

Todo recorte também mascara os FABs do `FloatingNav` (`floatingNavMask` no
spec). São `position: fixed`, então entram no recorte de qualquer seção que
caia no canto inferior direito da viewport — estavam em 16 das 26 baselines de
seção até 2026-10-09 —, e a visibilidade deles depende do scroll, logo da
altura da página. A máscara cobre o border-box; a sombra fica de fora, e no
pior caso (os dois FABs sumindo juntos) muda 1.486 px crus com delta máximo de
41,5% do limiar do pixelmatch: o comparador conta 0 (runs 37882163019 /
37888645408).

## Decisão D3 — mobile spec fica fora desta lane

Snapshot mobile (<767px) exige decisão de produto sobre o que sai/vira
lista — ver [batch2.13](../../archive/BACKLOG-pre-shim-2026-05-07.md#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes).
Quando convergir, abrir lane `report-mobile-spec` separada e adicionar
viewport mobile a este spec ou um spec irmão.

## Por que não mergeei baselines neste commit

Baselines têm que vir do runner Linux do CI, não da máquina dev (macOS).
A ordem correta:

1. ✅ Spec + CI job + docs (este commit)
2. Trigger primeiro `workflow_dispatch run_visual=true` em main após o
   merge → baselines geradas pelo Linux runner.
3. Baixar artefato + commitar baselines (`__snapshots__/*-linux.png`).
4. CI subsequentes diffam contra elas.

Esse passo 2-3 é tarefa do mantenedor da lane (humano), não automação.
