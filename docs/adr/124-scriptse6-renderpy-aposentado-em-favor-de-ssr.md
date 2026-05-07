---
id: ADR-124
type: adr
title: "`scripts/e6_render.py` aposentado em favor de SSR standalone do Next"
status: Decidido
phase: "Fase 0"
date: "1970-01-01"
relates_to: []
supersedes: ["[[ADR-076]]"]
superseded_by: ["[[ADR-129]]"]
aliases: ["ADR 124"]
tags:
  - type/adr
  - status/decidido
size_lines: 106
---

# ADR-124 — `scripts/e6_render.py` aposentado em favor de SSR standalone do Next

**Status:** ~~Decidido (Fase 0)~~ **Superseded by [ADR-129](#adr-129--descontinuação-completa-do-renderer-html-server-side)** (2026-04-24). A premissa (manter o endpoint HTML ativo, apenas trocar o renderer por Next SSR) caiu quando o usuário confirmou que o produto ainda está em **desenvolvimento**, o uso é **100 % web** e **não há caso de uso** para "download HTML" — os 3 consumidores hipotéticos (email para contador, backup offline, impressão sem app) deixaram de existir. Não há rota Next SSR a construir; o endpoint inteiro morre junto com o renderer. • **Data original:** 2026-04-23 • **Revisado:** 2026-04-24 (descoberta de reconnaissance em §Implementação abaixo, ainda sob ADR-124 original) • **Supersedes** parte operacional de ADR-076 (seção "e6_render.py é exportador standalone").

**Contexto:** O plano Fase 11 previa reescrever `e6_render.py` em Jinja2
para paridade visual com o shell React. Custo alto (4 867 linhas
procedurais + 19 V-checks + templates novos) e dívida de duplicação
(dois renderers para os mesmos dados). Usuário decidiu aposentar o
renderer standalone.

**Decisão:** `scripts/e6_render.py` **não sobrevive** à Fase 11. Em seu
lugar, uma rota Next SSR `/reports/[id]/export` renderiza o mesmo shell
React com CSS inline (via `next-export-optimize` ou rota `generateStaticParams`
sob demanda) e retorna HTML auto-contido com Chart.js do CDN e tokens
inline — mesma função do `EXEMPLO_DE_RELATORIO.html`. O endpoint
`GET /v1/reports/{id}/html` (que hoje chama `e6_render.py`) passa a
proxyar para a rota Next.

**Implementação (descoberta de reconnaissance 2026-04-24):**

A rota `/export` **não pode ser uma Next Page** com hidratação normal,
porque o HTML auto-contido (email/backup) não tem acesso ao bundle
client do Next. Precisa ser **Next Route Handler** (`app/api/reports/[id]/export/route.ts`)
que usa `renderToStaticMarkup` de `react-dom/server` — produz HTML
estático sem scripts de hidratação.

Charts continuam client-only: mesma estratégia do `EXEMPLO_DE_RELATORIO.html`
— `<canvas>` emitido server-side + config serializada em
`<script type="application/json">` + bootstrap vanilla Chart.js do CDN
(`chart.umd.min.js@4.4.0` + `chartjs-plugin-datalabels@2.2.0`) inicializa
no navegador destinatário.

**Sub-refactor obrigatório (Onda 11.1):** componentes no tree do shell
que hoje dependem de hooks de router (`useSearchParams`, `useRouter`,
`usePathname`, `useParams`) precisam de providers alternativos "estáticos"
para a render path do `/export`:
- `StaticReportModeProvider` — aceita `mode` como prop, sem URL sync.
- `useReportMode` funciona igual em ambas as paths.
- `ReportHeader`, `ReportTopNav`, `FloatingNav`, `ExportToolbar` — tornar
  interações toggleable (botões inertes na versão estática ou `data-*`
  pilotado por vanilla JS bootstrap mínimo).

**Auth entre backend e Next:**
- `NEXT_INTERNAL_URL` (backend env; default dev `http://localhost:3000`).
- `BACKEND_INTERNAL_URL` (Next env; default dev `http://localhost:8000`).
- JWT **pass-through** via header `X-Forwarded-Auth` — backend extrai
  JWT do `Authorization` do usuário original e reenvia pra Next. Next
  usa o mesmo JWT para buscar `/v1/workspaces/{id}/reports/{id}/data` e
  `/v1/workspaces/{id}/reports/{id}` no backend. Sem shared secret novo.

**Endpoint `/v1/workspaces/{wsid}/reports/{rid}/html`:**
- **Deixa de ler disco.** Hoje lê `report.html_path` (pré-renderizado pelo
  pipeline). Passa a fazer `httpx.AsyncClient().get()` contra
  `{NEXT_INTERNAL_URL}/api/reports/{rid}/export?workspaceId={wsid}` com
  header `X-Forwarded-Auth`. Pipe do response body + `Content-Type: text/html`.
- Campo `report.html_path` fica nullable (migration Alembic) — deprecado
  mas mantido por backcompat de jobs antigos.

**Pipeline stage `pipeline/stages/e6.py`:**
- **Removido.** Não pré-gera HTML. Registry atualizado; stage desaparece
  do `FULL_ORDER`/`DETERMINISTIC_ORDER`.
- `STAGE_RENAME_MAP` mantém entrada histórica para ler artefatos legados.
- Callsites (`scripts/e6_regen.py`, `scripts/e7_review.py`, `scripts/e_reset.py`)
  ajustados ou removidos.

**Migração dos 19 V-checks:**
- `scripts/e6/validate.py` deletado. Checks viram especs Playwright em
  `frontend/tests/e2e/reports/export.@critical.spec.ts` contra a rota
  `/api/reports/{id}/export` (fixture P/M/G). Alguns V-checks (V1, V2,
  V3, V4) tornam-se desnecessários (React garante por construção); os
  semânticos (V8–V19) viram assertions Playwright sobre DOM + JSON embebido.

**Consequências:**
- ✅ Um renderer só — fim da duplicação. Cada mudança visual viaja sozinha.
- ✅ Exporta HTML standalone com mesmo nível de polish que a rota web
  (mesmo shell, mesmos primitivos).
- ✅ JWT pass-through reusa auth existente; sem shared secret novo.
- ⚠️ Backend precisa alcançar Next SSR em deploy (URL interna +
  authentication header). Runbook atualizado.
- ⚠️ Sub-refactor do shell (StaticReportModeProvider + botões inertes na
  versão estática) aumenta escopo da Fase 11 — 4-5 ondas de commits.
- ⚠️ Pipeline perde artefato "HTML pré-gerado" em disco — todo acesso
  HTML é lazy via Next. Se Next SSR falhar, endpoint retorna 503.
- ❌ `scripts/e6/validate.py` (19 V-checks) migra para Playwright (V1–V4
  podem ser deletados; V5–V19 ganham equivalente Playwright).
- ❌ Email/backup flows que hoje chamam `e6_render.py` via CLI (fora da
  app) quebram — refatorar para chamar endpoint HTTP.

**Ondas de execução (Fase 11):**
- **11.1** — `StaticReportModeProvider` + audit de hooks router-dependentes.
- **11.2** — Route Handler `/api/reports/[id]/export`; `renderToStaticMarkup`;
  template HTML com CSS tokens inline + Chart.js CDN + bootstrap vanilla.
- **11.3** — Endpoint backend proxya Next (`httpx`); remove `pipeline/stages/e6.py`;
  deleta `scripts/e6_render.py` + `scripts/e6/` (menos validate migrado);
  `html_path` → nullable; callsites ajustados.
- **11.4** — 19 V-checks → Playwright; remove `tests/test_e6_*`.
- **11.5** — Docs (PLAN §10 marca aposentado; CHANGELOG; BACKLOG; RUNBOOK;
  ARCHITECTURE §10; CLAUDE.md §design system referência).

🛑 **PAUSA humana obrigatória** entre Onda 11.4 e 11.5 (§10.4 do PLAN):
gerar 3 fixtures em `_scratch/phase11-previews/` e aprovar visualmente
antes do merge.

Relaciona-se a: ADR-076 (design system), ADR-117, Fase 11 do plano.
