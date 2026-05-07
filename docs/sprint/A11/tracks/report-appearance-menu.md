---
id: TRACK-report-appearance-menu
type: track
title: "Track Report Appearance Menu — refinement ADR-121 Fase 4"
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

# Track Report Appearance Menu — refinement ADR-121 Fase 4

> **Lane ID:** `report-appearance-menu`
> **Branch prefix:** `agent/report-appearance-menu/<yyyyMMdd-HHmm>`
> **Depende de:** nada bloqueante.
> **Paralelo com:** qualquer lane que **não** toque `frontend/src/components/report/shell/**`, `frontend/src/components/report/ReportShell.tsx`, `frontend/src/components/report/useReportFontScale.ts`, `frontend/src/styles/tokens.css`, `design-tokens/tokens.json`, `design-tokens/build.py`.
> **Conflita com:** Onda E (charts UX) **não** — escopos disjuntos. Lanes que mexem na top-nav do relatório (`ReportTopNav.tsx`, `ReportActions.tsx`) — coordenar.
> **Sprint:** Report Premium · refinement [ADR-121](../DECISIONS.md#adr-121--typography-base-13px-com-override-configurável) Fase 4
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:**
> - [BACKLOG.md — pickup table](../BACKLOG.md#lanes-abertas-agora--pickup-table) (linha `report-appearance-menu`)
> - [DECISIONS.md — ADR-121 Refinamento UX (2026-04-26)](../DECISIONS.md#adr-121--typography-base-13px-com-override-configurável)

> **Objetivo (1 frase):** substituir os dois segmented controls separados na top-nav (`FontScaleToggle` "Compacto/Normal/Confortável" + `ReportThemeToggle` "Light/Dark") por um único popover `Aa` (`AppearanceMenu`), com default `normal` (16px) e passos de 4px (14/16/18) — sem alterar a arquitetura `localStorage` da [ADR-121](../DECISIONS.md#adr-121--typography-base-13px-com-override-configurável).

---

## Por que esta lane agora

Reclamação direta do David em sessão de revisão de produto (2026-04-26):

> "No relatório prévia, para que servem os botões 'Compacto', 'Normal' e
> 'Confortável'? Se isso for pra mudar a apresentação do relatório
> deveria estar em configurações. Aparentemente esses botões não fazem
> nada ainda."

Análise CTO + Product Designer (sessão 2026-04-26):

1. Os botões **fazem** algo — alteram `--report-font-base-px` via
   `data-font-scale="..."` no wrapper `[data-report-scope]` e persistem
   em `localStorage["mathoms:report:font-scale"]`. ADR-121 Fase 4
   entregou esse contrato. **A queixa é UX, não bug.**
2. Default era `"compact"` (13px). Passo para `"normal"` (15px) era
   apenas **2px** — visualmente imperceptível, especialmente em
   `MonetaryValue` com `tabular-nums`. Padrão fintech moderno
   (Bloomberg, Mercury, Ramp, Stripe) opera 14-16px; 13px é mesquinho
   para leitura prolongada de famílias e planejadores.
3. Labels "Compacto/Normal/Confortável" são jargão tipográfico — não
   comunicam "tamanho da fonte". Apps de leitura (Medium, NYT, Notion,
   Kindle, Substack, Apple Books) usam ícone `Aa` em escala progressiva.
4. Hipótese do David ("deveria estar em Configurações") confunde duas
   classes de pref: **reading-time** (fonte, tema, line-height — ajustadas
   durante a leitura, com feedback imediato) e **account-time** (locale,
   notificações, default workspace). Pattern de indústria: reading-time
   fica **inline na superfície de leitura**, não em Settings. Idêntico
   ao que `ReportThemeToggle` e `useReportTocOpen` já fazem.
5. Ter dois controles separados (`FontScaleToggle` + `ReportThemeToggle`)
   inflava a top-nav e não escalava: futuras prefs (line-height, largura
   de coluna, modo print) precisariam de mais espaço.

---

## Decisão

| Eixo | Antes | Depois |
| --- | --- | --- |
| Default scale | `compact` (13px) | `normal` (16px) |
| Escalas (base) | 13 / 15 / 17 px | **14 / 16 / 18** px |
| Passo entre extremos | 2 px | **4 px** (perceptível) |
| Controles na top-nav | 2 separados (Font + Theme) | 1 popover unificado (`Aa`) |
| Labels do font scale | "Compacto / Normal / Confortável" | Ícone `Aa` em 3 tamanhos progressivos (12/14/16 px) + tooltip + `aria-label` textual |
| Transição visual | nenhuma | `transition: font-size 180ms ease-out` em `[data-report-scope]` |
| Persistência | `localStorage["mathoms:report:font-scale"]` | **inalterado** |
| Persistência tema | `next-themes` (cookie/localStorage) | **inalterado** |
| ADR | ADR-121 Fase 4 | ADR-121 com subseção "Refinamento UX (2026-04-26)" — **não é ADR nova** |

### Por que NÃO mover para `/settings`

Reading-time prefs seguem padrão da indústria — ficam inline. Settings é
"set once and forget"; reading prefs são tweakadas durante a leitura,
com feedback imediato. Mover para `/settings` força round-trip cognitivo
(ajusta → volta → não gostou → volta de novo) e perde a vantagem do
preview ao vivo (re-flow das tabelas é o melhor "antes/depois"
possível). Idêntico ao padrão consagrado de `ReportThemeToggle` e
`useReportTocOpen`.

Quando `/settings` cross-app nascer (provável com [ADR-130](../DECISIONS.md#adr-130--i18n-dois-eixos-locale--idioma) i18n),
uma ADR nova deverá explicitar o split: **account-level** (locale,
notificações, default workspace) → DB · **reading-level** (fonte, tema,
TOC, futuros line-height/largura) → localStorage. Esta ADR-121
refinada permanece autoritativa sobre o que **fica local**.

---

## Escopo de implementação

### Código

| Arquivo | Mudança |
| --- | --- |
| `frontend/src/components/report/shell/AppearanceMenu.tsx` | **NOVO** — popover `Aa` com 2 segmentos (tamanho + tema). `<details>`-free, `useRef` para click-outside, `useEffect` para `Escape`. SSR-safe (mounted flag para `useTheme`). `aria-label="Aparência"` no trigger; `role="dialog"` no painel. |
| `frontend/src/components/report/shell/index.ts` | Export `AppearanceMenu` (substitui `FontScaleToggle`) |
| `frontend/src/components/report/shell/FontScaleToggle.tsx` | **DELETADO** — absorvido em `AppearanceMenu` |
| `frontend/src/components/report/ReportThemeToggle.tsx` | **DELETADO** — único consumer era `ReportShell`; lógica absorvida em `AppearanceMenu` |
| `frontend/src/components/report/useReportFontScale.ts` | `DEFAULT_SCALE: "compact"` → `"normal"` |
| `frontend/src/components/report/ReportShell.tsx` | Imports atualizados; `<FontScaleToggle/>` + `<ReportThemeToggle/>` → `<AppearanceMenu/>` |
| `frontend/tests/components/report/AppearanceMenu.test.tsx` | **NOVO** — 8 testes do menu (trigger, popover open/close, Escape, click-outside, persistência localStorage, setTheme) + 4 testes do hook (default `"normal"`, leitura/escrita storage, valor inválido). |
| `frontend/tests/components/report/ReportThemeToggle.test.tsx` | **DELETADO** — substituído por `AppearanceMenu.test.tsx` |
| `frontend/tests/components/report/shellPrimitives.test.tsx` | Bloco `<FontScaleToggle />` removido — coberto agora em `AppearanceMenu.test.tsx` |

### Tokens

| Arquivo | Mudança |
| --- | --- |
| `design-tokens/tokens.json` | `report_typography.default_scale`: `"compact"` → `"normal"`. Escalas `compact/normal/comfortable` recalculadas (14/16/18 base + família proporcional). Novo campo `report_typography.transition: "font-size 180ms ease-out"`. |
| `design-tokens/build.py` | `_report_scope_block` emite `transition: ...;` se `typo.transition` estiver presente. Idempotente (gate via `python design-tokens/build.py` reproduz output). |
| `frontend/src/styles/tokens.css` | **REGENERADO** via `python design-tokens/build.py`. Default block agora 16px; `[data-font-scale="compact"]` 14px; `[data-font-scale="comfortable"]` 18px. Transition no base block. |
| `frontend-ops/src/styles/tokens.css` | **REGENERADO** (mesma fonte tokens.json). |

---

## Critérios de aceite

- [ ] `cd frontend && npm test -- --run` — 596+ testes verdes (suite full).
- [ ] `python3 -m pre_commit run --files <arquivos da lane>` — todos hooks pass:
  - `Design tokens gerados estão em sync com tokens.json (ADR-076)` ✅
  - `Code style baseline (P1/P7/P8 não regridem)` ✅ (sem hex novos)
  - `ESLint: frontend/src (no-explicit-any)` ✅
- [ ] **Smoke manual** (UI):
  - Abrir `/reports/[id]` qualquer; trigger `Aa` aparece à direita do divisor na top-nav.
  - Click no `Aa` abre popover; click fora **e** `Escape` fecham.
  - Click em "Confortável" (Aa grande) muda fonte visivelmente; recarregar página mantém preferência.
  - Click em "Dark" muda tema; popover fecha.
  - `tab` percorre os botões em ordem; `Enter`/`Space` ativa.
- [ ] Branch pushed; orchestrator integra em `main` com gate verde.

---

## Fora de escopo (NÃO fazer nesta lane)

- Criar `/settings` page — fica para quando ADR-130 (i18n) abrir conta-nível.
- Endpoint `/users/me/preferences` — idem.
- Sync cross-device — decidido manter local-only (cada device tem tela diferente; pref por-device é até desejável).
- Adicionar dependência de popover (Radix, Headless UI) — implementar com `useRef`+`useEffect` próprios.
- Animar transição do popover (open/close) — só a transição de `font-size` no scope.
- Mexer em outras prefs de leitura (line-height, largura de coluna) — slot reservado no painel para futuro, mas **sem** UI nesta lane.

---

## Quando criar ADR nova (futuros agentes)

Quando `/settings` cross-app nascer (provável com [ADR-130](../DECISIONS.md#adr-130--i18n-dois-eixos-locale--idioma) i18n),
**criar ADR nova** explicitando o split:

- **Account-level → DB** (`/users/me/preferences` ou tabela equivalente):
  locale, idioma, fuso, notificações, default workspace.
- **Reading-level → localStorage** (mantém ADR-121): fonte, tema, TOC,
  futuros line-height/largura/print.

Esta lane (`report-appearance-menu`) **refina** ADR-121, **não a
substitui**. ADR-121 continua autoritativa sobre o lado local. A nova
ADR só desambigua o lado conta-nível quando ele existir.
