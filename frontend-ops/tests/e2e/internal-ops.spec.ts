import { test, expect } from "@playwright/test";

/**
 * F7F-Local Slice 3 — smoke `@internal-ops` (1 test por área).
 *
 * Pré-requisito: backend up em 127.0.0.1:8000 com flag
 * MATHOMS_INTERNAL_OPS_UI_ENABLED=1, operator YAML seeded com username/password
 * em `PW_OPS_USERNAME`/`PW_OPS_PASSWORD`, e 1 user fixture (`PW_FIXTURE_USER_ID`)
 * via `scripts/seed_internal_ops_smoke.py`.
 */

const OPS_USERNAME = process.env.PW_OPS_USERNAME ?? "superadmin";
const OPS_PASSWORD = process.env.PW_OPS_PASSWORD ?? "super-admin-pw!";

async function login(page: import("@playwright/test").Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/usu[aá]rio|username/i).fill(OPS_USERNAME);
  await page.getByLabel(/senha|password/i).fill(OPS_PASSWORD);
  await page.getByRole("button", { name: /entrar|login/i }).click();
  await page.waitForURL(/\/users/);
}

test.describe("@internal-ops", () => {
  test("login: credenciais inválidas exibem erro", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/usu[aá]rio|username/i).fill(OPS_USERNAME);
    await page.getByLabel(/senha|password/i).fill("wrong-password-xxx");
    await page.getByRole("button", { name: /entrar|login/i }).click();
    await expect(page.getByText(/401|inv[aá]lido|erro/i)).toBeVisible();
  });

  test("login: credenciais válidas redireciona para /users", async ({ page }) => {
    await login(page);
    await expect(page).toHaveURL(/\/users/);
    await expect(page.getByRole("heading", { name: /usu[aá]rios/i })).toBeVisible();
  });

  test("users: lista renderiza sem erro", async ({ page }) => {
    await login(page);
    await expect(page.getByRole("heading", { name: /usu[aá]rios/i })).toBeVisible();
    await expect(page.getByText(/total/i)).toBeVisible();
  });

  test("documents: preview purge retorna sem erro", async ({ page }) => {
    await login(page);
    await page.goto("/documents");
    await expect(page.getByRole("heading", { name: /documentos/i })).toBeVisible();
    const userId = process.env.PW_FIXTURE_USER_ID;
    if (!userId) test.skip(true, "PW_FIXTURE_USER_ID não setado");
    await page.getByPlaceholder(/UUID do usu[aá]rio/i).fill(userId as string);
    await page.getByRole("button", { name: /pr[eé]via/i }).click();
    await expect(page.getByText(/documento\(s\)/i)).toBeVisible();
  });

  test("metrics: carrega cards e troca período", async ({ page }) => {
    await login(page);
    await page.goto("/metrics");
    await expect(page.getByRole("heading", { name: /m[eé]tricas/i })).toBeVisible();
    await expect(page.getByText(/Usu[aá]rios \(total\)/i)).toBeVisible();
    await page.getByRole("button", { name: "7d" }).click();
    await expect(page.getByText(/Gerado em/i)).toBeVisible();
  });

  test("reports: lista renderiza (pode estar vazia)", async ({ page }) => {
    await login(page);
    await page.goto("/reports");
    await expect(page.getByRole("heading", { name: /relat[oó]rios/i })).toBeVisible();
    await expect(page.getByText(/resultado\(s\)/i)).toBeVisible();
  });
});
