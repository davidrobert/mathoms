---
id: ADR-076
type: adr
title: "Design Tokens Unificados Site ↔ Relatório"
status: Decidido
phase: "F9"
date: "2026-04-15"
relates_to: []
supersedes: ["[[ADR-050]]", "[[ADR-051]]"]
superseded_by: ["[[ADR-124]]"]
aliases: ["ADR 076"]
tags:
  - area/frontend
  - area/pipeline
  - area/report
  - status/decidido
  - type/adr
size_lines: 75
---

# ADR-076 — Design Tokens Unificados Site ↔ Relatório

**Status:** Decidido (F9) • **Data:** 2026-04-15

**Contexto:**
Auditoria visual comparando `frontend/src/app/globals.css` e `config/templates/report_template.html` revelou duas linguagens de design completamente divergentes, sem ponte:

| Eixo | Site | Relatório |
|---|---|---|
| Cor primária | `oklch(0.205 0 0)` (navy neutro) | `#1A3A5C` (navy quente, hex fixo) |
| Accent | `oklch(0.97 0 0)` (quase sem saturação) | `#15803D` (verde floresta) |
| Fonte | Geist | Inter + Plus Jakarta Sans |
| Cards | Minimais, borda neutra | Left-border 4px colorida, gradientes |
| Dark mode | CSS vars + `next-themes` | `data-theme="dark"` com hex hardcoded |

Ao abrir `/reports/{id}`, o usuário experimenta uma quebra visual perceptível — duas identidades de produto disputando o mesmo espaço. O relatório tem o DNA fintech mais maduro (navy institucional, verde/vermelho semânticos, tipografia editorial); o site está na paleta shadcn default.

**Alternativas consideradas:**
- **A** — Nivelar o site pelo relatório manualmente (copiar cores/fontes no `globals.css`). Resolve agora, diverge de novo no próximo ciclo.
- **B** — TypeScript como fonte de verdade (tokens em `.ts`, exportar CSS). Bom para frontend, mas E6 (Python) vira consumidor de TS — inversão estranha.
- **C** — ✅ **Escolhida**: fonte única declarativa (`design-tokens/tokens.json`) + build step que gera CSS para Next.js e CSS para o template standalone do E6. Padrão OpenAPI/Stripe.

**Decisão:**

1. **Fonte de verdade:** `design-tokens/tokens.json` na raiz do monorepo. Estrutura semântica por categoria (color, typography, spacing, radius, shadow) com variantes light/dark. Referência visual: DNA do relatório (navy + verde/vermelho semânticos + Plus Jakarta + Inter).

2. **Build step:** `design-tokens/build.py` — emite dois arquivos:
   - `frontend/src/styles/tokens.css` — custom properties CSS consumidas por `globals.css` via `@import`. Tailwind v4 lê via `@theme inline`.
   - `config/templates/_tokens.css` — custom properties injetadas no `<style>` do relatório standalone (E6).
   Ambos são **gerados e gitignored no frontend** (regenerados no build), mas **commitados no template E6** (standalone precisa funcionar offline sem build step).

3. **Valores semânticos canônicos** (derivados do DNA do relatório):
   - `--brand-primary: #1A3A5C` (navy institucional)
   - `--brand-accent: #15803D` (verde patrimônio/gain)
   - `--brand-danger: #B91C1C` (vermelho passivo/loss)
   - `--brand-warning: #F4A261` (atenção)
   - `--font-display: 'Plus Jakarta Sans'`
   - `--font-body: 'Inter'`
   - `--font-mono: 'JetBrains Mono'` (exclusivo para valores monetários com tabular-nums)
   - `--radius-card: 12px`

4. **Dark mode:** ambos ambientes consomem os mesmos tokens; a classe `.dark` (ou `[data-theme="dark"]`) reescreve as mesmas custom properties. Elimina o divergence atual onde site usa OKLch swap e relatório usa hex hardcoded.

5. **Migração das variantes de card do relatório** (highlight, feature, success, warn, critical, primary, neutral, top-danger, top-accent) viram tokens compostos em `tokens.json` sob `card.variants.*`, consumidos identicamente pelos componentes React novos (Fase 2) e pelo E6 standalone.

6. **Regras de uso obrigatórias** (enforçadas via ESLint + pre-commit):
   - Nenhum `#` hex literal em CSS/TSX de `frontend/src/` (exceto tokens gerados).
   - Nenhum `font-family:` fora de `tokens.css`.
   - Valores monetários SEMPRE com `font-family: var(--font-mono); font-variant-numeric: tabular-nums;` — centralizado no componente `<MonetaryValue/>`.

7. **Backwards-compat:** ADR-050 (Tailwind v4 `@theme inline`) e ADR-051 (Geist fonts) são **parcialmente supersedidos** — Tailwind v4 theme continua, mas agora hidratado por `tokens.css` ao invés de hardcoded; Geist é substituído por Plus Jakarta + Inter.

**Consequências:**
- ✅ Uma identidade visual, um lugar para mudar. Mathoms AI vira produto coeso.
- ✅ Fim da dissonância site × relatório — critério de aceite F9.
- ✅ Rebase rápido para tema white-label futuro (multi-família com branding próprio — F10+): sobrescrever `tokens.json` por workspace.
- ✅ Testes de token via snapshot (`tests/design_tokens/test_build.py`) garantem paridade.
- ✅ Princípio de "config/ é fonte de verdade" preservado: tokens vivem na raiz do monorepo, acima de site e pipeline.
- ⚠️ Adiciona build step obrigatório antes de rodar `pnpm dev` — mitigado por hook `pnpm predev` e CI check.
- ⚠️ Fontes Plus Jakarta + Inter adicionam ~150KB de fontes sobre Geist (~80KB). Aceito — trade visual > bytes.
- ❌ `globals.css` atual precisa ser reescrito (~200 linhas). Aceito — custo pontual, ganho permanente.
- ❌ Qualquer branch em andamento com CSS hardcoded conflita na merge. Aceito — migração concentrada em F9.

**Supersedes parcial:**
- [ADR-050 "Tailwind v4 theme inline"](#adr-050--tailwind-v4-theme-inline) — tema continua inline, agora hidratado por tokens gerados.
- [ADR-051 "Geist fonts"](#adr-051--geist-fonts) — Geist substituída por Plus Jakarta Sans (display) + Inter (body).

**Implementação (F9):**
- F0.2: `design-tokens/tokens.json` + `build.py` + geração de ambos os CSS
- F0.2.5: estender build step para também gerar tipos do layout (YAML→TS/Pydantic)
- F1.2: `globals.css` consome `tokens.css`; fontes carregadas via Next.js `next/font/google`
- F4.1: E6 standalone template importa `_tokens.css` gerado
- F5.x: ESLint rule `no-hex-literal` + `no-direct-font-family` ativadas
