import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — F7F-Local Slice 3 (`@internal-ops`).
 *
 * Backend precisa estar up em 127.0.0.1:8000 com:
 *   - MATHOMS_INTERNAL_OPS_UI_ENABLED=1
 *   - MATHOMS_INTERNAL_OPS_SESSION_SECRET=<distinto-do-SECRET_KEY>
 *   - config/internal_operators.yaml com operator de teste
 * Next-ops sobe via `webServer` em 127.0.0.1:3100.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: "./playwright-results/output",

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3100",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],

  webServer: {
    command: "npm run start -- --port 3100 --hostname 127.0.0.1",
    url: "http://127.0.0.1:3100/login",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
