import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useRef } from "react";

import {
  useStallWarning,
  progressStallThreshold,
} from "@/app/(app)/pipeline/_components/useStallWarning";
import type { PipelineStageActivity } from "@/lib/api";

interface WrapperProps {
  isPending?: boolean;
  isRunning?: boolean;
  hasNoStages?: boolean;
  startedAt?: string;
  lastWsAt?: number;
  lastProgressAt?: number;
  liveStageActivity?: PipelineStageActivity | null;
  wsStatus?: string;
}

function makeWrapper(props: WrapperProps) {
  return () => {
    const wsRef = useRef<number>(props.lastWsAt ?? Date.now());
    const progRef = useRef<number>(props.lastProgressAt ?? Date.now());
    return useStallWarning({
      isPending: props.isPending ?? false,
      isRunning: props.isRunning ?? true,
      hasNoStages: props.hasNoStages ?? false,
      startedAt: props.startedAt ?? new Date().toISOString(),
      lastWsEventRef: wsRef,
      lastProgressEventRef: progRef,
      liveStageActivity: props.liveStageActivity ?? null,
      wsStatus: props.wsStatus ?? "connected",
    });
  };
}

describe("progressStallThreshold", () => {
  it("usa o piso de 90s quando não há activity", () => {
    expect(progressStallThreshold(null)).toBe(90_000);
  });

  it("usa adaptativo quando estimated/items é maior que o piso", () => {
    // 20min × 2 / 5 itens = 480s
    expect(
      progressStallThreshold({
        stage: "E1.5",
        estimatedDurationMs: 20 * 60_000,
        itemsTotal: 5,
        itemsDone: 0,
      }),
    ).toBe(480_000);
  });

  it("nunca cai abaixo do piso", () => {
    // 10s × 2 / 10 itens = 2s — piso 90s vence.
    expect(
      progressStallThreshold({
        stage: "E2-llm",
        estimatedDurationMs: 10_000,
        itemsTotal: 10,
        itemsDone: 0,
      }),
    ).toBe(90_000);
  });
});

describe("useStallWarning", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-02T20:00:00Z"));
  });
  afterEach(() => vi.useRealTimers());

  it("retorna null em estado saudável", () => {
    const now = Date.now();
    const { result } = renderHook(
      makeWrapper({
        startedAt: new Date(now - 5_000).toISOString(),
        lastWsAt: now,
        lastProgressAt: now,
      }),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current).toBeNull();
  });

  it("warning de fila quando pending sem stages há > 30s", () => {
    const now = Date.now();
    const { result } = renderHook(
      makeWrapper({
        isPending: true,
        isRunning: false,
        hasNoStages: true,
        startedAt: new Date(now - 35_000).toISOString(),
      }),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current).toMatch(/aguardando há mais de 30s/);
  });

  it("warning de WS morto quando lastWs > 60s atrás", () => {
    const now = Date.now();
    const { result } = renderHook(
      makeWrapper({
        startedAt: new Date(now - 120_000).toISOString(),
        lastWsAt: now - 70_000,
        lastProgressAt: now - 70_000,
        wsStatus: "disconnected",
      }),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current).toMatch(/atualizações recentes|sinal do servidor/i);
  });

  it("warning de 'sem avanço' dispara mesmo com WS saudável (heartbeats)", () => {
    // Cenário do screenshot: heartbeats mantêm lastWs fresh, mas
    // lastProgress está congelado há 2min — antes ninguém avisava.
    const now = Date.now();
    const { result } = renderHook(
      makeWrapper({
        startedAt: new Date(now - 5 * 60_000).toISOString(),
        lastWsAt: now - 5_000, // heartbeat recente
        lastProgressAt: now - 120_000, // 2min sem stage_*
        wsStatus: "connected",
      }),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current).toMatch(/Sem avanço de etapa/);
    expect(result.current).toMatch(/min/);
  });

  it("threshold adaptativo silencia 'sem avanço' em LLM stage longa", () => {
    // E1.5 IRPF estimated 10min × 2 / 1 item = 1200s. Aos 200s NÃO deve
    // alertar — está dentro do envelope esperado.
    const now = Date.now();
    const { result } = renderHook(
      makeWrapper({
        startedAt: new Date(now - 5 * 60_000).toISOString(),
        lastWsAt: now - 5_000,
        lastProgressAt: now - 200_000,
        liveStageActivity: {
          stage: "E1.5",
          estimatedDurationMs: 10 * 60_000,
          itemsTotal: 1,
          itemsDone: 0,
        },
        wsStatus: "connected",
      }),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current).toBeNull();
  });

  it("'sem avanço' aparece ao ultrapassar o threshold adaptativo", () => {
    // Mesmo cenário: estimated=10min, total=1 → threshold = 1200s. Aos 1300s, alerta.
    const now = Date.now();
    const { result } = renderHook(
      makeWrapper({
        startedAt: new Date(now - 25 * 60_000).toISOString(),
        lastWsAt: now - 5_000,
        lastProgressAt: now - 1_300_000,
        liveStageActivity: {
          stage: "E1.5",
          estimatedDurationMs: 10 * 60_000,
          itemsTotal: 1,
          itemsDone: 0,
        },
        wsStatus: "connected",
      }),
    );
    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current).toMatch(/Sem avanço de etapa/);
  });
});
