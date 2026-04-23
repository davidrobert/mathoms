"use client";

import { useEffect, useState } from "react";
import type { PipelineStageActivity } from "@/lib/api";

// ADR-119 item 6 — piso absoluto do threshold de "sem sinal".
// Mesmo com estimated_duration_ms baixo, não emitimos alerta antes de 3min —
// pequenos spikes de rede/backoff são esperados.
const STALL_FLOOR_MS = 180_000;

export interface StageStallState {
  stalled: boolean;
  stalledForMs: number;
}

/**
 * ADR-119 — detecta stall por-stage. Threshold:
 * ``max(180s, 2×estimated_duration_ms / items_total)``.
 *
 * `lastActivityByStageRef` é atualizada pelo parent a cada ``stage_activity``
 * do WS (mesmo pattern de ``lastWsEventRef``). O hook relê a ref a cada 1s
 * e devolve ``{ stalled, stalledForMs }`` só para a stage do `activity` atual.
 */
export function useStageStall(
  activity: PipelineStageActivity | null,
  lastActivityByStageRef: React.RefObject<Record<string, number>>,
): StageStallState {
  const [state, setState] = useState<StageStallState>({
    stalled: false,
    stalledForMs: 0,
  });

  useEffect(() => {
    if (!activity) {
      setState({ stalled: false, stalledForMs: 0 });
      return;
    }
    const id = setInterval(() => {
      const last =
        lastActivityByStageRef.current?.[activity.stage] ?? Date.now();
      const delta = Date.now() - last;
      const threshold = computeThreshold(activity);
      setState({ stalled: delta > threshold, stalledForMs: delta });
    }, 1000);
    return () => clearInterval(id);
  }, [activity, lastActivityByStageRef]);

  return state;
}

function computeThreshold(activity: PipelineStageActivity): number {
  const { estimatedDurationMs, itemsTotal } = activity;
  if (
    typeof estimatedDurationMs === "number" &&
    typeof itemsTotal === "number" &&
    itemsTotal > 0
  ) {
    const perItemCeiling = (2 * estimatedDurationMs) / itemsTotal;
    return Math.max(STALL_FLOOR_MS, perItemCeiling);
  }
  return STALL_FLOOR_MS;
}
