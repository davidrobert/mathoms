/**
 * Snapshots por seção (light + dark) — Lane `report-a11y-finalize` item 3.
 *
 * Não-`@critical` (lento, 28 snapshots). Roda apenas no projeto `visual`
 * do `playwright.config.ts` (PW_VISUAL=1 no CI dedicado), porque
 * snapshots são OS/font-rendering específicos e baselines devem vir do
 * runner Linux.
 *
 * Decisão D3 do track: spec mobile fica **fora** desta lane (lane futura
 * `report-mobile-spec` quando produto decidir o que sai em <767px).
 * Aqui rodamos só desktop @ 1280×800.
 *
 * Cobertura (28 baselines = 14 alvos × {light, dark}):
 * - shell global (cover) × {light, dark}
 * - Estratégico: S1, S2, S3, S7, S8, S9, S10 + APP_A, APP_B, APP_D, APP_E
 * - `S_parecer` nos 2 estados de degradação (retido, parcial)
 *
 * `S4` e `APP_C` estão nas listas abaixo mas NÃO geram baseline com a fixture
 * `medium` — ver `SECTIONS_NOT_IN_MEDIUM_FIXTURE`.
 *
 * ADR-151 (Direção E): Modo Tático removido. ADR-168 (A8.4 PR4): Modo USA
 * removido — Estratégico é o modo único. As 20 baselines órfãs desses dois
 * modos foram deletadas em 2026-08-08; sobreviveram ~4 meses à remoção do
 * código porque nada cruza PNG em disco com teste existente.
 *
 * Baselines vivem em `sections.snapshots.visual.spec.ts-snapshots/` (default
 * do Playwright, irmão deste arquivo).
 * Atualização: `npm run test:e2e -- --project=visual --grep sections.snapshots --update-snapshots`
 * (em CI Linux, nunca local em macOS — pixel rendering diverge).
 */
import { test, expect, type Page } from "@playwright/test";
import {
  mockReportPage,
  plannerReviewStub,
  waitForReportReady,
} from "../helpers/mock-report";

const VIEWPORT = { width: 1280, height: 800 };

const STRATEGIC_SECTIONS = ["S1", "S2", "S3", "S4", "S7", "S8", "S9", "S10"];
const APPENDICES = ["APP_A", "APP_B", "APP_C", "APP_D", "APP_E"];

const THEMES = ["light", "dark"] as const;
type Theme = (typeof THEMES)[number];

/** A40.l22 — os 2 estados de degradação de `S_parecer`.
 *
 * `S_parecer` fica FORA de `STRATEGIC_SECTIONS` acima de propósito: no estado
 * default (404) a seção é um empty state de 3 linhas, e uma baseline dele não
 * detectaria nada. O que muda de fato é o DOM dos estados novos.
 */
const PARECER_STATES = ["retido", "parcial"] as const;

/** Seções listadas acima que a fixture `medium` **não faz montar**.
 *
 * Ambas retornam `null` por hide-when-empty, e o dado que as ligaria não
 * existe na fixture:
 * - `S4`    — `data.real_estate` ausente (ADR-216 Onda 6).
 * - `APP_C` — `cenarios_conjuge` é `{}` e não há `programa_milhas`, então
 *   `hasCenarios`/`hasMilhas` são falsos (ADR-167). Atenção: a chave
 *   `cenarios_conjuge` **existe** na fixture — só está vazia. Ler o topo do
 *   JSON dá a impressão de que a seção monta.
 *
 * As baselines das duas foram deletadas em 2026-08-08: eram do #174 (abril),
 * de quando a fixture ainda ligava as seções, e nunca mais foram exercitadas.
 * Mantê-las era o pior dos mundos — no dia em que alguém popular a fixture, o
 * Playwright compararia contra um PNG de 4 meses que ninguém revisou.
 *
 * O que cada uma perde ao sair daqui é DIFERENTE — medido em 2026-08-08 sobre
 * as 6 fixtures de `tests/e2e/fixtures/reports/`:
 * - `S4` perde só o baseline de pixel. Continua com cobertura estrutural em
 *   `sections.fixtures.smoke.visual.spec.ts`, que a trata como **required** em
 *   4 fixtures (`degraded`, `large-values`, `long-strings`, `sparse-data` — as
 *   que têm `real_estate`). `medium` é uma das 2 sem.
 * - `APP_C` não tem cobertura **nenhuma**: `cenarios_conjuge.labels` está vazia
 *   nas 6 fixtures e nenhuma tem `programa_milhas`, e o smoke a lista em
 *   `APPENDICES_OPTIONAL`. `StressScenarioCard` não é renderizado por teste
 *   algum. Esse é o buraco real — S4 é o menor dos dois problemas.
 *
 * Ligar as duas aqui é trabalho separado: rebaseline no runner Linux **com
 * revisão visual humana** das PNGs novas. Para `S4` o dado sai de copiar o
 * bloco `real_estate` de outra fixture; para `APP_C` é preciso autorar
 * `cenarios_conjuge` do zero, porque não existe em lugar nenhum.
 *
 * Esta lista é allowlist, não decoração: qualquer OUTRA seção que deixe de
 * montar vira falha. Sem isso, o `test.skip` abaixo transformava regressão de
 * render (seção sumiu por bug) em job verde. */
const SECTIONS_NOT_IN_MEDIUM_FIXTURE = new Set(["S4", "APP_C"]);

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
  /** A40.l22 — nome da baseline quando a MESMA seção tem >1 estado. */
  baselineId: string = sectionId,
): Promise<void> {
  const selector = `section#${sectionId}[data-report-section]`;
  const exists = await page.locator(selector).count();
  if (exists === 0) {
    if (!SECTIONS_NOT_IN_MEDIUM_FIXTURE.has(sectionId)) {
      throw new Error(
        `seção ${sectionId} não montou com a fixture atual. Se isso for ` +
          `deliberado, adicione-a a SECTIONS_NOT_IN_MEDIUM_FIXTURE e delete a ` +
          `baseline órfã; caso contrário é regressão de render.`,
      );
    }
    test.skip(true, `seção ${sectionId} não montada com a fixture medium`);
    return;
  }
  await page.locator(selector).scrollIntoViewIfNeeded();
  await expect(page.locator(selector)).toHaveScreenshot(
    `${baselineId}.${theme}.png`,
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
      // `clip` só é aceito em `expect(page).toHaveScreenshot`, não em locator —
      // usamos page-level clip para limitar à área do cover.
      await expect(page).toHaveScreenshot(`cover.${theme}.png`, {
        maxDiffPixels: 200,
        clip: { x: 0, y: 0, width: VIEWPORT.width, height: 720 },
      });
    });
  }
});

// ADR-168 (A8.4 PR4): Modo USA removido — bloco USA `test.describe` deletado.
// Modo Estratégico cobre 100% do relatório.

// ─── A40.l22 · S_parecer degradado ─────────────────────────────────────

test.describe("Snapshots — S_parecer degradado", () => {
  for (const theme of THEMES) {
    for (const estado of PARECER_STATES) {
      test(`S_parecer ${estado} — ${theme}`, async ({ page }) => {
        await page.addInitScript((t) => localStorage.setItem("theme", t), theme);
        const { workspaceId, reportId } = await mockReportPage(page, {
          plannerReview: plannerReviewStub(estado),
        });
        await page.setViewportSize(VIEWPORT);
        await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
        await waitForReportReady(page);
        // Controle positivo: sem isto, um estado que não montou geraria
        // baseline do empty state e o gate ficaria verde sobre o DOM errado.
        await page.waitForSelector(
          estado === "retido"
            ? '[data-testid="parecer-retained"]'
            : '[data-testid="parecer-retencao-parcial"]',
          { timeout: 5_000 },
        );
        await snapshotSection(page, "S_parecer", theme, `S_parecer-${estado}`);
      });
    }
  }
});
