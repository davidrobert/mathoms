import type { APIRequestContext, Page, TestInfo } from "@playwright/test";

/**
 * Auth helper para E2E — F6.5 (sub-fase 6.5C.1)
 *
 * Strategy de workspace isolation por worker (6.5F.6):
 * - Cada Playwright worker tem `parallelIndex` único (0..workers-1).
 * - Email gerado: `e2e-w${index}-${stamp}@test.com` (stamp = run timestamp).
 * - Garante que workers paralelos NUNCA colidam em registro.
 *
 * Uso típico em E2E:
 *   import { test, expect } from "@playwright/test";
 *   import { ensureLoggedIn } from "../helpers/auth";
 *
 *   test("dashboard mostra KPIs", async ({ page, request }, info) => {
 *     await ensureLoggedIn(page, request, info);
 *     await page.goto("/dashboard");
 *     await expect(page.getByText("Saldo")).toBeVisible();
 *   });
 */

const STAMP = process.env.PW_RUN_STAMP ?? String(Date.now());

export interface E2EUser {
  email: string;
  password: string;
  full_name: string;
}

export function userForWorker(info: TestInfo): E2EUser {
  const idx = info.parallelIndex;
  return {
    email: `e2e-w${idx}-${STAMP}@test.com`,
    password: "TestPass123!",
    full_name: `E2E Worker ${idx}`,
  };
}

/** Registra o user (ignora se já existe) e retorna access_token. */
async function registerOrLogin(
  request: APIRequestContext,
  user: E2EUser,
): Promise<string> {
  const reg = await request.post("/api/v1/auth/register", {
    data: {
      email: user.email,
      password: user.password,
      full_name: user.full_name,
    },
    failOnStatusCode: false,
  });
  if (reg.ok()) {
    return (await reg.json()).access_token as string;
  }

  // Já existe (registro bate 400/409 dependendo da API) → faz login.
  const login = await request.post("/api/v1/auth/login", {
    data: { email: user.email, password: user.password },
  });
  if (!login.ok()) {
    const body = await login.text();
    throw new Error(`Login falhou para ${user.email}: ${login.status()} ${body}`);
  }
  return (await login.json()).access_token as string;
}

/**
 * Garante user autenticado: registra (ou faz login se já existe) e injeta o
 * token em localStorage da Page. Após chamar, navegação para `/(app)/...` é
 * passada pelo auth gate.
 */
export async function ensureLoggedIn(
  page: Page,
  request: APIRequestContext,
  info: TestInfo,
): Promise<E2EUser> {
  const user = userForWorker(info);
  const token = await registerOrLogin(request, user);

  // injeta token antes de qualquer JS de produção rodar
  await page.addInitScript((t) => {
    localStorage.setItem("fin_token", t);
  }, token);

  return user;
}
