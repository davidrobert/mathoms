/**
 * Chrome de app não vaza para a superfície de print (PDF exportado).
 *
 * Por que existe: o PDF é a única superfície do produto que sai para
 * terceiros (contador, corretor, banco), e o gate de pixel que deveria
 * pegar isso (`frontend-print-visual`) é opt-in por label e comparava
 * contra uma baseline que era um error boundary — nunca teve sinal.
 *
 * INSTRUMENTO — as duas escolhas abaixo não são cosméticas:
 *
 * 1. `PAGE_BOX` é a CAIXA DE PÁGINA A4 (210mm − 12mm de margem por lado
 *    ≈ 703px), não o viewport do browser. Ao imprimir, o Chromium
 *    reavalia media query contra a página, não contra a janela — o
 *    renderer (`pdf_renderer.py`) usa `new_page()` sem viewport, logo
 *    1280px de janela, e mesmo assim o PDF sai em layout `<lg`.
 *    Medido por mutação (sem `.no-print`): a 703px vazam 4 controles,
 *    dois deles com `opacity: 1` — o toggle `lg:hidden` do AppShell e o
 *    FAB de índice (`isMobile`), que são exatamente os dois vistos no PDF
 *    em 2026-08-08. A 1280px vazam só os 2 FABs de scroll (`opacity: 0`):
 *    medir na janela em vez da página esconde justamente os que aparecem.
 *
 * 2. A varredura é DERIVADA (todo `<button>` com `position: fixed`), não
 *    uma lista de aria-labels. FAB novo cai no gate sozinho — foi
 *    exatamente o modo de falha original, em que o `<nav>` do FloatingNav
 *    já era escondido e os botões que o abrem, não.
 *
 * Ancoragem anti-fail-open: se a rota crashar, o inventário fica vazio e
 * a asserção de chrome passa à toa. Por isso o teste primeiro exige que o
 * relatório tenha renderizado.
 */
import { expect, test, type Page } from "@playwright/test";

import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

/** Caixa de página A4 útil do `pdf_renderer.py` (margens 15/12/15/12mm). */
const PAGE_BOX = { width: 703, height: 1009 };

interface ControleFixo {
  readonly label: string;
  readonly opacity: string;
}

async function abrirSuperficieDePrint(page: Page): Promise<void> {
  // Sem `emulateMedia` o spec mede a tela: `@media print` não se aplica.
  await page.emulateMedia({ media: "print" });
  await page.addInitScript(() => {
    localStorage.setItem("theme", "light");
  });
  const { workspaceId, reportId } = await mockReportPage(page);
  await page.setViewportSize(PAGE_BOX);
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}&print=1`);
  await waitForReportReady(page);
}

/** Todo `<button>` fixo que ainda tem caixa de layout — o que o Chromium
 * assaria no PDF. `display: none` remove a caixa, então some daqui. */
async function controlesFixosNoPrint(page: Page): Promise<ControleFixo[]> {
  return page.evaluate(() =>
    [...document.querySelectorAll("button")]
      .filter((el) => {
        const cs = getComputedStyle(el);
        if (cs.position !== "fixed") return false;
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      })
      .map((el) => ({
        label:
          el.getAttribute("aria-label") ?? (el.textContent ?? "").trim().slice(0, 40),
        opacity: getComputedStyle(el).opacity,
      })),
  );
}

test.describe("superfície de print · chrome de app @critical", () => {
  test("nenhum controle flutuante do app chega ao PDF", async ({ page }) => {
    await abrirSuperficieDePrint(page);

    // Anti-fail-open: sem relatório renderizado, zero botões é vacuidade,
    // não aprovação. Esta é a lição da baseline que era um crash.
    await expect(page.locator("[data-report-section]").first()).toBeAttached();

    expect(await controlesFixosNoPrint(page)).toEqual([]);
  });
});
