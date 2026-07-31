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
  "degraded",
  // A40.l3 — única fixture com `fluxo_caixa.janela_12m` + `consumo_consciente`
  // populados. Sem ela, o smoke por fixture nunca renderizava os componentes
  // que a lane corrige (0/4 das anteriores têm `receita_recorrente_mensal`).
  "janela-divergente",
];

const THEMES = ["light", "dark"] as const;
type Theme = (typeof THEMES)[number];

const STRATEGIC_SECTIONS = ["S1", "S2", "S3", "S4", "S7", "S8", "S9", "S10"];
// APP_C é hide-when-empty (ADR-167): renderiza só quando o workspace tem
// `cenarios_conjuge.labels` ou `programa_milhas` populados — fixtures
// sintéticas omitem esses campos, então a seção corretamente retorna
// null. Tratá-la como required quebra o smoke; tratá-la como optional
// (count <= 1) mantém o gate "no ErrorBoundary regression" sem confundir
// "deliberadamente oculta" com "quebrada".
const APPENDICES_REQUIRED = ["APP_A", "APP_B", "APP_D", "APP_E"];
const APPENDICES_OPTIONAL = ["APP_C"];

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

        // (c) todas as seções estratégicas + apêndices required presentes
        for (const id of [...STRATEGIC_SECTIONS, ...APPENDICES_REQUIRED]) {
          const node = page.locator(`section#${id}[data-report-section]`);
          await expect(
            node,
            `seção ${id} faltando para fixture ${fixture}/${theme}`,
          ).toHaveCount(1);
        }
        // Hide-when-empty: aceitar 0 ou 1.
        for (const id of APPENDICES_OPTIONAL) {
          const count = await page
            .locator(`section#${id}[data-report-section]`)
            .count();
          expect(
            count,
            `seção ${id} (hide-when-empty) deve renderizar 0 ou 1 vez para fixture ${fixture}/${theme}`,
          ).toBeLessThanOrEqual(1);
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

// ─── A28.l9 — teste de honestidade da fixture degradada ───
//
// Critério da lane: leitor que vê só hero + banner responde "quão
// confiável é este relatório?" sem abrir <details>. Verifica que os
// sinais de degradação aparecem agregados no topo, que o Monte Carlo
// carrega a ressalva de premissas fallback e que o doughnut sinaliza
// o nao_identificado de forma persistente.
test.describe("Honestidade — fixture degraded (A28.l9)", () => {
  test("banner agregado + ressalva S7 + alerta do doughnut visíveis", async ({
    page,
  }) => {
    await setupReport(page, "light", "degraded");

    // Banner entre o sumário executivo e a primeira seção, com os 3
    // sinais derivados do DTO (needs_review vem de /documents — mock
    // catch-all devolve 0 aqui; coberto em unit test).
    const banner = page.getByTestId("data-quality-banner");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("3 pendências afetam");
    await expect(banner).toContainText("23,0% do total");
    await expect(banner).toContainText("10/10 classes sem premissa vigente");
    await expect(banner).toContainText("7 imóveis sem classificação");
    await expect(
      banner.getByRole("link", { name: "Reclassificar transações" }),
    ).toBeVisible();

    // Nunca probabilidade precisa sobre premissa em fallback sem Alert.
    const s7Alert = page.getByTestId("s7-premissas-fallback-alert");
    await expect(s7Alert).toBeAttached();
    await expect(s7Alert).toContainText("premissas de mercado padrão");

    // Doughnut: sinal persistente de nao_identificado > 10%.
    await expect(
      page.getByTestId("despesas-nao-identificado-alert"),
    ).toBeAttached();

    // Barra fina NÃO aparece quando há sinais.
    await expect(page.getByTestId("data-quality-clean")).toHaveCount(0);
  });

  test("fixture limpa (medium): banner colapsa para barra fina", async ({
    page,
  }) => {
    await setupReport(page, "light", "medium");
    await expect(page.getByTestId("data-quality-clean")).toBeVisible();
    await expect(page.getByTestId("data-quality-banner")).toHaveCount(0);
  });
});
