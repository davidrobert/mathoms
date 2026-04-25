/**
 * tab-order E2E — Lane `report-a11y-finalize` item 1.
 *
 * Garante que o usuário com teclado:
 *  1. Recebe o skip-nav como primeiro foco e ele aponta para `#report-main`.
 *  2. Encontra os controles globais do shell (theme, mode, font-scale, TOC,
 *     FloatingNav) com accessible name não vazio.
 *  3. Não encontra controle interativo sem nome acessível nas primeiras
 *     25 paradas de Tab.
 *
 * Regressão alvo: alguém adiciona `<button>` sem `aria-label` no shell —
 * este teste falha porque o focável aparece sem accessible name.
 */
import { test, expect, type Page } from "@playwright/test";
import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

async function getFocusedAccessibleName(page: Page): Promise<string> {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    if (!el) return "";
    const aria = el.getAttribute("aria-label");
    if (aria) return aria;
    const labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      const ref = document.getElementById(labelledBy);
      if (ref?.textContent) return ref.textContent.trim();
    }
    if (el.tagName === "A" && el.textContent) return el.textContent.trim();
    if (el.tagName === "BUTTON" && el.textContent) return el.textContent.trim();
    const title = el.getAttribute("title");
    if (title) return title;
    return "";
  });
}

test.describe("Report tab-order @critical", () => {
  test("primeiro Tab foca skip-nav, Enter pula para #report-main", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    await page.evaluate(() => (document.activeElement as HTMLElement)?.blur?.());

    await page.keyboard.press("Tab");
    const firstFocusName = await getFocusedAccessibleName(page);
    expect(
      firstFocusName,
      "primeiro foco deve ser o skip-nav 'Pular para o conteúdo principal'",
    ).toMatch(/Pular para o conteúdo/i);

    await page.keyboard.press("Enter");
    await page.waitForTimeout(150);
    const hash = await page.evaluate(() => window.location.hash);
    expect(hash, "skip-nav deve apontar para #report-main").toBe("#report-main");
  });

  test("controles globais do shell têm accessible name", async ({ page }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const expected = [
      /Tema do relatório/i,
      /Modo do relatório/i,
      /Tamanho da fonte/i,
      /Navegação do relatório/i,
      /Voltar ao topo/i,
      /Ir para o final/i,
    ];
    for (const pattern of expected) {
      const locator = page.getByLabel(pattern).first();
      await expect(
        locator,
        `controle com aria-label ${pattern} deve existir no shell`,
      ).toBeAttached();
    }
  });

  test("nenhum controle focável sem accessible name nas primeiras 25 tabs", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    await page.evaluate(() => (document.activeElement as HTMLElement)?.blur?.());

    const offending: { index: number; tag: string; outerHTML: string }[] = [];
    for (let i = 0; i < 25; i++) {
      await page.keyboard.press("Tab");
      const info = await page.evaluate((idx) => {
        const el = document.activeElement as HTMLElement | null;
        if (!el || el === document.body) return null;
        const tag = el.tagName;
        if (!["A", "BUTTON", "INPUT", "SELECT", "TEXTAREA"].includes(tag)) {
          return null;
        }
        const aria = el.getAttribute("aria-label");
        const labelledBy = el.getAttribute("aria-labelledby");
        const title = el.getAttribute("title");
        const text = (el.textContent ?? "").trim();
        const hasName = !!(aria || labelledBy || title || text);
        if (hasName) return null;
        return {
          index: idx,
          tag,
          outerHTML: el.outerHTML.slice(0, 200),
        };
      }, i);
      if (info) offending.push(info);
    }

    expect(
      offending,
      `controles focáveis sem accessible name:\n${offending
        .map((o) => `  #${o.index} <${o.tag}> ${o.outerHTML}`)
        .join("\n")}`,
    ).toEqual([]);
  });
});
