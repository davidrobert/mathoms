import { apiFetch } from "./core";

// ─── Dashboard Types ───

export interface DashboardKPI {
  key: string;
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
  /** Origem no E5: o summary da "Análise Financeira" conta só `ponto_urgente`. */
  kind: "ponto_urgente" | "aviso";
  /** Tom decidido pelo backend: `critical` é o ponto urgente de prioridade alta. */
  severity: "critical" | "warning";
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
