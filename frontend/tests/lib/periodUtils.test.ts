import { describe, expect, it } from "vitest";

import { parseChartMonthLabel, resolveAnchorDate } from "@/lib/periodUtils";

describe("parseChartMonthLabel", () => {
  it("parseia o formato numérico YY/MM", () => {
    const date = parseChartMonthLabel("26/04");
    expect(date?.getFullYear()).toBe(2026);
    expect(date?.getMonth()).toBe(3);
    expect(date?.getDate()).toBe(30);
  });

  it("parseia o formato de mês pt-BR", () => {
    const date = parseChartMonthLabel("fev/26");
    expect(date?.getFullYear()).toBe(2026);
    expect(date?.getMonth()).toBe(1);
    expect(date?.getDate()).toBe(28);
  });

  it("preserva o último dia em ano bissexto", () => {
    expect(parseChartMonthLabel("24/02")?.getDate()).toBe(29);
  });

  it("rejeita mês inválido e input malformado", () => {
    expect(parseChartMonthLabel("26/13")).toBeNull();
    expect(parseChartMonthLabel("26/00")).toBeNull();
    expect(parseChartMonthLabel("")).toBeNull();
    expect(parseChartMonthLabel("abril/2026")).toBeNull();
    expect(parseChartMonthLabel("xyz/26")).toBeNull();
  });
});

describe("resolveAnchorDate", () => {
  it("usa data_corte quando a série chega até o mês do corte", () => {
    const date = resolveAnchorDate(["26/07", "26/08"], "2026-08-11");
    expect(date?.getFullYear()).toBe(2026);
    expect(date?.getMonth()).toBe(7);
    expect(date?.getDate()).toBe(11);
  });

  it("mantém o último label quando ele é anterior ao corte", () => {
    const date = resolveAnchorDate(["26/05", "26/06"], "2026-08-11");
    expect(date?.getMonth()).toBe(5);
    expect(date?.getDate()).toBe(30);
  });

  it("corta label posterior ao corte", () => {
    const date = resolveAnchorDate(["26/07", "26/09"], "2026-08-11");
    expect(date?.getMonth()).toBe(7);
    expect(date?.getDate()).toBe(11);
  });

  it("cai no último label quando não há data_corte", () => {
    expect(resolveAnchorDate(["26/07", "26/09"], undefined)?.getMonth()).toBe(
      8,
    );
  });

  it("devolve undefined sem labels e sem corte", () => {
    expect(resolveAnchorDate(undefined, undefined)).toBeUndefined();
    expect(resolveAnchorDate([], undefined)).toBeUndefined();
  });

  it("usa data_corte mesmo sem labels", () => {
    expect(resolveAnchorDate([], "2026-08-11")?.getDate()).toBe(11);
  });
});
