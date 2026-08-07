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
import { mkdirSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";

import {
  mockReportPage,
  PARECER_ITENS_RETIDOS,
  waitForReportReady,
  type PlannerReviewFixture,
} from "../helpers/mock-report";

const VIEWPORT = { width: 1280, height: 800 };
const SNAPSHOT_DIR = join(__dirname, "__snapshots__");
const BASELINE_PATH = join(SNAPSHOT_DIR, "report.print.pdf.png");
const ACTUAL_PATH = join(SNAPSHOT_DIR, "report.print.pdf.actual.png");
const DIFF_PATH = join(SNAPSHOT_DIR, "report.print.pdf.diff.png");
const MAX_DIFF_PIXELS = 500;
const UPDATE_BASELINE = process.env.UPDATE_PRINT_BASELINE === "1";

/** Vocabulário de operador que não pode sair do produto num arquivo que vai
 *  para terceiro. `E5`/`E6` ficam fora da lista: "E5" casaria dentro de
 *  qualquer número em notação científica do PDF. */
const PROIBIDO_NO_PDF = [
  "error_detail",
  "_meta",
  "whitelist_miss",
  "resolve_null",
  "pairing_mismatch",
  "number_in_prose",
  "needs_review",
  "parecer.citacao_nao_confirmada",
  "entregue_com_retencao",
  "items_dropped",
  "evidencia unverified",
];

async function setupPrintReport(
  page: Page,
  plannerReview: PlannerReviewFixture = "none",
): Promise<void> {
  // Theme light é o padrão do PDF (impressão). Injeta antes de qualquer
  // navegação para evitar flash dark→light no PDF gerado.
  await page.addInitScript(() => {
    localStorage.setItem("theme", "light");
  });

  const { workspaceId, reportId } = await mockReportPage(page, { plannerReview });
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

/** A40.l22 — extração de TEXTO do PDF via `pdftotext` (Poppler).
 *
 * Complementa o diff de pixel acima, que é cego a conteúdo: `MAX_DIFF_PIXELS
 * = 500` não distingue "2 itens retidos" de "0 itens retidos" em 12px. E
 * complementa `parecer-degradacao.@critical.spec.ts`, que assere o DOM sob
 * `emulateMedia({media:"print"})` — DOM de print não é o mesmo que camada de
 * texto do PDF: um `color: transparent`, um glifo que não embute ou um
 * `content: ""` gerado passariam no DOM e sairiam ilegíveis do PDF.
 *
 * `pdftotext` em vez de pdfjs de propósito: é o instrumento que o §Critério de
 * aceite da lane nomeia, e é o que um terceiro (contador, corretor) usaria
 * para ler o arquivo. Instalado no job por `apt-get install poppler-utils`.
 */
async function pdfToText(pdfBytes: Buffer): Promise<string> {
  const { execFileSync } = await import("node:child_process");
  const tmp = join(SNAPSHOT_DIR, "parecer.print.tmp.pdf");
  writeFileSync(tmp, pdfBytes);
  try {
    // `-layout` preserva a ordem de leitura das colunas; `-` escreve em stdout.
    return execFileSync("pdftotext", ["-layout", tmp, "-"], {
      encoding: "utf-8",
      maxBuffer: 32 * 1024 * 1024,
    });
  } finally {
    rmSync(tmp, { force: true });
  }
}

function pdftotextDisponivel(): boolean {
  try {
    const { execFileSync } = require("node:child_process") as typeof import("node:child_process");
    execFileSync("pdftotext", ["-v"], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

test.describe("Parecer degradado · texto do PDF @critical", () => {
  test.skip(
    ({ browserName }) => browserName !== "chromium",
    "PDF exige Chromium (CDP printToPDF).",
  );

  test("a ressalva de retenção chega à camada de texto do PDF", async ({ page }) => {
    if (!pdftotextDisponivel()) {
      test.skip(true, "pdftotext (poppler-utils) ausente — instale no job.");
      return;
    }
    await setupPrintReport(page, "parcial");
    const texto = await pdfToText(await generatePdf(page));

    // Controle positivo do instrumento: sem uma âncora que SABEMOS estar na
    // superfície de print, o assert negativo abaixo passaria por ausência.
    // Os `<h2>` de seção NÃO servem: nenhum título de seção sai na camada de
    // texto do PDF ("Parecer do Planejador", "Síntese Estratégica",
    // "Apêndice" — 0 ocorrências), medido em 2026-08-07.
    expect(texto).toContain("Qualidade dos dados");

    expect(texto).toMatch(
      new RegExp(`${PARECER_ITENS_RETIDOS} itens do parecer retidos na confer`),
    );
    // "retido", nunca "não publicado" (COPY_GUIDELINES §2.2), no arquivo que
    // sai do produto e chega a terceiro que não pode perguntar.
    expect(texto).not.toMatch(/n[ãa]o publicad/i);
    for (const leak of PROIBIDO_NO_PDF) expect(texto).not.toContain(leak);
  });

  // O sinal da SEÇÃO (a nota do hero) não chega ao PDF em geometria A4, e a
  // causa é pré-existente e independente desta lane: com `paperHeight: 300in` o
  // mesmo run traz a nota, os pontos fortes e o diagnóstico; com A4 (a
  // geometria real de `pdf_renderer.py`) nenhum deles aparece, e o título de
  // TODA seção também não. Medido 2026-08-07 — `pdftotext -layout` sobre o PDF
  // do próprio harness, com e sem a mudança desta lane.
  //
  // `fixme` e não assert: deixar vermelho bloquearia um gate por defeito de
  // outra superfície, e reescrever para passar sobre a linha do banner
  // esconderia que a seção não chega. A ressalva do banner (assertada acima)
  // é o que o PDF de hoje carrega.
  test.fixme(
    "a nota da seção chega ao PDF em A4 — bloqueado por truncagem pré-existente do export",
    async ({ page }) => {
      await setupPrintReport(page, "parcial");
      const texto = await pdfToText(await generatePdf(page));
      expect(texto).toContain("Os números das demais seções não mudam.");
    },
  );
});
