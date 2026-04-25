/**
 * tab-order E2E — Lane `report-a11y-finalize` item 1.
 *
 * Garante que o usuário com teclado consegue:
 *  1. Localizar o skip-nav do relatório e usá-lo para focar `#report-main`.
 *  2. Encontrar os controles globais do shell (theme, mode, font-scale, TOC,
 *     FloatingNav) com accessible name não vazio.
 *  3. Não encontrar nenhum controle interativo dentro do escopo do relatório
 *     (`[data-report-scope]`) sem accessible name.
 *
 * Nota: o relatório é renderizado dentro do AppShell (sidebar + nav global),
 * que tem seus próprios focáveis. Assertion não verifica que skip-nav é o
 * PRIMEIRO Tab da página inteira — verifica que ele é o primeiro do
 * escopo do relatório (`[data-report-scope]`).
 *
 * Regressão alvo: alguém adiciona `<button>` sem `aria-label` no shell —
 * teste #3 falha porque o focável aparece sem accessible name.
 */
import { test, expect, type Page } from "@playwright/test";
import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

async function reportFocusables(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const scope = document.querySelector("[data-report-scope]");
    if (!scope) return [];
    const sel = "a[href], button, input, select, textarea, [tabindex]:not([tabindex='-1'])";
    return Array.from(scope.querySelectorAll<HTMLElement>(sel))
      .filter((el) => !el.hasAttribute("disabled") && el.offsetParent !== null)
      .map((el) => {
        const aria = el.getAttribute("aria-label");
        const labelledBy = el.getAttribute("aria-labelledby");
        const labelEl = labelledBy ? document.getElementById(labelledBy) : null;
        const title = el.getAttribute("title");
        const text = (el.textContent ?? "").trim();
        return aria ?? labelEl?.textContent?.trim() ?? text ?? title ?? "";
      });
  });
}

test.describe("Report tab-order @critical", () => {
  test("skip-nav existe, é focável e Enter pula para #report-main", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const skipNav = page
      .getByRole("link", { name: /Pular para o conteúdo/i })
      .first();
    await expect(
      skipNav,
      "skip-nav 'Pular para o conteúdo principal' deve existir",
    ).toBeAttached();

    await skipNav.focus();
    await page.keyboard.press("Enter");
    await page.waitForTimeout(150);
    const hash = await page.evaluate(() => window.location.hash);
    expect(hash, "skip-nav deve apontar para #report-main").toBe("#report-main");

    const mainExists = await page.locator("#report-main").count();
    expect(mainExists, "destino #report-main deve existir no DOM").toBeGreaterThan(0);
  });

  test("skip-nav é o primeiro focável do escopo [data-report-scope]", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const names = await reportFocusables(page);
    expect(names.length, "deve haver focáveis no escopo do relatório").toBeGreaterThan(0);
    expect(
      names[0],
      `primeiro focável do escopo do relatório deve ser skip-nav (got: ${JSON.stringify(names.slice(0, 5))})`,
    ).toMatch(/Pular para o conteúdo/i);
  });

  test("controles globais do shell estão presentes com accessible name", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const expected = [
      "Tema do relatório",
      "Modo do relatório",
      "Tamanho da fonte",
      "Navegação do relatório",
      "Voltar ao topo",
      "Ir para o final",
    ];
    for (const label of expected) {
      const locator = page.locator(`[aria-label="${label}"]`).first();
      await expect(
        locator,
        `controle com aria-label="${label}" deve existir no shell`,
      ).toBeAttached();
    }
  });

  test("nenhum focável dentro de [data-report-scope] sem accessible name", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const offending = await page.evaluate(() => {
      const scope = document.querySelector("[data-report-scope]");
      if (!scope) return [{ tag: "ROOT", outerHTML: "[data-report-scope] não encontrado" }];
      const sel = "a[href], button, input, select, textarea";
      return Array.from(scope.querySelectorAll<HTMLElement>(sel))
        .filter((el) => !el.hasAttribute("disabled") && el.offsetParent !== null)
        .map((el) => {
          const aria = el.getAttribute("aria-label");
          const labelledBy = el.getAttribute("aria-labelledby");
          const labelEl = labelledBy ? document.getElementById(labelledBy) : null;
          const title = el.getAttribute("title");
          const text = (el.textContent ?? "").trim();
          const hasName = !!(aria || labelEl?.textContent?.trim() || title || text);
          if (hasName) return null;
          return { tag: el.tagName, outerHTML: el.outerHTML.slice(0, 200) };
        })
        .filter((v): v is { tag: string; outerHTML: string } => v !== null);
    });

    expect(
      offending,
      `controles focáveis sem accessible name dentro do relatório:\n${offending
        .map((o) => `  <${o.tag}> ${o.outerHTML}`)
        .join("\n")}`,
    ).toEqual([]);
  });
});
