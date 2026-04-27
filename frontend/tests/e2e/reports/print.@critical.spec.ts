/**
 * v2.10 — PDF visual diff em Playwright (Report Premium UI v2 · Onda C).
 *
 * Renderiza o relatório React em modo print (`?print=1`), gera PDF via CDP
 * `Page.printToPDF()` (parity com `backend/app/services/pdf_renderer.py`:
 * A4 portrait, margens 15/12/15/12mm, `print_background:true`), converte
 * a primeira página do PDF para PNG (`pdf-to-png-converter`) e compara
 * contra baseline em `__snapshots__/report.print.pdf.png` usando
 * `pixelmatch` com tolerância `maxDiffPixels: 500` (PDFs renderizados são
 * mais barulhentos que screenshots DOM puros).
 *
 * Por que PNG e não diff binário do PDF:
 *   PDF carrega timestamps + IDs de objetos que mudam por geração,
 *   gerando diff binário 100% para a mesma renderização visual. Renderizar
 *   o PDF como PNG e diff pixel-a-pixel é o único caminho determinístico.
 *
 * Por que `__snapshots__/` e comparator manual (vs Playwright `toHaveScreenshot`):
 *   Caminho explícito pedido em [track_report_v2.md §3 v2.10] e fixo
 *   independente de OS (PDF→PNG via Poppler/pdf-to-png-converter é
 *   determinístico cross-OS dado o mesmo PDF). Playwright `toMatchSnapshot`
 *   default vai para `<spec>-snapshots/`; usamos `pixelmatch` direto para
 *   garantir o path canônico.
 *
 * Job CI: `frontend-print-visual` opt-in via label `print` (ver
 * `.github/workflows/ci.yml`). Não roda no CI default — baselines são
 * Linux/CI-parity, gerar localmente em macOS produz baselines inúteis.
 *
 * Atualização de baseline: `gh workflow run CI -f run_print=true -f update_print_baseline=true`
 * + commit dedicado dos PNGs gerados.
 */
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";

import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

const VIEWPORT = { width: 1280, height: 800 };
const SNAPSHOT_DIR = join(__dirname, "__snapshots__");
const BASELINE_PATH = join(SNAPSHOT_DIR, "report.print.pdf.png");
const ACTUAL_PATH = join(SNAPSHOT_DIR, "report.print.pdf.actual.png");
const DIFF_PATH = join(SNAPSHOT_DIR, "report.print.pdf.diff.png");
const MAX_DIFF_PIXELS = 500;
const UPDATE_BASELINE = process.env.UPDATE_PRINT_BASELINE === "1";

async function setupPrintReport(page: Page): Promise<void> {
  // Theme light é o padrão do PDF (impressão). Injeta antes de qualquer
  // navegação para evitar flash dark→light no PDF gerado.
  await page.addInitScript(() => {
    localStorage.setItem("theme", "light");
  });

  const { workspaceId, reportId } = await mockReportPage(page);
  await page.setViewportSize(VIEWPORT);
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}&print=1`);
  await waitForReportReady(page);

  // Charts canvas + recharts SVG terminam de animar; backend espera 2s
  // (ver `pdf_renderer.py:107`). Manter paridade.
  await page.waitForTimeout(2_000);
}

async function generatePdf(page: Page): Promise<Buffer> {
  // CDP `Page.printToPDF` — paridade com `backend/app/services/pdf_renderer.py:109`.
  // Precisa contexto Chromium (não funciona em Firefox/WebKit; teste só roda
  // em chromium).
  const client = await page.context().newCDPSession(page);
  const { data } = await client.send("Page.printToPDF", {
    paperWidth: 8.27, // A4 portrait — polegadas
    paperHeight: 11.69,
    marginTop: 15 / 25.4, // 15mm em polegadas
    marginRight: 12 / 25.4,
    marginBottom: 15 / 25.4,
    marginLeft: 12 / 25.4,
    printBackground: true,
    preferCSSPageSize: false,
  });
  await client.detach().catch(() => undefined);
  return Buffer.from(data, "base64");
}

async function pdfFirstPageToPng(pdfBytes: Buffer): Promise<Buffer> {
  // Lazy require: pdf-to-png-converter só é instalado no job CI dedicado
  // (ver `.github/workflows/ci.yml` job `frontend-print-visual`). Evita
  // quebrar a instalação default `npm ci` no e2e padrão.
  const mod = (await import("pdf-to-png-converter")) as {
    pdfToPng: (
      buf: Buffer,
      opts?: { disableFontFace?: boolean; viewportScale?: number },
    ) => Promise<Array<{ content: Buffer }>>;
  };
  const pages = await mod.pdfToPng(pdfBytes, {
    // viewportScale 2 dá ~2x DPI sem inflar PNG demais; suficiente para
    // detectar regressão de margem/cor/charts.
    viewportScale: 2,
    disableFontFace: false,
  });
  if (pages.length === 0) {
    throw new Error("pdf-to-png-converter retornou 0 páginas");
  }
  return pages[0].content;
}

interface DiffResult {
  diffPixels: number;
  width: number;
  height: number;
  diffPng: Buffer;
}

async function comparePngs(
  actual: Buffer,
  baseline: Buffer,
): Promise<DiffResult> {
  const { PNG } = (await import("pngjs")) as typeof import("pngjs");
  const pixelmatchMod = (await import("pixelmatch")) as {
    default: (
      img1: Uint8Array,
      img2: Uint8Array,
      output: Uint8Array | null,
      width: number,
      height: number,
      options?: { threshold?: number; includeAA?: boolean },
    ) => number;
  };
  const pixelmatch = pixelmatchMod.default;

  const a = PNG.sync.read(actual);
  const b = PNG.sync.read(baseline);
  if (a.width !== b.width || a.height !== b.height) {
    throw new Error(
      `dimensões divergem: actual ${a.width}x${a.height} vs baseline ${b.width}x${b.height}. ` +
        `regenere a baseline com UPDATE_PRINT_BASELINE=1 ou via workflow_dispatch.`,
    );
  }
  const diff = new PNG({ width: a.width, height: a.height });
  const diffPixels = pixelmatch(
    a.data,
    b.data,
    diff.data,
    a.width,
    a.height,
    { threshold: 0.2, includeAA: true },
  );
  return {
    diffPixels,
    width: a.width,
    height: a.height,
    diffPng: PNG.sync.write(diff),
  };
}

test.describe("Report Premium · PDF visual diff @critical", () => {
  // PDF rendering só faz sentido em Chromium (CDP `Page.printToPDF` é
  // específico do Chrome DevTools Protocol).
  test.skip(
    ({ browserName }) => browserName !== "chromium",
    "PDF visual diff requer Chromium (CDP printToPDF).",
  );

  test("relatório renderizado em PDF bate com baseline (margem @page A4)", async ({
    page,
  }) => {
    // CI sem `pdf-to-png-converter` instalado (ex.: jobs cross-browser ou
    // visual de seções) deve pular silenciosamente — o gate é o job
    // dedicado `frontend-print-visual`.
    try {
      await import("pdf-to-png-converter");
      await import("pngjs");
      await import("pixelmatch");
    } catch (err) {
      test.skip(
        true,
        `dependências de PDF→PNG ausentes (${(err as Error).message}). ` +
          `instale com 'npm install --save-dev pdf-to-png-converter pngjs pixelmatch' ` +
          `e rode no job 'frontend-print-visual' (label 'print').`,
      );
      return;
    }

    await setupPrintReport(page);
    const pdfBytes = await generatePdf(page);
    const actualPng = await pdfFirstPageToPng(pdfBytes);

    mkdirSync(SNAPSHOT_DIR, { recursive: true });

    if (UPDATE_BASELINE || !existsSync(BASELINE_PATH)) {
      mkdirSync(dirname(BASELINE_PATH), { recursive: true });
      writeFileSync(BASELINE_PATH, actualPng);
      console.warn(
        `[print.@critical] baseline gravada em ${BASELINE_PATH}. ` +
          `commite o PNG e remova UPDATE_PRINT_BASELINE para gate ativo.`,
      );
      // No primeiro run, "passa" — gate só aperta quando baseline existe
      // e flag não está ligada.
      return;
    }

    const baseline = readFileSync(BASELINE_PATH);
    const result = await comparePngs(actualPng, baseline);

    if (result.diffPixels > MAX_DIFF_PIXELS) {
      // Persiste artefatos para o operador inspecionar via upload do CI.
      writeFileSync(ACTUAL_PATH, actualPng);
      writeFileSync(DIFF_PATH, result.diffPng);
    }

    expect(
      result.diffPixels,
      `PDF render divergiu da baseline em ${result.diffPixels}px ` +
        `(tolerância ${MAX_DIFF_PIXELS}px, dimensões ${result.width}x${result.height}). ` +
        `Veja ${ACTUAL_PATH} + ${DIFF_PATH} no artefato do CI. ` +
        `Se a mudança é intencional, regere com UPDATE_PRINT_BASELINE=1.`,
    ).toBeLessThanOrEqual(MAX_DIFF_PIXELS);
  });
});
