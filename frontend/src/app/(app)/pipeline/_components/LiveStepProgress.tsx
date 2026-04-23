"use client";

import { AlertCircle } from "lucide-react";
import type { LiveStepPhase, PipelineStageActivity } from "@/lib/api";

// ADR-119: pesos fixos por fase. Somado a `items_done` divide por `items_total`
// para gerar progresso determinístico que nunca recua.
const PHASE_WEIGHT: Record<LiveStepPhase, number> = {
  preparing: 0.1,
  awaiting_llm: 0.4,
  validating: 0.8,
  persisting: 0.95,
  finalizing: 1.0,
};

// ADR-119: mensagens fixas PT-BR. Adicionar valor = breaking change (nova ADR).
const PHASE_LABEL: Record<LiveStepPhase, string> = {
  preparing: "Preparando…",
  awaiting_llm: "Consultando IA…",
  validating: "Validando resposta…",
  persisting: "Salvando…",
  finalizing: "Concluindo…",
};

function phaseWeight(phase: LiveStepPhase | undefined): number {
  return phase ? PHASE_WEIGHT[phase] : 0;
}

function computeProgressPct(
  itemsDone: number,
  itemsTotal: number,
  phase: LiveStepPhase | undefined,
): number {
  if (itemsTotal <= 0) return 0;
  const weighted = itemsDone + phaseWeight(phase);
  return Math.min(100, (weighted / itemsTotal) * 100);
}

function formatDurationShort(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  if (m === 0) return `${s}s`;
  return s === 0 ? `${m}m` : `${m}m${s}s`;
}

export interface LiveStepProgressProps {
  activity: PipelineStageActivity;
  /** Wall-time gasto na stage até agora (ms). Opcional — habilita linha "X / ~Y est.". */
  elapsedMs?: number;
  /** ADR-119 item 6 — quando true, dot pulsante vira alerta âmbar "sem sinal". */
  stalled?: boolean;
  /** Tempo desde último evento (ms). Renderizado dentro do aviso de stall. */
  stalledForMs?: number;
}

/**
 * Renderiza progresso LiveStep (ADR-119) uniforme para qualquer stage iterativa.
 *
 * Props-only — heartbeat/stall é computado pelo parent (`useStallWarning`), o
 * componente só exibe. Degrada graciosamente: sem `itemsTotal` mostra mensagem
 * textual antiga (compat com emissores não-migrados).
 */
export function LiveStepProgress({
  activity,
  elapsedMs,
  stalled = false,
  stalledForMs,
}: LiveStepProgressProps) {
  const hasCounter =
    typeof activity.itemsTotal === "number" && activity.itemsTotal > 0;
  const displayItem = activity.currentItem ?? activity.file;

  if (!hasCounter && !activity.message && !displayItem) return null;

  const done = activity.itemsDone ?? 0;
  const total = activity.itemsTotal ?? 0;
  const phase = activity.phase;
  const pct = hasCounter ? computeProgressPct(done, total, phase) : 0;
  const phaseLabel = phase ? PHASE_LABEL[phase] : activity.message;
  const currentIndex = hasCounter ? Math.min(done + 1, total) : 0;

  return (
    <div
      className="mx-3 mb-1 rounded-md border border-border/50 bg-muted/40 px-3 py-2 text-xs"
      data-testid="live-step-progress"
    >
      {hasCounter && (
        <>
          <div className="flex items-center justify-between gap-2 font-medium text-foreground">
            <span aria-live="polite">
              Item {currentIndex} de {total}
            </span>
            <span className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
              <span>
                {done}/{total}
              </span>
              {typeof elapsedMs === "number" &&
                typeof activity.estimatedDurationMs === "number" &&
                activity.estimatedDurationMs > 0 && (
                  <span
                    className={
                      elapsedMs > activity.estimatedDurationMs
                        ? "text-warning"
                        : "text-muted-foreground"
                    }
                    title="Tempo decorrido / mediana histórica"
                  >
                    {formatDurationShort(elapsedMs)} / ~
                    {formatDurationShort(activity.estimatedDurationMs)} est.
                  </span>
                )}
            </span>
          </div>
          <div
            className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(pct)}
            aria-label={`Progresso da etapa: ${done} de ${total} itens${phase ? `, fase ${phase}` : ""}`}
          >
            <div
              className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
              style={{ width: `${pct}%` }}
            />
          </div>
        </>
      )}
      {displayItem && (
        <p
          className={`${hasCounter ? "mt-2" : ""} truncate font-mono text-[11px] text-foreground/90`}
          title={displayItem}
        >
          {displayItem}
        </p>
      )}
      {phaseLabel && (
        <p className="mt-1 flex items-center gap-1.5 leading-snug text-muted-foreground">
          {stalled ? (
            <AlertCircle
              className="h-3 w-3 shrink-0 text-warning"
              aria-label="Sem sinal do servidor"
            />
          ) : (
            <span
              className="inline-block h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-primary"
              aria-hidden="true"
            />
          )}
          <span>
            {phaseLabel}
            {stalled && typeof stalledForMs === "number" && (
              <span className="ml-1 text-warning">
                — sem sinal há {formatDurationShort(stalledForMs)}
              </span>
            )}
          </span>
        </p>
      )}
    </div>
  );
}
