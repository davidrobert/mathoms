/**
 * V0 (SNAPSHOT_CHANGELOG_V3 W4/D6 · ADR-190 §Emenda) — E2E @critical:
 * 2º relatório carrega /reports/[id] e mostra a seção "O que mudou desde o
 * último relatório" (manchete neutra do M_PL + tabela de indicadores por
 * unidade + rodapé de completude).
 *
 * Usa `mockReportPage` (fixture `medium.json`, que traz as métricas
 * canônicas v3 em `comparisons` + `comparison_periods`): o router bespoke
 * antigo não cobria /suggestions|/decisions|/consumo-pontuais e derrubava o
 * shell via ErrorBoundary (failure modes documentados em mock-report.ts).
 *
 * Valores esperados (medium.json):
 * - M_PL 1.150.000 → 1.200.000 ⇒ manchete "+R$ 50.000,00"
 * - M_TAXA_POUPANCA 12,0% → 15,0% (pp, up) ⇒ "+3,0 pp"
 * - M_AUVP_DESVIO 8,0 → 5,0 (pp, down, direction_positive=down) ⇒ "-3,0 pp"
 * - M_RESERVA_MESES stable ⇒ fora da tabela, rodapé de completude
 */
import { expect, test } from "@playwright/test";

import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

test.describe("Report Premium · V0 o-que-mudou @critical", () => {
  test("seção V0 mostra manchete do M_PL + indicadores vs relatório anterior", async ({
    page,
  }) => {
    const { reportId } = await mockReportPage(page);

    await page.goto(`/reports/${reportId}`);
    await waitForReportReady(page);

    // Seção V0 renderizada entre o Sumário Executivo e o banner de qualidade.
    const section = page.locator("section#V0[data-report-section]");
    await expect(section).toBeVisible();
    await expect(
      section.getByRole("heading", {
        name: "O que mudou desde o último relatório",
      }),
    ).toBeVisible();

    // Moldura temporal com os períodos reais do par.
    await expect(page.getByTestId("v0-subtitle")).toHaveText(
      "Este relatório (abril de 2026) comparado ao anterior (março de 2026). Listamos apenas variações relevantes.",
    );

    // Manchete neutra: Δ do M_PL com sinal explícito, sem glifo ▲/▼.
    const headline = page.getByTestId("v0-headline");
    await expect(headline).toBeVisible();
    await expect(headline).toContainText(/\+R\$\s*50\.000,00/);
    await expect(headline).not.toContainText("▲");
    await expect(page.getByTestId("v0-headline-caption")).toContainText(
      "A separação entre aporte, rendimento e efeito de mercado ainda não está disponível.",
    );

    // Tabela de indicadores: formatação por unidade + julgamento W2.
    const table = page.getByTestId("v0-indicators-table");
    await expect(table).toBeVisible();
    const taxaRow = table.locator('tr[data-section-id="M_TAXA_POUPANCA"]');
    await expect(taxaRow).toHaveAttribute("data-delta-signal", "up");
    await expect(taxaRow).toContainText("+3,0 pp");
    const desvioRow = table.locator('tr[data-section-id="M_AUVP_DESVIO"]');
    await expect(desvioRow).toHaveAttribute("data-delta-signal", "down");
    await expect(desvioRow).toContainText("-3,0 pp");

    // Stable some da lista e vai para o rodapé de completude.
    await expect(
      table.locator('tr[data-section-id="M_RESERVA_MESES"]'),
    ).toHaveCount(0);
    await expect(page.getByTestId("v0-stable-footer")).toHaveText(
      "Outro indicador acompanhado permaneceu estável.",
    );
  });
});
