---
id: TRACK-report-a11y-finalize
type: track
title: "Track Report a11y + Playwright finalize — resíduo F12 do Report Premium"
sprint: A11
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a11
  - status/consumed
---

# Track Report a11y + Playwright finalize — resíduo F12 do Report Premium

> **Lane ID:** `report-a11y-finalize`
> **Branch prefix:** `agent/report-a11y-finalize/<yyyyMMdd-HHmm>`
> **Depende de:** nada bloqueante. **Recomendado** ter [batch2.8](../../../BACKLOG.md#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes) (shapes TS de `ReportAnalysisData`) antes — destrava asserções estáveis de DOM. Pode rodar em paralelo se aceitar `data-testid` defensivo.
> **Paralelo com:** `adr-129-e6-kill` (independente — não toca disco/E6) · `report-v1-polish` (este lane produz código + CI; o outro produz docs/checklist)
> **Conflita com:** qualquer agente mexendo em `frontend/src/components/report/**`, `frontend/tests/e2e/reports/**`, `frontend/playwright.config.ts`, `.github/workflows/*frontend*`
> **Sprint:** Report Premium UI · resíduo Fase 12
> **Índice de prompts:** [README.md](../../../../README.md)
> **Fonte de verdade:**
> - [BACKLOG.md — pickup table](../../../BACKLOG.md#lanes-abertas-agora--pickup-table) (linha `report-a11y-finalize`)
> - [plan/REPORT_PREMIUM/_README.md §11](../../../plan/REPORT_PREMIUM/_README.md) (Fase 12 original — itens não-E6 que sobreviveram)
> - [F11.2c](../../../BACKLOG.md#f112--hierarquia-de-números) e [F11.3](../../../BACKLOG.md#f113--print--pdf-como-entregável-de-consultoria) (itens já entregues, contexto)
> - [batch2.14](../../../BACKLOG.md#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes) (checklist WCAG — output desta lane)

> **Objetivo (1 frase):** levar o relatório React `/reports/[id]` ao gate
> de qualidade que justificava a Fase 12 do plano Premium — axe-core sem
> violações `critical+serious` por seção, tab-order completo, Lighthouse
> com threshold no CI, snapshots Playwright por seção em light+dark — sem
> nada que dependesse do `e6_render.py` (morto via [ADR-129](../../../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side)).

---

## Por que esta lane agora

Print CSS, export PDF e checklist humano de QA já estão entregues em
[F11.3a/b/c](../../../BACKLOG.md#f113--print--pdf-como-entregável-de-consultoria).
Os itens **não-entregues** que sobreviveram à ADR-129:

1. **axe-core gate** por seção — hoje a a11y é confiada na construção do
   React + tokens; não há fail-build se um componente novo introduzir
   violação.
2. **Tab-order garantido** — `aria-label` em FloatingNav/ThemeToggle/
   ModeToggle existe pontualmente, mas não há E2E que percorre o tab
   order completo do relatório.
3. **Lighthouse threshold no CI** — não roda hoje; usuários só descobrem
   regressão em audit ad-hoc.
4. **Snapshots por seção light+dark** — só smoke do hero (cover) tem
   screenshot; S1–S10/T3–T6/U1–U4 não. F11.2c (regressão visual) está
   ☐ pendente exatamente por isso.
5. **Checklist WCAG operacional** ([batch2.14](../../../BACKLOG.md#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes))
   — pode ser auto-derivado do output dos 4 itens acima.

Gate empírico: **toda mudança visual futura no shell falha cedo** se
violar a11y, tab order ou regredir snapshot.

---

## ⚠️ Decisões pendentes — alinhar com dono ANTES de pegar a lane

Não execute sem responder estas três; o trade-off muda o esforço em ~1.5×.

### Decisão D1 — Severidade do gate axe-core

| Opção | Trade-off |
|---|---|
| **`critical+serious`** | Catch-all dos riscos reais; ~zero falsos-positivos. Recomendado. |
| **Só `critical`** | Mais permissivo; deixa contraste-AA-borderline e label-implícito passarem. |
| `critical+serious+moderate` | Pega tudo, mas inclui "color-contrast" em estados de hover que dependem de tokens — vai dar falso-positivo até batch2.14 do checklist convergir. |

**Default sugerido:** `critical+serious`. Anuncie a escolha no commit
inicial e linkar no [BACKLOG batch2.14](../../../BACKLOG.md#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes).

### Decisão D2 — Lighthouse no CI: thresholds e número de runs

Recomendação:

```yaml
# frontend/lighthouserc.cjs (sugestão)
{
  ci: {
    collect: { numberOfRuns: 3, settings: { preset: "desktop" } },
    assert: {
      assertions: {
        "categories:performance":      ["error", { minScore: 0.85 }],
        "categories:accessibility":    ["error", { minScore: 0.95 }],
        "categories:best-practices":   ["error", { minScore: 0.95 }],
        "categories:seo":              ["warn",  { minScore: 0.90 }],
      }
    }
  }
}
```

Decisão real: roda a cada PR (custa ~2-3 min) ou só no `main` post-merge?
**Default sugerido:** PR-time, mas só na rota `/reports/[id]` com fixture
medium (não percorre app inteiro).

### Decisão D3 — Spec mobile entra ou fica fora?

[batch2.13](../../../BACKLOG.md#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes)
está aberto: "que seções saem em <767px? Kanban vira lista?". Há duas
saídas:

- **Dentro desta lane:** snapshots adicionais em viewport mobile + spec
  Markdown em `docs/plan/REPORT_PREMIUM/_README.md` Delta novo. **+1.5 dia**.
- **Fora:** lane separada `report-mobile-spec` futura. Esta lane gateia
  só desktop + tablet largo (1280×800).

**Default sugerido:** **fora**. A spec mobile é decisão de produto,
não engenharia; arrastar pra esta lane mistura preocupações.

---

## Regras inegociáveis

- **Sem código novo de runtime no shell.** Esta lane é gate + testes +
  CI. Se descobrir um componente sem `aria-label`, **adiciona o label**
  (mudança defensiva pequena), mas não refatora estrutura — abre
  follow-up se não for trivial.
- **Sem `any` em TypeScript.** Vale também para fixtures Playwright e
  helpers axe.
- **Fixtures sintéticas.** Zero dado real (CPF, valores, nomes da
  família Andrade Silva do dataset atual). Use fakes em
  `frontend/tests/e2e/fixtures/reports/{small,medium,large}.json` —
  o slug `small/medium/large` reflete densidade de dados, não tamanho
  de tela.
- **Snapshots commitados são source-of-truth.** Atualização explícita:
  `npm run test:e2e -- --update-snapshots` em commit dedicado, com
  diff visual revisado; nunca `--update` direto + push.
- **Gate empírico:** após o merge, alguém deve ser capaz de adicionar um
  componente sem `aria-label` ou um valor sem `tabular-nums` e ver o
  CI falhar. Se o gate não pega regressão real, ele não vale o tempo.

---

## Entregas

### 1. Tab-order E2E `@critical`

**Arquivo:** `frontend/tests/e2e/reports/tab-order.@critical.spec.ts`

Percorre o tab order esperado em `/reports/[id]` (fixture medium):

```
skip-nav  →  ReportThemeToggle  →  ModeToggle  →  ReportTopNav (TOC links)
       →  S1 cards/charts  →  S2 ...  →  T1 Kanban  →  ...  →  ExportToolbar
```

Para cada par `(componente, índice esperado)`, asserta `await
expect(page.locator(":focus")).toHaveAttribute("data-tab-target", ...)`
ou seletor equivalente. Se alguém adicionar `<button>` sem
`tabindex={-1}` ou `aria-hidden`, o teste falha.

Bônus: smoke de skip-nav — `Tab` → `Enter` em "Pular para conteúdo"
foca o `main`.

### 2. axe-core gate por seção

**Arquivo:** `frontend/tests/e2e/reports/a11y.@critical.spec.ts`

Para cada seção registrada em
[`config/report_layout.yaml`](../../../../config/report_layout.yaml) — S1–S10,
T1–T6, U1–U4, A–E — roda `@axe-core/playwright` e asserta zero
violações no nível escolhido em D1.

Helper compartilhado em `frontend/tests/e2e/helpers/axe.ts`:

```ts
export async function expectNoA11yViolations(
  page: Page,
  selector: string,
  severities: ("critical" | "serious" | "moderate")[] = ["critical", "serious"],
) { /* roda axe(), filtra por severities, formata mensagem com seletor + regra */ }
```

### 3. Snapshots por seção (light + dark)

**Arquivo:** `frontend/tests/e2e/reports/sections.snapshots.spec.ts`

Não-`@critical` (lento). Para cada seção habilitada no layout:

```ts
test(`S1 hero — light`, async ({ page }) => {
  await page.goto("/reports/fixture-medium?theme=light");
  await page.locator('[data-section="S1"]').screenshot({ /* ... */ });
  await expect(buf).toMatchSnapshot("S1.light.png", { maxDiffPixels: 200 });
});
```

Total: ~25 seções × 2 temas = 50 snapshots. Espera-se que rode em
~3-4 min em CI.

### 4. Lighthouse no CI

**Arquivo:** `frontend/lighthouserc.cjs` + entrada nova em
`.github/workflows/frontend-ci.yml` (ou onde o CI frontend mora).

Thresholds em D2. Job separado dos outros para isolar custo.

### 5. Checklist WCAG operacional

**Arquivo:** `docs/plan/REPORT_PREMIUM/A11Y_CHECKLIST.md` (novo).

Tabela por seção × WCAG 2.1 AA criterion (1.4.3 contrast,
2.1.1 keyboard, 2.4.3 focus order, 2.4.7 focus visible, 4.1.2 name/role/
value). Output dos itens 1–4 popula a coluna "automatizado por"; o que
sobrar fica como "checklist humano". Absorve [batch2.14](../../../BACKLOG.md#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes).

### 6. Atualização do BACKLOG e CHANGELOG

- `docs/BACKLOG.md` — marca a lane `report-a11y-finalize` como ✅,
  marca `batch2.14` como ✅ (absorvida), atualiza F11.2c para ✅.
- `docs/CHANGELOG.md` — entrada "Report Premium UI — a11y/Lighthouse
  gates ativados (resíduo F12, ADR-129 contexto)".

---

## Gate de saída (commit final em `main`, CI verde)

1. `npm run test:e2e -- --grep @critical` verde, com a11y + tab-order
   incluídos.
2. Suíte de snapshots verde local; commit de baseline mergeado.
3. Lighthouse CI passa thresholds em D2 contra fixture `medium`.
4. `docs/plan/REPORT_PREMIUM/A11Y_CHECKLIST.md` mergeado, lane fechada no BACKLOG.
5. **Teste empírico do gate:** abrir PR descartável adicionando
   `<button>` sem `aria-label` num card; CI **deve falhar**. Reverter
   o PR e referenciá-lo no commit final ("gate validado por PR
   descartável `agent/test-axe-gate/...`").

---

## Estimativa

3-5 dias de trabalho ativo, depende muito de D3 (mobile in/out).
Distribuição típica:

- Item 1 (tab-order): 0.5 dia
- Item 2 (axe gate): 1 dia (helpers + 25 seções)
- Item 3 (snapshots): 1.5 dia (gerar baseline + revisar visualmente)
- Item 4 (Lighthouse CI): 0.5 dia
- Item 5 (checklist): 0.5 dia (mecânico, decorre dos outros)
- Item 6 (docs): 0.5 dia

**Commits esperados:** 6-10 commits coesos. Cada item em 1-2 commits.
Snapshots têm commit dedicado de baseline.

---

## Anti-escopo (não fazer aqui)

- Refactor de componentes do shell (FloatingNav etc.). Adicionar
  `aria-label` faltante ✅; trocar API do componente ❌.
- Mobile spec — D3 default = fora.
- Mexer em `e6_render.py` ou qualquer ressurreição do renderer
  server-side. Está morto via [ADR-129](../../../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side).
- Migrar suíte E2E para outro runner. Continua Playwright.
- Performance budget no React (React Profiler, code-split novo). Lighthouse
  já cobre o que importa para esta lane.
