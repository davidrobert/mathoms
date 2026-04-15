/**
 * Visual regression — F6.5D.3
 *
 * Snapshots versionados em tests/e2e/__snapshots__/ (1 baseline por teste).
 * Regenerar: npx playwright test --update-snapshots
 *
 * Cobertura planejada (ver ADR-063):
 * - 4 charts Recharts (bar, pie, line, donut) em dark/light
 * - 3 KPI states (positive delta, negative delta, loading)
 * - Print preview do report viewer
 * - AppShell mobile (360px width)
 *
 * Infra criada AQUI (spec scaffold). Baseline real capturada quando CI
 * subir (primeiro run cria snapshots; CI subsequentes diffam contra).
 *
 * Gate: zero diffs não-aprovados em PR → CI falha.
 */
import { test, expect } from "@playwright/test";
import { ensureLoggedIn } from "./helpers/auth";

test.describe("Visual regression — compostos e pages", () => {
  test("login page @visual", async ({ page }) => {
    await page.goto("/login");
    await expect(page).toHaveScreenshot("login-page.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.01,
    });
  });

  test("register page @visual", async ({ page }) => {
    await page.goto("/register");
    await expect(page).toHaveScreenshot("register-page.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.01,
    });
  });

  test("login page dark mode @visual", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto("/login");
    await expect(page).toHaveScreenshot("login-page-dark.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.01,
    });
  });

  test("AppShell mobile 360px @visual", async ({ page, request }, info) => {
    await ensureLoggedIn(page, request, info);
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/dashboard");
    // Aguarda dashboard carregar (Pipeline não rodou — vai mostrar empty)
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot("appshell-mobile-360.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.02, // mobile tem mais variação
    });
  });

  test("empty state documents @visual", async ({ page, request }, info) => {
    await ensureLoggedIn(page, request, info);
    await page.goto("/documents");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot("documents-empty.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.01,
    });
  });
});
