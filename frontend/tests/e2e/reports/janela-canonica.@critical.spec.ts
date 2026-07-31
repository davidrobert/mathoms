/**
 * A40.l3 — verificação **renderizada** da janela canônica (ADR-306 D1).
 *
 * O contract test em Vitest (`tests/components/report/janelaCanonica.contract.test.tsx`)
 * é a guarda permanente e bloqueante — roda em `frontend-checks`, que está em
 * `all-green.needs`. Este spec fecha o débito de método herdado da revisão r3:
 * a lane não fecha sobre inferência de código, precisa do par rótulo↔valor no
 * DOM real, tela **e** superfície de PDF. Ele roda no mesmo job, como step
 * gateado por `changes.outputs.report` (ver ci.yml) — não pelo label `e2e`,
 * que estava skipped em 12/12 runs recentes.
 *
 * Fixture `janela-divergente` tem `fluxo_caixa.janela_12m` divergente do bloco
 * `full` por valor detectável (receita 92k vs 40k/mês; gastos pontuais R$ 96.000
 * vs R$ 250.000) — nas 5 fixturas anteriores o texto infrator **não renderiza**
 * (0/5 têm `receita_recorrente_mensal`, 0/5 têm `consumo_consciente`), então um
 * spec escrito sobre elas passaria sem exercitar o defeito.
 *
 * Instrumento da perna de PDF: `page.emulateMedia({ media: "print" })` ANTES
 * do `goto`. `?print=1` **não** liga `isPrint` — a rota só marca
 * `data-print-route="1"` para CSS, enquanto `useIsPrint` depende de
 * `window.matchMedia("print")`. Assert de DOM após `?print=1` observaria a
 * superfície de TELA acreditando medir a de PDF (falso-verde). Aqui a
 * superfície de print é assertada por CONTEÚDO; rasterização de PDF segue
 * label-only em `frontend-print-visual` e é cega a diferença de valor
 * (`MAX_DIFF_PIXELS = 500` não distingue R$ 4.000 de R$ 11.000 em 12px).
 */
import { test, expect, type Page, type Locator } from "@playwright/test";

import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

const VIEWPORT = { width: 1280, height: 800 };

/** Valores canônicos (bloco `janela_12m`) e proibidos (bloco `full`). */
const RECEITA_12M = /R\$\s?92\.000/;
const DESPESA_12M = /R\$\s?81\.000/;
const RECEITA_FULL = /R\$\s?40\.000/;
const DESPESA_FULL = /R\$\s?36\.000/;
/** Média da série inteira — a mensalização sem rótulo que o chart irmão emitia. */
const MEDIA_SERIE_FULL = /R\$\s?42\.667/;
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
  await expect(fluxoCard(page).locator("[data-chart-conclusion]")).toBeVisible();
}

function fluxoCard(page: Page): Locator {
  return page
    .locator("section.card-variant-neutral")
    .filter({ has: page.getByRole("heading", { name: "Fluxo de Caixa Mensal" }) });
}

function rdmCard(page: Page): Locator {
  return page
    .locator("section.card-variant-neutral")
    .filter({ has: page.getByRole("heading", { name: "Receita vs Despesa — Mês a Mês" }) });
}

function consumoCard(page: Page): Locator {
  return page
    .locator("section.card-variant-success")
    .filter({ has: page.getByRole("heading", { name: "Consumo Consciente" }) });
}

/** Valores citados como `X/mês` na seção — invariante de CONSUMO, não de site
 * enumerado: componente novo que mensalize o bloco full cai aqui. */
async function valoresPorMes(page: Page): Promise<string[]> {
  const texto = (await page.locator("section#S2[data-report-section]").innerText()) ?? "";
  return [...texto.matchAll(/R\$\s*([\d.]+(?:,\d+)?)\s*\/mês/g)].map((m) => m[1]);
}

test.describe("janela canônica de fluxo @critical", () => {
  test("tela: texto rotulado 12m cita o agregado de janela_12m", async ({ page }) => {
    await openReport(page);

    const context = fluxoCard(page).locator("[data-chart-context]");
    // Contagem das barras vem do render; a base do agregado, do payload.
    await expect(context).toContainText("No gráfico: 12 meses");
    await expect(context).toContainText("os últimos 12 meses documentados");
    await expect(context).toContainText(RECEITA_12M);
    await expect(context).toContainText(DESPESA_12M);
    await expect(context).not.toContainText(RECEITA_FULL);
    await expect(context).not.toContainText(DESPESA_FULL);

    const conclusion = fluxoCard(page).locator("[data-chart-conclusion]");
    await expect(conclusion).toContainText("os últimos 12 meses documentados");
    await expect(conclusion).toContainText(RECEITA_12M);
    await expect(conclusion).toContainText(DESPESA_12M);
    await expect(conclusion).not.toContainText(RECEITA_FULL);
    await expect(conclusion).not.toContainText(DESPESA_FULL);
  });

  test("tela: chart irmão não emite segunda mensalização nem taxa própria", async ({
    page,
  }) => {
    await openReport(page);
    const conclusion = rdmCard(page).locator("[data-chart-conclusion]");
    await expect(conclusion).toContainText("Janela exibida — 12 meses");
    await expect(conclusion).not.toContainText(MEDIA_SERIE_FULL);
    await expect(conclusion).not.toContainText(/Taxa de poupança/i);
    // A taxa canônica vive no hero (S1). S2 não emite taxa própria — emitir é
    // reintroduzir a segunda leitura divergente que a lane fechou.
    const s2 = await page.locator("section#S2[data-report-section]").innerText();
    expect(s2).not.toMatch(/taxa de poupança/i);
    expect([...s2.matchAll(/\((\d{1,3}[.,]\d)% da receita\)/g)]).toEqual([]);
  });

  test("tela: hero imprime o rótulo da janela ao lado da taxa", async ({ page }) => {
    await openReport(page);
    // ADR-306 §Emenda A40.l3 — tooltip não conta como rótulo: não imprime.
    const badge = page.locator("[data-janela-badge]").first();
    await expect(badge).toContainText("últimos 12 meses documentados");
  });

  test("tela: KPIs de consumo declaram cada base em texto impresso", async ({
    page,
  }) => {
    await openReport(page);

    const kpis = consumoCard(page).locator("dl").first();
    // D6 — o inventário de pontuais é o acumulado de todo o período, mesma base
    // da prosa do E5 logo abaixo. A troca para base de janela é a lane A40.l15.
    await expect(kpis).toContainText(PONTUAIS_FULL);
    await expect(kpis).not.toContainText(PONTUAIS_12M);
    await expect(kpis).toContainText("20,8");

    // Rótulos IMPRESSOS, um por base: histórico (pontuais/equivalente) e janela
    // da folga (folga/teto).
    const badges = consumoCard(page).locator("[data-janela-badge]");
    await expect(badges).toHaveCount(4);
    expect(await badges.allInnerTexts()).toEqual([
      "todo o período documentado",
      "todo o período documentado",
      "últimos 12 meses documentados",
      "últimos 12 meses documentados",
    ]);

    // A lista tem toggle próprio (default 3M) — escopo declarado em cima dela.
    await expect(consumoCard(page).locator("[data-consumo-tabela-escopo]")).toContainText(
      "Lista: últimos 3M",
    );
  });

  test("tela: toda mensalização de S2 vem da janela canônica", async ({ page }) => {
    await openReport(page);
    const porMes = await valoresPorMes(page);
    expect(porMes.length).toBeGreaterThan(0);
    const permitidos = new Set(["92.000", "81.000"]);
    expect(porMes.filter((v) => !permitidos.has(v))).toEqual([]);
  });

  test("tela: todo agregado citado em S2 declara a base", async ({ page }) => {
    await openReport(page);
    const s2 = page.locator("section#S2[data-report-section]");
    await expect(s2).toContainText("todo o período analisado");
    // Varredura de TODOS os textos derivados da seção — não só os que a lane
    // tocou. Texto sem cláusula de base é o defeito, venha de onde vier.
    const textos = await s2
      .locator("[data-chart-conclusion], [data-chart-context], .chart-context")
      .allInnerTexts();
    expect(textos.length).toBeGreaterThan(0);
    for (const t of textos) {
      expect(t).toMatch(
        /meses documentados|mês documentado|janela exibida|todo o período analisado|No gráfico:/i,
      );
    }
  });

  test("PDF: superfície print carrega a mesma janela canônica", async ({ page }) => {
    // Instrumento — sem isto `isPrint` é false e o spec mede a tela.
    await page.emulateMedia({ media: "print" });
    await openReport(page);

    // Bloco print-only: prova que `isPrint === true` (senão não renderiza) e
    // que o total da série inteira agora vem rotulado (ADR-306 D1).
    const printTotals = page.locator("[data-rdm-print-totals]");
    await expect(printTotals).toHaveCount(1);
    await expect(printTotals).toContainText("Série completa");
    await expect(printTotals).toContainText("36 meses");

    const context = fluxoCard(page).locator("[data-chart-context]");
    await expect(context).toContainText("os últimos 12 meses documentados");
    await expect(context).toContainText(RECEITA_12M);
    await expect(context).not.toContainText(RECEITA_FULL);

    const conclusion = fluxoCard(page).locator("[data-chart-conclusion]");
    await expect(conclusion).toContainText(RECEITA_12M);
    await expect(conclusion).not.toContainText(RECEITA_FULL);

    // I5 — no PDF o rótulo tem de estar impresso ao lado do número, nos dois
    // portadores: hero (taxa) e card de consumo (duas bases).
    await expect(page.locator("[data-janela-badge]").first()).toContainText(
      "últimos 12 meses documentados",
    );
    expect(await consumoCard(page).locator("[data-janela-badge]").allInnerTexts()).toEqual([
      "todo o período documentado",
      "todo o período documentado",
      "últimos 12 meses documentados",
      "últimos 12 meses documentados",
    ]);
  });
});
