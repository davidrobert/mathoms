/**
 * Snapshots por seção (light + dark) — Lane `report-a11y-finalize` item 3.
 *
 * Não-`@critical` (lento, ~50 snapshots). Roda apenas no projeto `visual`
 * do `playwright.config.ts` (PW_VISUAL=1 no CI dedicado), porque
 * snapshots são OS/font-rendering específicos e baselines devem vir do
 * runner Linux.
 *
 * Decisão D3 do track: spec mobile fica **fora** desta lane (lane futura
 * `report-mobile-spec` quando produto decidir o que sai em <767px).
 * Aqui rodamos só desktop @ 1280×800.
 *
 * Cobertura:
 * - shell global (cover, premissas) × {light, dark}
 * - Estratégico: S1-S10 + APP_A-E × {light, dark}
 *
 * ADR-151 (Direção E): Modo Tático removido. ADR-168 (A8.4 PR4): Modo USA
 * removido — Estratégico é o modo único.
 *
 * Baselines vivem em `tests/e2e/reports/__snapshots__/sections.snapshots.visual.spec.ts/`.
 * Atualização: `npm run test:e2e -- --project=visual --grep sections.snapshots --update-snapshots`
 * (em CI Linux, nunca local em macOS — pixel rendering diverge).
 */
import { test, expect, type Page } from "@playwright/test";
import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

const VIEWPORT = { width: 1280, height: 800 };

const STRATEGIC_SECTIONS = ["S1", "S2", "S3", "S4", "S7", "S8", "S9", "S10"];
const APPENDICES = ["APP_A", "APP_B", "APP_C", "APP_D", "APP_E"];

const THEMES = ["light", "dark"] as const;
type Theme = (typeof THEMES)[number];

async function setupReport(page: Page, theme: Theme): Promise<void> {
  // next-themes lê localStorage key="theme" antes do mount — injetar
  // ANTES de qualquer goto evita flash light → dark no snapshot.
  await page.addInitScript((t) => {
    localStorage.setItem("theme", t);
  }, theme);

  const { workspaceId, reportId } = await mockReportPage(page);
  await page.setViewportSize(VIEWPORT);
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
  await waitForReportReady(page);

  // Aguarda chart canvases renderizarem (chart.js anima por default;
  // animation:disabled no playwright config cobre CSS, não canvas).
  await page.waitForTimeout(500);
}

async function snapshotSection(
  page: Page,
  sectionId: string,
  theme: Theme,
): Promise<void> {
  const selector = `section#${sectionId}[data-report-section]`;
  const exists = await page.locator(selector).count();
  if (exists === 0) {
    test.skip(true, `seção ${sectionId} não montada no modo atual`);
    return;
  }
  await page.locator(selector).scrollIntoViewIfNeeded();
  await expect(page.locator(selector)).toHaveScreenshot(
    `${sectionId}.${theme}.png`,
    {
      // Tolerância proporcional — chart.js canvas tem não-determinismo
      // inerente entre runs no mesmo runner Linux (~1-2% da imagem em
      // antialiasing de paths, tooltip positioning, font hinting). Threshold
      // anterior `maxDiffPixels: 200` (~0.007% em S2) gerava flake crônico:
      // PRs #147-#165 mergeavam com gate red mesmo sem regressão real.
      // 2.5% via `maxDiffPixelRatio` captura mudanças estruturais
      // (ex.: +35px de altura = 7% diff em S1) sem perseguir variance
      // de subpixel do canvas. NÃO combinar com `maxDiffPixels` absoluto
      // — Playwright usa `Math.min(absoluto, ratio×area)`, então o piso
      // absoluto anula o ratio em imagens grandes.
      maxDiffPixelRatio: 0.025,
      // Mascarar elementos cuja renderização exata não importa para
      // detecção de regressão estrutural (ex.: timestamps).
      mask: [page.locator("[data-mask-snapshot]")],
    },
  );
}

// ─── Estratégico (default mode) ────────────────────────────────────────

test.describe("Snapshots — modo estratégico", () => {
  for (const theme of THEMES) {
    for (const sectionId of [...STRATEGIC_SECTIONS, ...APPENDICES]) {
      test(`${sectionId} — ${theme}`, async ({ page }) => {
        await setupReport(page, theme);
        await snapshotSection(page, sectionId, theme);
      });
    }
  }
});

// ─── Cover (estratégico, fullPage do hero) ─────────────────────────────

test.describe("Snapshots — cover (hero)", () => {
  for (const theme of THEMES) {
    test(`cover — ${theme}`, async ({ page }) => {
      await setupReport(page, theme);
      // ReportCover é um <section> separado fora do article. Achamos
      // pelo aria-label do badge "Relatório Premium".
      const cover = page.locator('text="Relatório Premium"').first();
      const exists = await cover.count();
      if (exists === 0) {
        test.skip(true, "ReportCover não encontrada");
        return;
      }
      // Captura a parte de cima do main (cover + premissas).
      await expect(page.locator("#report-main")).toHaveScreenshot(
        `cover.${theme}.png`,
        {
          maxDiffPixels: 200,
          clip: { x: 0, y: 0, width: VIEWPORT.width, height: 720 },
        },
      );
    });
  }
});

// ADR-168 (A8.4 PR4): Modo USA removido — bloco USA `test.describe` deletado.
// Modo Estratégico cobre 100% do relatório.
