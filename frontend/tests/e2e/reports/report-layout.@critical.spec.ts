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

import { LAYOUT } from "@/generated/report-layout";

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

  /** RV3-04 (A40.l7) — âncora de nav/ToC não pode apontar para seção que o
   * relatório nunca renderiza.
   *
   * `enabled: false` com entrada de nav viva entregava link morto em 100% dos
   * relatórios. O gate estático vive no codegen (`validate_nav_targets`); este
   * é a verificação RENDERIZADA que o §Débito de método da sprint exige — a
   * lane não fecha sobre inferência de código.
   *
   * Enumera os anchors das DUAS superfícies de índice sem depender de elas
   * estarem abertas: a sidebar nasce fechada (`useReportTocOpen`) e o drawer
   * só existe em `<lg`, então um assert que só olhasse o visível passaria
   * vazio — que é o modo de falha registrado no §Insumos da lane.
   */
  test("Toda âncora de nav/ToC aponta para alvo com altura > 0", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1512, height: 945 });
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const result = await page.evaluate(() => {
      const hrefs = new Set<string>();
      document
        .querySelectorAll<HTMLAnchorElement>('a[href^="#"]')
        .forEach((a) => hrefs.add(a.getAttribute("href") as string));
      const dead: string[] = [];
      const flat: string[] = [];
      for (const href of hrefs) {
        if (href === "#") continue;
        const target = document.querySelector(href);
        if (!target) {
          dead.push(href);
        } else if (target.getBoundingClientRect().height <= 0) {
          flat.push(href);
        }
      }
      return { total: hrefs.size, dead, flat };
    });

    // Guarda contra verde vazio: se o seletor parar de achar âncora, o teste
    // passaria sem medir nada.
    expect(
      result.total,
      "nenhuma âncora encontrada — o índice mudou de marcação e o gate virou vácuo",
    ).toBeGreaterThan(5);

    // Ausente do DOM ≠ defeito: `hide-when-empty` (ADR-167) tira do ar seção
    // HABILITADA cujo payload não tem dado, e a fixture de mock é esparsa de
    // propósito. O defeito é âncora para seção que NUNCA renderiza — desligada
    // no layout ou inexistente. Medido em CI: com a fixture atual somem S4,
    // S_IRPF_RENDA, S_IRPF_OTIMIZACAO e APP_C, todas `enabled: true`.
    const habilitadas = new Set(
      [...LAYOUT.estrategico.sections, ...(LAYOUT.estrategico.appendices ?? [])]
        .filter((s) => s.enabled)
        .map((s) => s.id),
    );
    const naoRenderizavel = result.dead.filter(
      (href) => !habilitadas.has(href.slice(1)) && href.slice(1) !== "V0",
    );
    expect(
      naoRenderizavel,
      "âncora aponta para seção desligada ou inexistente — nunca vai renderizar",
    ).toEqual([]);

    // Alvo que EXISTE mas mede zero é a classe RV3-05 (seção que colapsa):
    // aqui não há desculpa de hide-when-empty, o elemento está no DOM.
    expect(result.flat, "alvo de âncora existe mas tem altura 0").toEqual([]);
  });

  test('Desktop: "Voltar ao topo" aparece após scroll e funciona', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1512, height: 945 });
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const backToTop = page.getByRole("button", { name: /Voltar ao topo/i });

    // Estado inicial: invisível
    await expect(backToTop).toHaveAttribute("data-visible", "false");

    // Rola além do limiar showAfter=400px. FloatingNav resolve o scroll
    // container automaticamente: no AppShell atual o `<main>` declara
    // overflow-y mas se estica para conteúdo (scrollHeight==clientHeight),
    // logo quem rola de fato é o `window`/body.
    await page.evaluate(() => window.scrollTo({ top: 1500 }));

    // FAB aparece após o listener detectar o scroll
    await expect(backToTop).toHaveAttribute("data-visible", "true");

    // Click → volta ao topo via scrollTo do scroll container resolvido
    await backToTop.click();
    await expect
      .poll(() => page.evaluate(() => window.scrollY), { timeout: 3000 })
      .toBeLessThan(50);
    await expect(backToTop).toHaveAttribute("data-visible", "false");
  });

  test("Mobile (390×844): FAB Índice abre dialog do TOC", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const indexBtn = page.getByRole("button", {
      name: /Abrir índice do relatório/i,
    });
    await expect(indexBtn).toBeVisible();

    const dialogOpen = await page.evaluate(() => {
      const d = document.querySelector(
        'dialog[aria-label="Índice do relatório"]',
      ) as HTMLDialogElement | null;
      return d?.open ?? false;
    });
    expect(dialogOpen).toBe(false);

    await indexBtn.click();

    await expect
      .poll(
        () =>
          page.evaluate(() => {
            const d = document.querySelector(
              'dialog[aria-label="Índice do relatório"]',
            ) as HTMLDialogElement | null;
            return d?.open ?? false;
          }),
        { timeout: 2000 },
      )
      .toBe(true);
  });
});
