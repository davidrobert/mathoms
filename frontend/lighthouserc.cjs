/**
 * Lighthouse CI config — Lane `report-a11y-finalize` item 4.
 *
 * Decisão D2 do track:
 * - PR-time, fixture `medium` (não percorre o app inteiro).
 * - 3 runs para reduzir variância (default lhci).
 * - Thresholds: perf 0.85 / a11y 0.95 / best-practices 0.95 / seo 0.90 (warn).
 *
 * Setup:
 * - `tests/lighthouse/lighthouse-mock.cjs` injeta token + intercepta
 *   `/api/v1/**` com fixture sintética. Sem backend real.
 * - `npm run dev` (Next dev) já é assumido rodando em :3000 — no CI o
 *   workflow sobe ele explicitamente.
 *
 * `npm run lhci` localmente (Next dev em :3000); `npm run lhci:ci` em CI.
 */
module.exports = {
  ci: {
    collect: {
      url: ["http://127.0.0.1:3000/reports/report-fixture-medium?workspace=ws-fixture"],
      numberOfRuns: 3,
      puppeteerScript: "./tests/lighthouse/lighthouse-mock.cjs",
      // Em CI (ubuntu-24.04 + setup-chrome via /opt/hostedtoolcache) o
      // chrome-sandbox não tem owner=root mode=4755 e o launch aborta.
      // --no-sandbox é seguro neste contexto: rodamos contra fixture
      // sintética em loopback, sem código não-confiável.
      puppeteerLaunchOptions: {
        args: ["--no-sandbox", "--disable-dev-shm-usage"],
      },
      settings: {
        preset: "desktop",
        // next-themes monta async; aguarda mais tempo p/ paint estabilizar.
        maxWaitForLoad: 45000,
        chromeFlags: "--no-sandbox --disable-dev-shm-usage",
      },
    },
    assert: {
      assertions: {
        "categories:performance":    ["error", { minScore: 0.85 }],
        "categories:accessibility":  ["error", { minScore: 0.95 }],
        "categories:best-practices": ["error", { minScore: 0.95 }],
        "categories:seo":            ["warn",  { minScore: 0.90 }],
      },
    },
    upload: {
      target: "temporary-public-storage",
    },
  },
};
