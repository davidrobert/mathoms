/**
 * a11y gate por seção — Lane `report-a11y-finalize` item 2.
 *
 * Roda `@axe-core/playwright` em /reports/[id] (fixture medium) com gate
 * em `critical+serious` (decisão D1). Cada seção visível recebe scan
 * isolado para que falha aponte direto o componente.
 *
 * Tagged @critical — bloqueia push em CI quando regredido.
 */
import { test } from "@playwright/test";
import { expectNoA11yViolations } from "../helpers/axe";
import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

// V0 (SNAPSHOT_CHANGELOG_V3 W4/D6) — renderiza quando a fixture tem
// `comparisons` (medium.json inclui o bloco desde a V0).
const STRATEGIC_SECTIONS = ["V0", "S1", "S2", "S3", "S4", "S7", "S8", "S9", "S10"];
const APPENDICES = ["APP_A", "APP_B", "APP_C", "APP_D", "APP_E"];
// ADR-151 (Direção E): Modo Tático removido. ADR-168 (A8.4 PR4): Modo USA removido.

test.describe("Report a11y @critical", () => {
  test("relatório completo (modo estratégico) sem violações critical+serious", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    await expectNoA11yViolations(page, {
      selector: '[data-report-scope]',
    });
  });

  for (const sectionId of STRATEGIC_SECTIONS) {
    test(`seção ${sectionId} sem violações critical+serious`, async ({ page }) => {
      const { workspaceId, reportId } = await mockReportPage(page);
      await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
      await waitForReportReady(page);

      const selector = `section#${sectionId}[data-report-section]`;
      await page.waitForSelector(selector, { timeout: 5_000 });
      await expectNoA11yViolations(page, { selector });
    });
  }

  for (const sectionId of APPENDICES) {
    test(`apêndice ${sectionId} sem violações critical+serious`, async ({ page }) => {
      const { workspaceId, reportId } = await mockReportPage(page);
      await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
      await waitForReportReady(page);

      const selector = `section#${sectionId}[data-report-section]`;
      const exists = await page.locator(selector).count();
      if (exists === 0) {
        test.skip(true, `seção ${sectionId} não montada no modo padrão`);
        return;
      }
      await expectNoA11yViolations(page, { selector });
    });
  }
});

// ADR-168 (A8.4 PR4): Modo USA removido — bloco describe USA deletado.
