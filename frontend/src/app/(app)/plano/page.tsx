"use client";

/**
 * /plano — overview do plano financeiro do workspace (F8.1 + F8.5).
 *
 * Dashboard multi-goal:
 * - Grid 2x2 com status cards para IF, Aportes, Dolarizacao, Alocacao
 * - Banner CTA quando 0 goals configuradas
 * - Barra de progresso IF + KPI cards + tarefas (backward compat)
 */

import Link from "next/link";
import { AlertCircle, RefreshCw } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspace } from "@/lib/WorkspaceProvider";

import { EmptyGoalsBanner } from "./_components/EmptyGoalsBanner";
import { GoalsOverviewGrid } from "./_components/GoalsOverviewGrid";
import { IFKPIsRow } from "./_components/IFKPIsRow";
import { IFParamsCard } from "./_components/IFParamsCard";
import { IFProgressBar } from "./_components/IFProgressBar";
import { LinkedTasksSection } from "./_components/LinkedTasksSection";
import { usePlanoOverview } from "./_components/usePlanoOverview";

export default function PlanoPage() {
  const { workspace, isLoading: wsLoading } = useWorkspace();
  const { goals, linkedTasks, progress, loading, error } = usePlanoOverview(
    workspace?.id
  );

  if (wsLoading || (workspace?.id && loading)) {
    return <PlanoLoadingState />;
  }

  if (error) {
    return <PlanoErrorState error={error} />;
  }

  if (!workspace) {
    return <PlanoNoWorkspaceState />;
  }

  const configuredCount = [
    goals.ifGoal,
    goals.aporteGoal,
    goals.dolarGoal,
    goals.alocacaoGoal,
  ].filter(Boolean).length;

  const ifGoal = goals.ifGoal;

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader
        title="Meu Plano"
        description="Metas financeiras e progresso"
        actions={
          ifGoal ? (
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link href="/plano/meta-if" />}
            >
              Revisar meta IF
            </Button>
          ) : undefined
        }
      />

      {configuredCount === 0 && <EmptyGoalsBanner />}

      <GoalsOverviewGrid
        ifGoal={goals.ifGoal}
        aporteGoal={goals.aporteGoal}
        dolarGoal={goals.dolarGoal}
        alocacaoGoal={goals.alocacaoGoal}
      />

      {ifGoal && (
        <>
          {progress && (
            <IFProgressBar
              pct={progress.pct}
              faltante={progress.faltante}
              patrimonio={progress.patrimonio}
              metaBrl={ifGoal.derived.if_meta_brl}
            />
          )}
          <IFKPIsRow goal={ifGoal} />
          <IFParamsCard goal={ifGoal} />
          <LinkedTasksSection tasks={linkedTasks} />
        </>
      )}
    </div>
  );
}

function PlanoLoadingState() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader title="Meu Plano" description="Carregando..." />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-28 rounded-lg" />
        ))}
      </div>
    </div>
  );
}

function PlanoErrorState({ error }: { error: string }) {
  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
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
    <div className="mx-auto max-w-5xl px-6 py-8">
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
