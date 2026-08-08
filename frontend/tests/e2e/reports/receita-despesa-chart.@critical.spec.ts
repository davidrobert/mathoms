/**
 * v2.E.6 — gate funcional do chart "Receita vs Despesa — Mês a Mês".
 *
 * Tagged @critical: confirma que slide window e legenda toggle funcionam
 * em /reports/[id] com fixture `medium.json` (estendida com 14 meses
 * para garantir nav visivel).
 */
import { type Page, expect, test } from "@playwright/test";

import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

/** O `<section>` do `ReportCard` vive DENTRO de `section#S2`, e `hasText`
 *  casa qualquer ancestral que contenha o texto — as duas seções, portanto
 *  (strict mode violation). `hasNot: section` seleciona a folha: é o card,
 *  não a seção que o hospeda. */
function receitaDespesaCard(page: Page) {
  return page
    .locator("section")
    .filter({ hasText: "Receita vs Despesa — Mês a Mês" })
    .filter({ hasNot: page.locator("section") });
}

test.describe("ReceitaDespesaMensal chart @critical", () => {
  test("slide window: next muda o periodo exibido", async ({ page }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const card = receitaDespesaCard(page);
    await expect(card).toBeVisible();

    const nav = card.locator("[data-rdm-nav]");
    await expect(nav).toBeVisible();

    const periodLabel = card.locator("[data-rdm-period]");
    const initial = (await periodLabel.textContent()) ?? "";

    // 14 meses, default offset = 14-12 = 2; prev habilitado
    const prevBtn = card.getByRole("button", { name: "Meses anteriores" });
    await expect(prevBtn).toBeEnabled();
    await prevBtn.click();
    await page.waitForTimeout(150);

    const afterPrev = (await periodLabel.textContent()) ?? "";
    expect(afterPrev).not.toBe(initial);
  });

  test("legenda: clicar swatch alterna data-legend-hidden", async ({ page }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const card = receitaDespesaCard(page);
    await expect(card).toBeVisible();

    const swatch = card.locator("[data-legend-swatch]").first();
    await expect(swatch).toBeVisible();
    await expect(swatch).toHaveAttribute("data-legend-hidden", "false");

    await swatch.click();
    await expect(swatch).toHaveAttribute("data-legend-hidden", "true");

    await swatch.click();
    await expect(swatch).toHaveAttribute("data-legend-hidden", "false");
  });
});
