"use client";

/**
 * /plano — hub de metas financeiras do workspace (F8.1 + F8.5).
 *
 * Hierarquia: hero IF (meta-mãe) → metas de suporte (Aportes/Dolarização/
 * Alocação) → tarefas que destravam a IF.
 */

import { AlertCircle, RefreshCw } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspace } from "@/lib/WorkspaceProvider";

import { DecisionsSection } from "./_components/DecisionsSection";
import { IFEmptyHero, IFHeroCard } from "./_components/IFHeroCard";
import { LinkedTasksSection } from "./_components/LinkedTasksSection";
import { PlanoKpiRow } from "./_components/PlanoKpiRow";
import { SuggestionsBanner } from "./_components/SuggestionsBanner";
import { SupportGoalsRow } from "./_components/SupportGoalsRow";
import { usePlanoOverview } from "./_components/usePlanoOverview";

export default function PlanoPage() {
  const { workspace, isLoading: wsLoading } = useWorkspace();
  const { goals, linkedTasks, progress, patrimonio, loading, error } =
    usePlanoOverview(workspace?.id);

  if (wsLoading || (workspace?.id && loading)) {
    return <PlanoLoadingState />;
  }

  if (error) {
    return <PlanoErrorState error={error} />;
  }

  if (!workspace) {
    return <PlanoNoWorkspaceState />;
  }

  const ifGoal = goals.ifGoal;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader
        title="Meu Plano"
        description="Onde você está hoje, onde quer chegar"
      />

      <PlanoKpiRow
        patrimonio={patrimonio}
        ifGoal={ifGoal}
        ifProgress={progress}
        aporteGoal={goals.aporteGoal}
        loading={false}
      />

      <SuggestionsBanner workspaceId={workspace.id} />

      {ifGoal ? (
        <IFHeroCard goal={ifGoal} progress={progress} />
      ) : (
        <IFEmptyHero />
      )}

      <SupportGoalsRow
        aporteGoal={goals.aporteGoal}
        dolarGoal={goals.dolarGoal}
        alocacaoGoal={goals.alocacaoGoal}
      />

      <DecisionsSection workspaceId={workspace.id} />

      {ifGoal && <LinkedTasksSection tasks={linkedTasks} />}
    </div>
  );
}

function PlanoLoadingState() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
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
    <div className="mx-auto max-w-6xl px-6 py-8">
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
    <div className="mx-auto max-w-6xl px-6 py-8">
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
