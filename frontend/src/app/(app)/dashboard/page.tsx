"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  TrendingUp,
  Wallet,
  PiggyBank,
  ArrowUpDown,
  AlertTriangle,
  AlertCircle,
  Clock,
  RefreshCw,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

import { getDashboard } from "@/lib/api";
import type {
  DashboardResponse,
  DashboardChart,
  DashboardAlert,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { KPICard } from "@/components/KPICard";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { StatusBadge } from "@/components/StatusBadge";
import { UpcomingTasksWidget } from "@/components/tasks/UpcomingTasksWidget";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspace } from "@/lib/WorkspaceProvider";

// ─── Chart Palette ───

const CHART_COLORS = [
  "#3b82f6",
  "#22c55e",
  "#ef4444",
  "#f59e0b",
  "#8b5cf6",
  "#06b6d4",
  "#ec4899",
  "#6366f1",
  "#14b8a6",
  "#f97316",
  "#64748b",
  "#84cc16",
];

const KPI_ICONS: LucideIcon[] = [TrendingUp, Wallet, PiggyBank, ArrowUpDown];

// ─── Helpers ───

function freshnessVariant(iso: string | null): "success" | "warning" {
  if (!iso) return "warning";
  const diff = Date.now() - new Date(iso).getTime();
  return diff > 30 * 24 * 60 * 60 * 1000 ? "warning" : "success";
}

function formatFreshness(iso: string | null): string {
  if (!iso) return "Sem dados";
  const d = new Date(iso);
  return `Atualizado em ${d.toLocaleDateString("pt-BR")}`;
}

interface BarDataRow {
  month: string;
  [key: string]: string | number;
}

function normalizeBarData(chart: DashboardChart): {
  rows: BarDataRow[];
  keys: { key: string; name: string; color: string }[];
} {
  const raw = chart.data as {
    labels?: string[];
    datasets?: { label: string; data: number[] }[];
  };
  const labels = raw.labels ?? [];
  const datasets = raw.datasets ?? [];

  const rows: BarDataRow[] = labels.map((label, i) => {
    const row: BarDataRow = { month: label };
    datasets.forEach((ds) => {
      row[ds.label] = ds.data[i] ?? 0;
    });
    return row;
  });

  const keys = datasets.map((ds, i) => ({
    key: ds.label,
    name: ds.label,
    color: CHART_COLORS[i % CHART_COLORS.length],
  }));

  return { rows, keys };
}

interface PieDataItem {
  name: string;
  value: number;
}

function normalizePieData(chart: DashboardChart): PieDataItem[] {
  const raw = chart.data as Record<string, unknown>;

  if (Array.isArray(raw.labels) && Array.isArray(raw.values)) {
    const labels = raw.labels as string[];
    const values = raw.values as number[];
    return labels.map((label, i) => ({
      name: label,
      value: values[i] ?? 0,
    }));
  }

  return Object.entries(raw)
    .filter(([, v]) => typeof v === "number")
    .map(([name, value]) => ({ name, value: value as number }));
}

function monthLabelToDateRange(label: string): {
  date_from: string;
  date_to: string;
} | null {
  const months: Record<string, string> = {
    jan: "01", fev: "02", mar: "03", abr: "04",
    mai: "05", jun: "06", jul: "07", ago: "08",
    set: "09", out: "10", nov: "11", dez: "12",
  };

  const match = label.toLowerCase().match(/^([a-zç]+)\/?(\d{4})$/);
  if (!match) return null;
  const mm = months[match[1]];
  const yyyy = match[2];
  if (!mm || !yyyy) return null;

  const start = `${yyyy}-${mm}-01`;
  const lastDay = new Date(Number(yyyy), Number(mm), 0).getDate();
  const end = `${yyyy}-${mm}-${String(lastDay).padStart(2, "0")}`;
  return { date_from: start, date_to: end };
}

// ─── Chart Cards ───

function ChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[300px] w-full rounded-lg" />
      </CardContent>
    </Card>
  );
}

function BarChartCard({
  chart,
  onBarClick,
}: {
  chart: DashboardChart;
  onBarClick?: (label: string) => void;
}) {
  const { rows, keys } = normalizeBarData(chart);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{chart.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={rows}
            margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 12 }}
              className="text-muted-foreground"
            />
            <YAxis
              tick={{ fontSize: 12, className: "tabular-nums" }}
              className="text-muted-foreground"
              tickFormatter={(v: number) => formatCurrency(v)}
            />
            <Tooltip
              formatter={(value) => formatCurrency(Number(value))}
              itemStyle={{
                fontFamily: "var(--font-mono)",
                fontVariantNumeric: "tabular-nums",
              }}
              contentStyle={{
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
                background: "var(--popover)",
                color: "var(--popover-foreground)",
              }}
            />
            <Legend />
            {keys.map((dk) => (
              <Bar
                key={dk.key}
                dataKey={dk.key}
                name={dk.name}
                fill={dk.color}
                radius={[4, 4, 0, 0]}
                cursor={onBarClick ? "pointer" : undefined}
                onClick={
                  onBarClick
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    ? (entry: any) => {
                        const label = entry?.month ?? entry?.payload?.month;
                        if (typeof label === "string") onBarClick(label);
                      }
                    : undefined
                }
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function PieChartCard({
  chart,
  onSliceClick,
}: {
  chart: DashboardChart;
  onSliceClick?: (name: string) => void;
}) {
  const data = normalizePieData(chart);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{chart.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius="80%"
              innerRadius="45%"
              paddingAngle={2}
              strokeWidth={0}
              cursor={onSliceClick ? "pointer" : undefined}
              onClick={
                onSliceClick
                  ? (entry) => {
                      if (entry?.name) onSliceClick(entry.name as string);
                    }
                  : undefined
              }
            >
              {data.map((entry, idx) => (
                <Cell
                  key={entry.name}
                  fill={CHART_COLORS[idx % CHART_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => formatCurrency(Number(value))}
              itemStyle={{
                fontFamily: "var(--font-mono)",
                fontVariantNumeric: "tabular-nums",
              }}
              contentStyle={{
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
                background: "var(--popover)",
                color: "var(--popover-foreground)",
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// ─── Alert Card ───

function AlertCard({ alert }: { alert: DashboardAlert }) {
  const isCritical = alert.severity === "critical";
  const Icon = isCritical ? AlertCircle : AlertTriangle;
  const borderColor = isCritical ? "border-l-red-500" : "border-l-amber-500";
  const iconColor = isCritical ? "text-red-500" : "text-amber-500";

  return (
    <Card className={`border-l-4 ${borderColor}`}>
      <CardContent className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${iconColor}`} />
        <div>
          <p className="font-medium">{alert.title}</p>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {alert.message}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Page ───

export default function DashboardPage() {
  const { workspace } = useWorkspace();
  const router = useRouter();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getDashboard(workspace!.id);
      setData(res);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erro ao carregar dashboard"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleBarClick = (label: string) => {
    const range = monthLabelToDateRange(label);
    if (range) {
      router.push(
        `/transactions?date_from=${range.date_from}&date_to=${range.date_to}`
      );
    }
  };

  const handlePieSliceClick = (name: string) => {
    router.push(`/transactions?category=${encodeURIComponent(name)}`);
  };

  if (!workspace) return null;

  // Error state
  if (!loading && error) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-8">
        <PageHeader title="Dashboard" />
        <EmptyState
          variant="error"
          title="Erro ao carregar dados"
          description={error}
          action={{ label: "Tentar novamente", onClick: load }}
        />
      </div>
    );
  }

  // Empty state — no analysis data yet
  if (!loading && data && data.kpis.length === 0 && data.charts.length === 0) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-8">
        <PageHeader title="Dashboard" />
        <EmptyState
          variant="no-data"
          title="Nenhuma análise disponível"
          description="Execute o pipeline de processamento para gerar o dashboard com KPIs e gráficos financeiros."
          action={{ label: "Ir para Pipeline", href: "/pipeline" }}
        />
      </div>
    );
  }

  const freshVariant = freshnessVariant(data?.data_freshness ?? null);

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader
        title="Dashboard"
        description={data?.periodo ?? undefined}
        actions={
          <div className="flex items-center gap-3">
            {data?.data_freshness && (
              <StatusBadge variant={freshVariant}>
                <Clock className="mr-1 h-3 w-3" />
                {formatFreshness(data.data_freshness)}
              </StatusBadge>
            )}
            {!data?.data_freshness && !loading && (
              <StatusBadge variant="warning">
                <AlertTriangle className="mr-1 h-3 w-3" />
                Sem dados
              </StatusBadge>
            )}
            <button
              onClick={load}
              disabled={loading}
              className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-50"
              aria-label="Atualizar dashboard"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        }
      />

      {/* Alerts */}
      {data && data.alerts.length > 0 && (
        <div className="mb-6 space-y-3">
          {data.alerts.map((alert, i) => (
            <AlertCard key={`${alert.severity}-${i}`} alert={alert} />
          ))}
        </div>
      )}

      {/* KPI Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <KPICard key={i} label="" value="" loading />
            ))
          : data?.kpis.map((kpi, i) => (
              <KPICard
                key={kpi.label}
                label={kpi.label}
                value={kpi.value}
                icon={KPI_ICONS[i % KPI_ICONS.length]}
                delta={
                  kpi.delta != null
                    ? {
                        value: kpi.delta,
                        percent: kpi.delta_percent ?? undefined,
                      }
                    : undefined
                }
              />
            ))}
      </div>

      {/* F8.2: Widget de tarefas próximas (ADR-074) */}
      <div className="mb-6">
        <UpcomingTasksWidget />
      </div>

      {/* Charts Grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <ChartSkeleton key={i} />
          ))}
        </div>
      ) : (
        data &&
        data.charts.length > 0 && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {data.charts.map((chart) => {
              const isPie = chart.chart_type === "pie";
              const isDespesasCategory =
                chart.title.toLowerCase().includes("categoria") ||
                chart.title.toLowerCase().includes("despesas por");

              if (isPie) {
                return (
                  <PieChartCard
                    key={chart.title}
                    chart={chart}
                    onSliceClick={
                      isDespesasCategory ? handlePieSliceClick : undefined
                    }
                  />
                );
              }

              return (
                <BarChartCard
                  key={chart.title}
                  chart={chart}
                  onBarClick={handleBarClick}
                />
              );
            })}
          </div>
        )
      )}
    </div>
  );
}
