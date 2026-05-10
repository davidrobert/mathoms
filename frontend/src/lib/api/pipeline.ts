import { apiFetch } from "./core";

// ─── Pipeline Types ───

export type PipelineRunStatus =
  | "pending"
  | "running"
  | "completed"
  | "partial_failure"
  | "failed"
  | "cancelled"
  | "needs_review"
  | "resuming";

export type PipelineStageStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped"
  | "skipped_free_tier"
  | "needs_review";

export interface PipelineStageLog {
  id: string;
  stage: string;
  status: PipelineStageStatus;
  output_summary: Record<string, unknown> | null;
  errors: string | null;
  duration_ms: number | null;
  started_at: string;
  completed_at: string | null;
}

export interface PipelineRunResponse {
  id: string;
  workspace_id: string;
  status: PipelineRunStatus;
  current_stage: string | null;
  failed_at_stage: string | null;
  paused_at_stage: string | null;
  tier_at_run: string;
  total_documents: number | null;
  incremental: boolean;
  celery_task_id: string | null;
  started_at: string;
  completed_at: string | null;
  stage_logs: PipelineStageLog[];
  report_id: string | null;
}

export interface PipelineRunListResponse {
  runs: PipelineRunResponse[];
  total: number;
}

/** ADR-119: fases do contrato LiveStep. Pesos fixos em `phaseWeight()`. */
export type LiveStepPhase =
  | "preparing"
  | "awaiting_llm"
  | "validating"
  | "persisting"
  | "finalizing";

/** Live sub-step within a stage (WebSocket ``stage_activity``). */
export interface PipelineStageActivity {
  stage: string;
  file?: string;
  message?: string;
  currentItem?: string;
  itemsDone?: number;
  itemsTotal?: number;
  /** ADR-119 — sub-fase intra-item. */
  phase?: LiveStepPhase;
  /** ADR-119 — mediana dos últimos runs bem-sucedidos (só no 1º evento). */
  estimatedDurationMs?: number;
}

export interface PipelineEvent {
  event: string;
  run_id?: string;
  stage?: string;
  status?: string;
  progress_pct?: number;
  error?: string;
  detail?: Record<string, unknown>;
  timestamp?: string;
}

// ─── Pipeline ───

export async function triggerPipeline(workspaceId: string, opts?: {
  from_stage?: string;
  skip_llm?: boolean;
  stop_on_error?: boolean;
  incremental?: boolean;
}): Promise<PipelineRunResponse> {
  return apiFetch(`/workspaces/${workspaceId}/pipeline/run`, {
    method: "POST",
    body: JSON.stringify({
      from_stage: opts?.from_stage ?? null,
      skip_llm: opts?.skip_llm ?? true,
      stop_on_error: opts?.stop_on_error ?? true,
      incremental: opts?.incremental ?? false,
    }),
  });
}

export async function reclassifyExpenses(workspaceId: string): Promise<PipelineRunResponse> {
  return triggerPipeline(workspaceId, { from_stage: "E4", skip_llm: true });
}

export async function getNewDocCount(workspaceId: string): Promise<{ new_count: number }> {
  return apiFetch(`/workspaces/${workspaceId}/pipeline/new-doc-count`);
}

export async function listPipelineRuns(workspaceId: string): Promise<PipelineRunListResponse> {
  return apiFetch(`/workspaces/${workspaceId}/pipeline/runs`);
}

export async function getPipelineRun(
  workspaceId: string,
  runId: string
): Promise<PipelineRunResponse> {
  return apiFetch(`/workspaces/${workspaceId}/pipeline/runs/${runId}`);
}

export async function cancelPipelineRun(workspaceId: string, runId: string): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/pipeline/runs/${runId}/cancel`, { method: "POST" });
}

// ─── Pipeline Resume ───

export async function resumePipelineRun(workspaceId: string, runId: string): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/pipeline/runs/${runId}/resume`, { method: "POST" });
}

// ─── Stage Review ───

/** Status do StageReview no backend (`backend/app/models/stage_review.py`). */
export type StageReviewStatus = "pending" | "approved" | "edited";

/** Issue de validação estruturada (ADR-165) — espelha
 * `backend/app/schemas/pipeline.ValidationIssueDTO`. */
export interface ValidationIssue {
  code: string;
  severity: "error" | "warning";
  path: string | null;
  context: Record<string, string | number | boolean | null>;
  legacy_message: string;
}

/** Shape da resposta de `GET /reviews` e `POST /reviews/{id}` — espelha
 * `backend/app/schemas/pipeline.StageReviewResponse`. */
export interface StageReviewResponse {
  id: string;
  pipeline_run_id: string;
  stage: string;
  status: StageReviewStatus;
  original_output_json: Record<string, unknown> | null;
  edited_output_json: Record<string, unknown> | null;
  validation_errors: string | null;
  /** ADR-165 onda 2: lista estruturada de issues. NULL para reviews pré-cutover. */
  validation_issues: ValidationIssue[] | null;
  /** ADR-165 onda 2: frase curta derivada das issues no DTO. */
  summary: string;
  created_at: string;
  reviewed_at: string | null;
}

/** Body de `POST /reviews/{id}` — espelha
 * `backend/app/schemas/pipeline.StageReviewActionRequest`. */
export interface StageReviewActionRequest {
  action: "approve" | "edit";
  edited_output_json?: Record<string, unknown>;
}

export async function listStageReviews(
  workspaceId: string,
  runId: string
): Promise<StageReviewResponse[]> {
  return apiFetch(`/workspaces/${workspaceId}/pipeline/runs/${runId}/reviews`);
}

export async function submitStageReview(
  workspaceId: string,
  runId: string,
  reviewId: string,
  data: StageReviewActionRequest
): Promise<StageReviewResponse> {
  return apiFetch(`/workspaces/${workspaceId}/pipeline/runs/${runId}/reviews/${reviewId}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
