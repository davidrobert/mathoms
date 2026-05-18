import type { PipelineRunResponse } from "@/lib/api";

export function deriveFailedStage(
  run: Pick<PipelineRunResponse, "failed_at_stage" | "stage_logs">,
): string | null {
  if (run.failed_at_stage) return run.failed_at_stage;
  const failedLog = run.stage_logs.find((s) => s.status === "failed");
  return failedLog?.stage ?? null;
}
