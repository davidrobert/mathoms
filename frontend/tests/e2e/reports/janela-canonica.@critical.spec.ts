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
 * **Escopo:** o TEXTO derivado de `DespesasDoughnutChart` e
 * `ReceitaDespesaMensalChart` saiu desta lane para a A40.l15 (os dois citam
 * bases legitimamente distintas — janela ex-aporte por ADR-333 vs bruto de todo
 * o período — e escolher qual base cada texto declara é decisão de domínio).
 * `CARDS_DA_L15` os exclui nominalmente das varreduras; o resto de S2 segue
 * coberto, e o desenho do donut continua assertado.
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
import { CITA_AGREGADO, CLAUSULA_DE_BASE } from "../../shared/janelaBaseClause";

const VIEWPORT = { width: 1280, height: 800 };

/** Valores canônicos (bloco `janela_12m`) e proibidos (bloco `full`). */
const RECEITA_12M = /R\$\s?92\.000/;
const DESPESA_12M = /R\$\s?81\.000/;
const RECEITA_FULL = /R\$\s?40\.000/;
const DESPESA_FULL = /R\$\s?36\.000/;
const PONTUAIS_12M = /R\$\s?96\.000,00/;
const PONTUAIS_FULL = /R\$\s?250\.000,00/;

/** Cards cujo TEXTO derivado saiu desta lane para a A40.l15 (base e rótulo do
 * par são decisão de domínio). Mesma exclusão nominal do contract test —
 * renomear um card devolve o texto ao invariante, e falha alto. */
const CARDS_DA_L15 = ["Despesas por Categoria", "Receita vs Despesa — Mês a Mês"];

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

function consumoCard(page: Page): Locator {
  return page
    .locator("section.card-variant-success")
    .filter({ has: page.getByRole("heading", { name: "Consumo Consciente" }) });
}

function s2(page: Page): Locator {
  return page.locator("section#S2[data-report-section]");
}

/** Texto de S2 sem os cards herdados pela A40.l15. Usa `textContent` no clone
 * porque nó destacado não tem layout e `innerText` volta vazio; a diferença é
 * espaçamento entre elementos, e todo `X/mês` desta seção vive num único nó de
 * texto (prosa). */
async function textoNoEscopoDaLane(page: Page): Promise<string> {
  return s2(page).evaluate((sec, fora) => {
    const copia = sec.cloneNode(true) as HTMLElement;
    for (const card of [...copia.querySelectorAll("section")]) {
      const titulo = card.querySelector("h3")?.textContent?.trim() ?? "";
      if (fora.includes(titulo)) card.remove();
    }
    return copia.textContent ?? "";
  }, CARDS_DA_L15);
}

/** Valores citados como `X/mês` na seção — invariante de CONSUMO, não de site
 * enumerado: componente novo que mensalize o bloco full cai aqui. */
async function valoresPorMes(page: Page): Promise<string[]> {
  const texto = await textoNoEscopoDaLane(page);
  return [...texto.matchAll(/R\$\s*([\d.]+(?:,\d+)?)\s*\/mês/g)].map((m) => m[1]);
}

/** Todo texto derivado de S2 com o título do card que o hospeda — varredura,
 * não enumeração de site. */
async function textosDerivadosPorCard(
  page: Page,
): Promise<{ titulo: string; texto: string }[]> {
  return s2(page).evaluate((sec) =>
    [
      ...sec.querySelectorAll(
        "[data-chart-conclusion], [data-chart-context], .chart-context",
      ),
    ].map((n) => ({
      titulo: n.closest("section")?.querySelector("h3")?.textContent?.trim() ?? "",
      texto: n.textContent ?? "",
    })),
  );
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

  test("tela: no escopo da lane, S2 não emite taxa de poupança própria", async ({
    page,
  }) => {
    await openReport(page);
    // A taxa canônica vive no hero (S1). `ReceitaDespesaMensalChart` continua
    // emitindo uma taxa própria da série inteira — herdado pela A40.l15 junto
    // com o resto do texto daquele card.
    const texto = await textoNoEscopoDaLane(page);
    expect(texto).not.toMatch(/taxa de poupança/i);
    expect([...texto.matchAll(/\((\d{1,3}[.,]\d)% da receita\)/g)]).toEqual([]);
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

  test("tela: no escopo da lane, toda mensalização vem da janela canônica", async ({
    page,
  }) => {
    await openReport(page);
    const porMes = await valoresPorMes(page);
    expect(porMes.length).toBeGreaterThan(0);
    const permitidos = new Set(["92.000", "81.000"]);
    expect(porMes.filter((v) => !permitidos.has(v))).toEqual([]);
  });

  test("tela: todo texto que cita agregado declara a base", async ({ page }) => {
    await openReport(page);
    await expect(s2(page)).toContainText("todo o período analisado");
    // Varredura de TODOS os textos derivados da seção — não só os que a lane
    // tocou. Texto que cita agregado sem cláusula de base é o defeito, venha de
    // onde vier. Os dois cards da A40.l15 ficam de fora, nominalmente.
    const derivados = await textosDerivadosPorCard(page);
    expect(derivados.length).toBeGreaterThan(0);
    for (const titulo of CARDS_DA_L15) {
      expect(derivados.map((d) => d.titulo)).toContain(titulo);
    }
    const sujeitos = derivados
      .filter((d) => !CARDS_DA_L15.includes(d.titulo))
      .filter((d) => CITA_AGREGADO.test(d.texto));
    expect(sujeitos.length).toBeGreaterThan(0);
    // Mesma const do contract test (Vitest) — ver tests/shared/janelaBaseClause.ts.
    for (const { texto } of sujeitos) expect(texto).toMatch(CLAUSULA_DE_BASE);
  });

  test("tela: fatias do donut somam a janela, ex-aporte (ADR-333)", async ({ page }) => {
    await openReport(page);
    // Único assert desta lane sobre o donut: o total DESENHADO é o consumo da
    // janela (828k), não o bruto (972k). O par (valor, rótulo) do texto do card
    // é da A40.l15 — hoje a conclusão dele cita a base full.
    const donut = page
      .locator("section.card-variant-neutral")
      .filter({ has: page.getByRole("heading", { name: "Despesas por Categoria" }) });
    const ctx = donut.locator(".chart-context");
    await expect(ctx).toContainText(/R\$\s?828\.000/);
    await expect(ctx).not.toContainText(/R\$\s?972\.000/);
    await expect(ctx).toContainText("3 categorias");
  });

  test("PDF: superfície print carrega a mesma janela canônica", async ({ page }) => {
    // Instrumento — sem isto `isPrint` é false e o spec mede a tela.
    await page.emulateMedia({ media: "print" });
    await openReport(page);

    // Bloco print-only: prova que `isPrint === true` — sem `isPrint` ele não
    // renderiza e o resto do teste mediria a superfície de tela.
    await expect(page.locator("[data-rdm-print-totals]")).toHaveCount(1);

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
