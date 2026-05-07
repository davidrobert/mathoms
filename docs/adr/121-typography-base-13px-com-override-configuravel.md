---
id: ADR-121
type: adr
title: "Typography base 13px com override configurável"
status: Decidido
phase: "Fase 0"
date: "2026-04-23"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 121"]
tags:
  - area/frontend
  - area/persistence
  - area/report
  - status/decidido
  - type/adr
size_lines: 63
---

# ADR-121 — Typography base 13px com override configurável

**Status:** Decidido (Fase 0) • **Data:** 2026-04-23

**Contexto:** Exemplo usa `font-base: 13px` (denso, próprio para relatório
financeiro com muita tabela). Tokens atuais partem de 16px (`rem` default
do browser). Divergência força trade-off: mudar tudo para 13px quebra
densidade visual do resto do app; manter 16px deixa o relatório com ar
menos "editorial". Usuário pede base 13px **mas configurável**.

**Decisão:** CSS var `--font-base-px` default `13px` **apenas dentro de
`/reports/**`** (escopado no `<html data-report-scope>` ou wrapper do
shell). Resto do app continua em 16px (sem mudança). Escala de fontes
(`--font-xs` a `--font-3xl`) recalculada em torno de 13px conforme o
exemplo (10/12/13/14/16/22/28/38px). User preference: toggle
"Compacto (13px) / Normal (15px) / Confortável (17px)" na top-nav do
relatório, persistido em localStorage `mathoms:report:font-scale`.

**Consequências:**
- ✅ Densidade editorial do exemplo preservada por default.
- ✅ Usuário com dificuldade de leitura ajusta sem sair da tela.
- ⚠️ Escopo da var requer rigor — qualquer `rem` dentro de `/reports/**`
  resolve contra 13px, não 16px. Tests visuais devem cobrir.
- ❌ Componentes compartilhados (`@/components/ui/*`) usados dentro do
  relatório podem ficar levemente menores — revisar caso a caso.

**Refinamento UX (2026-04-26):**

Após uso real, ficou claro que (a) o segmented control "Compacto / Normal /
Confortável" não comunicava "tamanho da fonte" para usuários não-técnicos
(David: "aparentemente esses botões não fazem nada"); (b) default
"Compacto" 13px era mesquinho para tabelas monetárias com `tabular-nums`
(padrão fintech moderno opera 14-16px); (c) passos 13/15/17 eram
imperceptíveis (apenas 2px); (d) ter 2 controles separados
(`FontScaleToggle` + `ReportThemeToggle`) inflava a top-nav e não
escalava para futuras prefs de leitura.

Mudanças (sem alterar arquitetura — continua local + localStorage):

- Default `useReportFontScale` passa de `"compact"` para `"normal"`.
- Tokens `--report-font-base-px` por scale: `compact: 14px` (era 13),
  `normal: 16px` (era 15), `comfortable: 18px` (era 17). Família
  proporcional recalculada. Passo de 4px entre extremos torna a diferença
  perceptível.
- `FontScaleToggle.tsx` e `ReportThemeToggle.tsx` removidos. Novo
  componente `AppearanceMenu.tsx` unifica fonte + tema em popover único
  disparado por botão `Aa` na top-nav (padrão Medium/NYT/Apple Books).
- `transition: font-size 180ms ease-out` em `[data-report-scope]` para
  feedback visual perceptível ao trocar.

**Por que não mover para `/settings`:** reading-time prefs (fonte, tema,
line-height) seguem padrão da indústria — ficam inline na superfície de
leitura, não em Settings. Settings é "set once and forget"; reading prefs
são ajustadas durante a leitura, com feedback imediato. Idêntico ao
padrão já consagrado de `useReportTocOpen`. Quando `/settings` cross-app
nascer (provável com ADR-130 i18n), uma ADR nova deverá explicitar o
split: account-level (locale, notificações, default workspace) → DB ·
reading-level (fonte, tema, TOC) → localStorage. Esta ADR-121 refinada
permanece autoritativa sobre o que **fica local**.

Relaciona-se a: ADR-076 (design tokens), ADR-117.
