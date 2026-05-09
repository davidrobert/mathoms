import type { Page, Route } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { ReportResponse } from "@/lib/api";

/**
 * Mock helper para rota /reports/[id] sem backend real.
 *
 * Lane `report-a11y-finalize` (resíduo F12, ADR-129): a11y/tab-order
 * gates não devem depender do pipeline E2E completo. `page.route()`
 * intercepta `/api/v1/**` antes de bater no backend; combinado com
 * token injetado em localStorage, o shell renderiza com fixture
 * sintética.
 *
 * Fixtures cobrem variância de dado real para evitar regressões pontuais
 * (overflow, anchoring, long strings) que escapam ao baseline `medium`:
 *
 * - `medium`         — densidade média, zero PII (fixture canônica)
 * - `long-strings`   — nomes/descrições longas (Top 15 ativos, dívidas)
 * - `large-values`   — totais grandes (R$ XX.XXX.XXX) → overflow em cards
 * - `sparse-data`    — datasets curtos / cauda longa (period anchoring)
 */
export type FixtureName = "medium" | "long-strings" | "large-values" | "sparse-data";

const FIXTURES_DIR = join(__dirname, "..", "fixtures", "reports");

export const MOCK_WORKSPACE_ID = "ws-fixture";
export const MOCK_REPORT_ID = "report-fixture-medium";

interface MockOptions {
  reportId?: string;
  workspaceId?: string;
  fixture?: FixtureName;
}

function loadFixture(name: FixtureName): unknown {
  const raw = readFileSync(join(FIXTURES_DIR, `${name}.json`), "utf-8");
  return JSON.parse(raw);
}

function buildReportResponse(
  reportId: string,
  workspaceId: string,
): ReportResponse {
  return {
    id: reportId,
    workspace_id: workspaceId,
    title: "Relatório Sintético — Abril 2026",
    period: "2026-04",
    score: 82,
    patrimonio_liquido: 1200000,
    created_at: "2026-04-25T12:00:00Z",
    pipeline_run_id: "run-fixture",
    source_document_count: 3,
    source_document_ids: ["doc-1", "doc-2", "doc-3"],
    consumed_document_count: 3,
    consumed_document_ids: ["doc-1", "doc-2", "doc-3"],
    has_analysis_data: true,
    premissas_snapshot: null,
  };
}

function buildWorkspace(workspaceId: string) {
  return {
    id: workspaceId,
    name: "Workspace Fixture",
    family_surname: "Sintético",
    role: "owner" as const,
    joined_at: "2026-01-01T00:00:00Z",
  };
}

function buildUser() {
  return {
    id: "user-fixture",
    email: "fixture@test.com",
    full_name: "Fixture User",
    is_active: true,
    is_superuser: false,
    created_at: "2026-01-01T00:00:00Z",
  };
}

/**
 * Configura `page.route()` para responder a todas as chamadas necessárias
 * para renderizar /reports/[id] com fixture sintética. Roteador é tolerante
 * — endpoints não previstos retornam 200 com `[]` ou `{}` para não quebrar
 * o shell.
 */
export async function mockReportPage(
  page: Page,
  opts: MockOptions = {},
): Promise<{ workspaceId: string; reportId: string }> {
  const workspaceId = opts.workspaceId ?? MOCK_WORKSPACE_ID;
  const reportId = opts.reportId ?? MOCK_REPORT_ID;
  const data = loadFixture(opts.fixture ?? "medium");

  // Token para passar pelo auth gate da página
  await page.addInitScript(() => {
    localStorage.setItem("fin_token", "fixture-token");
  });

  const json = (route: Route, body: unknown, status = 200) =>
    route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });

  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api\/v1/, "");

    if (path === "/auth/me") return json(route, buildUser());
    if (path === "/me/workspaces") {
      return json(route, { workspaces: [buildWorkspace(workspaceId)], total: 1 });
    }
    if (path === `/workspaces/${workspaceId}/reports/${reportId}`) {
      return json(route, buildReportResponse(reportId, workspaceId));
    }
    if (path === `/workspaces/${workspaceId}/reports/${reportId}/data`) {
      return json(route, data);
    }
    if (path === `/workspaces/${workspaceId}/reports/${reportId}/notes`) {
      return json(route, {
        id: "notes-1",
        report_id: reportId,
        content: "",
        author_user_id: null,
        updated_at: "2026-04-25T00:00:00Z",
      });
    }
    if (path === `/workspaces/${workspaceId}/reports/${reportId}/kanban`) {
      return json(route, { items: [] });
    }
    if (path.includes("/notifications")) {
      return json(route, { notifications: [], total: 0, unread_count: 0 });
    }
    if (path.includes("/transactions")) {
      return json(route, {
        transactions: [],
        total: 0,
        page: 1,
        page_size: 500,
        summary: {
          total_in: 0,
          total_out: 0,
          net: 0,
          by_category: {},
          by_member: {},
        },
      });
    }
    // ADR-153 — `useSuggestions` (consumido por `<SuggestionCalloutInline/>`
    // dentro do AppLayout) faz `setSuggestions(resp.suggestions)` sem
    // guard. Sem esta rota, o catch-all `{}` produz `suggestions = undefined`
    // e o `.filter()` na seção dispara ErrorBoundary, derrubando o
    // `<article data-report-ready>` em **todas** as fixture variants
    // (regressão entrou junto com o spec smoke fixture-variants em #157).
    if (path.match(/\/workspaces\/[^/]+\/suggestions$/)) {
      return json(route, { suggestions: [], total: 0 });
    }

    // ADR-136 — `useDecisions` em `PlanoDeAcaoSection` faz
    // `setDecisions(resp.decisions)` sem guard. Mesmo padrão de
    // failure mode: catch-all `{}` produz `decisions = undefined` e
    // `.length`/`.filter()` em `DecisionTable` dispara ErrorBoundary.
    if (path.match(/\/workspaces\/[^/]+\/decisions$/)) {
      return json(route, { decisions: [], total: 0 });
    }

    // ADR-148 — `useConsumoPontuais` consome este endpoint em S2 (card
    // ConsumoConscienteCard). Sem esta rota, o catch-all `{}` quebrava
    // o shape e disparava ErrorBoundary, derrubando o `<article>` inteiro
    // — bug que fazia 28 baselines visuais skipar com `count===0` para
    // `section#S1[data-report-section]` (regressão pós-commit ba29df1).
    if (path.includes("/reports/consumo-pontuais")) {
      return json(route, {
        period: "3m",
        date_from: "2026-01-01",
        date_to: "2026-04-25",
        items: [],
        total: 0,
        total_valor: 0,
      });
    }
    if (path.includes("/dashboard")) {
      return json(route, {});
    }
    // ADR-153/161 — `useSuggestions` (SuggestionCalloutInline em S2/S7/...)
    // e `getSuggestionsSummary`/`countSuggestions` (banners em /plano).
    // Catch-all `{}` quebrava `resp.suggestions.filter()` em
    // SuggestionCalloutInline → ErrorBoundary global → snapshot tests
    // skipam silenciosamente, smoke spec falha em `data-report-ready`.
    if (path.endsWith("/suggestions") || path.includes("/suggestions?")) {
      return json(route, { suggestions: [], total: 0 });
    }
    if (path.endsWith("/suggestions/count")) {
      return json(route, { count: 0 });
    }
    if (path.endsWith("/suggestions/summary")) {
      return json(route, { count: 0, max_severity: null, by_category: {} });
    }
    // ADR-136 — `useDecisions` em PlanoDeAcaoSection. Mesmo motivo dos
    // `/suggestions`: catch-all sem `decisions` quebrava `.filter()`.
    if (path.endsWith("/decisions") || path.includes("/decisions?")) {
      return json(route, { decisions: [], total: 0 });
    }

    return json(route, {});
  });

  return { workspaceId, reportId };
}

/** Espera o shell estar pronto (data-report-ready="true" no <article>). */
export async function waitForReportReady(page: Page): Promise<void> {
  await page.waitForSelector('[data-report-ready="true"]', { timeout: 15_000 });
}
