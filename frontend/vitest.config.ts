/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

/**
 * Vitest config — F6.5 Testing & Hardening (sub-fase 6.5A.1)
 *
 * - jsdom environment (DOM APIs em Node)
 * - React plugin (suporte a JSX/TSX + Fast Refresh em watch)
 * - Path alias `@/*` espelhado de tsconfig.json
 * - Coverage v8 com thresholds gradativos por sub-fase:
 *   - lib/: 80% line / 70% branch (target final F6.5 — ADR-067)
 *   - components/: 70% line / 60% branch
 *   - app/: 70% line / 60% branch
 * - tests/: ignorado para não inflar cobertura
 *
 * Convenções:
 * - Tests vivem em `frontend/tests/` (não colocados side-by-side com source)
 * - Setup global em `tests/setup.ts` (jest-dom matchers, MSW server lifecycle)
 * - Mocks reusáveis em `tests/mocks/` (MSW handlers + fixtures)
 * - Factories em `tests/factories/` (data builders type-safe)
 *
 * Comando: `npm test` (alias para `vitest run`)
 *          `npm run test:watch` (modo dev)
 *          `npm run test:coverage` (gera relatório HTML em coverage/)
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    environmentOptions: {
      jsdom: {
        // URL real é necessária para localStorage/sessionStorage funcionarem
        // em jsdom (Storage é per-origin; sem URL, o origin é "null" e jsdom
        // retorna um stub não-funcional).
        url: "http://localhost:3000/",
      },
    },
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    css: true,
    include: ["tests/**/*.{test,spec}.{ts,tsx}"],
    exclude: [
      "node_modules",
      ".next",
      "tests/e2e/**", // E2E roda via Playwright, não Vitest
    ],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "json-summary", "lcov"],
      reportsDirectory: "./coverage",
      exclude: [
        "node_modules/",
        ".next/",
        "tests/",
        "**/*.config.{ts,js,mjs}",
        "**/*.d.ts",
        "src/app/layout.tsx", // Server Component shell, sem lógica testável
        "next-env.d.ts",
      ],
      // Thresholds globais (soft em sub-fase 6.5A; hard em 6.5C após integração FE completa)
      thresholds: {
        lines: 60,
        functions: 60,
        branches: 50,
        statements: 60,
        // Per-glob (mais restrito em lib/ — código puro, alvo de unit tests)
        "src/lib/**/*.ts": {
          lines: 80,
          functions: 80,
          branches: 70,
          statements: 80,
        },
      },
    },
    // Reporters
    reporters: process.env.CI ? ["default", "junit"] : ["default"],
    outputFile: {
      junit: "./coverage/junit.xml",
    },
    // Performance
    pool: "threads",
    poolOptions: {
      threads: {
        singleThread: false,
      },
    },
    // Timeouts conservadores (unit deve ser rápido)
    testTimeout: 10_000,
    hookTimeout: 10_000,
  },
});
