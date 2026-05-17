# Visual snapshots do relatório — operação

> Lane `report-a11y-finalize` item 3. Snapshots por seção × tema light/dark
> em [`frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts`](../../../frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts).

## Por que existe

Detectar regressão visual estrutural — mudança em token de cor, sumiço de
componente, layout shift — em cada seção do relatório nativo. Cobre o
buraco que axe-core (semântica) e Lighthouse (perfis agregados) não
pegam.

## Por que é opt-in (label `visual` ou `workflow_dispatch`)

- ~50 testes (24 seções × 2 temas) — roda em ~3-4 min, mas não vale
  bloquear todo PR por isso. Maioria dos PRs não toca o renderer.
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

`maxDiffPixels: 200` por seção. Calibrado para absorver:

- Anti-aliasing de chart.js em valores idênticos.
- Variância de tabular-nums em `<MonetaryValue/>` quando o valor não
  mudou (subpixel rendering).

Diffs > 200 pixels indicam mudança estrutural — vão pro fluxo de
revisão acima.

## Mascarar elementos voláteis

O spec respeita `[data-mask-snapshot]`. Se um componente legitimamente
muda em cada render (ex.: timestamp "Gerado em ${now}"), adicionar o
atributo evita falsos-positivos:

```tsx
<span data-mask-snapshot>{generatedAt}</span>
```

## Decisão D3 — mobile spec fica fora desta lane

Snapshot mobile (<767px) exige decisão de produto sobre o que sai/vira
lista — ver [batch2.13](../../BACKLOG.md#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes).
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
