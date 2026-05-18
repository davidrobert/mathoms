"use client";

import type { PipelineRunResponse } from "@/lib/api";
import { HistoryRow } from "./HistoryRow";
import { deriveFailedStage } from "./failedStage";

const ACTIVE_STATUSES = new Set(["pending", "running", "resuming"]);

export function RunHistoryList({
  runs,
  activeRun,
  lastFailedRun,
  highlightedRunId,
  triggering,
  onTrigger,
}: {
  runs: PipelineRunResponse[];
  activeRun: PipelineRunResponse | null;
  lastFailedRun: PipelineRunResponse | null;
  highlightedRunId: string | null;
  triggering: boolean;
  onTrigger: (fromStage?: string) => void;
}) {
  if (runs.length === 0) return null;

  const visible = runs
    .filter((r) => r.id !== activeRun?.id || !ACTIVE_STATUSES.has(r.status))
    .filter((r) => r.id !== lastFailedRun?.id || activeRun != null);

  return (
    <div>
      <h2 className="mb-3 text-lg font-medium">Histórico</h2>
      <div className="space-y-2">
        {visible.map((run) => {
          const failedStage = deriveFailedStage(run);
          return (
            <HistoryRow
              key={run.id}
              run={run}
              highlighted={highlightedRunId === run.id}
              onRetry={() => onTrigger()}
              onRetryFrom={failedStage ? () => onTrigger(failedStage) : undefined}
              triggering={triggering}
            />
          );
        })}
      </div>
    </div>
  );
}
