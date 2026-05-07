---
id: TRACK-onda-9-design-system-polish
type: track
title: "Track — Onda 9: design system polish + dedup tarefas + mobile"
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

# Track — Onda 9: design system polish + dedup tarefas + mobile

> **Status:** ☐ aberta · independente (pode rodar paralelo com Ondas 7/8)
>
> **Contexto:** prompt self-contained para nova sessão Claude Code.
> Branch: `agent/onda-9-design-system-polish/<ts>`, partindo de
> `origin/main`.
>
> **Esforço estimado:** ~3 dias (7 itens, baixo risco — só polish UI +
2 ajustes de produto travados).
> **Prioridade:** P2 — qualidade do design system.

---

## Briefing

Revisão de produto (2026-04-29) com `product-designer` identificou
**inconsistências de design system** que erodem confiança visual e
desorganizam a hierarquia:

- **4 patterns de H2** na mesma página `/plano`
- **5 patterns de empty state** entre componentes
- **3 patterns de "filter as tabs"** (DecisionsSection, InboxTab,
  TasksTab — todos diferentes)
- **HeaderActions com refresh apenas em /plano**, não em `/acao`
- **Tarefas em 4 lugares com cache independente**, dedup ausente
- **Mobile <767px** — `/plano` é doloroso (3000-4800px scroll,
  sem collapse)

Esta onda unifica design + ergonomia mobile + dedup tarefas.

## Itens (7 fixes — 5 design system + 2 produto travados em 2026-04-29)

### 1. Unificar 4 patterns de H2 → 1 componente `<SectionHeading/>`

**Arquivo novo:** `frontend/src/components/ui/SectionHeading.tsx`

**API:**
```tsx
interface SectionHeadingProps {
  icon?: LucideIcon;
  label: string;
  count?: number;          // exibido em mono tabular após o label
  badge?: ReactNode;       // ex.: "3 a decidir" para Decisions
  action?: ReactNode;      // botão à direita ("Nova decisão")
  level?: 2 | 3;           // tipografia (default 2)
}
```

**Padrão visual unificado:**
```
[icon 14px] LABEL UPPERCASE TRACKING-WIDE  (count) [badge]   [action]
─────────────────────── (border-b sutil)
```

**Migrações:**
- `SectionDivider` em `plano/page.tsx:147-153` → `<SectionHeading>`
- `SupportGoalsRow` h2 inline → `<SectionHeading>`
- `DecisionsSection` h2 com ícone + counter + badge → `<SectionHeading>`
- `LinkedTasksSection` h2 com ícone → `<SectionHeading>`

**Critério de aceite:**
- Visual de H2 igual em toda `/plano`
- Componente em design system, importado por consumidores
- Custo: ~40 LOC + 4 migrações

### 2. Unificar 5 patterns de empty state → `<EmptyState/>`

**Arquivo novo:** `frontend/src/components/ui/EmptyState.tsx`

**API:**
```tsx
interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  variant?: "card" | "inline" | "hero";
  ctas?: Array<{ label: string; href?: string; onClick?: () => void; variant?: "primary" | "secondary" }>;
}
```

**Migrações:**
- `IFEmptyHero` (variant: hero, ctas primário)
- `DecisionsEmptyState` (variant: inline, border-dashed)
- `InboxTab` empty (variant: card)
- `LinkedTasksSection` empty (variant: inline)
- `NotasTab` empty (variant: card, ensinante)

**Critério de aceite:**
- Visual de empty consistente; variants cobrem 3 contextos (hero,
  inline, card)
- Custo: ~50 LOC + 5 migrações

### 3. Unificar 3 patterns de filter-tabs → `<SegmentedTabs/>`

**Arquivo novo:** `frontend/src/components/ui/SegmentedTabs.tsx`

**API:**
```tsx
interface SegmentedTabsProps<T extends string> {
  value: T;
  onChange: (next: T) => void;
  options: Array<{ value: T; label: string; count?: number }>;
  ariaLabel: string;
}
```

**Padrão visual:** pill rounded-full, `bg-muted` inativo,
`bg-primary text-primary-foreground` ativo, count mono em badge
após label.

**Migrações:**
- `DecisionsSection.StatusFilters` (Todas / A decidir / Em vigor /
  Aplicadas / Substituídas / Descartadas)
- `InboxTab` filtro por status
- `TasksTab.ViewToggle` (priority/deadline/category)

**Critério de aceite:**
- 3 lugares com filtro segmentado têm exatamente o mesmo visual
- Custo: ~60 LOC + 3 migrações

### 4. Dedup tarefas entre `UpcomingTasksWidget` e `LinkedTasksSection`

**Arquivo:** `frontend/src/app/(app)/plano/page.tsx`

**Problema atual:** Mesma task pode aparecer em UpcomingTasksWidget
(próximas 7 dias) E em LinkedTasksSection (vinculadas a IF) na
mesma página `/plano`. Sem dedup.

**Mudança:**
- `usePlanoOverview` retorna conjuntos diferentes mas com IDs
  identificáveis
- `/plano/page.tsx` filtra `UpcomingTasksWidget` para excluir
  IDs já em `LinkedTasksSection` (LinkedTasks tem prioridade
  semântica — vinculadas a meta IF)
- Ou: agrupar visualmente — "Tarefas — esta semana" no topo, com
  badge "ligada à IF" nas que destravam IF

**Decisão pendente:** dedup por exclusão OU agrupamento visual?
Recomendação: **agrupamento visual com badge** (não esconde info,
só clarifica relação).

**Adicional:** `/acao` Tarefas tab aceita `?filter=upcoming|linked`
no URL para preservar contexto vindo de `/plano`. Click "Ver todas"
em UpcomingTasksWidget leva a `/acao?tab=tarefas&filter=upcoming`.

**Critério de aceite:**
- Tarefa que destrava IF e vence em 5 dias aparece **uma vez** em
  `/plano` com badge "→ IF"
- Click "Ver todas" preserva filtro
- Custo: ~30 LOC

### 5b. Badge "Inbox pending" no AppShell `/acao`

**Arquivo:** `frontend/src/components/AppShell.tsx`

**Decisão de produto (2026-04-29):** Inbox **continua como tab dentro de
`/acao`** (não vira rota top-level `/inbox`). Para preservar visibilidade
do gatilho ritual mensal, AppShell sidebar mostra badge contador no
item "Ação" quando há sugestões pendentes.

**Mudança:**
- Item nav "Ação" passa a aceitar `badge?: number` (count de sugestões
  pendentes do workspace ativo)
- Hook `useSuggestionsCount` consumido no AppShell (cuidado com
  performance — só faz fetch quando workspace presente)
- Badge usa `<Badge variant="default">` shadcn com cor por severidade
  máxima (depende de Onda 8 #5 — `useSuggestionsSummary`)

**Critério de aceite:**
- 3 sugestões pendentes (1 danger, 2 warning) → badge vermelho com "3"
  no nav "Ação"
- Sem pendentes → sem badge
- Custo: ~20 LOC

### 5c. Kill Timeline tab em `/acao`

**Decisão de produto (2026-04-29):** Timeline tab está como placeholder
ensinante há toda a Direção E sem fonte de dados real. Manter
placeholder vivo erodu confiança ("o app tem partes não funcionais").

**Mudança:**
- Remover `TimelineTab` import e tab em
  `frontend/src/app/(app)/acao/page.tsx`
- Deletar `frontend/src/app/(app)/acao/_components/TimelineTab.tsx`
- `TabId` reduz para `"inbox" | "tarefas" | "notas"` (3 tabs)
- `timelineAdapter.ts` em `report/utils/` permanece — primitivo
  Timeline pode ressurgir como **componente embutido em outro lugar**
  futuro (ex.: dashboard widget) sem precisar de tab dedicada
- Atualizar comentário em `timelineAdapter.ts:1-7` removendo referência
  à Onda 6
- `ActionStatusBar` mantém os 3 chips (sugestões · tarefas · decisões)

**Critério de aceite:**
- `/acao` mostra 3 tabs (Inbox, Tarefas, Notas)
- Tests E2E `frontend/tests/e2e/plano-de-acao.spec.ts` (se houver
  asserção sobre Timeline) atualizados
- Custo: ~30 LOC + delete

### 5. Mobile review (collapsibles em <767px)

**Arquivo:** `frontend/src/app/(app)/plano/page.tsx` + componentes filhos

**Problema atual:** `/plano` em <767px tem 3000-4800px de scroll
vertical. IFHeroCard tem `divide-x sm:divide-x-0` que vira 3 linhas.
SupportGoalsRow já é grid responsivo (OK). ChartsGrid quebra mas
charts ficam empilhados grandes.

**Mudança:**
- "Mês corrente" `<details>` (já feito em Onda 7 #1) **default
  colapsado em mobile** mesmo se for aberto em desktop
- "Plano de Ação" `<details>` colapsado em mobile (UpcomingTasksWidget
  + LinkedTasksSection)
- Estratégia (top) sempre visível em mobile
- Charts em mobile: ResponsiveContainer com `aspect="3:2"` no lugar
  de altura fixa

**Tap targets:** auditar SuggestionCard, DecisionCard, TaskCard —
mínimo 44×44px nos botões de ação inline.

**Critério de aceite:**
- `/plano` em iPhone 13 (390×844) abre em ≤2 viewport heights
  (Estratégia + headings collapsed)
- Tap targets passam Lighthouse mobile audit
- Spec Playwright `device.iPhone 13` valida estado inicial
- Custo: ~30 LOC + spec

## Coordenação com outras ondas

- **Independente** — todos os itens são UI / design system / mobile.
  Pode rodar em paralelo com Ondas 7 e 8.
- **Conflitos triviais com Onda 7:** Onda 7 #1 (reordenar /plano +
  collapsible) toca o mesmo arquivo que Onda 9 #4 (dedup tarefas) e
  #5 (mobile). Ordem ideal: Onda 7 mergeia primeiro; Onda 9 rebase
  rápida em cima. Se paralelo, conflitos de merge concentram em
  `plano/page.tsx`.

## Referências

- Revisão product-designer (2026-04-29) na sessão da revisão de
  produto.
- Design tokens: `design-tokens/tokens.json`.
- shadcn primitivos existentes: `frontend/src/components/ui/`
  (button, card, badge, tabs, dialog, etc).
- Mobile spec preliminar: [REPORT_MOBILE_SPEC.md](../REPORT_MOBILE_SPEC.md)
  (escopo é relatório, não /plano — mas heurísticas reusáveis).

## Sequência de execução

1. **Phase 1 (~0.5 dia):** item #1 `<SectionHeading/>` — primitivo
   simples, alta reutilização.
2. **Phase 2 (~0.5 dia):** item #2 `<EmptyState/>` — variants são
   simples; migração mecânica.
3. **Phase 3 (~0.5 dia):** item #3 `<SegmentedTabs/>` — primitivo +
   3 migrações.
4. **Phase 4 (~0.5 dia):** item #4 dedup tarefas — pequeno.
5. **Phase 5 (~1 dia):** item #5 mobile — auditoria + collapsibles +
   tap targets + Playwright spec.
6. **Phase 6 (~0.25 dia):** ADR-160 (curta — "design system primitivos
   v2"), CHANGELOG.

## Não fazer

- ❌ Mexer em lógica de negócio (Onda 8)
- ❌ Reordenar /plano (Onda 7 já fez)
- ❌ Fix anchor / default tab (Onda 7)
- ❌ Novas regras Suggestion (Onda 8)
- ❌ Refactor de hooks (foco em UI)

## Critério de aceite global

- [ ] 7 itens entregues em main
- [ ] 3 primitivos novos no design system (`<SectionHeading/>`,
  `<EmptyState/>`, `<SegmentedTabs/>`)
- [ ] Migrações aplicadas (4 lugares H2, 5 lugares empty, 3 lugares
  filter-tabs)
- [ ] AppShell `/acao` com badge de sugestões pendentes
- [ ] Timeline tab removida; `/acao` reduzido para 3 tabs
- [ ] Lighthouse mobile audit verde para tap targets
- [ ] Spec Playwright `device.iPhone 13` valida `/plano`
- [ ] Vitest verde com snapshots atualizados se necessário
- [ ] Pre-commit verde, code-style baseline mantido
- [ ] ADR-160 + CHANGELOG

## Branch + commits

- Partir de `origin/main` (qualquer momento)
- Branch: `agent/onda-9-design-system-polish/<yyyyMMdd-HHmm>`
- Commits sugeridos:
  1. `feat(ui): SectionHeading primitivo + 4 migrações`
  2. `feat(ui): EmptyState primitivo + 5 migrações`
  3. `feat(ui): SegmentedTabs primitivo + 3 migrações`
  4. `feat(plano): dedup tarefas Upcoming/Linked + filter param em /acao`
  5. `feat(appshell): badge sugestões pendentes no nav /acao`
  6. `feat(acao): kill Timeline tab (sem fonte de dados)`
  7. `feat(plano): mobile collapsibles + tap targets`
  8. `docs(adr): ADR-160 design system v2 + CHANGELOG`
