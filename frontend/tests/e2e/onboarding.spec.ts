/**
 * F6.5C.2 — Onboarding completo (Fluxo 1)
 *
 * Cobre registro → login → primeiro uso, com variações:
 * - Happy path (registro fresh → primeira página)
 * - Email duplicado → erro user-friendly
 * - Password fraca (<6 chars) → HTML5 validation bloqueia submit
 *
 * Tagged @critical para cross-browser.
 */
import { test, expect } from "@playwright/test";

const STAMP = Date.now();

test.describe("Onboarding @critical", () => {
  test("happy path: registro → login automático → /plano", async ({ page }) => {
    const email = `onboarding-${STAMP}@test.com`;
    await page.goto("/register");

    await page.getByLabel(/seu nome/i).fill("Novo User");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/senha/i).fill("SenhaForte123!");
    await page.getByRole("button", { name: /criar conta/i }).click();

    // Default pós-login é /plano (ver lib/nextUrl.ts)
    await expect(page).toHaveURL(/\/plano/, { timeout: 10_000 });
    await expect(
      page.getByRole("heading", { name: "Meu Plano" }),
    ).toBeVisible();
  });

  test("email duplicado mostra mensagem clara", async ({ page, request }) => {
    const email = `dup-${STAMP}@test.com`;

    // Pré-registra o email via API
    await request.post("/api/v1/auth/register", {
      data: { email, password: "pre123abc", full_name: "Pre User" },
    });

    await page.goto("/register");
    await page.getByLabel(/seu nome/i).fill("Segundo Tentativa");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/senha/i).fill("senha456def");
    await page.getByRole("button", { name: /criar conta/i }).click();

    // Mensagem user-friendly (não "HTTP 409")
    await expect(page.getByText(/já está cadastrado/i)).toBeVisible({
      timeout: 5_000,
    });
  });

  test("senha curta: HTML5 minLength=6 bloqueia submit", async ({ page }) => {
    await page.goto("/register");
    await page.getByLabel(/seu nome/i).fill("X");
    await page.getByLabel(/email/i).fill(`short-${STAMP}@test.com`);
    await page.getByLabel(/senha/i).fill("abc"); // 3 chars
    await page.getByRole("button", { name: /criar conta/i }).click();

    // Continua em /register (browser bloqueou via minLength)
    await expect(page).toHaveURL(/\/register/);
    // Input inválido tem :invalid CSS pseudo
    const pw = page.getByLabel(/senha/i);
    const isInvalid = await pw.evaluate((el: HTMLInputElement) => !el.validity.valid);
    expect(isInvalid).toBe(true);
  });

  test("link Entrar leva para /login", async ({ page }) => {
    await page.goto("/register");
    await page.getByRole("link", { name: /entrar/i }).click();
    await expect(page).toHaveURL(/\/login/);
  });

  test("login com credenciais erradas mostra mensagem amigável", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email/i).fill(`inexistente-${STAMP}@test.com`);
    await page.getByLabel(/senha/i).fill("qualquer123");
    await page.getByRole("button", { name: /entrar/i }).click();
    await expect(page.getByText(/email ou senha incorretos/i)).toBeVisible({
      timeout: 5_000,
    });
  });
});
