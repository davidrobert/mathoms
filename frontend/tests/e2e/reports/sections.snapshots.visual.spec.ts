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
 * - Tático: T1-T6 × {light, dark} (deep-link `?mode=tatico`)
 * - USA: U1-U4 × {light, dark} (deep-link `?mode=usa`)
 *
 * v2.2b: troca de modo via URL `?mode=tatico|usa` (lida por
 * `ReportModeProvider`) em vez de click — evita brittleness do toggle
 * (role="tab" + label fora do botão) e funciona com `usa` oculto da UI.
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
const TATICO_SECTIONS = ["T1", "T2", "T3", "T4", "T5", "T6"];
const USA_SECTIONS = ["U1", "U2", "U3", "U4"];

const THEMES = ["light", "dark"] as const;
type Theme = (typeof THEMES)[number];

type Mode = "estrategico" | "tatico" | "usa";

async function setupReport(
  page: Page,
  theme: Theme,
  mode: Mode = "estrategico",
): Promise<void> {
  // next-themes lê localStorage key="theme" antes do mount — injetar
  // ANTES de qualquer goto evita flash light → dark no snapshot.
  await page.addInitScript((t) => {
    localStorage.setItem("theme", t);
  }, theme);

  const { workspaceId, reportId } = await mockReportPage(page);
  await page.setViewportSize(VIEWPORT);
  // v2.2b — modo via URL (`?mode=tatico|usa`) em vez de click no toggle.
  // ReportModeProvider lê searchParams na montagem (deep-link). Robusto
  // contra: (a) toggle "usa" oculto da UI (TEMP em ReportActions), (b)
  // role="tab" + label dentro do TooltipTrigger sem aria-label, que
  // quebrava `getByRole("button", { name: /Tático|USA/i })`.
  const modeParam = mode === "estrategico" ? "" : `&mode=${mode}`;
  await page.goto(
    `/reports/${reportId}?workspace=${workspaceId}${modeParam}`,
  );
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
      // Tolerância — chart.js + tabular-nums podem variar em ~100px.
      maxDiffPixels: 200,
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

// ─── Tático ────────────────────────────────────────────────────────────

test.describe("Snapshots — modo tático", () => {
  for (const theme of THEMES) {
    for (const sectionId of TATICO_SECTIONS) {
      test(`${sectionId} — ${theme}`, async ({ page }) => {
        await setupReport(page, theme, "tatico");
        await snapshotSection(page, sectionId, theme);
      });
    }
  }
});

// ─── USA ──────────────────────────────────────────────────────────────

test.describe("Snapshots — modo USA", () => {
  for (const theme of THEMES) {
    for (const sectionId of USA_SECTIONS) {
      test(`${sectionId} — ${theme}`, async ({ page }) => {
        await setupReport(page, theme, "usa");
        await snapshotSection(page, sectionId, theme);
      });
    }
  }
});
