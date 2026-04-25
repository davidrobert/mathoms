import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/**
 * Helper de a11y para Playwright — Lane `report-a11y-finalize`.
 *
 * Decisão D1 do track: gate em `critical+serious`. `moderate` fica fora
 * para evitar falsos-positivos de contraste-AA-borderline em estados de
 * hover dependentes de tokens.
 */

export type AxeSeverity = "critical" | "serious" | "moderate" | "minor";

const DEFAULT_SEVERITIES: AxeSeverity[] = ["critical", "serious"];

interface ExpectNoA11yViolationsOpts {
  /** Seletor CSS para escopo do scan; default = página inteira. */
  selector?: string;
  /** Severidades que falham o teste. Default `critical+serious` (D1). */
  severities?: AxeSeverity[];
  /** Regras axe a desabilitar (use para falsos-positivos conhecidos com link de issue). */
  disabledRules?: string[];
}

/**
 * Roda axe-core e asserta zero violações nas severidades configuradas.
 * Mensagem de erro inclui regra + nó ofensor + URL de help do axe.
 */
export async function expectNoA11yViolations(
  page: Page,
  opts: ExpectNoA11yViolationsOpts = {},
): Promise<void> {
  const severities = opts.severities ?? DEFAULT_SEVERITIES;
  let builder = new AxeBuilder({ page }).withTags([
    "wcag2a",
    "wcag2aa",
    "wcag21a",
    "wcag21aa",
  ]);
  if (opts.selector) {
    builder = builder.include(opts.selector);
  }
  if (opts.disabledRules?.length) {
    builder = builder.disableRules(opts.disabledRules);
  }

  const results = await builder.analyze();
  const offending = results.violations.filter((v) =>
    severities.includes(v.impact as AxeSeverity),
  );

  if (offending.length > 0) {
    const formatted = offending
      .map((v) => {
        const nodes = v.nodes
          .slice(0, 3)
          .map((n) => `    - ${n.target.join(" > ")}`)
          .join("\n");
        return `  · [${v.impact}] ${v.id}: ${v.description}\n    help: ${v.helpUrl}\n${nodes}`;
      })
      .join("\n\n");
    expect(
      offending,
      `axe-core encontrou ${offending.length} violação(ões) em ${
        opts.selector ?? "página"
      }:\n${formatted}`,
    ).toEqual([]);
  }
}
