/**
 * ADR-119 item 6 — heartbeat por-stage.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useRef } from "react";

import { useStageStall } from "@/app/(app)/pipeline/_components/useStageStall";
import type { PipelineStageActivity } from "@/lib/api";

function wrapper(
  activity: PipelineStageActivity | null,
  lastByStage: Record<string, number>,
) {
  return () => {
    const ref = useRef<Record<string, number>>(lastByStage);
    return useStageStall(activity, ref);
  };
}

describe("useStageStall", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-23T15:00:00Z"));
  });
  afterEach(() => vi.useRealTimers());

  it("retorna stalled=false quando activity é null", () => {
    const { result } = renderHook(wrapper(null, {}));
    expect(result.current).toEqual({ stalled: false, stalledForMs: 0 });
  });

  it("respeita piso de 180s quando não há estimativa", () => {
    const now = Date.now();
    const { result } = renderHook(
      wrapper({ stage: "E1.5", itemsDone: 0, itemsTotal: 3 }, { "E1.5": now - 120_000 }),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    // 120s < 180s → não stalled
    expect(result.current.stalled).toBe(false);
    expect(result.current.stalledForMs).toBeGreaterThanOrEqual(120_000);
  });

  it("vira stalled após 180s sem evento (piso absoluto)", () => {
    const now = Date.now();
    const { result } = renderHook(
      wrapper({ stage: "E1.5", itemsDone: 0, itemsTotal: 3 }, { "E1.5": now - 200_000 }),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current.stalled).toBe(true);
    expect(result.current.stalledForMs).toBeGreaterThanOrEqual(200_000);
  });

  it("threshold adaptativo: 2×estimated/total supera o piso em LLM lento", () => {
    // estimated = 20min, total = 5 → 2×240s/item = 480s (8min).
    // Aos 400s (6.67min) ainda NÃO deve estar stalled — piso 180s perdeu
    // para 480s adaptativo.
    const now = Date.now();
    const { result } = renderHook(
      wrapper(
        {
          stage: "E1.5",
          itemsDone: 2,
          itemsTotal: 5,
          estimatedDurationMs: 20 * 60_000,
        },
        { "E1.5": now - 400_000 },
      ),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current.stalled).toBe(false);
  });

  it("adaptativo vira stalled quando ultrapassa 2×per-item", () => {
    // estimated = 20min, total = 5 → threshold 480s. Aos 500s → stalled.
    const now = Date.now();
    const { result } = renderHook(
      wrapper(
        {
          stage: "E1.5",
          itemsDone: 2,
          itemsTotal: 5,
          estimatedDurationMs: 20 * 60_000,
        },
        { "E1.5": now - 500_000 },
      ),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current.stalled).toBe(true);
  });

  it("estimativa pequena não afunda o piso: threshold nunca abaixo de 180s", () => {
    // estimated = 10s, total = 10 → 2×1s/item = 2s. Piso 180s vence.
    // Aos 60s não deve estar stalled ainda.
    const now = Date.now();
    const { result } = renderHook(
      wrapper(
        {
          stage: "E2-llm",
          itemsDone: 0,
          itemsTotal: 10,
          estimatedDurationMs: 10_000,
        },
        { "E2-llm": now - 60_000 },
      ),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current.stalled).toBe(false);
  });

  it("cada stage tem timestamp próprio (não vaza entre stages)", () => {
    const now = Date.now();
    const { result } = renderHook(
      wrapper(
        { stage: "E1.5", itemsDone: 0, itemsTotal: 3 },
        { "E1.5": now - 200_000, E1: now - 10_000 },
      ),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current.stalled).toBe(true); // E1.5 stalled...
    // ...apesar de E1 ter evento recente (10s atrás).
  });

  it("sem timestamp para a stage (primeira vez), conta de agora — não stalled", () => {
    const { result } = renderHook(
      wrapper({ stage: "E3", itemsDone: 0, itemsTotal: 1 }, {}),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current.stalled).toBe(false);
  });
});
