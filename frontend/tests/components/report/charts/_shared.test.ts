import { describe, expect, it } from "vitest";

import { formatChartMonthLabel } from "@/components/report/charts/_shared";

describe("formatChartMonthLabel()", () => {
  it("converte yy/mm canônico para MMM/aa pt-BR", () => {
    expect(formatChartMonthLabel("26/02")).toBe("fev/26");
    expect(formatChartMonthLabel("25/01")).toBe("jan/25");
    expect(formatChartMonthLabel("24/12")).toBe("dez/24");
  });

  it("retorna input cru quando formato não casa yy/mm", () => {
    expect(formatChartMonthLabel("2026-02")).toBe("2026-02");
    expect(formatChartMonthLabel("Q1 2026")).toBe("Q1 2026");
    expect(formatChartMonthLabel("")).toBe("");
  });

  it("retorna input cru quando mês fora de 01-12", () => {
    expect(formatChartMonthLabel("26/00")).toBe("26/00");
    expect(formatChartMonthLabel("26/13")).toBe("26/13");
  });
});
