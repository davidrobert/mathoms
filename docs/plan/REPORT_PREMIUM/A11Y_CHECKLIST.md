# Report a11y — Checklist WCAG 2.1 AA operacional

> Lane `report-a11y-finalize` item 5 + absorve
> [batch2.14](../../BACKLOG.md#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes).
>
> **Para que serve:** mapa do que está protegido por gate automático
> versus o que ainda depende de revisão humana, por seção do relatório
> nativo (`/reports/[id]`). Use ao alterar uma seção/componente — antes
> de abrir o PR, percorra a coluna "checklist humano" da linha
> correspondente.
>
> **Não use** como roadmap de a11y. Cobertura ≠ ausência de bugs.

---

## Critérios WCAG 2.1 AA cobertos

| ID | Critério | Como o relatório o trata |
|---|---|---|
| **1.4.3** | Contraste mínimo (texto 4.5:1, large 3:1) | tokens `--brand-*`/`--surface-*`/`--semantic-*` calibrados; `<MonetaryValue/>` com `--color-compare-neg`/`--color-compare-pos` (regredido em estados de hover é o risco real). |
| **2.1.1** | Acessível por teclado | sem `onClick` em `<div>`; toggles e Kanban são `<button>`/`role="button"` com handlers de teclado. |
| **2.4.3** | Ordem de foco | DOM order = ordem visual; skip-nav primeiro focável do escopo. |
| **2.4.7** | Foco visível | `:focus-visible` global + outline em tokens; FloatingNav/ExportToolbar idem. |
| **4.1.2** | Nome, papel, valor | `aria-label` em controles icon-only; `<MonetaryValue/>` com texto + `aria-label` para leitor de tela quando ofender visual. |

Demais critérios AA (1.3.1 estrutura, 2.4.4 link purpose, 3.3.1 erros)
são cobertos transversalmente pelo axe-core; não viram colunas próprias
nesta tabela porque nenhuma seção tem regra específica.

---

## Cobertura automática (gates ativos em `main`)

| Gate | Cobre | Onde | Severidade |
|---|---|---|---|
| `axe-core` por seção | 1.4.3 (parcial), 4.1.2 | [a11y.@critical.spec.ts](../../../frontend/tests/e2e/reports/a11y.@critical.spec.ts) | `critical+serious` (D1) |
| Tab-order escopado a `[data-report-scope]` | 2.1.1, 2.4.3, 4.1.2 | [tab-order.@critical.spec.ts](../../../frontend/tests/e2e/reports/tab-order.@critical.spec.ts) | `@critical` (PR-blocking) |
| Lighthouse CI (categoria `accessibility`) | 1.4.3, 2.4.7, 4.1.2 (mistura) | [lighthouserc.cjs](../../../frontend/lighthouserc.cjs) + job `frontend-lighthouse` | `error` em score < 0.95 (D2) |
| Snapshots visuais por seção × tema | regressão estrutural light/dark (não substitui revisão humana de contraste em estados) | [sections.snapshots.visual.spec.ts](../../../frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts) + job `frontend-visual` (opt-in) — ops em [REPORT_VISUAL_SNAPSHOTS.md](VISUAL_SNAPSHOTS.md) | `maxDiffPixels: 200` por seção |
| Gate empírico (one-shot) | meta-validação dos gates acima | [REPORT_A11Y_GATE_PROOF.md](A11Y_GATE_PROOF.md) | manual, 2026-04-25 |

**O que NÃO está coberto automaticamente** (vai pra "checklist humano"):

- Contraste em estados dinâmicos (hover, focus, disabled). Axe corre no
  estado padrão; estados interativos exigem revisão visual.
- Coerência de copy em `aria-label` (axe garante presença, não qualidade
  semântica). "Botão" como label passa axe e falha o usuário.
- Contraste em estados dinâmicos passa por snapshot visual (item 3
  entregue), mas snapshots detectam mudança estrutural — não auditam
  WCAG diretamente.
- Drag & drop do Kanban com teclado (T3) — comportamento que axe não
  detecta.

---

## Por seção × critério × gate

Legenda:
- ✅ — coberto por gate automático (regrede → CI quebra).
- 👁 — checklist humano obrigatório no PR que toca a seção.
- — — N/A para a seção.

### Shell global (cover, top nav, floating nav, export toolbar)

| Componente | 1.4.3 | 2.1.1 | 2.4.3 | 2.4.7 | 4.1.2 | Notas |
|---|---|---|---|---|---|---|
| `SkipNav` | ✅ | ✅ | ✅ | ✅ | ✅ | tab-order garante 1º focável + Enter → `#report-main`. |
| `ReportTopNav` | ✅ | 👁 | ✅ | ✅ | ✅ | TOC humano: link click leva à âncora certa? |
| `ReportThemeToggle` | ✅ | ✅ | — | ✅ | ✅ | aria-label gateado por tab-order. |
| `ModeToggle` | ✅ | 👁 | — | ✅ | ✅ | humano: aria-pressed reflete modo ativo? |
| `FontScaleToggle` | ✅ | ✅ | — | ✅ | ✅ | — |
| `FloatingNav` | ✅ | ✅ | — | ✅ | ✅ | "Voltar ao topo"/"Ir para o final" gateados. |
| `ExportToolbar` | ✅ | ✅ | ✅ | ✅ | ✅ | botões com texto visível. |

### Modo Estratégico (S1–S10 + APP_A–E)

| Seção | 1.4.3 | 2.1.1 | 2.4.3 | 2.4.7 | 4.1.2 | Checklist humano específico |
|---|---|---|---|---|---|---|
| **S1** Patrimônio | ✅ | 👁 | ✅ | ✅ | ✅ | `<MonetaryValue/>` em vermelho contrasta no dark? |
| **S2** Fluxo de Caixa | ✅ | 👁 | ✅ | ✅ | ✅ | gráficos têm `aria-label` descritivo (não só "Chart")? |
| **S3** Investimentos | ✅ | 👁 | ✅ | ✅ | ✅ | tooltips de alocação acessíveis por teclado? |
| **S4** Real Estate | ✅ | — | ✅ | ✅ | ✅ | — |
| **S7** Independência | ✅ | 👁 | ✅ | ✅ | ✅ | toggle de período acessível? |
| **S8** Previdência | ✅ | — | ✅ | ✅ | ✅ | — |
| **S9** Riscos | ✅ | 👁 | ✅ | ✅ | ✅ | matriz de risco descritível? |
| **S10** Síntese | ✅ | ✅ | ✅ | ✅ | ✅ | regressão histórica do gate (commit `9d87ddb`). |
| **APP_A** | ✅ | — | ✅ | ✅ | ✅ | — |
| **APP_B** | ✅ | — | ✅ | ✅ | ✅ | — |
| **APP_C** | ✅ | — | ✅ | ✅ | ✅ | — |
| **APP_D** | ✅ | — | ✅ | ✅ | ✅ | — |
| **APP_E** | ✅ | — | ✅ | ✅ | ✅ | — |

### Modo Tático (T1–T6) — REMOVIDO em [ADR-151](../../DECISIONS.md#adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces)

> **Histórico (2026-04-29):** Modo Tático removido do relatório
> (Direção E · Onda 3). Conteúdo redistribuído: Kanban (T3) e Notas
> (T6) migrados para `/acao` Tarefas/Notas via ADR-154 (Onda 1 ✅);
> tarefas viviam em `/plano-de-acao` (renomeada para `/acao` em
> ADR-152). Sugestões acionáveis vivem em `/acao` Inbox via ADR-153
> (Suggestion aggregate · Onda 5 ✅). Checklist a11y dos novos
> componentes (`<SuggestionCallout/>` inline no relatório,
> `<SuggestionCard/>` em /acao Inbox, NotasTab com `<WorkspaceNotes/>`)
> precisa ser adicionado em lane futura.

### Modo USA (U1–U4)

| Seção | 1.4.3 | 2.1.1 | 2.4.3 | 2.4.7 | 4.1.2 | Checklist humano específico |
|---|---|---|---|---|---|---|
| **U1** Mudança EUA | ✅ | — | ✅ | ✅ | ✅ | — |
| **U2** Green Card | ✅ | — | ✅ | ✅ | ✅ | — |
| **U3** NCLEX | ✅ | — | ✅ | ✅ | ✅ | — |
| **U4** Simulação Mariana | ✅ | 👁 | ✅ | ✅ | ✅ | toggles de cenário acessíveis? |

---

## Checklist humano antes do PR

Use ao tocar qualquer arquivo em `frontend/src/components/report/`:

- [ ] Rodei `npm run test:e2e -- --grep @critical --project=chromium`
      e os 28 testes da lane `report-a11y-finalize` passam.
- [ ] Se adicionei controle interativo: tem `aria-label` (icon-only) ou
      texto visível (botão com label).
- [ ] Se adicionei valor monetário: usei `<MonetaryValue/>`.
- [ ] Se mudei copy de `aria-label`: o texto é compreensível para um
      leitor de tela (não "botão" ou "click here").
- [ ] Se a seção tem novo gráfico: o `<canvas>` tem `aria-label`
      descrevendo o conteúdo (axe não falha sem isso, mas WCAG 1.1.1
      exige).
- [ ] Se mudei tokens de cor: contraste verificado em light **e** dark
      (axe corre em light por default).
- [ ] Se a seção é nova: adicionei o id correspondente em
      `STRATEGIC_SECTIONS`/`TATICO_SECTIONS`/`USA_SECTIONS`/`APPENDICES`
      em [a11y.@critical.spec.ts](../../../frontend/tests/e2e/reports/a11y.@critical.spec.ts).

---

## Quando atualizar este documento

- Sempre que a tabela de cobertura mudar (gate novo, gate removido,
  severidade mudou).
- Sempre que uma 👁 virar ✅ porque um gate cobriu.
- Não atualizar para refletir trabalho feito num PR — esse é trabalho
  do CHANGELOG.
