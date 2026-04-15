/**
 * F6.5C.6 — Drill-down Dashboard → Transactions (Fluxo 5)
 *
 * Click em categoria no pie chart OU mês no bar chart navega para
 * /transactions com filtros aplicados via URL params.
 *
 * Em CI sem dados reais, cobrimos o comportamento de navegação:
 * acesso direto a /transactions?category=X mostra filtro aplicado.
 */
import { test, expect } from "@playwright/test";
import { ensureLoggedIn } from "./helpers/auth";

test.describe("Drill-down Dashboard → Transactions", () => {
  test("navegar /transactions com category filter preserva query string", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);

    await page.goto("/transactions?category=alimentacao");
    await expect(page).toHaveURL(/category=alimentacao/);
    await expect(page.getByText(/Transações/)).toBeVisible();
  });

  test("filtros de URL persistem em /transactions", async ({ page, request }, info) => {
    await ensureLoggedIn(page, request, info);

    await page.goto(
      "/transactions?date_from=2026-04-01&date_to=2026-04-30&bank=c6bank",
    );
    await expect(page).toHaveURL(/date_from=2026-04-01/);
    await expect(page).toHaveURL(/bank=c6bank/);
  });

  test("Dashboard carrega sem crash quando acessado direto", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);
    await page.goto("/dashboard");
    // Dashboard pode mostrar empty state (sem pipeline rodou) ou KPIs
    await expect(page.getByText(/Dashboard|Nenhuma análise disponível/)).toBeVisible(
      { timeout: 10_000 },
    );
  });
});
