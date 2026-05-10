/**
 * E2E — Category Overrides UI (A11.cat-overrides-ux W4 · ADR-185).
 *
 * Fluxo: /config/categorias → editar teto de categoria → save → reload →
 * teto persistido (UI + DB via GET /category-overrides/resolved).
 *
 * Tagged @critical.
 */
import { test, expect } from "@playwright/test";
import { ensureLoggedIn } from "./helpers/auth";

test.describe("Config /categories override round-trip @critical", () => {
  test("editar teto → save → reload → persiste no backend", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);
    await page.goto("/config");

    // CategoriesTab é a primeira tab (default). Espera lista carregar.
    await expect(page.getByText(/despesas/i).first()).toBeVisible({ timeout: 10000 });

    // Pega a primeira linha de categoria visível (test-id estável: category-row-<code>).
    const firstRow = page.locator('[data-testid^="category-row-"]').first();
    await expect(firstRow).toBeVisible();

    // Extrai o code da test-id pra usar no GET final.
    const testId = await firstRow.getAttribute("data-testid");
    const code = testId?.replace(/^category-row-/, "");
    expect(code).toBeTruthy();

    // Clica em "Editar" da primeira linha.
    await firstRow.getByRole("button", { name: "Editar" }).click();

    // Edita o teto mensal — onBlur dispara o PUT.
    const sentinel = 1234.5 + Math.floor(Math.random() * 100);
    const capInput = firstRow.locator('input[type="number"]');
    await capInput.fill(String(sentinel));
    await capInput.blur();

    // Espera UI refletir — badge "Personalizada" deve aparecer eventualmente.
    await expect(firstRow.getByTestId("badge-personalizada")).toBeVisible({
      timeout: 10000,
    });

    // Reload e verifica que o teto persistiu.
    await page.reload();
    const reloadedRow = page.locator(`[data-testid="category-row-${code}"]`);
    await expect(reloadedRow).toBeVisible();
    await expect(reloadedRow.getByTestId("badge-personalizada")).toBeVisible();

    // Confirma persistência via GET direto na API.
    const token = await page.evaluate(() => localStorage.getItem("fin_token"));
    const wsListResp = await request.get("/api/v1/me/workspaces", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const wsList = await wsListResp.json();
    const workspaceId = wsList.workspaces?.[0]?.id;
    expect(workspaceId).toBeTruthy();

    const cfgResp = await request.get(
      `/api/v1/workspaces/${workspaceId}/config/category-overrides/resolved`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(cfgResp.ok()).toBeTruthy();
    const payload = await cfgResp.json();
    const target = payload.categories.find(
      (c: { code: string; monthly_cap: number | null }) => c.code === code,
    );
    expect(target).toBeTruthy();
    expect(target.monthly_cap).toBeCloseTo(sentinel, 0);
  });
});
