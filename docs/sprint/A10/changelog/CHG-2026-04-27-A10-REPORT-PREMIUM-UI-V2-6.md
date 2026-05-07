---
id: CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-6
type: changelog-entry
date: "2026-04-27"
sprint: A10
commits: ["24998747289", "6b09407", "10bf48b", "fd1f1fd"]
summary: |
  Report Premium UI v2 — v2.7 DnD real Kanban ✅ (2026-04-27). - **Report Premium UI v2 — v2.7 DnD real Kanban ✅ (2026-04-27):** Fecha o **débito #1 do BACKLOG** (declarado pré-v2: `@dnd-kit/core` não foi adicionado à v1; p
tags:
  - type/changelog-entry
  - sprint/a10
---


# Report Premium UI v2 — v2.7 DnD real Kanban ✅ (2026-04-27)

- **Report Premium UI v2 — v2.7 DnD real Kanban ✅ (2026-04-27):**
  Fecha o **débito #1 do BACKLOG** (declarado pré-v2:
  `@dnd-kit/core` não foi adicionado à v1; primitivo Kanban usava
  botões "→ Coluna X" em vez de drag-and-drop). Lane v2.7 instala
  `@dnd-kit/core@^6.3.1` (42KB minified / 13KB gzipped — bem abaixo
  dos 50KB do gate de bundle do prompt) e refatora
  [Kanban.tsx](frontend/src/components/report/ui/kanban/Kanban.tsx)
  para usar `DndContext` + `useDraggable` (cards) + `useDroppable`
  (colunas). API `onMove(id, to)` preservada — `TaticoSections.tsx`
  não muda; o handler `onDragEnd` chama o mesmo callback quando o
  card é solto sobre uma coluna diferente.

  **Decisões:**
  - **`@dnd-kit/sortable` NÃO instalado.** O escopo desta lane cobre
    apenas drag entre colunas (cross-column moves), que é o caso de
    uso de `onMove(id, to)`. Reordenação dentro da mesma coluna
    (campo `ordem` do backend) ficaria mais natural com sortable, mas
    exige extensão da API (`onReorder?` callback novo) e mudança em
    TaticoSections para fazer PATCH de `ordem`. Conservadorismo: o
    handler em `Kanban.tsx` checa `item.coluna === target` e retorna
    sem chamar `onMove` — drag intra-coluna é no-op (Vitest +
    Playwright validam).
  - **Fallback mobile via CSS media query.** Botões "→ Coluna" agora
    ficam em `data-kanban-move-buttons`. Em viewports `≥768px`
    (`globals.css` regra adicionada), `display: none !important`
    esconde os botões — DnD mouse é a interação primária. Em
    `<767px`, os botões aparecem (long-press em touch é problemático
    com scroll natural). Trade-off documentado em comentário CSS +
    docstring do componente.
  - **`activationConstraint: { distance: 6 }`** em `useSensor(PointerSensor)`
    evita drag acidental ao clicar nos botões de fallback (3px
    movimento espontâneo do dedo não dispara drag).

  **Validação:**
  - 3 specs Vitest novos em `tests/components/report/uiPrimitives.test.tsx`:
    drop zones renderizados; cards com `data-kanban-item`; sem onMove
    não renderiza botões de fallback. Mais 1 spec atualizado (caminho
    botão clicável continua chamando `onMove`).
  - Playwright `@critical` em
    `frontend/tests/e2e/reports/kanban.@critical.spec.ts`:
    drag de "A fazer" → "Em andamento" emite PATCH com `coluna:
    em_andamento`; drag dentro da mesma coluna NÃO emite PATCH.
    Roda em CI opt-in via label `e2e` (workflow `frontend-e2e` —
    cross-browser).
  - Vitest 36 tests pass localmente (uiPrimitives 29 + taticoSections 7
    — superfície tocada por v2.7); tsc clean em `src/`; pre-commit verde.

  **Hang RDM em CI Vitest:** o run `24998747289` cancelou em 10min no
  job "Frontend unit + integration (Vitest)" por hang em
  `tests/components/report/ReceitaDespesaMensalChart.test.tsx`
  (introduzido em `6b09407`, v2.E.6, 2026-04-26 — pré-existe v2.7).
  Workaround aplicado em `10bf48b`/`fd1f1fd` (rename `.slow.test.tsx` +
  exclude do glob default) substituído pelo fix definitivo descrito no
  bullet "CI fix — Vitest hang…" acima.
