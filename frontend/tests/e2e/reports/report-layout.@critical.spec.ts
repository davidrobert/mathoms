/**
 * Gate de regressão para layout do shell de relatório.
 *
 * Cobre 3 sintomas reportados (PRs #169 e #170):
 * 1. Scroll horizontal indesejado no main em viewport MacBook Pro 14".
 * 2. Dois scrolls verticais simultâneos (body do AppShell + report-main interno).
 * 3. ReportTopNav sobrepondo o logo "Mathoms" no sidebar do AppShell.
 *
 * Tagged @critical para rodar em todos os browsers do matriz Playwright.
 */
import { test, expect } from "@playwright/test";

import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

test.describe("Report shell layout @critical", () => {
  test('MacBook Pro 14" (1512×945): único scroller vertical, sem scroll-x, sidebar não coberto', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1512, height: 945 });
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    // 1. Sem scroll horizontal global
    const horizontalDelta = await page.evaluate(() => {
      const html = document.documentElement;
      return html.scrollWidth - html.clientWidth;
    });
    expect(
      horizontalDelta,
      "documento não deve ter scroll horizontal — verifique min-w-0 no wrapper flex",
    ).toBeLessThanOrEqual(1);

    // 2. No máximo 1 scroller vertical efetivo no DOM
    const verticalScrollers = await page.evaluate(() => {
      const all = Array.from(document.querySelectorAll<HTMLElement>("*"));
      return all
        .filter((el) => {
          const cs = getComputedStyle(el);
          if (cs.overflowY !== "auto" && cs.overflowY !== "scroll") return false;
          return el.scrollHeight > el.clientHeight + 1;
        })
        .map((el) => ({
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          className: el.className || null,
        }));
    });
    expect(
      verticalScrollers.length,
      `esperado ≤1 scroll-y rolável; encontrados: ${JSON.stringify(verticalScrollers)}`,
    ).toBeLessThanOrEqual(1);

    // 3. Sidebar do AppShell não pode ser coberto pelo TopNav do relatório.
    const sidebar = page.locator("aside[data-app-sidebar]");
    const topnav = page.locator("[data-report-topnav]");
    await expect(sidebar).toBeVisible();
    await expect(topnav).toBeVisible();

    const sidebarBox = await sidebar.boundingBox();
    const topnavBox = await topnav.boundingBox();
    if (!sidebarBox || !topnavBox) {
      throw new Error("sidebar ou topnav sem bounding box");
    }
    expect(
      sidebarBox.x + sidebarBox.width,
      `sidebar.right (${sidebarBox.x + sidebarBox.width}) deve ser ≤ topnav.left (${topnavBox.x}) + 1`,
    ).toBeLessThanOrEqual(topnavBox.x + 1);
  });

  test("Mobile (390×844): FAB visível e em camada acima do TopNav", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const fab = page.getByRole("button", { name: /Abrir menu/i });
    await expect(fab).toBeVisible();

    const stacking = await fab.evaluate((el) => {
      const fabZ = parseInt(getComputedStyle(el).zIndex || "0", 10) || 0;
      const topnav = document.querySelector(
        "[data-report-topnav]",
      ) as HTMLElement | null;
      const topnavZ = topnav
        ? parseInt(getComputedStyle(topnav).zIndex || "0", 10) || 0
        : 0;
      return { fabZ, topnavZ };
    });
    expect(
      stacking.fabZ,
      `FAB z-index (${stacking.fabZ}) deve ser ≥ TopNav z-index (${stacking.topnavZ}) para não sumir atrás do header sticky`,
    ).toBeGreaterThanOrEqual(stacking.topnavZ);
  });
});
