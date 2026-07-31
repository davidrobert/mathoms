/**
 * A40.l3 — verificação **renderizada** da janela canônica (ADR-306 D1).
 *
 * O contract test em Vitest (`tests/components/report/janelaCanonica.contract.test.tsx`)
 * é a guarda permanente — roda em `frontend-checks`, o único job renderizável
 * na lista `needs` de `All checks green`. Este spec fecha o débito de método
 * herdado da revisão r3: a lane não fecha sobre inferência de código, precisa
 * do par rótulo↔valor no DOM real, tela **e** superfície de PDF.
 *
 * Fixture `janela-divergente` tem `fluxo_caixa.janela_12m` divergente do bloco
 * `full` por valor detectável (sobra mensal R$ 11.000 vs R$ 4.000; gastos
 * pontuais R$ 96.000 vs R$ 250.000) — nas 5 fixtures anteriores o texto
 * infrator **não renderiza** (0/5 têm `receita_recorrente_mensal`, 0/5 têm
 * `consumo_consciente`), então um spec escrito sobre elas passaria sem
 * exercitar o defeito.
 *
 * Instrumento da perna de PDF: `page.emulateMedia({ media: "print" })` ANTES
 * do `goto`. `?print=1` **não** liga `isPrint` — a rota só marca
 * `data-print-route="1"` para CSS, enquanto `useIsPrint` depende de
 * `window.matchMedia("print")`. Assert de DOM após `?print=1` observaria a
 * superfície de TELA acreditando medir a de PDF (falso-verde). Aqui não
 * usamos pixel-diff: `MAX_DIFF_PIXELS = 500` de `print.@critical.spec.ts` não
 * distingue R$ 4.000 de R$ 11.000 em parágrafo de 12px.
 */
import { test, expect, type Page, type Locator } from "@playwright/test";

import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

const VIEWPORT = { width: 1280, height: 800 };

/** Valores canônicos (bloco `janela_12m`) e proibidos (bloco `full`). */
const RECEITA_12M = /R\$\s?92\.000/;
const DESPESA_12M = /R\$\s?81\.000/;
const SOBRA_12M = /R\$\s?11\.000/;
const RECEITA_FULL = /R\$\s?40\.000/;
const DESPESA_FULL = /R\$\s?36\.000/;
const SOBRA_FULL = /R\$\s?4\.000/;
/** `janela_12m.fluxo_liquido` — TOTAL de 12 meses, nunca a sobra mensal. */
const TOTAL_INTERVALO = /R\$\s?228\.000/;
const PONTUAIS_12M = /R\$\s?96\.000,00/;
const PONTUAIS_FULL = /R\$\s?250\.000,00/;

async function openReport(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem("theme", "light");
  });
  const { workspaceId, reportId } = await mockReportPage(page, {
    fixture: "janela-divergente",
  });
  await page.setViewportSize(VIEWPORT);
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
  await waitForReportReady(page);
  await page.waitForTimeout(500);
}

function fluxoCard(page: Page): Locator {
  return page
    .locator("section.card-variant-neutral")
    .filter({ has: page.getByRole("heading", { name: "Fluxo de Caixa Mensal" }) });
}

function consumoCard(page: Page): Locator {
  return page
    .locator("section.card-variant-success")
    .filter({ has: page.getByRole("heading", { name: "Consumo Consciente" }) });
}

test.describe("janela canônica de fluxo @critical", () => {
  test("tela: texto rotulado 12m cita o agregado de janela_12m", async ({ page }) => {
    await openReport(page);

    const context = fluxoCard(page).locator("[data-chart-context]");
    await expect(context).toContainText("últimos 12 meses");
    await expect(context).toContainText(RECEITA_12M);
    await expect(context).toContainText(DESPESA_12M);
    await expect(context).not.toContainText(RECEITA_FULL);
    await expect(context).not.toContainText(DESPESA_FULL);

    const conclusion = fluxoCard(page).locator("[data-chart-conclusion]");
    await expect(conclusion).toContainText("12 meses documentados");
    await expect(conclusion).toContainText(SOBRA_12M);
    await expect(conclusion).not.toContainText(SOBRA_FULL);
    await expect(conclusion).not.toContainText(TOTAL_INTERVALO);
  });

  test("tela: KPI de gastos pontuais usa a janela e declara o rótulo", async ({
    page,
  }) => {
    await openReport(page);

    const kpis = consumoCard(page).locator("dl").first();
    await expect(kpis).toContainText(PONTUAIS_12M);
    await expect(kpis).not.toContainText(PONTUAIS_FULL);
    await expect(
      consumoCard(page).getByRole("button", {
        name: "Sobre a janela dos gastos pontuais",
      }),
    ).toBeVisible();
    await expect(
      consumoCard(page).getByRole("button", {
        name: "Sobre a janela do equivalente em meses de aporte",
      }),
    ).toBeVisible();
  });

  test("tela: agregado full só aparece rotulado (composição por fonte)", async ({
    page,
  }) => {
    await openReport(page);
    const s2 = page.locator("section#S2[data-report-section]");
    await expect(s2).toContainText("todo o período analisado");
    // Discriminador da armadilha de 20×: fluxo_liquido do intervalo não vaza.
    await expect(s2).not.toContainText(TOTAL_INTERVALO);
  });

  test("PDF: superfície print carrega a mesma janela canônica", async ({ page }) => {
    // Instrumento — sem isto `isPrint` é false e o spec mede a tela.
    await page.emulateMedia({ media: "print" });
    await openReport(page);
    // Paridade com pdf_renderer.py:141 (charts/recharts terminam de animar).
    await page.waitForTimeout(2_000);

    // Bloco print-only: prova que `isPrint === true` (senão não renderiza) e
    // que o total da série inteira agora vem rotulado (ADR-306 D1).
    const printTotals = page.locator("[data-rdm-print-totals]");
    await expect(printTotals).toHaveCount(1);
    await expect(printTotals).toContainText("Série completa");
    await expect(printTotals).toContainText("36 meses");

    const context = fluxoCard(page).locator("[data-chart-context]");
    await expect(context).toContainText("últimos 12 meses");
    await expect(context).toContainText(RECEITA_12M);
    await expect(context).not.toContainText(RECEITA_FULL);

    const conclusion = fluxoCard(page).locator("[data-chart-conclusion]");
    await expect(conclusion).toContainText(SOBRA_12M);
    await expect(conclusion).not.toContainText(SOBRA_FULL);

    const kpis = consumoCard(page).locator("dl").first();
    await expect(kpis).toContainText(PONTUAIS_12M);
    await expect(kpis).not.toContainText(PONTUAIS_FULL);
  });
});
