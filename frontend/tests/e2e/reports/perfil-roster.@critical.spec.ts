/**
 * Roster de CPFs do bloco de identidade (`PerfilFamiliaSection`, PR #1382).
 *
 * Sobra do #1382: o mock não servia `GET /config/members`, então o `<dl>`
 * nome→CPF mascarado nunca renderizava no e2e — a cobertura era só unitária
 * (jsdom), e axe/tab-order/print passavam por AUSÊNCIA da superfície.
 *
 * O que se trava aqui:
 * 1. O roster monta com o mock: ordenado por `order` (a fixture serve fora
 *    de ordem de propósito), membro sem CPF omitido, máscara do servidor
 *    exibida como veio (`***.***.NNN-NN`, ADR-259 §4 — nunca mascarar local).
 * 2. Owner (`/me/workspaces` do mock) vê o reveal com accessible name.
 * 3. Em `@media print` o reveal some (`useIsPrint`) e nenhum CPF pleno
 *    aparece — o PDF que vai a terceiro só carrega a máscara.
 */
import { expect, test } from "@playwright/test";

import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

/** CPF pleno (`123.456.789-00`). A máscara `***.***.111-22` não casa. */
const FULL_CPF = /\d{3}\.\d{3}\.\d{3}-\d{2}/;

test.describe("Perfil da família · roster de CPFs @critical", () => {
  test("roster monta ordenado, mascarado e sem membro sem CPF", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const section = page.locator("section#perfil[data-report-section]");
    await expect(section).toBeAttached();

    // O roster chega depois do shell (2 fetches no useEffect) — o auto-wait
    // do toBeVisible cobre a janela.
    const roster = section.locator("dl");
    await expect(
      roster,
      "o <dl> do roster deve montar com o mock de members",
    ).toBeVisible();

    const nomes = roster.locator("dt");
    await expect(nomes, "membro sem CPF não entra no roster").toHaveCount(2);
    await expect(nomes.nth(0), "ordena por `order`, não pela resposta").toContainText(
      "Titular Sintético",
    );
    await expect(nomes.nth(1)).toContainText("Cônjuge Sintética");
    await expect(roster).not.toContainText("Dependente Sintético");

    await expect(roster).toContainText("***.***.111-22");
    expect(await roster.innerText()).not.toMatch(FULL_CPF);

    await expect(
      section.getByRole("button", {
        name: /Ver CPF completo de Titular Sintético/,
      }),
      "owner vê o reveal auditado, com accessible name",
    ).toBeVisible();
  });

  test("em print o reveal some e só a máscara chega ao papel", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const section = page.locator("section#perfil[data-report-section]");
    const roster = section.locator("dl");
    await expect(roster).toBeVisible();

    await page.emulateMedia({ media: "print" });
    // `useIsPrint` reage ao matchMedia("print"); o unmount do botão é
    // assíncrono — toHaveCount espera.
    await expect(
      section.getByRole("button", { name: /Ver CPF completo/ }),
      "affordance interativa não imprime",
    ).toHaveCount(0);
    await expect(roster).toContainText("***.***.111-22");
    expect(await roster.innerText()).not.toMatch(FULL_CPF);
    await page.emulateMedia({ media: null });
  });
});
