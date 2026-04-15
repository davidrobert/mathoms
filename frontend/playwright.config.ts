import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — F6.5 (sub-fase 6.5C.1)
 *
 * Cobertura cross-browser conforme ADR-063:
 * - chromium (default, paridade com prod Chrome+Edge)
 * - firefox (Gecko quirks, ~5% market share BR)
 * - webkit (Safari iOS — críitco para mobile no BR)
 *
 * Fluxos críticos rodam em todos os 3 browsers (6.5D.4); demais só chromium.
 *
 * Backend real: webServer abaixo sobe Next em 3000 e assume backend rodando
 * em 127.0.0.1:8000 (rewrite de /api/* em next.config.ts). Para CI, ver
 * 6.5F.3 (`docker-compose.test.yml` + `scripts/test_backend_up.sh`).
 *
 * Workspace isolation: 6.5F.6 — cada worker tem seu user via
 * `worker-${workerInfo.parallelIndex}@test.com` no auth helper.
 *
 * Flaky policy (6.5F.8): retries=2 em CI, 0 em local. Quarentena via
 * `test.skip(true, "flaky: TODO BUG-XXX")`.
 *
 * Artifacts (6.5F.9): vídeo + trace on-failure, retention via GitHub Actions.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI
    ? [["html", { open: "never" }], ["junit", { outputFile: "playwright-results/junit.xml" }], ["github"]]
    : [["html", { open: "never" }], ["list"]],
  outputDir: "./playwright-results/output",

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
      // 6.5D.4: roda subconjunto crítico (filtrado por @critical tag)
      grep: process.env.PW_CROSS_BROWSER ? undefined : /@critical/,
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
      grep: process.env.PW_CROSS_BROWSER ? undefined : /@critical/,
    },
    // Visual regression isolado (snapshots dependentes de OS/font rendering)
    {
      name: "visual",
      testMatch: /.*\.visual\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        // Tolerância pequena para anti-aliasing entre máquinas;
        // CI deve regenerar snapshots em job dedicado se desviarem.
      },
    },
  ],

  webServer: process.env.PLAYWRIGHT_SKIP_WEB_SERVER
    ? undefined
    : {
        command: "npm run dev",
        url: "http://127.0.0.1:3000",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
        stdout: "pipe",
        stderr: "pipe",
      },

  expect: {
    timeout: 5_000,
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01, // 1% tolerância (anti-aliasing)
      animations: "disabled",
    },
  },
});
