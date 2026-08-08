import type { Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  mockReportPage,
  plannerReviewStub,
  waitForReportReady,
  type PlannerReviewFixture,
} from "./mock-report";

/** Geometria do export real — paridade com `backend/app/services/pdf_renderer.py`
 *  (A4 portrait, margens 15/12/15/12mm, `print_background=True`).
 *
 *  Fonte única de propósito: dois specs com cópias próprias da geometria podem
 *  divergir sem que nada falhe, e o verde passaria a valer sobre um PDF que não
 *  é o que o usuário baixa. */
export const A4_PRINT_PARAMS = {
  paperWidth: 8.27,
  paperHeight: 11.69,
  marginTop: 15 / 25.4,
  marginRight: 12 / 25.4,
  marginBottom: 15 / 25.4,
  marginLeft: 12 / 25.4,
  printBackground: true,
  preferCSSPageSize: false,
} as const;

/** Área útil de uma página, em CSS px @96dpi — o papel menos as margens acima. */
export const PRINT_AREA_PX = {
  width: Math.round(((210 - 12 - 12) / 25.4) * 96),
  height: Math.round(((297 - 15 - 15) / 25.4) * 96),
};

const REPORT_VIEWPORT = { width: 1280, height: 800 };

/** Abre `/reports/[id]?print=1` com fixture mockada e espera o estado terminal. */
export async function setupPrintReport(
  page: Page,
  /** Ausente = default do roteador (404 → empty state), como antes da A40.l22. */
  plannerReview?: PlannerReviewFixture,
): Promise<void> {
  // Theme light é o padrão do PDF (impressão). Injeta antes de qualquer
  // navegação para evitar flash dark→light no PDF gerado.
  await page.addInitScript(() => {
    localStorage.setItem("theme", "light");
  });

  const { workspaceId, reportId } = await mockReportPage(page, {
    plannerReview: plannerReview ? plannerReviewStub(plannerReview) : undefined,
  });
  await page.setViewportSize(REPORT_VIEWPORT);
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}&print=1`);
  await waitForReportReady(page);

  // Charts canvas + recharts SVG terminam de animar; o backend espera 2s
  // (`pdf_renderer.py`). Manter paridade.
  await page.waitForTimeout(2_000);
}

/** CDP `Page.printToPDF` — mesma chamada que o backend faz via Playwright. */
export async function generateReportPdf(page: Page): Promise<Buffer> {
  const client = await page.context().newCDPSession(page);
  const { data } = await client.send("Page.printToPDF", A4_PRINT_PARAMS as never);
  await client.detach().catch(() => undefined);
  return Buffer.from(data, "base64");
}

export function pdftotextInstalado(): boolean {
  try {
    execFileSync("pdftotext", ["-v"], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

/** Camada de texto do PDF, via Poppler.
 *
 * `pdftotext` e não pdfjs de propósito: é o instrumento que o §Critério de
 * aceite da A40.l22 nomeia, e é o que um terceiro (contador, corretor, banco)
 * usaria para ler o arquivo que sai do produto. */
export function pdfToText(pdfBytes: Buffer): string {
  const dir = mkdtempSync(join(tmpdir(), "mathoms-pdf-"));
  const file = join(dir, "report.pdf");
  writeFileSync(file, pdfBytes);
  try {
    // `-layout` preserva a ordem de leitura das colunas; `-` escreve em stdout.
    return execFileSync("pdftotext", ["-layout", file, "-"], {
      encoding: "utf-8",
      maxBuffer: 64 * 1024 * 1024,
    });
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

/** Colapsa o whitespace que `-layout` usa para alinhar colunas.
 *
 * Sem isto, um título que o papel quebra em duas linhas (a coluna de impressão
 * é 703px, quase metade do viewport de tela) não casaria por `includes` e o
 * gate acusaria ausência onde há só reflow. */
export function normalizarTexto(txt: string): string {
  return txt.replace(/\s+/g, " ").trim();
}

/** Conta páginas reais: `pdftotext` termina cada página com `\f`, inclusive a
 *  última — split cru devolve um elemento vazio a mais. */
export function contarPaginas(txt: string): number {
  return txt.split("\f").filter((p) => p.length > 0).length;
}
