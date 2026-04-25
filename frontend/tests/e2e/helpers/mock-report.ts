import type { Page, Route } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Mock helper para rota /reports/[id] sem backend real.
 *
 * Lane `report-a11y-finalize` (resíduo F12, ADR-129): a11y/tab-order
 * gates não devem depender do pipeline E2E completo. `page.route()`
 * intercepta `/api/v1/**` antes de bater no backend; combinado com
 * token injetado em localStorage, o shell renderiza com fixture
 * sintética.
 *
 * Fixture única (`medium.json`): densidade média, zero PII. `small`/
 * `large` ficam para uma futura iteração de snapshots por densidade.
 */

const FIXTURES_DIR = join(__dirname, "..", "fixtures", "reports");

export const MOCK_WORKSPACE_ID = "ws-fixture";
export const MOCK_REPORT_ID = "report-fixture-medium";

interface MockOptions {
  reportId?: string;
  workspaceId?: string;
  fixture?: "medium";
}

function loadFixture(name: "medium"): unknown {
  const raw = readFileSync(join(FIXTURES_DIR, `${name}.json`), "utf-8");
  return JSON.parse(raw);
}

function buildReportResponse(reportId: string, workspaceId: string) {
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
    if (path.includes("/dashboard")) {
      return json(route, {});
    }

    return json(route, {});
  });

  return { workspaceId, reportId };
}

/** Espera o shell estar pronto (data-report-ready="true" no <article>). */
export async function waitForReportReady(page: Page): Promise<void> {
  await page.waitForSelector('[data-report-ready="true"]', { timeout: 15_000 });
}
