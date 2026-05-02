"use client";

import { useEffect, useState } from "react";
import type { PipelineStageActivity } from "@/lib/api";

const STALL_PENDING_MS = 30_000;
const STALL_RUNNING_MS = 60_000;
// Default mínimo para "sem avanço de etapa" — heartbeats do WS continuam
// chegando, mas nenhum `stage_*` em ≥90s sinaliza fila/worker preso.
const STALL_PROGRESS_FLOOR_MS = 90_000;

export interface UseStallWarningProps {
  isPending: boolean;
  isRunning: boolean;
  hasNoStages: boolean;
  startedAt: string;
  /** Bumpado por qualquer sinal de vida do WS (eventos + heartbeats). */
  lastWsEventRef: React.RefObject<number>;
  /** Bumpado SÓ por eventos `stage_*` — não por heartbeats. */
  lastProgressEventRef: React.RefObject<number>;
  /** Atividade da stage corrente; usada para threshold adaptativo. */
  liveStageActivity: PipelineStageActivity | null;
  wsStatus: string;
}

export function progressStallThreshold(
  activity: PipelineStageActivity | null,
): number {
  if (
    activity &&
    typeof activity.estimatedDurationMs === "number" &&
    typeof activity.itemsTotal === "number" &&
    activity.itemsTotal > 0
  ) {
    return Math.max(
      STALL_PROGRESS_FLOOR_MS,
      (2 * activity.estimatedDurationMs) / activity.itemsTotal,
    );
  }
  return STALL_PROGRESS_FLOOR_MS;
}

/**
 * Diferencia três tipos de stall:
 *  1. Pending + sem stages há >30s → fila travada.
 *  2. Running + sem QUALQUER sinal de WS (incl. heartbeats) há >60s → conexão morta.
 *  3. Running + sem evento de progresso há > threshold (90s ou adaptativo) → worker
 *     travado (heartbeats continuam mas nada avança).
 */
export function useStallWarning(p: UseStallWarningProps): string | null {
  const [warning, setWarning] = useState<string | null>(null);
  useEffect(() => {
    const id = setInterval(() => {
      const now = Date.now();
      const runAge = now - new Date(p.startedAt).getTime();
      const sinceLastWs = now - p.lastWsEventRef.current;
      const sinceLastProgress = now - p.lastProgressEventRef.current;
      const progThreshold = progressStallThreshold(p.liveStageActivity);

      if (p.isPending && p.hasNoStages && runAge > STALL_PENDING_MS) {
        setWarning(
          "O processamento está aguardando há mais de 30s. Pode haver um problema na fila de execução.",
        );
      } else if (p.isRunning && sinceLastWs > STALL_RUNNING_MS) {
        setWarning(
          p.wsStatus === "connected"
            ? "Sem sinal do servidor há mais de 1 min. Se o indicador mostrar “Tempo real”, aguarde; caso contrário, verifique a conexão."
            : "Sem atualizações recentes. O processamento pode estar lento.",
        );
      } else if (p.isRunning && sinceLastProgress > progThreshold) {
        const minutes = Math.floor(sinceLastProgress / 60_000);
        const dur =
          minutes >= 1 ? `${minutes} min` : `${Math.floor(sinceLastProgress / 1000)}s`;
        setWarning(
          `Sem avanço de etapa há ${dur}. Etapas com IA podem demorar; se persistir, considere cancelar e tentar novamente.`,
        );
      } else {
        setWarning(null);
      }
    }, 1000);
    return () => clearInterval(id);
  }, [
    p.isPending,
    p.isRunning,
    p.hasNoStages,
    p.startedAt,
    p.lastWsEventRef,
    p.lastProgressEventRef,
    p.liveStageActivity,
    p.wsStatus,
  ]);
  return warning;
}
