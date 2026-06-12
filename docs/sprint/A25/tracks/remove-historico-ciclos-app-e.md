---
id: TRACK-remove-historico-ciclos-app-e
type: track
title: "Remover card 'Histórico de Ciclos' (Apêndice E) do relatório React"
lane: null
sprint: A25
plan: PLAN-snapshot-changelog-v3
status: ready
created_at: "2026-06-12"
agent_role: null
tags:
  - type/track
  - status/ready
  - area/report
  - sprint/a25
  - priority/p2
---

# Track — remover card "Histórico de Ciclos" do Apêndice E

Self-contained: executável sem contexto da sessão de origem. Branch
`agent/remove-historico-ciclos/<yyyyMMdd-HHmm>`. **1 PR frontend-only**
(código + testes + entrada de changelog). P2 standalone — não bloqueia
nem é bloqueado por lanes da A25.

## Contexto e decisão

O card "Histórico de Ciclos" vive dentro do Apêndice E ("Próximos
Ciclos e Roadmap") em
`frontend/src/components/report/sections/ApendicesSections.tsx`
(função `ApendiceESection`). Ele renderiza `data.changelog`
([[ADR-148]] v2.8) — o **mesmo** diff t vs. t-1 que já aparece inline
nas seções via `SectionSnapshotDiff` (S1/S2/S3/T2/T3/T5). Não é
histórico: é um único par (relatório atual vs. imediatamente anterior),
sem âncora de seção, num apêndice forward-looking.

Decisão de 2026-06-12 (sessão com `product-designer` +
`financial-planner` + `product-manager`): **remover já, sem esperar
W4 do plano [[PLAN-snapshot-changelog-v3]]**. Razões:

1. Duplicata com fidelidade inferior do que a futura seção V0
   ([[ADR-190]] · W4) entregará no topo do relatório; pós-W4 viraria
   contradição visual (sem `direction_positive`, dívida ↑ apareceria
   "verde" no apêndice e "vermelha" no V0).
2. Rótulo enganoso — promete série multi-ciclo, entrega par único.
   O formato foi declarado "não diz nada" pelo usuário em 2026-05-11
   (origem do ADR-190).
3. W2–W4 não têm data; W4-T07 **não** cobre o APP_E — sem este track,
   o card ficaria órfão pós-W4.
4. Nenhuma metodologia (Perini/Cerbasi/AUVP) prescreve retrospecto
   narrativo single-pair em apêndice. A necessidade real (série
   multi-ciclo de KPIs) virou backlog W5 do plano
   [[PLAN-snapshot-changelog-v3]] — **não** é escopo deste track.

Não exige ADR `Proposto`: remoção frontend-only de UI, sem DB, sem
contrato API, sem invariante crítico (política CLAUDE.md §ADR).

## Mapa de remoção (dead code: o que sai)

Todos os paths relativos à raiz do repo. Linhas referem-se ao estado
de 2026-06-12 (commit `81850612`) — confirme com `rg` antes de editar.

### 1. `frontend/src/components/report/sections/ApendicesSections.tsx`

- **Import** `SnapshotChangelogList` + `type SnapshotChangelogEntryView`
  (linhas 8–11) — único uso no arquivo é o card; remover.
- **Import** `type ChangelogEntryRead` (linha 13) — único uso é
  `toEntryView`; remover do import (manter `ReportAnalysisData`).
- **`toEntryView`** (linhas 384–391) — helper local exclusivo do card;
  remover. Atenção: `SectionSnapshotDiff.tsx` tem uma **cópia própria**
  de `toEntryView` — não é compartilhado, não há outro consumidor.
- **Em `ApendiceESection`** (linhas 400–424): remover as consts
  `changelog` e `entries` e o bloco
  `<ReportCard variant="highlight" title="Histórico de Ciclos" …>`
  inteiro (incluindo os fallbacks "Primeiro relatório do workspace…"
  e "Nenhuma mudança material…", que vivem dentro do card). A função
  passa a renderizar apenas `SectionSummary` + `SectionFallback`.
- **Docstring** (linhas 393–399): reescrever — hoje descreve o card
  removido ("Consolida `data.changelog` … em 'Histórico de Ciclos'").
  Nova docstring: APP_E é seção forward-looking de roadmap/próximos
  passos, alimentada por narrativas E5.N com fallback determinístico;
  histórico de variação vs. relatório anterior é responsabilidade dos
  diffs por seção (e da futura V0, [[ADR-190]]).

### 2. `frontend/src/components/report/utils/conclusionUtils.ts`

- Linha 278: fallback de summary do APP_E é
  `"Histórico de ciclos e próximos passos do roadmap."` → trocar por
  `"Próximos passos do roadmap."`.
- **NÃO tocar** na linha ~301 (`deriveConclusion` lê `data.changelog`
  para anexar summary determinístico à conclusão) — é feature
  independente do card e continua válida.

### 3. Testes — `frontend/tests/components/report/apendices.test.tsx`

O `describe("ApendiceESection")` (linhas 204–259) tem 4 testes que
asseguram o card e seus fallbacks. Substituir por testes que travam o
**novo** comportamento:

- APP_E renderiza com `emptyData()` sem crash e **sem** o texto
  "Histórico de Ciclos" (`queryByText` → `null`).
- Com `data.changelog` populado (reusar o payload do teste atual),
  os summaries do changelog **não** aparecem no APP_E (anti-regressão
  de duplicação — é o teste que impede o card de voltar).
- Fallback de summary da seção presente ("Próximos passos do
  roadmap.") quando narrativas ausentes.

### 4. Baselines visuais (Playwright `visual`, linux/CI-only)

- `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts-snapshots/APP-E-dark-visual-linux.png`
  e `APP-E-light-visual-linux.png` mudam (card `size="full"` some).
  Regenerar **no CI** (baselines são OS-specific):
  `npm run test:e2e -- --project=visual --grep sections.snapshots --update-snapshots`
  conforme header do spec — nunca gerar em macOS local.
- **PDF print baseline** (`__snapshots__/report.print.pdf.png`):
  compara só a **página 1** do PDF; APP_E é o último apêndice e não
  aparece na página 1 → **não regenerar**. Se o job opt-in
  `frontend-print-visual` (label `print`) acusar diff, investigar
  antes de aceitar.

## O que NÃO remover (vivo até W4 — não é dead code)

| Símbolo | Onde | Consumidor que o mantém vivo |
| --- | --- | --- |
| `SnapshotChangelogList` + `SnapshotChangelogEntryView` | `frontend/src/components/report/ui/SnapshotChangelogList.tsx` (+ re-export em `ui/index.ts`) | `SectionSnapshotDiff.tsx` (diffs inline S1/S2/S3/T2/T3/T5) |
| `SectionSnapshotDiff.tsx` (incl. seu `toEntryView` próprio) | `frontend/src/components/report/` | Seções S1/S2/S3/T2/T3/T5 — remoção é **W4-T07** do plano v3 |
| `ChangelogEntryRead` + campo `changelog` do payload | `frontend/src/lib/api/reports.ts` | Wire ADR-148; consumido por `SectionSnapshotDiff` e `conclusionUtils` |
| `SnapshotChangelogBuilder` + DTOs backend/pipeline | `pipeline/` + `backend/app/` | Produtor do `data.changelog`; fora de escopo |
| Cards `proximos_ciclos`/`disclaimers` do APP_E em `config/report_layout.yaml` | `config/report_layout.yaml` linhas ~574–579 | **Non-goal explícito**: APP_E está em `MIGRATED_SECTIONS` (`MigratedSection.tsx`) — cards de seção migrada não são consumidos pelo renderer, são documentação de intenção; o mesmo vale para APP_D etc. Limpeza disso é cleanup repo-wide do plano REPORT_PREMIUM, não deste track |
| Specs e2e `a11y.@critical` / `sections.fixtures.smoke.visual` | `frontend/tests/e2e/reports/` | Asseguram **presença da seção** APP_E, que continua existindo |
| `dev/_planner_coverage_internals.py` (`APP_E` em `PLANNER_INTERNAL_SECTIONS`) | `dev/` | Seção continua existindo; sem mudança |

**Nota de sequência (W4 ↔ este track):** se este track mergear
**depois** de W4-T07, reconferir se `SnapshotChangelogList` ainda tem
consumidor; se não tiver, sinalizar follow-up de dead code (o non-goal
acima pressupõe ordem track → W4).

## Passos

1. `git checkout -b agent/remove-historico-ciclos/<ts>` a partir de
   `origin/main` atualizado.
2. Aplicar §Mapa de remoção itens 1–2; rodar
   `cd frontend && npx tsc --noEmit` para confirmar zero import órfão.
3. Reescrever testes (§3); `cd frontend && npm test -- --run` verde.
4. Varredura final de resíduo:
   `rg -i "histórico de ciclos" frontend/ backend/ config/ docs/reference/`
   deve retornar **0 hits em código/config** (hits em `docs/plan/`,
   `docs/sprint/` e ADRs são histórico de decisão — esperados).
5. Criar `docs/sprint/A25/changelog/CHG-<yyyy-mm-dd>-REMOVE-HISTORICO-CICLOS.md`
   (criar o diretório `changelog/`; frontmatter conforme
   `docs/_schemas/note-changelog-entry.schema.json`: `sprint: A25`,
   `lane: null`, `prs: [<n>]`) e rodar
   `python3 dev/build_doc_index.py --inline` (commitar diff de
   `_generated/`).
6. Flippar este track para `status: consumed` + `consumed_at` no
   mesmo PR; atualizar a linha de W4-T07 no plano
   [[PLAN-snapshot-changelog-v3]] de "remoção planejada" para
   "removido em PR #<n>".
7. `pre-commit run --all-files` + suíte frontend; abrir PR; baselines
   visuais APP-E regeneradas via CI antes do merge.

## Critério de aceite (gate verificável)

Card removido quando **todas** as condições valem:

- `rg -i "histórico de ciclos" frontend/src frontend/tests backend config`
  → 0 hits.
- `npx tsc --noEmit` e `npm test -- --run` verdes; nenhum import/type
  órfão (`SnapshotChangelogEntryView` permanece **somente** via
  `SnapshotChangelogList`/`SectionSnapshotDiff`).
- Teste anti-regressão de duplicação presente (changelog populado não
  renderiza no APP_E).
- Baselines `APP-E-{dark,light}-visual-linux.png` regeneradas no CI;
  PDF página-1 inalterado.
- PR mergeado em `main` (squash) com CI verde; entrada de changelog em
  `docs/sprint/A25/changelog/`; track flippado para `consumed`.
