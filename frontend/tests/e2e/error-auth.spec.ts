/**
 * F6.5C.8 — Error handling e auth redirect (Fluxo 7)
 *
 * - Acesso a /(app)/* sem token → redirect /login
 * - Token inválido / expirado → redirect /login + token limpo
 * - 404 rota inexistente → Next.js default 404 page
 *
 * Tagged @critical.
 */
import { test, expect } from "@playwright/test";

test.describe("Error handling + auth redirect @critical", () => {
  test("sem token: /dashboard redireciona para /login", async ({ page }) => {
    await page.goto("/dashboard");
    // AppShell detecta ausência/invalidez → clearToken + router.replace("/login")
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
  });

  test("sem token: /vault redireciona para /login", async ({ page }) => {
    await page.goto("/vault");
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
  });

  test("token inválido: getMe 401 → clearToken + redirect", async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("fin_token", "token-invalido-xyz");
    });
    await page.goto("/documents");

    // AppShell chama getMe → 401 → clearToken + replace /login
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });

    // Token foi removido
    const tokenAfter = await page.evaluate(() => localStorage.getItem("fin_token"));
    expect(tokenAfter).toBeNull();
  });

  test("rota inexistente /(app)/xyz mostra 404", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    // Next.js default 404 page
    await expect(page.getByText(/404|not found|esta página não existe/i)).toBeVisible(
      { timeout: 10_000 },
    );
  });

  test("/login sempre acessível mesmo com token inválido", async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("fin_token", "invalid");
    });
    await page.goto("/login");
    await expect(page.getByText(/Entrar/).first()).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });
});
