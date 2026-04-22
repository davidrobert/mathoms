"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getDashboard, type DashboardResponse } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { UpcomingTasksWidget } from "@/components/tasks/UpcomingTasksWidget";
import { useWorkspace } from "@/lib/WorkspaceProvider";

import { AlertCard } from "./_components/AlertCard";
import { ChartsGrid } from "./_components/ChartsGrid";
import { HeaderActions } from "./_components/HeaderActions";
import { KpiRow } from "./_components/KpiRow";
import { monthLabelToDateRange } from "./_components/dashboardHelpers";

function DashboardErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader title="Dashboard" />
      <EmptyState
        variant="error"
        title="Erro ao carregar dados"
        description={error}
        action={{ label: "Tentar novamente", onClick: onRetry }}
      />
    </div>
  );
}

function DashboardEmptyState() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader title="Dashboard" />
      <div className="space-y-4">
        <EmptyState
          variant="no-data"
          title="Nenhuma análise disponível"
          description="Execute o pipeline para gerar o dashboard deste período. Ajuste metas e plano de vida em Meu Plano quando quiser."
          action={{ label: "Ir para Pipeline", href: "/pipeline" }}
        />
        <p className="text-center text-sm text-muted-foreground">
          <Link href="/plano" className="font-medium text-primary underline-offset-2 hover:underline">
            Abrir Meu Plano (metas)
          </Link>
        </p>
      </div>
    </div>
  );
}

function useDashboardData(workspaceId: string | undefined) {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!workspaceId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await getDashboard(workspaceId);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar dashboard");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, error, load };
}

export default function DashboardPage() {
  const { workspace } = useWorkspace();
  const router = useRouter();
  const { data, loading, error, load } = useDashboardData(workspace?.id);

  const handleBarClick = (label: string) => {
    const range = monthLabelToDateRange(label);
    if (range) {
      router.push(`/transactions?date_from=${range.date_from}&date_to=${range.date_to}`);
    }
  };

  const handlePieSliceClick = (name: string) => {
    router.push(`/transactions?category=${encodeURIComponent(name)}`);
  };

  if (!workspace) return null;

  if (!loading && error) {
    return <DashboardErrorState error={error} onRetry={load} />;
  }

  if (!loading && data && data.kpis.length === 0 && data.charts.length === 0) {
    return <DashboardEmptyState />;
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader
        title="Dashboard"
        description={data?.periodo ?? undefined}
        actions={
          <HeaderActions
            dataFreshness={data?.data_freshness}
            loading={loading}
            onRefresh={load}
          />
        }
      />

      {data && data.alerts.length > 0 && (
        <div className="mb-6 space-y-3">
          {data.alerts.map((alert, i) => (
            <AlertCard key={`${alert.severity}-${i}`} alert={alert} />
          ))}
        </div>
      )}

      <KpiRow loading={loading} kpis={data?.kpis ?? []} />

      {/* F8.2: Widget de tarefas próximas (ADR-074) */}
      <div className="mb-6">
        <UpcomingTasksWidget />
      </div>

      <ChartsGrid
        loading={loading}
        charts={data?.charts ?? []}
        onBarClick={handleBarClick}
        onSliceClick={handlePieSliceClick}
      />
    </div>
  );
}
