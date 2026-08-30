# Visual snapshots do relatório — operação

> Lane `report-a11y-finalize` item 3. Snapshots por seção × tema light/dark
> em [`frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts`](../../../frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts).

## Por que existe

Detectar regressão visual estrutural — mudança em token de cor, sumiço de
componente, layout shift — em cada seção do relatório nativo. Cobre o
buraco que axe-core (semântica) e Lighthouse (perfis agregados) não
pegam.

## Por que é opt-in (label `visual` ou `workflow_dispatch`)

- 34 testes neste spec (13 seções + cover + sumário executivo + 2 estados de
  `S_parecer`, × 2 temas), dos quais 30 produzem baseline — `S4` e `APP_C` não
  montam com a fixture `medium`. O projeto `visual` roda 44 no total, somando o
  `sections.fixtures.smoke.visual.spec.ts`. ~2 min (medido: 1m57s no run
  `33326297663`), mas não vale bloquear todo PR por isso: a maioria não toca o
  renderer. <!-- re-medido 2026-08-30 no closeout da A40.l103 (#1859), que
  somou as 2 baselines de `sumario-executivo`: 32→34, 28→30, 42→44. -->
  <!-- O "~50 testes (24 seções)" que estava aqui era da era Tático+USA
       (ADR-151 / ADR-168) e ficou stale por ~4 meses. Contagem em doc
       envelhece — confira no spec antes de citar. -->
- Baselines são **OS-específicas** (chromium em Linux ≠ macOS por
  font hinting + sub-pixel antialiasing). Comitar baselines macOS em
  PR de dev quebra o CI Linux.

## Fluxo de baseline (primeira vez OU após mudança visual aprovada)

1. Marcar PR com label `visual` (ou disparar `workflow_dispatch` com
   `run_visual=true`).
2. Job `frontend-visual` roda e **falha** se não houver baseline (ou
   se diff for > tolerância).
3. Baixar artefato `report-visual-snapshots` do run do CI.
4. Inspecionar o diff visualmente:
   - Se a mudança é intencional: extrair `tests/e2e/reports/__snapshots__/`
     do artefato + commitar como nova baseline (apenas `*-linux.png`).
   - Se é regressão: corrigir o código.
5. Re-rodar — baseline atualizada, CI passa.

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

Dois valores em uso, e a diferença é deliberada:

| Alvo | Valor | Por quê |
| --- | --- | --- |
| Seções (helper) | `maxDiffPixelRatio: 0.025` | Absorve subpixel de canvas do chart.js. Herdado da [[A40.l53]]; **não** re-medido desde então |
| `cover` e `sumario-executivo` | `maxDiffPixelRatio: 0.0003` | **Medido nos dois extremos** pela [[A40.l103]]: piso de ruído 0px (2 `workflow_dispatch` do mesmo SHA devolveram 28/28 baselines byte-idênticas) e menor mudança que precisa reprovar 304px (~0,076%, `"XX"` no `subtitle`). Nenhum dos dois tem canvas, logo não herdam o `0.025` |

> ⚠️ **`0.025` é folga grande em imagem pequena.** O primeiro valor tentado na
> capa, `0.005`, deixava passar uma mudança de texto por folga de 6,6× — a
> classe em que o `<h2>` da S9 mudou e o gate ficou verde. Ao criar baseline
> nova, meça o par (piso de ruído, menor mudança que importa) em vez de herdar.

> ⚠️ **`--update-snapshots` só reescreve quando a comparação FALHA.** Mutação
> sob a tolerância devolve o arquivo antigo intacto e o diff acusa `0px` — que
> é o arquivo comparado consigo mesmo, não medição. Para medir de verdade,
> apague a baseline na branch de sonda.

## Mascarar elementos voláteis

O spec respeita `[data-mask-snapshot]`. Se um componente legitimamente
muda em cada render (ex.: timestamp "Gerado em ${now}"), adicionar o
atributo evita falsos-positivos:

```tsx
<span data-mask-snapshot>{generatedAt}</span>
```

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
