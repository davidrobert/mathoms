import { describe, expect, it } from "vitest";

import type { TransactionItem } from "@/lib/api";
import {
  aggregateDespesasMediaMensal,
  aggregateReceitas,
  getPeriodDates,
  getPeriodMonths,
  isIncomeCategory,
  parseChartMonthLabel,
} from "@/lib/periodUtils";

describe("parseChartMonthLabel", () => {
  it("parses YY/MM numeric format", () => {
    const d = parseChartMonthLabel("26/04");
    expect(d?.getFullYear()).toBe(2026);
    expect(d?.getMonth()).toBe(3); // April (0-indexed)
    expect(d?.getDate()).toBe(30); // last day of April
  });

  it("parses pt-BR named month format", () => {
    const d = parseChartMonthLabel("fev/26");
    expect(d?.getFullYear()).toBe(2026);
    expect(d?.getMonth()).toBe(1); // February
    expect(d?.getDate()).toBe(28); // last day of Feb 2026 (non-leap)
  });

  it("returns last day of month with leap year", () => {
    const d = parseChartMonthLabel("24/02");
    expect(d?.getDate()).toBe(29); // 2024 is leap
  });

  it("returns null for invalid month", () => {
    expect(parseChartMonthLabel("26/13")).toBeNull();
    expect(parseChartMonthLabel("26/00")).toBeNull();
  });

  it("returns null for malformed input", () => {
    expect(parseChartMonthLabel("")).toBeNull();
    expect(parseChartMonthLabel("abril/2026")).toBeNull();
    expect(parseChartMonthLabel("xyz/26")).toBeNull();
  });
});

describe("getPeriodDates with anchorDate", () => {
  const anchor = new Date(2026, 3, 30); // April 30, 2026

  it("anchors date_to to provided date for 3M", () => {
    const { date_from, date_to } = getPeriodDates("3m", anchor);
    expect(date_to).toBe("2026-04-30");
    expect(date_from).toBe("2026-01-30");
  });

  it("anchors date_to for 6M", () => {
    const { date_from, date_to } = getPeriodDates("6m", anchor);
    expect(date_to).toBe("2026-04-30");
    expect(date_from).toBe("2025-10-30");
  });

  it("anchors date_to for 12M", () => {
    const { date_from, date_to } = getPeriodDates("12m", anchor);
    expect(date_to).toBe("2026-04-30");
    expect(date_from).toBe("2025-04-30");
  });

  it("anchors YTD to anchor's year, not today's year", () => {
    const oldAnchor = new Date(2024, 5, 15); // June 15, 2024
    const { date_from, date_to } = getPeriodDates("ytd", oldAnchor);
    expect(date_from).toBe("2024-01-01");
    expect(date_to).toBe("2024-06-15");
  });

  it("falls back to today when anchor is omitted", () => {
    const { date_to } = getPeriodDates("3m");
    const today = new Date().toISOString().split("T")[0];
    expect(date_to).toBe(today);
  });
});

describe("getPeriodMonths with anchorDate", () => {
  it("returns fixed counts for 3M/6M/12M regardless of anchor", () => {
    const anchor = new Date(2024, 5, 1);
    expect(getPeriodMonths("3m", anchor)).toBe(3);
    expect(getPeriodMonths("6m", anchor)).toBe(6);
    expect(getPeriodMonths("12m", anchor)).toBe(12);
  });

  it("YTD count uses anchor's month index, not today's", () => {
    expect(getPeriodMonths("ytd", new Date(2024, 0, 1))).toBe(1); // Jan
    expect(getPeriodMonths("ytd", new Date(2024, 5, 1))).toBe(6); // Jun
    expect(getPeriodMonths("ytd", new Date(2024, 11, 1))).toBe(12); // Dec
  });
});

describe("isIncomeCategory", () => {
  it("matches receita_ prefix and outras_receitas", () => {
    expect(isIncomeCategory("receita_clt")).toBe(true);
    expect(isIncomeCategory("receita_aluguel")).toBe(true);
    expect(isIncomeCategory("outras_receitas")).toBe(true);
  });

  it("matches PJ income labels from transaction_classifier_pj (ADR-236)", () => {
    expect(isIncomeCategory("pro_labore")).toBe(true);
    expect(isIncomeCategory("lucros_distribuidos")).toBe(true);
  });

  it("does not match PJ expense labels", () => {
    expect(isIncomeCategory("das_simples")).toBe(false);
    expect(isIncomeCategory("iss")).toBe(false);
    expect(isIncomeCategory("folha_pj")).toBe(false);
  });

  it("does not match regular expense categories", () => {
    expect(isIncomeCategory("alimentacao")).toBe(false);
    expect(isIncomeCategory("moradia")).toBe(false);
    expect(isIncomeCategory("nao_identificado")).toBe(false);
  });
});

const mkTx = (categoria: string, valor: number): TransactionItem =>
  ({
    categoria,
    valor,
  }) as TransactionItem;

describe("aggregateDespesasMediaMensal", () => {
  it("does not leak PJ income labels into expenses (regression: lucros_distribuidos in Orçamento Prospectivo)", () => {
    const txs = [
      mkTx("alimentacao", 1500),
      mkTx("lucros_distribuidos", 20000),
      mkTx("pro_labore", 8000),
      mkTx("das_simples", 600),
    ];
    const out = aggregateDespesasMediaMensal(txs, 3);
    expect(out).not.toHaveProperty("lucros_distribuidos");
    expect(out).not.toHaveProperty("pro_labore");
    expect(out.alimentacao).toBe(500); // 1500 / 3
    expect(out.das_simples).toBe(200); // 600 / 3 — PJ expense fica
  });
});

describe("aggregateReceitas", () => {
  it("includes PJ income labels (pro_labore, lucros_distribuidos)", () => {
    const txs = [
      mkTx("receita_clt", 10000),
      mkTx("pro_labore", 8000),
      mkTx("lucros_distribuidos", 20000),
      mkTx("alimentacao", 1500), // despesa, ignorada
    ];
    const out = aggregateReceitas(txs);
    expect(out.receita_clt).toBe(10000);
    expect(out.pro_labore).toBe(8000);
    expect(out.lucros_distribuidos).toBe(20000);
    expect(out).not.toHaveProperty("alimentacao");
  });
});
