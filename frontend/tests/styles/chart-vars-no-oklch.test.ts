/**
 * Anti-regressão: --chart-N não pode ser oklch/oklab/lab/lch.
 *
 * Why: Chart.js usa @kurkle/color, que parseia apenas hex/rgb/hsl. Se
 * `--chart-N` for definido em oklch(), `getComputedStyle().getPropertyValue`
 * devolve a string literal `oklch(...)`, o parser falha silenciosamente
 * e `ctx.fillStyle` cai para preto — exatamente o bug fechado em
 * `de2c00a` (2026-04-27, barras pretas no Receita vs Despesa Mensal).
 *
 * O teste vizinho em `tests/components/report/ReceitaDespesaMensalChart.test.tsx`
 * só valida que o dataset não usa literal `var(...)`; em jsdom o
 * `useChartTheme` cai para `LIGHT_FALLBACK` (hex hard-coded), então
 * regressão na CSS escapa. Este lint scan é o gate.
 */
import { readFileSync } from "node:fs";
import { readdirSync, statSync } from "node:fs";
import path from "node:path";
import { describe, it, expect } from "vitest";

const SRC_ROOT = path.resolve(__dirname, "../../src");

function findCssFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    const s = statSync(full);
    if (s.isDirectory()) {
      out.push(...findCssFiles(full));
    } else if (s.isFile() && entry.endsWith(".css")) {
      out.push(full);
    }
  }
  return out;
}

const FORBIDDEN_FN_RE =
  /--chart-\d+\s*:\s*(oklch|oklab|lab|lch)\s*\(/gi;

describe("CSS lint · --chart-N não pode ser oklch/oklab/lab/lch", () => {
  const cssFiles = findCssFiles(SRC_ROOT);

  it("encontra ao menos um arquivo CSS para varrer (sanity)", () => {
    expect(cssFiles.length).toBeGreaterThan(0);
  });

  for (const file of cssFiles) {
    const rel = path.relative(SRC_ROOT, file);
    it(`${rel} não define --chart-N com função de cor incompatível`, () => {
      const content = readFileSync(file, "utf8");
      const matches = [...content.matchAll(FORBIDDEN_FN_RE)];
      if (matches.length > 0) {
        const offenders = matches
          .map((m) => {
            const upTo = content.slice(0, m.index ?? 0);
            const line = upTo.split("\n").length;
            return `  ${rel}:${line} → ${m[0]}…`;
          })
          .join("\n");
        throw new Error(
          `--chart-N definido com ${matches[0][1]}() — Chart.js (@kurkle/color) não parseia esse formato e cai para preto.\n` +
            `Use hex (#1A3A5C), rgb() ou hsl(). Bug histórico: de2c00a (2026-04-27).\n` +
            offenders,
        );
      }
      expect(matches.length).toBe(0);
    });
  }
});
