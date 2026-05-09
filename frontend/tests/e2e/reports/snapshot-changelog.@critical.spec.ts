/**
 * v2.8 (ADR-148) — E2E @critical: 2º relatório carrega /reports/[id]
 * e mostra "Patrimônio Líquido cresceu X% desde o relatório anterior"
 * na seção S1 alimentado pelo SnapshotChangelogBuilder.
 *
 * Cenário: workspace com prev/curr snapshots. Mock backend injeta
 * `comparisons` + `changelog` no payload de /reports/[id]/data; UI
 * deve renderizar SectionSnapshotDiff em S1 com a tabela antes→depois
 * + a entry determinística do changelog.
 */
import { expect, test, type Route } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import {
  MOCK_REPORT_ID,
  MOCK_WORKSPACE_ID,
  waitForReportReady,
} from "../helpers/mock-report";

const FIXTURES_DIR = join(__dirname, "..", "fixtures", "reports");

test.describe("Report Premium · v2.8 comparisons + changelog @critical", () => {
  // Unfrozen 2026-04-27: root cause em useConsumoPontuais.toState() +
  // mock-report rota /reports/consumo-pontuais fixado em b47dd47 (Lane 4+2).
  // ErrorBoundary parou de comer S1-S10 do DOM; spec @critical volta ao verde.
  test("seção S1 mostra delta vs relatório anterior", async ({ page }) => {
    const baseFixture = JSON.parse(
      readFileSync(join(FIXTURES_DIR, "medium.json"), "utf-8"),
    ) as Record<string, unknown>;

    const fixtureWithDiff = {
      ...baseFixture,
      comparisons: [
        {
          section_id: "S1",
          section_label: "Patrimônio Líquido",
          before: 1_000_000,
          after: 1_200_000,
          delta_pct: 20.0,
          delta_signal: "up",
        },
        {
          section_id: "S2",
          section_label: "Receita Total",
          before: 240_000,
          after: 240_000,
          delta_pct: 0.0,
          delta_signal: "stable",
        },
      ],
      changelog: [
        {
          section_id: "S1",
          summary:
            "Patrimônio líquido cresceu R$ 200.000,00 desde o relatório anterior (+20,0%)",
          delta_signal: "up",
          delta_pct: 20.0,
        },
      ],
    };

    await page.addInitScript(() => {
      localStorage.setItem("fin_token", "fixture-token");
    });

    const json = (route: Route, body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });

    const workspaceId = MOCK_WORKSPACE_ID;
    const reportId = MOCK_REPORT_ID;

    await page.route("**/api/v1/**", async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^\/api\/v1/, "");

      if (path === "/auth/me") {
        return json(route, {
          id: "user-fixture",
          email: "fixture@test.com",
          full_name: "Fixture User",
          is_active: true,
          is_superuser: false,
          created_at: "2026-01-01T00:00:00Z",
        });
      }
      if (path === "/me/workspaces") {
        return json(route, {
          workspaces: [
            {
              id: workspaceId,
              name: "Workspace Fixture",
              family_surname: "Sintético",
              role: "owner",
              joined_at: "2026-01-01T00:00:00Z",
            },
          ],
          total: 1,
        });
      }
      if (path === `/workspaces/${workspaceId}/reports/${reportId}`) {
        return json(route, {
          id: reportId,
          workspace_id: workspaceId,
          title: "Relatório com Diff",
          period: "2026-04",
          score: 82,
          patrimonio_liquido: 1_200_000,
          created_at: "2026-04-25T12:00:00Z",
          pipeline_run_id: "run-fixture",
          source_document_count: 3,
          source_document_ids: ["doc-1", "doc-2", "doc-3"],
          consumed_document_count: 3,
          consumed_document_ids: ["doc-1", "doc-2", "doc-3"],
          has_analysis_data: true,
          premissas_snapshot: null,
        });
      }
      if (path === `/workspaces/${workspaceId}/reports/${reportId}/data`) {
        return json(route, fixtureWithDiff);
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

    await page.goto(`/reports/${reportId}`);
    await waitForReportReady(page);

    // SectionSnapshotDiff em S1 deve renderizar com testid.
    const diff = page.getByTestId("section-snapshot-diff-S1");
    await expect(diff).toBeVisible();

    // Tabela do ComparisonItemsBlock — linha S1 com sinal "up".
    const block = page.getByTestId("comparison-items-block").first();
    await expect(block).toBeVisible();
    await expect(block.locator("tr[data-section-id='S1']")).toHaveAttribute(
      "data-delta-signal",
      "up",
    );

    // SnapshotChangelogList em S1 mostra a summary determinística.
    await expect(
      diff.getByText(
        /Patrimônio líquido cresceu R\$ 200\.000,00 desde o relatório anterior \(\+20,0%\)/,
      ),
    ).toBeVisible();
  });
});
