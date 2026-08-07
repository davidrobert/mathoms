/**
 * A40.l22 — o relatório declara o que foi retido, **inclusive no PDF**.
 *
 * As guardas permanentes e bloqueantes deste sinal são os specs Vitest
 * (`tests/components/SParecerSection.test.tsx`,
 * `tests/components/report/ReportDataQualityBanner.test.tsx`,
 * `tests/components/HistoryRow.test.tsx`), que rodam em `frontend-checks`.
 * Este spec fecha o que jsdom **não pode** medir: se a nota sobrevive à
 * superfície de PRINT. Roda no mesmo job, como step gateado por
 * `changes.outputs.report` — precedente e argumento na A40.l3
 * (`janela-canonica.@critical.spec.ts`): o label `e2e` estava skipped em
 * 12/12 runs recentes, então spec atrás dele não é gate.
 *
 * **Instrumento:** `page.emulateMedia({ media: "print" })` ANTES do `goto`.
 * `?print=1` só marca `data-print-route="1"` para CSS — assertar DOM depois
 * dele observaria a superfície de TELA acreditando medir a de PDF. A
 * rasterização do PDF vive em `print.@critical.spec.ts` (label `print`) e é
 * cega a texto; aqui a superfície de print é assertada por CONTEÚDO.
 *
 * O que este spec NÃO cobre: `dedupeBySemanticKey`
 * (`utils/curadoriaDestaques.ts`) colapsa itens de `pontos_fortes`/
 * `pontos_urgentes` por regex, *first-wins*, e o descartado some sem rastro —
 * herdado da A40.l10. Medido em 2026-08-07 nas 6 fixtures de `/reports` + no
 * snapshot do view-model dogfood: **0 descartes**. Zero descarte no corpus
 * disponível é propriedade do CORPUS, não do supressor; por isso todo assert
 * aqui é de RENDER, nunca de payload.
 */
import { expect, test, type Page } from "@playwright/test";

import {
  mockReportPage,
  PARECER_ITENS_RETIDOS,
  plannerReviewStub,
  waitForReportReady,
  type PlannerReviewFixture,
} from "../helpers/mock-report";

const VIEWPORT = { width: 1280, height: 800 };
const MOBILE = { width: 375, height: 812 };

/** Vocabulário de operador que nenhuma das superfícies pode conter. */
const VAZAMENTOS = [
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

async function abrir(
  page: Page,
  plannerReview: PlannerReviewFixture,
  opts: { print?: boolean; viewport?: { width: number; height: number } } = {},
): Promise<void> {
  await page.addInitScript(() => localStorage.setItem("theme", "light"));
  if (opts.print) await page.emulateMedia({ media: "print" });
  const { workspaceId, reportId } = await mockReportPage(page, {
    plannerReview: plannerReviewStub(plannerReview),
  });
  await page.setViewportSize(opts.viewport ?? VIEWPORT);
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
  await waitForReportReady(page);
}

function secao(page: Page) {
  return page.locator("section#S_parecer[data-report-section]");
}

async function textoDaSecao(page: Page): Promise<string> {
  return (await secao(page).innerText()).trim();
}

test.describe("S_parecer — retenção parcial @critical", () => {
  test("tela: nota + 3º contador, e o contador de retidos não se diz de riscos", async ({
    page,
  }) => {
    await abrir(page, "parcial");

    const nota = page.getByTestId("parecer-retencao-parcial");
    await expect(nota).toBeVisible();
    await expect(nota).toContainText(
      `${PARECER_ITENS_RETIDOS} itens do parecer retidos na conferência`,
    );
    await expect(nota).toContainText("Os números das demais seções não mudam.");

    const caption = page.getByTestId("parecer-risks-caption");
    await expect(caption).toContainText("Mostrando 2 de 2 riscos");
    await expect(caption).toContainText(
      `${PARECER_ITENS_RETIDOS} itens do parecer retidos`,
    );
    expect(await caption.innerText()).not.toMatch(/\d+\s+riscos?\s+retid/i);
  });

  test("banner agregado ganha exatamente 1 linha, dentro do banner existente", async ({
    page,
  }) => {
    await abrir(page, "parcial");

    const banner = page.getByTestId("data-quality-banner");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText(
      `${PARECER_ITENS_RETIDOS} itens do parecer retidos na conferência antes da publicação`,
    );
    // "leitura", não "precisão" — item retido afeta completude.
    await expect(banner).toContainText("a leitura deste relatório");
    expect(await banner.innerText()).not.toMatch(/precis[ãa]o deste relat[óo]rio/);
    // Zero banner novo: a linha nasce na <ul> que já existia.
    const lista = banner.getByLabel("Pendências de qualidade de dados");
    await expect(lista.locator("> li")).toHaveCount(1);
  });

  test("PDF: a nota sobrevive à superfície de print", async ({ page }) => {
    await abrir(page, "parcial", { print: true });

    const nota = page.getByTestId("parecer-retencao-parcial");
    // `toBeVisible` sob `emulateMedia({media:"print"})` avalia o CSS de print:
    // é isto que pega um `display:none` acidental em `SParecer.print.css`.
    await expect(nota).toBeVisible();
    await expect(nota).toContainText(
      `${PARECER_ITENS_RETIDOS} itens do parecer retidos na conferência`,
    );
    // Texto no DOM, nunca hover: `title=` falha WCAG 1.4.13 e não imprime.
    await expect(nota.locator("[title]")).toHaveCount(0);
  });

  test("<md: a nota é linha própria e a caption não estoura", async ({ page }) => {
    await abrir(page, "parcial", { viewport: MOBILE });

    const nota = page.getByTestId("parecer-retencao-parcial");
    await expect(nota).toBeVisible();
    const caption = page.getByTestId("parecer-risks-caption");
    const box = await caption.boundingBox();
    expect(box).not.toBeNull();
    // A caption não pode transbordar a viewport nem o container da seção.
    const secaoBox = await secao(page).boundingBox();
    expect(box!.x + box!.width).toBeLessThanOrEqual(
      secaoBox!.x + secaoBox!.width + 1,
    );
    // Documento não rola na horizontal.
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });

  test("nenhuma superfície vaza vocabulário de operador", async ({ page }) => {
    await abrir(page, "parcial");
    const alvo = [
      await textoDaSecao(page),
      await page.getByTestId("data-quality-banner").innerText(),
    ].join("\n");

    for (const leak of VAZAMENTOS) expect(alvo).not.toContain(leak);
    expect(alvo).not.toMatch(/risco:\s*\d/i);
  });
});

test.describe("S_parecer — retido inteiro @critical", () => {
  test("tela: declara a retenção e delimita o dano", async ({ page }) => {
    await abrir(page, "retido");

    const estado = page.getByTestId("parecer-retained");
    await expect(estado).toBeVisible();
    await expect(estado).toContainText("Parecer retido neste relatório");
    await expect(estado).toContainText("Os números das demais seções não mudam.");
    // A copy de "ainda não gerado" mente aqui.
    await expect(page.getByTestId("parecer-empty")).toHaveCount(0);
  });

  test("PDF: o estado retido chega ao print — e sem sugerir que os números são suspeitos", async ({
    page,
  }) => {
    await abrir(page, "retido", { print: true });

    const estado = page.getByTestId("parecer-retained");
    await expect(estado).toBeVisible();
    await expect(estado).toContainText("Os números das demais seções não mudam.");
    // Sem a delimitação, o terceiro que recebe o PDF generaliza a lacuna do
    // add-on para o relatório inteiro — o dano real.
    const texto = await estado.innerText();
    for (const leak of VAZAMENTOS) expect(texto).not.toContain(leak);
  });

  test("retido inteiro NÃO ganha linha no banner — sinal proporcional à invisibilidade", async ({
    page,
  }) => {
    await abrir(page, "retido");
    // A seção ausente é auto-evidente ao rolar; duas vozes para o mesmo fato
    // treinariam o leitor a ignorar as duas. A fixture `medium` não tem
    // degradação de E5, então o banner não deve nem montar.
    const banner = page.getByTestId("data-quality-banner");
    if ((await banner.count()) > 0) {
      expect(await banner.innerText()).not.toMatch(/parecer/i);
    }
  });
});
