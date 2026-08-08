/**
 * A40.l22 — gate da CAMADA DE TEXTO do PDF exportado.
 *
 * Complementa `print.@critical.spec.ts`, que compara **só a primeira página**
 * por pixel (`MAX_DIFF_PIXELS = 500`): esse diff é cego a conteúdo que some da
 * página 12, e foi por isso que o export passou a truncar sem ninguém ver —
 * medido em 2026-08-07, corrigido em 2026-08-08. Nenhum `<h2>` de seção saía
 * do PDF e o texto parava no meio do relatório.
 *
 * E complementa `parecer-degradacao.@critical.spec.ts`, que assere o DOM sob
 * `emulateMedia({media:"print"})`: DOM de print não é a camada de texto do PDF.
 * Um `color: transparent`, um `display:none` de ancestral, uma quebra de página
 * que engole o bloco, ou um glifo que não embute passariam no DOM e sairiam
 * ilegíveis — ou ausentes — do arquivo que o usuário manda para o contador.
 *
 * Roda no step `Report render gate` de `frontend-checks` (que está em
 * `all-green.needs`), não no job `frontend-print-visual` — este é opt-in por
 * label `print` e ficou skipped na maioria dos PRs.
 */
import { expect, test, type Page } from "@playwright/test";

import { PARECER_ITENS_RETIDOS } from "../helpers/mock-report";
import {
  contarPaginas,
  generateReportPdf,
  normalizarTexto,
  pdfToText,
  pdftotextInstalado,
  PRINT_AREA_PX,
  setupPrintReport,
} from "../helpers/report-pdf";

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

/** Sem `pdftotext` o gate não mede nada. Local isso é um skip legítimo (nem
 *  todo dev tem Poppler); no CI é falso-verde, e o step instala o pacote. */
function exigirPdftotext(): void {
  if (pdftotextInstalado()) return;
  if (process.env.CI) {
    throw new Error(
      "pdftotext (poppler-utils) ausente no CI — o gate de texto do PDF não " +
        "pode passar sem medir. Instale no step: `apt-get install -y poppler-utils`.",
    );
  }
  test.skip(true, "pdftotext (poppler-utils) ausente — instale com `brew install poppler`.");
}

async function textoDoPdf(page: Page, plannerReview?: Parameters<typeof setupPrintReport>[1]) {
  await setupPrintReport(page, plannerReview);
  return pdfToText(await generateReportPdf(page));
}

test.describe("Report Premium · camada de texto do PDF @critical", () => {
  test.skip(
    ({ browserName }) => browserName !== "chromium",
    "PDF exige Chromium (CDP printToPDF).",
  );

  test("todo título de seção renderizado na tela chega ao PDF", async ({ page }) => {
    exigirPdftotext();
    await setupPrintReport(page, "parcial");

    // A lista de títulos vem do DOM, não de um literal: seção nova entra no
    // gate sozinha, e o teste mede o invariante que interessa — o que está na
    // tela está no papel — em vez de uma amostra que envelhece.
    const titulos = await page.evaluate(() =>
      Array.from(document.querySelectorAll("section[id] h2"))
        .map((h) => (h.textContent ?? "").trim())
        .filter((t) => t.length > 0),
    );
    expect(titulos.length, "nenhum h2 de seção no DOM — fixture ou seletor mudou").toBeGreaterThan(8);

    const texto = normalizarTexto(pdfToText(await generateReportPdf(page)));
    const ausentes = titulos.filter((t) => !texto.includes(normalizarTexto(t)));

    expect(
      ausentes,
      `títulos de seção que a tela mostra e o PDF não: ${ausentes.join(" | ")}. ` +
        `Causa recorrente é regra de print que apaga ou trunca um ancestral ` +
        `(ver o histórico em report-print.css e globals.css §@media print).`,
    ).toEqual([]);
  });

  test("a última seção do relatório chega ao PDF", async ({ page }) => {
    exigirPdftotext();
    await setupPrintReport(page, "parcial");

    const ultima = await page.evaluate(() => {
      const secoes = document.querySelectorAll("section[id]");
      const alvo = secoes[secoes.length - 1] as HTMLElement | undefined;
      if (!alvo) return null;
      // Nó de texto folha, não `textContent`: este concatena nós irmãos sem
      // separador ("…RoadmapPróximos passos…") e o PDF os separa por quebra de
      // linha — a comparação falharia por artefato do instrumento.
      const walker = document.createTreeWalker(alvo, NodeFilter.SHOW_TEXT);
      let ultimoTexto = "";
      while (walker.nextNode()) {
        const t = (walker.currentNode.textContent ?? "").trim();
        if (t.length > 12) ultimoTexto = t;
      }
      return { id: alvo.id, texto: ultimoTexto };
    });
    expect(ultima, "nenhuma seção no DOM").not.toBeNull();
    expect(
      ultima!.texto.length,
      `a última seção (#${ultima!.id}) não tem nó de texto sondável`,
    ).toBeGreaterThan(12);

    const bruto = pdfToText(await generateReportPdf(page));
    const texto = normalizarTexto(bruto);

    // Sonda o FIM do documento, não uma âncora do meio: truncagem de export
    // corta a cauda, e um gate que só olha o miolo passa verde sobre um PDF
    // que perdeu os apêndices.
    expect(
      texto.includes(normalizarTexto(ultima!.texto)),
      `a última seção (#${ultima!.id}) não chegou ao PDF — export truncado. ` +
        `${contarPaginas(bruto)} páginas geradas; procurado: "${ultima!.texto}".`,
    ).toBe(true);
  });

  test("nenhum bloco proíbe quebra sendo mais alto que a página", async ({ page }) => {
    await setupPrintReport(page, "parcial");
    // Larga como a coluna de impressão: a altura de um bloco na tela (1280px)
    // não prediz a altura no papel (703px), e é a do papel que decide se o
    // `avoid` é satisfazível.
    await page.setViewportSize(PRINT_AREA_PX);
    await page.emulateMedia({ media: "print" });

    const ofensores = await page.evaluate((limite) => {
      const achados: string[] = [];
      document.querySelectorAll<HTMLElement>("body *").forEach((el) => {
        const s = getComputedStyle(el);
        if (s.breakInside !== "avoid" && s.pageBreakInside !== "avoid") return;
        const altura = Math.round(el.getBoundingClientRect().height);
        if (altura <= limite) return;
        const nome = el.id || (el.className || "").toString().slice(0, 60) || el.tagName;
        achados.push(`${el.tagName}[${nome}] ${altura}px`);
      });
      return achados;
    }, PRINT_AREA_PX.height);

    await page.emulateMedia({ media: null });

    expect(
      ofensores,
      `bloco com break-inside:avoid mais alto que a página útil ` +
        `(${PRINT_AREA_PX.height}px): o Chromium descarta o excedente em vez de ` +
        `quebrar, e o conteúdo some do PDF sem erro. Libere a quebra do bloco ` +
        `— ou encolha-o. Ofensores: ${ofensores.join(" | ")}`,
    ).toEqual([]);
  });
});

test.describe("Parecer degradado · texto do PDF @critical", () => {
  test.skip(
    ({ browserName }) => browserName !== "chromium",
    "PDF exige Chromium (CDP printToPDF).",
  );

  test("a ressalva de retenção chega à camada de texto do PDF", async ({ page }) => {
    exigirPdftotext();
    const texto = await textoDoPdf(page, "parcial");

    // Controle positivo do instrumento: sem uma âncora que SABEMOS estar na
    // superfície de print, o assert negativo abaixo passaria por ausência.
    expect(texto).toContain("Qualidade dos dados");

    expect(normalizarTexto(texto)).toMatch(
      new RegExp(`${PARECER_ITENS_RETIDOS} itens do parecer retidos na confer`),
    );
    // "retido", nunca "não publicado" (COPY_GUIDELINES §2.2), no arquivo que
    // sai do produto e chega a terceiro que não pode perguntar.
    expect(texto).not.toMatch(/n[ãa]o publicad/i);
    for (const leak of PROIBIDO_NO_PDF) expect(texto).not.toContain(leak);
  });

  test("a nota da seção chega ao PDF em A4", async ({ page }) => {
    exigirPdftotext();
    const texto = normalizarTexto(await textoDoPdf(page, "parcial"));

    // Era `test.fixme` desde 2026-08-07: a nota existia no DOM de print e não
    // chegava ao PDF, porque o `<header>` da seção era apagado por
    // `globals.css §@media print` e a cauda era truncada por `break-inside`.
    expect(texto).toContain("Os números das demais seções não mudam.");
    expect(texto).toContain("Parecer do Planejador");
  });

  test("o estado retido inteiro chega ao PDF", async ({ page }) => {
    exigirPdftotext();
    const texto = normalizarTexto(await textoDoPdf(page, "retido"));

    expect(texto).toContain("Parecer do Planejador");
    for (const leak of PROIBIDO_NO_PDF) expect(texto).not.toContain(leak);
  });
});
