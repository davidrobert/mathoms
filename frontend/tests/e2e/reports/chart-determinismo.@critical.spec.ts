/** A40.l53 — determinismo do desenho dos charts.
 *
 * Roda no "Report render gate" de `frontend-checks` (seleção por diretório +
 * `@critical`), que `all-green` exige — de propósito **fora** do job
 * `Frontend visual snapshots`, que é opt-in por label. Os dois defeitos que
 * estes testes fecham escapavam justamente por só existir gate lá.
 *
 * Nenhum dos dois usa baseline: comparam o produto contra ele mesmo, então
 * não têm o acoplamento a OS/fonte que obriga runner Linux.
 */
import { test, expect, type Page } from "@playwright/test";
import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

const VIEWPORT = { width: 1280, height: 800 };

/** A S2 é a seção com mais canvas da fixture `medium` (4) — o pior caso. */
const SECTION = "S2";
const MIN_CHARTS_ESPERADOS = 4;

/** Throttle de CPU que simula runner carregado. Sem ele o teste passa mesmo
 * com o defeito: numa máquina ociosa o redesenho termina entre uma captura e
 * a seguinte, e foi por isso que o flake só aparecia no CI. Medido: com o
 * defeito reintroduzido, 6× reprova; sem defeito, 0 pixel de diferença. */
const CPU_THROTTLE = 6;

async function abrirRelatorio(page: Page): Promise<void> {
  await page.addInitScript(() => localStorage.setItem("theme", "dark"));
  const { workspaceId, reportId } = await mockReportPage(page);
  await page.setViewportSize(VIEWPORT);
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
  await waitForReportReady(page);
  await page.locator(`section#${SECTION}[data-report-section]`).scrollIntoViewIfNeeded();
}

test.describe("Determinismo do desenho dos charts", () => {
  test("o que vai para o PDF é o que está no canvas", async ({ page }) => {
    await abrirRelatorio(page);
    // Sem reduced-motion: este teste tem de exercitar o caminho de render que
    // o usuário (e o `pdf_renderer`) recebe, com animação ligada.
    await page.waitForTimeout(3_000);

    const charts = await page.evaluate((sectionId) => {
      const sec = document.querySelector(`section#${sectionId}[data-report-section]`);
      if (!sec) throw new Error(`seção ${sectionId} não montou com a fixture medium`);
      return Array.from(sec.querySelectorAll("[data-chart-canvas]")).map((holder, i) => {
        const canvas = holder.querySelector("canvas") as HTMLCanvasElement | null;
        const img = holder.querySelector("img.chart-print-img") as HTMLImageElement | null;
        return {
          i,
          impresso: img?.getAttribute("src") ?? null,
          naTela: canvas?.toDataURL("image/png") ?? null,
        };
      });
    }, SECTION);

    // Inventário antes da comparação: se o fallback deixar de ser gerado, a
    // comparação abaixo fica vazia e o teste passaria sobre nada.
    const comFallback = charts.filter((c) => c.impresso !== null);
    expect(
      comFallback.length,
      `charts com fallback de impressão em ${SECTION} (o PDF renderiza este <img>, não o canvas)`,
    ).toBeGreaterThanOrEqual(MIN_CHARTS_ESPERADOS);

    for (const chart of comFallback) {
      expect(
        chart.impresso,
        `chart #${chart.i} da ${SECTION}: a imagem de impressão difere do canvas — ` +
          `o PDF sai com um frame no meio da animação (A40.l53)`,
      ).toBe(chart.naTela);
    }
  });

  test("com reduced-motion, capturas consecutivas são idênticas", async ({ page }) => {
    test.setTimeout(120_000);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await abrirRelatorio(page);

    // Throttle SÓ a partir daqui: o que se quer simular é o runner carregado
    // durante a captura, não durante o carregamento. Throttlar o `goto`
    // também estourava o timeout do teste no runner do CI sem medir nada a
    // mais — o mecanismo é a captura, não o boot da página.
    const client = await page.context().newCDPSession(page);
    await client.send("Emulation.setCPUThrottlingRate", { rate: CPU_THROTTLE });
    // O alvo é UM chart, não a seção inteira: o resize que a captura provoca é
    // por canvas, então o mecanismo é o mesmo, e capturar 924×256 em vez de
    // 976×2960 (11× menos pixel) é o que faz o teste caber no runner do CI sob
    // throttle. Com a seção inteira, o step estourava os 30s de timeout.
    const alvo = page.locator(`section#${SECTION}[data-report-section] [data-chart-canvas]`).first();
    await expect(alvo).toBeVisible();

    // Cadência do próprio `toHaveScreenshot`: é ela que o gate visual usa, e é
    // a captura que provoca o redesenho que se quer provar ausente.
    const esperas = [0, 100, 250, 500];
    const capturas: Buffer[] = [];
    for (const espera of esperas) {
      if (espera) await page.waitForTimeout(espera);
      capturas.push(await alvo.screenshot({ animations: "disabled" }));
    }

    for (let i = 1; i < capturas.length; i++) {
      expect(
        capturas[i].equals(capturas[i - 1]),
        `capturas ${i - 1} e ${i} do 1º chart da ${SECTION} diferem sob throttle ` +
          `${CPU_THROTTLE}× — algo volta a animar depois de a captura ` +
          `redimensionar o canvas (A40.l53)`,
      ).toBe(true);
    }
  });
});
