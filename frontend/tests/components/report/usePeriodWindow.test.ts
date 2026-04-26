/**
 * v2.E.1 — unit specs do hook `usePeriodWindow`.
 *
 * Cobre: 4 períodos (3m/6m/12m/ytd) com 24 meses + edge cases (vazio,
 * len < window, anchorDate fornecido, formato pt-BR "fev/26").
 */
import { describe, expect, it } from "vitest";
import { renderHook } from "@testing-library/react";

import { usePeriodWindow } from "@/components/report/hooks/usePeriodWindow";

/** 24 labels mensais "YY/MM" — `25/05` (mai/2025) ... `27/04` (abr/2027). */
function build24Labels(): string[] {
  const out: string[] = [];
  let year = 2025;
  let month = 5;
  for (let i = 0; i < 24; i += 1) {
    out.push(`${String(year - 2000).padStart(2, "0")}/${String(month).padStart(2, "0")}`);
    month += 1;
    if (month > 12) {
      month = 1;
      year += 1;
    }
  }
  return out;
}

describe("usePeriodWindow — happy path (24 meses)", () => {
  const labels = build24Labels();

  it("12m retorna últimos 12 meses", () => {
    const { result } = renderHook(() => usePeriodWindow(labels, "12m"));
    expect(result.current.start).toBe(12);
    expect(result.current.end).toBe(24);
    expect(result.current.label).toBe("26/05 — 27/04");
  });

  it("6m retorna últimos 6 meses", () => {
    const { result } = renderHook(() => usePeriodWindow(labels, "6m"));
    expect(result.current.start).toBe(18);
    expect(result.current.end).toBe(24);
    expect(result.current.label).toBe("26/11 — 27/04");
  });

  it("3m retorna últimos 3 meses", () => {
    const { result } = renderHook(() => usePeriodWindow(labels, "3m"));
    expect(result.current.start).toBe(21);
    expect(result.current.end).toBe(24);
    expect(result.current.label).toBe("27/02 — 27/04");
  });

  it("ytd cobre janeiro do ano do último label até o fim", () => {
    // último label = 27/04 → ano referência = 2027 → procura 27/01
    const { result } = renderHook(() => usePeriodWindow(labels, "ytd"));
    expect(result.current.start).toBe(20); // 27/01 está no índice 20
    expect(result.current.end).toBe(24);
    expect(result.current.label).toBe("27/01 — 27/04");
  });
});

describe("usePeriodWindow — edge cases", () => {
  it("allLabels vazio retorna start/end zero e label vazio", () => {
    const { result } = renderHook(() => usePeriodWindow([], "12m"));
    expect(result.current).toEqual({ start: 0, end: 0, label: "" });
  });

  it("len < window (3m) usa toda a janela disponível", () => {
    const labels = ["26/02", "26/03"];
    const { result } = renderHook(() => usePeriodWindow(labels, "3m"));
    expect(result.current.start).toBe(0);
    expect(result.current.end).toBe(2);
    expect(result.current.label).toBe("26/02 — 26/03");
  });

  it("len < window (6m) usa toda a janela disponível", () => {
    const labels = ["26/01", "26/02", "26/03"];
    const { result } = renderHook(() => usePeriodWindow(labels, "6m"));
    expect(result.current.start).toBe(0);
    expect(result.current.end).toBe(3);
  });

  it("anchorDate fornecido força ano de referência para YTD", () => {
    // labels cobrem 2 anos; anchor em 2026 → cobre 26/01..26/12 só do ano 2026
    const labels = build24Labels(); // 25/05 .. 27/04
    const anchor = new Date("2026-06-15T00:00:00Z");
    const { result } = renderHook(() => usePeriodWindow(labels, "ytd", anchor));
    // 26/01 está no índice 8 (25/05..25/12 = 8 meses, depois 26/01 em 8)
    expect(result.current.start).toBe(8);
    expect(result.current.end).toBe(24);
    expect(result.current.label).toBe("26/01 — 27/04");
  });

  it("label de range com 1 mês retorna apenas esse label", () => {
    const labels = ["26/04"];
    const { result } = renderHook(() => usePeriodWindow(labels, "3m"));
    expect(result.current.label).toBe("26/04");
  });

  it("aceita formato pt-BR 'mes/aa' (ex.: 'fev/26')", () => {
    const labels = ["jan/26", "fev/26", "mar/26", "abr/26"];
    const { result } = renderHook(() => usePeriodWindow(labels, "ytd"));
    // ytd: ano de ref = 2026 (último label) → procura jan/26 → start 0
    expect(result.current.start).toBe(0);
    expect(result.current.end).toBe(4);
    expect(result.current.label).toBe("jan/26 — abr/26");
  });
});
