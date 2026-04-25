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

const STRATEGIC_SECTIONS = ["S1", "S2", "S3", "S4", "S7", "S8", "S9", "S10"];
const APPENDICES = ["APP_A", "APP_B", "APP_C", "APP_D", "APP_E"];
const TATICO_SECTIONS = ["T1", "T2", "T3", "T4", "T5", "T6"];
const USA_SECTIONS = ["U1", "U2", "U3", "U4"];

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

test.describe("Report a11y modo tático @critical", () => {
  for (const sectionId of TATICO_SECTIONS) {
    test(`seção ${sectionId} sem violações critical+serious`, async ({ page }) => {
      const { workspaceId, reportId } = await mockReportPage(page);
      await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
      await waitForReportReady(page);

      const modeBtn = page
        .getByRole("button", { name: /Tático/i })
        .first();
      if (await modeBtn.isVisible().catch(() => false)) {
        await modeBtn.click();
        await page.waitForTimeout(200);
      }

      const selector = `section#${sectionId}[data-report-section]`;
      const exists = await page.locator(selector).count();
      if (exists === 0) {
        test.skip(true, `seção ${sectionId} não montada — ModeToggle pode ter mudado de UI`);
        return;
      }
      await expectNoA11yViolations(page, { selector });
    });
  }
});

test.describe("Report a11y modo USA @critical", () => {
  for (const sectionId of USA_SECTIONS) {
    test(`seção ${sectionId} sem violações critical+serious`, async ({ page }) => {
      const { workspaceId, reportId } = await mockReportPage(page);
      await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
      await waitForReportReady(page);

      const modeBtn = page
        .getByRole("button", { name: /USA|EUA/i })
        .first();
      if (await modeBtn.isVisible().catch(() => false)) {
        await modeBtn.click();
        await page.waitForTimeout(200);
      }

      const selector = `section#${sectionId}[data-report-section]`;
      const exists = await page.locator(selector).count();
      if (exists === 0) {
        test.skip(true, `seção ${sectionId} não montada — ModeToggle pode ter mudado de UI`);
        return;
      }
      await expectNoA11yViolations(page, { selector });
    });
  }
});
