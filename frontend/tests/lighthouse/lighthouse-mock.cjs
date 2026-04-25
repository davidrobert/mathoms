/**
 * Puppeteer setup script para Lighthouse CI — Lane `report-a11y-finalize` item 4.
 *
 * Análogo ao `tests/e2e/helpers/mock-report.ts` (Playwright), mas em
 * Puppeteer, que é o runtime do `@lhci/cli`. Intercepta `/api/v1/**`
 * antes da navegação para que `/reports/[id]` renderize com fixture
 * sintética, sem backend real.
 *
 * Decisão D2 do track: roda contra fixture `medium` em formato desktop,
 * 3 runs (default lhci) para reduzir variância.
 */

const fs = require("node:fs");
const path = require("node:path");

const FIXTURE_PATH = path.join(__dirname, "..", "e2e", "fixtures", "reports", "medium.json");
const FIXTURE_DATA = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf-8"));

const WORKSPACE_ID = "ws-fixture";
const REPORT_ID = "report-fixture-medium";

const REPORT_RESPONSE = {
  id: REPORT_ID,
  workspace_id: WORKSPACE_ID,
  title: "Relatório Sintético — Abril 2026",
  period: "2026-04",
  size_bytes: 524288,
  score: 82,
  patrimonio_liquido: 1200000,
  created_at: "2026-04-25T12:00:00Z",
  pipeline_run_id: "run-fixture",
  source_document_count: 3,
  source_document_ids: ["doc-1", "doc-2", "doc-3"],
  has_analysis_data: true,
  premissas_snapshot: null,
};

const WORKSPACE_RESPONSE = {
  id: WORKSPACE_ID,
  name: "Workspace Fixture",
  family_surname: "Sintético",
  role: "owner",
  joined_at: "2026-01-01T00:00:00Z",
};

const USER_RESPONSE = {
  id: "user-fixture",
  email: "fixture@test.com",
  full_name: "Fixture User",
  is_active: true,
  is_superuser: false,
  created_at: "2026-01-01T00:00:00Z",
};

const TX_EMPTY = {
  transactions: [],
  total: 0,
  page: 1,
  page_size: 500,
  summary: { total_in: 0, total_out: 0, net: 0, by_category: {}, by_member: {} },
};

const NOTES_EMPTY = {
  id: "notes-1",
  report_id: REPORT_ID,
  content: "",
  author_user_id: null,
  updated_at: "2026-04-25T00:00:00Z",
};

function jsonResponse(body) {
  return {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  };
}

function resolveMock(rawUrl) {
  let pathname;
  try {
    pathname = new URL(rawUrl).pathname;
  } catch {
    return null;
  }
  const path = pathname.replace(/^\/api\/v1/, "");
  if (!pathname.startsWith("/api/v1/")) return null;

  if (path === "/auth/me") return USER_RESPONSE;
  if (path === "/me/workspaces") {
    return { workspaces: [WORKSPACE_RESPONSE], total: 1 };
  }
  if (path === `/workspaces/${WORKSPACE_ID}/reports/${REPORT_ID}`) {
    return REPORT_RESPONSE;
  }
  if (path === `/workspaces/${WORKSPACE_ID}/reports/${REPORT_ID}/data`) {
    return FIXTURE_DATA;
  }
  if (path === `/workspaces/${WORKSPACE_ID}/reports/${REPORT_ID}/notes`) {
    return NOTES_EMPTY;
  }
  if (path === `/workspaces/${WORKSPACE_ID}/reports/${REPORT_ID}/kanban`) {
    return { items: [] };
  }
  if (path.includes("/transactions")) return TX_EMPTY;
  if (path.includes("/notifications")) {
    return { notifications: [], total: 0, unread_count: 0 };
  }
  if (path.includes("/dashboard")) return {};

  return {};
}

/**
 * Assinatura `puppeteerScript(browser, context)` exigida pelo `@lhci/cli`
 * quando `puppeteerScript` está em `lighthouserc.cjs`. Recebe o browser
 * Puppeteer já aberto e injeta token + interceptor antes de qualquer
 * navegação em `context.url`.
 */
module.exports = async (browser, context) => {
  const page = await browser.newPage();

  await page.evaluateOnNewDocument(() => {
    try {
      window.localStorage.setItem("fin_token", "fixture-token");
    } catch {}
  });

  await page.setRequestInterception(true);
  page.on("request", (req) => {
    const url = req.url();
    if (url.includes("/api/v1/")) {
      const body = resolveMock(url);
      if (body !== null) {
        req.respond(jsonResponse(body));
        return;
      }
    }
    req.continue();
  });

  // Pre-aquece a rota antes do Lighthouse navegar — evita cold start
  // contaminar a primeira run e estabiliza next-themes mount.
  await page.goto(context.url, { waitUntil: "networkidle2", timeout: 30000 });
  await page
    .waitForSelector('[data-report-ready="true"]', { timeout: 15000 })
    .catch(() => {});

  await page.close();
};
