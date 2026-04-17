import { describe, expect, it } from "vitest";
import { REPORT_FORMULA_CATALOG } from "@/lib/reportFormulas";

describe("REPORT_FORMULA_CATALOG (F11.7c smoke)", () => {
  it("tem entradas com id e resumo", () => {
    expect(REPORT_FORMULA_CATALOG.length).toBeGreaterThanOrEqual(1);
    for (const e of REPORT_FORMULA_CATALOG) {
      expect(e.id.length).toBeGreaterThan(0);
      expect(e.title.length).toBeGreaterThan(0);
      expect(e.summary.length).toBeGreaterThan(10);
    }
  });
});
