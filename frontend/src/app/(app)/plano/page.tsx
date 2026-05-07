"use client";

/**
 * /plano — única "home" do app pós-ADR-155.
 *
 * Consolida 3 camadas em uma única tela vertical:
 *
 * 1. **Estratégia** (executive summary): KPIs estratégicos · banner de
 *    sugestões · Hero IF · Metas de suporte.
 * 2. **Mês corrente** (operacional, ex-/dashboard): alertas · KPIs
 *    operacionais · charts. Componentes vivem em `_dashboard/`.
 * 3. **Plano de Ação** (execução): Decisões em vigor · tarefas próximas ·
 *    tarefas que destravam IF.
 *
 * `/dashboard` agora redireciona 308 para `/plano` (ADR-155, Direção E
 * consolidação). `/acao` permanece como superfície dinâmica de execução
 * (Inbox, Tarefas, Notas).
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, RefreshCw } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { UpcomingTasksWidget } from "@/components/tasks/UpcomingTasksWidget";
import { getDashboard, type DashboardResponse } from "@/lib/api";
import { useWorkspace } from "@/lib/WorkspaceProvider";

import { DecisionsSection } from "./_components/DecisionsSection";
import { RisksSection } from "./_components/RisksSection";
import { IFEmptyHero, IFHeroCard } from "./_components/IFHeroCard";
import { LinkedTasksSection } from "./_components/LinkedTasksSection";
import { OnboardingHero } from "./_components/OnboardingHero";
import { PlanoKpiRow } from "./_components/PlanoKpiRow";
import { ReportLinkAction } from "./_components/ReportLinkAction";
import { SuggestionsBanner } from "./_components/SuggestionsBanner";
import { SupportGoalsRow } from "./_components/SupportGoalsRow";
import { usePlanoOverview } from "./_components/usePlanoOverview";
import { useWorkspaceZeroSignals } from "./_components/useWorkspaceZeroSignals";
import { AlertCard } from "./_components/_dashboard/AlertCard";
import { ChartsGrid } from "./_components/_dashboard/ChartsGrid";
import { HeaderActions } from "./_components/_dashboard/HeaderActions";
import { KpiRow as DashboardKpiRow } from "./_components/_dashboard/KpiRow";
import { monthLabelToDateRange } from "./_components/_dashboard/dashboardHelpers";

export default function PlanoPage() {
  const { workspace, isLoading: wsLoading } = useWorkspace();
  const overview = usePlanoOverview(workspace?.id);
  const dashboard = useDashboardData(workspace?.id);
  const zero = useWorkspaceZeroSignals(workspace?.id);
  const router = useRouter();

  if (wsLoading || (workspace?.id && (overview.loading || zero.loading))) {
    return <PlanoLoadingState />;
  }
  if (overview.error) {
    return <PlanoErrorState error={overview.error} />;
  }
  if (!workspace) {
    return <PlanoNoWorkspaceState />;
  }

  const ifGoal = overview.goals.ifGoal;
  const isWorkspaceZero =
    !ifGoal && zero.decisionCount === 0 && zero.taskCount === 0;
  if (isWorkspaceZero) {
    return (
      <div className="mx-auto max-w-content px-6 py-8">
        <PageHeader
          title="Meu Plano"
          description="Sua vida financeira — onde está, onde vai, o que está em jogo"
        />
        <OnboardingHero
          hasIfGoal={false}
          hasDecisions={zero.decisionCount > 0}
        />
      </div>
    );
  }
  const handleBarClick = (label: string) => {
    const range = monthLabelToDateRange(label);
    if (range) {
      router.push(
        `/transactions?date_from=${range.date_from}&date_to=${range.date_to}`,
      );
    }
  };
  const handleSliceClick = (name: string) => {
    router.push(`/transactions?category=${encodeURIComponent(name)}`);
  };

  return (
    <div className="mx-auto max-w-content px-6 py-8">
      <PageHeader
        title="Meu Plano"
        description="Sua vida financeira — onde está, onde vai, o que está em jogo"
        actions={
          <>
            <ReportLinkAction snapshot={overview.patrimonio_snapshot} />
            <HeaderActions
              dataFreshness={dashboard.data?.data_freshness}
              loading={dashboard.loading}
              onRefresh={dashboard.load}
            />
          </>
        }
      />

      <PlanoKpiRow
        patrimonioSnapshot={overview.patrimonio_snapshot}
        ifGoal={ifGoal}
        ifProgress={overview.progress}
        aporteGoal={overview.goals.aporteGoal}
        loading={false}
      />

      <SuggestionsBanner workspaceId={workspace.id} />

      {ifGoal ? (
        <IFHeroCard
          goal={ifGoal}
          progress={overview.progress}
          patrimonio={overview.patrimonio_snapshot?.value ?? null}
        />
      ) : (
        <IFEmptyHero />
      )}

      <SupportGoalsRow
        aporteGoal={overview.goals.aporteGoal}
        dolarGoal={overview.goals.dolarGoal}
        alocacaoGoal={overview.goals.alocacaoGoal}
      />

      <details className="group my-8">
        <summary className="flex cursor-pointer list-none items-center gap-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground">
          <ChevronOpenIcon />
          Plano de Ação
          <span className="hidden text-[10px] font-normal normal-case tracking-normal opacity-70 sm:inline">
            (decisões · tarefas — abra para ver)
          </span>
          <div className="flex-1 border-t border-border" />
        </summary>
        <div className="mt-4">
          <DecisionsSection workspaceId={workspace.id} />

          <RisksSection workspaceId={workspace.id} />

          <div className="mt-6">
            <UpcomingTasksWidget />
          </div>

          {ifGoal && <LinkedTasksSection tasks={overview.linkedTasks} />}
        </div>
      </details>

      <CurrentMonthDetails
        loading={dashboard.loading}
        data={dashboard.data}
        onBarClick={handleBarClick}
        onSliceClick={handleSliceClick}
      />
    </div>
  );
}

interface CurrentMonthDetailsProps {
  loading: boolean;
  data: DashboardResponse | null;
  onBarClick: (label: string) => void;
  onSliceClick: (name: string) => void;
}

/** Onda 7 #1 — "Mês corrente" colapsado por default. Casal abre quando
 * algo pisca; default é fechado para reduzir scroll na leitura mensal
 * típica (estratégia → ação primeiro; análise como footer). */
function CurrentMonthDetails({
  loading,
  data,
  onBarClick,
  onSliceClick,
}: CurrentMonthDetailsProps) {
  return (
    <details className="group my-8">
      <summary className="flex cursor-pointer list-none items-center gap-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground">
        <ChevronOpenIcon />
        Mês corrente
        <span className="hidden text-[10px] font-normal normal-case tracking-normal opacity-70 sm:inline">
          (alertas, KPIs e charts do mês — abra para ver)
        </span>
        <span className="flex-1 border-t border-border" />
      </summary>
      <div className="mt-6">
        {data && data.alerts.length > 0 && (
          <div className="mb-6 space-y-3">
            {data.alerts.map((alert, i) => (
              <AlertCard key={`${alert.severity}-${i}`} alert={alert} />
            ))}
          </div>
        )}
        <DashboardKpiRow loading={loading} kpis={data?.kpis ?? []} />
        <ChartsGrid
          loading={loading}
          charts={data?.charts ?? []}
          onBarClick={onBarClick}
          onSliceClick={onSliceClick}
        />
      </div>
    </details>
  );
}

function ChevronOpenIcon() {
  return (
    <svg
      className="h-3 w-3 transition-transform group-open:rotate-90"
      viewBox="0 0 12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path d="M4.5 3l3 3-3 3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

interface DashboardState {
  data: DashboardResponse | null;
  loading: boolean;
  error: string | null;
  load: () => Promise<void>;
}

function useDashboardData(workspaceId: string | undefined): DashboardState {
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
    void load();
  }, [load]);
  return { data, loading, error, load };
}

function PlanoLoadingState() {
  return (
    <div className="mx-auto max-w-content px-6 py-8">
      <PageHeader title="Meu Plano" description="Carregando..." />
      <Skeleton className="mb-6 h-56 rounded-xl" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 rounded-xl" />
        ))}
      </div>
    </div>
  );
}

function PlanoErrorState({ error }: { error: string }) {
  return (
    <div className="mx-auto max-w-content px-6 py-8">
      <PageHeader title="Meu Plano" />
      <Card>
        <CardContent className="py-12">
          <div className="mx-auto max-w-md text-center">
            <AlertCircle className="mx-auto mb-4 h-12 w-12 text-destructive" />
            <h2 className="text-lg font-semibold">Erro ao carregar</h2>
            <p className="mt-2 text-sm text-muted-foreground">{error}</p>
            <Button
              className="mt-6"
              onClick={() => window.location.reload()}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Tentar novamente
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PlanoNoWorkspaceState() {
  return (
    <div className="mx-auto max-w-content px-6 py-8">
      <PageHeader title="Meu Plano" />
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">
            Nenhum workspace encontrado.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
