import { describe, expect, it } from "vitest";

import {
  getPeriodDates,
  getPeriodMonths,
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
