import { apiFetch } from "./core";

// ─── Dashboard Types ───

export interface DashboardKPI {
  label: string;
  value: string;
  raw_value: number;
  delta?: number | null;
  delta_percent?: number | null;
}

export interface DashboardChart {
  chart_type: string;
  title: string;
  data: Record<string, unknown>;
}

export interface DashboardAlert {
  severity: string;
  title: string;
  message: string;
}

export interface DashboardResponse {
  kpis: DashboardKPI[];
  charts: DashboardChart[];
  alerts: DashboardAlert[];
  data_freshness: string | null;
  periodo: string | null;
}

// ─── Dashboard API ───

export async function getDashboard(workspaceId: string): Promise<DashboardResponse> {
  return apiFetch(`/workspaces/${workspaceId}/dashboard`);
}
