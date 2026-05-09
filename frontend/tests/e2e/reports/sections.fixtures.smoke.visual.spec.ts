/**
 * Smoke render por fixture variante — captura regressões estruturais
 * que escapam ao baseline `medium.json` (overflow, anchoring, long
 * strings). Baseado nas regressões #147 (overflow Endividamento), #148
 * (chart sem ReportCard wrapper), #150 (period anchoring) e #151
 * (display name longo Top 15).
 *
 * NÃO compara screenshots aqui — exercita só o caminho de renderização
 * com cada fixture e assegura: (a) shell pronto, (b) ausência de
 * ErrorBoundary, (c) presença de toda seção estratégica + apêndices.
 * Snapshot pixel-level por fixture × tema fica para follow-up
 * (track futuro) — exige ritual de baseline em CI Linux.
 *
 * Vive no projeto `visual` para reaproveitar gating + cache do
 * `frontend-visual` job (auto-trigger em PR que toca relatório). Sem
 * baselines → não falha por OS/font drift.
 */
import { test, expect, type Page } from "@playwright/test";

import {
  mockReportPage,
  waitForReportReady,
  type FixtureName,
} from "../helpers/mock-report";

const VIEWPORT = { width: 1280, height: 800 };

const FIXTURES: ReadonlyArray<FixtureName> = [
  "long-strings",
  "large-values",
  "sparse-data",
];

const THEMES = ["light", "dark"] as const;
type Theme = (typeof THEMES)[number];

const STRATEGIC_SECTIONS = ["S1", "S2", "S3", "S4", "S7", "S8", "S9", "S10"];
const APPENDICES = ["APP_A", "APP_B", "APP_C", "APP_D", "APP_E"];

async function setupReport(
  page: Page,
  theme: Theme,
  fixture: FixtureName,
): Promise<void> {
  await page.addInitScript((t) => {
    localStorage.setItem("theme", t);
  }, theme);

  const { workspaceId, reportId } = await mockReportPage(page, { fixture });
  await page.setViewportSize(VIEWPORT);
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
  await waitForReportReady(page);
  // Mesma espera de animação do spec de snapshots — chart.js anima por
  // default; sem isso pegamos canvas vazio em momento intermediário.
  await page.waitForTimeout(500);
}

test.describe("Smoke — fixture variants (sem snapshot, só estrutural)", () => {
  for (const fixture of FIXTURES) {
    for (const theme of THEMES) {
      test(`renders without error · ${fixture} · ${theme}`, async ({
        page,
      }) => {
        const consoleErrors: string[] = [];
        page.on("console", (msg) => {
          if (msg.type() === "error") consoleErrors.push(msg.text());
        });

        await setupReport(page, theme, fixture);

        // (a) shell montou
        await expect(page.locator('[data-report-ready="true"]')).toBeVisible();

        // (b) ErrorBoundary não disparou — fallback usa role="alert"
        // com texto "Não conseguimos carregar esta página"
        await expect(
          page.getByRole("alert", {
            name: /Não conseguimos carregar esta página/i,
          }),
        ).toHaveCount(0);

        // (c) todas as seções estratégicas + apêndices presentes
        for (const id of [...STRATEGIC_SECTIONS, ...APPENDICES]) {
          const node = page.locator(`section#${id}[data-report-section]`);
          await expect(
            node,
            `seção ${id} faltando para fixture ${fixture}/${theme}`,
          ).toHaveCount(1);
        }

        // (d) zero erros não-suprimidos no console — pega React render
        // errors silenciosos (key warnings, prop type, etc.) que
        // sinalizam quebra de contrato de dado entre fixture e card.
        // Filtra ruídos esperados de fonte/recurso externo bloqueado
        // em ambiente de teste sem rede (mock-report cobre /api/v1).
        const realErrors = consoleErrors.filter(
          (e) =>
            !/Failed to load resource/i.test(e) &&
            !/net::ERR_/i.test(e) &&
            !/Refused to/i.test(e),
        );
        expect(realErrors, realErrors.join("\n")).toEqual([]);
      });
    }
  }
});
