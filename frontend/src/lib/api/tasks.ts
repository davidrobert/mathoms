import { API_BASE, apiFetch } from "./core";

// ═══════════════════════════════════════════════════════════════════════
// Tasks (ADR-074, F8.2)
// ═══════════════════════════════════════════════════════════════════════

export type TaskPriority = "S" | "R" | "O";
export type TaskStatus =
  | "pending"
  | "in_progress"
  | "done"
  | "cancelled"
  | "blocked";
export type TaskDeadlineKind =
  | "HARD_DATE"
  | "MONTH"
  | "QUARTER"
  | "CONDITIONAL"
  | "UNSCHEDULED";
export type TaskCreatedFrom = "manual" | "seed" | "llm_suggestion";

export interface TaskResponse {
  id: string;
  workspace_id: string;
  number: number;
  title: string;
  description: string | null;
  category: string;
  priority: TaskPriority;
  status: TaskStatus;
  status_reason: string | null;
  deadline_kind: TaskDeadlineKind;
  deadline_date: string | null;
  deadline_label: string | null;
  ref: string | null;
  parent_task_id: string | null;
  related_transaction_id: string | null;
  related_goal_id: string | null;
  assigned_to: string | null;
  created_from: TaskCreatedFrom;
  source_suggestion_id: string | null;
  /** ADR-162 (Onda 8 #3) — sinaliza Tasks geradas a partir de Decision. */
  derived_from_decision_id: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  tasks: TaskResponse[];
  total: number;
}

export interface TaskCreateBody {
  title: string;
  description?: string | null;
  category: string;
  priority: TaskPriority;
  deadline_kind?: TaskDeadlineKind;
  deadline_date?: string | null;
  deadline_label?: string | null;
  ref?: string | null;
  parent_task_id?: string | null;
  related_goal_id?: string | null;
  assigned_to?: string | null;
  number?: number;
  /** ADR-162 (Onda 8 #3) — Tasks geradas via DecisionCard "Gerar tarefas". */
  derived_from_decision_id?: string | null;
}

export interface TaskUpdateBody {
  title?: string;
  description?: string | null;
  category?: string;
  priority?: TaskPriority;
  deadline_kind?: TaskDeadlineKind;
  deadline_date?: string | null;
  deadline_label?: string | null;
  ref?: string | null;
  parent_task_id?: string | null;
  related_goal_id?: string | null;
  assigned_to?: string | null;
}

export interface TaskFiltersQuery {
  status_filter?: TaskStatus;
  priority?: TaskPriority;
  category?: string;
  deadline_before?: string;
  deadline_after?: string;
  assigned_to?: string;
  include_done?: boolean;
  include_cancelled?: boolean;
}

export async function listTasks(
  workspaceId: string,
  filters: TaskFiltersQuery = {}
): Promise<TaskListResponse> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v !== undefined && v !== null) params.set(k, String(v));
  }
  const qs = params.toString();
  return apiFetch(
    `/workspaces/${workspaceId}/tasks${qs ? `?${qs}` : ""}`
  );
}

export async function listUpcomingTasks(
  workspaceId: string,
  days = 7
): Promise<TaskListResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/upcoming?days=${days}`);
}

export async function getTask(
  workspaceId: string,
  taskId: string
): Promise<TaskResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}`);
}

export async function createTask(
  workspaceId: string,
  body: TaskCreateBody
): Promise<TaskResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateTask(
  workspaceId: string,
  taskId: string,
  body: TaskUpdateBody
): Promise<TaskResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function transitionTaskStatus(
  workspaceId: string,
  taskId: string,
  status: TaskStatus,
  reason?: string
): Promise<TaskResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}/status`, {
    method: "POST",
    body: JSON.stringify({ status, status_reason: reason }),
  });
}

export async function deleteTask(
  workspaceId: string,
  taskId: string
): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}`, {
    method: "DELETE",
  });
}

// ─── Task Suggestions ────────────────────────────────────────────────

export type SuggestionStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "merged";

export interface TaskSuggestionResponse {
  id: string;
  workspace_id: string;
  proposed_payload: {
    title: string;
    category: string;
    priority: TaskPriority;
    deadline_kind?: TaskDeadlineKind;
    deadline_date?: string | null;
    deadline_label?: string | null;
    description?: string | null;
    [key: string]: unknown;
  };
  source: "e5n_llm" | "cross_validation" | "system_rule";
  source_run_id: string | null;
  status: SuggestionStatus;
  rejection_reason: string | null;
  approved_task_id: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface TaskSuggestionListResponse {
  suggestions: TaskSuggestionResponse[];
  total: number;
}

export async function listTaskSuggestions(
  workspaceId: string,
  statusFilter: SuggestionStatus = "pending"
): Promise<TaskSuggestionListResponse> {
  return apiFetch(
    `/workspaces/${workspaceId}/task-suggestions?status_filter=${statusFilter}`
  );
}

export async function approveTaskSuggestion(
  workspaceId: string,
  suggestionId: string,
  editedPayload?: TaskCreateBody
): Promise<TaskResponse> {
  return apiFetch(
    `/workspaces/${workspaceId}/task-suggestions/${suggestionId}/approve`,
    {
      method: "POST",
      body: JSON.stringify({ edited_payload: editedPayload }),
    }
  );
}

export async function rejectTaskSuggestion(
  workspaceId: string,
  suggestionId: string,
  reason?: string
): Promise<TaskSuggestionResponse> {
  return apiFetch(
    `/workspaces/${workspaceId}/task-suggestions/${suggestionId}/reject`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    }
  );
}

export async function mergeTaskSuggestion(
  workspaceId: string,
  suggestionId: string,
  targetTaskId: string
): Promise<TaskSuggestionResponse> {
  return apiFetch(
    `/workspaces/${workspaceId}/task-suggestions/${suggestionId}/merge-into/${targetTaskId}`,
    { method: "POST" }
  );
}

export interface ScanDeadlinesResult {
  created: number;
  skipped_existing: number;
  evaluated: number;
}

export async function scanTaskDeadlines(
  workspaceId: string
): Promise<ScanDeadlinesResult> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/scan-deadlines`, {
    method: "POST",
  });
}

// ─── Task Progress (F8.3 — Task↔Transaction) ────────────────────────

export interface TaskProgress {
  is_trackable: boolean;
  period_start: string | null;
  period_end: string | null;
  target_brl: number | null;
  executed_brl: number | null;
  percent_executed: number | null;
  matched_keywords: string[];
  matched_transactions_count: number;
}

export async function getTaskProgress(
  workspaceId: string,
  taskId: string
): Promise<TaskProgress> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}/progress`);
}

// ─── Task↔Goal (F8.3) ──────────────────────────────────────────────

export async function listTasksForGoal(
  workspaceId: string,
  goalId: string,
  includeDone = false
): Promise<TaskListResponse> {
  const qs = new URLSearchParams();
  if (includeDone) qs.set("include_done", "true");
  return apiFetch(
    `/workspaces/${workspaceId}/goals/${goalId}/tasks${
      qs.toString() ? `?${qs}` : ""
    }`
  );
}

// ─── Report Tasks Snapshot (ADR-074 §F8.3) ────────────────────────

export interface ReportTasksSnapshot {
  is_live_fallback: boolean;
  version: number;
  captured_at: string | null;
  total: number;
  counts_by_status: Record<string, number>;
  counts_by_priority: Record<string, number>;
  tasks: Array<{
    id?: string;
    number: number;
    title: string;
    description?: string | null;
    category: string;
    priority: TaskPriority;
    status: TaskStatus;
    ref: string | null;
    deadline_kind: TaskDeadlineKind;
    deadline_date: string | null;
    deadline_label: string | null;
  }>;
}

export async function getReportTasks(
  reportId: string
): Promise<ReportTasksSnapshot> {
  return apiFetch(`/reports/${reportId}/tasks`);
}

// ─── Task Attachments (F8.3) ──────────────────────────────────────────

export interface TaskAttachmentMeta {
  id: string;
  task_id: string;
  workspace_id: string;
  original_filename: string;
  content_type: string | null;
  size_bytes: number | null;
  uploaded_by: string | null;
  created_at: string;
}

export interface TaskAttachmentList {
  attachments: TaskAttachmentMeta[];
  total: number;
}

export async function listTaskAttachments(
  workspaceId: string,
  taskId: string
): Promise<TaskAttachmentList> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}/attachments`);
}

export async function uploadTaskAttachment(
  workspaceId: string,
  taskId: string,
  file: File
): Promise<TaskAttachmentMeta> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch(
    `/workspaces/${workspaceId}/tasks/${taskId}/attachments`,
    { method: "POST", body: form }
  );
}

export async function deleteTaskAttachment(
  workspaceId: string,
  taskId: string,
  attachmentId: string
): Promise<void> {
  return apiFetch(
    `/workspaces/${workspaceId}/tasks/${taskId}/attachments/${attachmentId}`,
    { method: "DELETE" }
  );
}

export function taskAttachmentDownloadUrl(
  workspaceId: string,
  taskId: string,
  attachmentId: string
): string {
  return `${API_BASE}/workspaces/${workspaceId}/tasks/${taskId}/attachments/${attachmentId}/download`;
}
