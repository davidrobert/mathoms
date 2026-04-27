/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

/**
 * Vitest config opt-in para tests `.slow.test.tsx` excluídos do glob default.
 *
 * Uso:
 *
 *   npm run test:slow                            # roda todos os slow tests (pode travar)
 *   npm run test:slow -- -t "tooltip helpers"    # roda subset isolado
 *
 * Por que tests `.slow` existem: alguns describes têm hang conhecido em
 * jsdom quando rodados combinados (interação entre `vi.mock` hoisted,
 * `userEvent.setup` e refs de mock-instance). O fix definitivo está em
 * lane follow-up; até lá, este config permite executar isoladamente
 * sem afetar o CI Frontend Vitest.
 *
 * Espelha a base de [vitest.config.ts](./vitest.config.ts) explicitamente
 * em vez de `mergeConfig` porque `mergeConfig` apende `include` em vez
 * de substituir.
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
        url: "http://localhost:3000/",
      },
    },
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    css: true,
    include: ["tests/**/*.slow.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules", ".next", "tests/e2e/**"],
  },
});
