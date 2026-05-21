/**
 * Sprint A16 L2 P5 (ADR-236 §D5) — E2E @critical do `<CascataFiscalCard/>`.
 *
 * Cobre o golden path do card "Tributário PJ — Cascata Fiscal" no
 * relatório nativo: render da cascata, bloco PGBL, decision triggers
 * com severity-tipados.
 *
 * Fixture `medium.json` ganha bloco `tributario` (Simples Anexo III + 2
 * triggers) em P5 — sem isso o card cai em "perfil pendente" e gates
 * estruturais não exercitam o cascata-render.
 *
 * Tagged @critical — bloqueia push em CI.
 */
import { test, expect } from "@playwright/test";
import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

test.describe("Cascata Fiscal card @critical", () => {
  test("seção S8 renderiza cascata com camadas, PGBL e triggers", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const s8 = page.locator("section#S8[data-report-section]");
    await expect(s8).toBeVisible();
    await s8.scrollIntoViewIfNeeded();

    // Header + regime
    await expect(s8).toContainText("Tributário PJ · Cascata Fiscal");
    await expect(s8).toContainText("Simples Nacional — Anexo III");
    await expect(s8).toContainText(/Fator-R 32,0% · Anexo III/);

    // Cascata layers
    await expect(s8).toContainText(/Receita bruta PJ \(12m\)/);
    await expect(s8).toContainText(/DAS Simples Nacional/);
    await expect(s8).toContainText(/Lucro contábil PJ/);
    await expect(s8).toContainText(/Lucros distribuídos \(isentos\)/);
    await expect(s8).toContainText(/Carga tributária total/);

    // PGBL block
    await expect(s8).toContainText("Base para dedução PGBL");
    await expect(s8).toContainText("Renda tributável PF/ano");
    await expect(s8).toContainText("Limite PGBL (12%)");
    await expect(s8).toContainText(
      /Lucros distribuídos\s+não entram na base PGBL/,
    );

    // Triggers (T3 + T1 do fixture)
    await expect(s8).toContainText("Pontos de atenção");
    await expect(s8).toContainText(
      /Oportunidade: PGBL dedutível dentro do seu perfil/,
    );
    await expect(s8).toContainText(
      /Trade-off observado: pró-labore × lucros distribuídos/,
    );

    // Protection sentence + disclaimer
    await expect(s8).toContainText(/Não é recomendação/);
    await expect(s8).toContainText(
      /Confirme com seu contador antes de qualquer decisão tributária/,
    );

    // Anti-folclore — string proibida (ADR-236 N3)
    await expect(s8).not.toContainText(/Lucro presumido \(32%\)/);
  });
});
