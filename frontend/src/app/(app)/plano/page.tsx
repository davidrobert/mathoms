"use client";

/**
 * /plano — overview do plano financeiro do workspace (F8.1).
 *
 * Mostra a meta IF vigente (se existir) com:
 * - Barra de progresso (% do patrimônio-alvo)
 * - Cards: patrimônio-alvo, aporte mensal necessário, renda passiva projetada
 * - Tarefas ligadas à meta (com sugestão quando 0)
 * - Link para wizard se ainda não configurou
 *
 * P0: skeleton só enquanto workspace carrega ou meta IF está sendo buscada
 * (sem `workspace.id`, não manter `loading=true` — evita spinner infinito).
 * P1: barra de progresso % meta IF
 * P4: sugestão de tarefas quando 0 ligadas
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  ListTodo,
  RefreshCw,
  Sparkles,
  Target,
  TrendingUp,
  Wallet,
} from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { KPICard } from "@/components/KPICard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

import { useWorkspace } from "@/lib/WorkspaceProvider";
import {
  getIFGoal,
  computeIFGoal,
  ifMonthlyContributionDisplay,
  listReports,
  listTasksForGoal,
  ApiError,
  type IFGoalResponse,
  type TaskResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { TaskPriorityChip } from "@/components/tasks/TaskPriorityChip";
import { TaskStatusPill } from "@/components/tasks/TaskStatusPill";
import { TaskDeadlineBadge } from "@/components/tasks/TaskDeadlineBadge";


export default function PlanoPage() {
  const { workspace, isLoading: wsLoading } = useWorkspace();
  const [goal, setGoal] = useState<IFGoalResponse | null>(null);
  const [linkedTasks, setLinkedTasks] = useState<TaskResponse[]>([]);
  const [progress, setProgress] = useState<{
    pct: number;
    faltante: number;
    patrimonio: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [notConfigured, setNotConfigured] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspace?.id) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setNotConfigured(false);
      setError(null);

      try {
        // 1. Busca meta IF vigente
        const goalData = await getIFGoal(workspace!.id);
        if (cancelled) return;
        setGoal(goalData);

        // 2. Em paralelo: tasks ligadas + progresso via patrimonio do último report
        const [tasksResult, progressResult] = await Promise.allSettled([
          listTasksForGoal(workspace!.id, goalData.id, false),
          loadProgress(workspace!.id, goalData),
        ]);

        if (cancelled) return;

        if (tasksResult.status === "fulfilled") {
          setLinkedTasks(tasksResult.value.tasks);
        }
        // Se tasks falhar, não é crítico — mostra 0 tasks

        if (progressResult.status === "fulfilled" && progressResult.value) {
          setProgress(progressResult.value);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotConfigured(true);
        } else {
          setError(
            err instanceof Error
              ? err.message
              : "Erro ao carregar o plano. Tente novamente."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [workspace?.id]);

  /** Calcula progresso usando patrimônio do último relatório. */
  async function loadProgress(
    wsId: string,
    goalData: IFGoalResponse
  ): Promise<{ pct: number; faltante: number; patrimonio: number } | null> {
    try {
      const { reports } = await listReports();
      // Pega o mais recente com patrimônio
      const latest = reports.find((r) => r.patrimonio_liquido != null);
      if (!latest?.patrimonio_liquido) return null;

      const result = await computeIFGoal(wsId, {
        inputs: goalData.inputs,
        patrimonio_atual_brl: latest.patrimonio_liquido,
      });

      if (result.percentual_conquistado != null && result.faltante_brl != null) {
        return {
          pct: result.percentual_conquistado,
          faltante: result.faltante_brl,
          patrimonio: latest.patrimonio_liquido,
        };
      }
    } catch {
      // Progresso é nice-to-have, não bloqueia a página
    }
    return null;
  }

  // ─── Loading ───

  if (wsLoading || (workspace?.id && loading)) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-8">
        <PageHeader title="Meu Plano" description="Carregando..." />
        <Skeleton className="mb-6 h-4 w-full rounded-full" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <KPICard label="" value="" loading icon={Target} />
          <KPICard label="" value="" loading icon={TrendingUp} />
          <KPICard label="" value="" loading icon={Wallet} />
        </div>
      </div>
    );
  }

  // ─── Error ───

  if (error) {
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

  // ─── No workspace ───

  if (!workspace) {
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

  // ─── Not configured (wizard CTA) ───

  if (notConfigured || !goal) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-8">
        <PageHeader
          title="Meu Plano"
          description="Vamos definir sua meta de Independência Financeira"
        />
        <Card>
          <CardContent className="py-12">
            <div className="mx-auto max-w-md text-center">
              <Target className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
              <h2 className="text-lg font-semibold">
                Configure sua meta IF
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Em 4 passos, definimos o patrimônio-alvo e o aporte
                mensal necessário para você viver de renda passiva.
              </p>
              <Button
                nativeButton={false}
                render={<Link href="/plano/meta-if/wizard" />}
                className="mt-6"
              >
                Começar <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ─── Main view ───

  const d = goal.derived;
  const i = goal.inputs;
  const trsConservPct = i.taxa_retirada_conservadora_pct ?? 4.0;

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader
        title="Meu Plano"
        description="Meta de Independência Financeira"
        actions={
          <Button
            variant="outline"
            nativeButton={false}
            render={<Link href="/plano/meta-if" />}
          >
            Revisar meta
          </Button>
        }
      />

      {/* P1: Barra de progresso */}
      {progress && (
        <Card className="mb-6">
          <CardContent className="py-5">
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Progresso: <span className="font-mono tabular-nums font-medium text-foreground">{formatCurrency(progress.patrimonio)}</span> de{" "}
                <span className="font-mono tabular-nums font-medium text-foreground">{formatCurrency(d.if_meta_brl)}</span>
              </span>
              <span className="font-mono tabular-nums font-semibold">
                {progress.pct.toFixed(1)}%
              </span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-400 transition-all duration-700"
                style={{ width: `${Math.min(progress.pct, 100)}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Faltam <span className="font-mono tabular-nums font-medium">{formatCurrency(progress.faltante)}</span> para a meta
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <KPICard
          label="Patrimônio-alvo (IF)"
          value={formatCurrency(d.if_meta_brl)}
          icon={Target}
        />
        <KPICard
          label="Renda passiva projetada"
          value={`${formatCurrency(i.renda_passiva_mensal_brl)}/mês`}
          icon={TrendingUp}
        />
        <KPICard
          label="Aporte mensal necessário"
          value={`${formatCurrency(ifMonthlyContributionDisplay(d))}/mês`}
          icon={Wallet}
        />
      </div>
      {d.aporte_mensal_com_patrimonio_atual_brl != null &&
        d.patrimonio_atual_utilizado_brl != null &&
        d.aporte_mensal_com_patrimonio_atual_brl !==
          d.aporte_necessario_mensal_brl && (
          <p className="-mt-2 mb-6 text-xs text-muted-foreground">
            Considera patrimônio líquido do último relatório (
            {formatCurrency(d.patrimonio_atual_utilizado_brl)}). Cenário
            partindo de zero:{" "}
            <span className="font-mono tabular-nums">
              {formatCurrency(d.aporte_necessario_mensal_brl)}/mês
            </span>
            .
          </p>
        )}

      <Card className="mt-6">
        <CardContent className="py-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Parâmetros atuais
          </h2>
          <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm md:grid-cols-4">
            <div>
              <dt className="text-muted-foreground">TRS operacional</dt>
              <dd className="mt-1 font-mono tabular-nums">
                {i.trs_pct.toFixed(1)}% a.a.
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Retorno real esperado</dt>
              <dd className="mt-1 font-mono tabular-nums">
                {i.retorno_real_anual_pct.toFixed(1)}% a.a.
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Horizonte</dt>
              <dd className="mt-1 font-mono tabular-nums">
                {i.horizonte_anos} anos
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">
                Meta conservadora ({trsConservPct.toFixed(1)}%)
              </dt>
              <dd className="mt-1 font-mono tabular-nums">
                {formatCurrency(d.if_meta_conservadora_brl)}
              </dd>
            </div>
          </dl>
          <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline">Vigente desde</Badge>
            <span>{new Date(goal.effective_from).toLocaleDateString("pt-BR")}</span>
            {goal.is_template && (
              <Badge variant="secondary">Template — personalize</Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* F8.3 + P4: Tarefas ligadas a esta meta */}
      <Card className="mt-6">
        <CardContent className="py-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              <ListTodo className="h-4 w-4" />
              Tarefas que destravam esta meta
              {linkedTasks.length > 0 && (
                <span className="ml-1 font-mono text-xs tabular-nums normal-case">
                  ({linkedTasks.length})
                </span>
              )}
            </h2>
            <Button
              variant="ghost"
              size="xs"
              nativeButton={false}
              render={<Link href="/plano-de-acao" />}
            >
              Ver todas <ArrowRight className="ml-1 h-3 w-3" />
            </Button>
          </div>

          {linkedTasks.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-muted/20 px-4 py-6 text-center">
              <ListTodo className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                Nenhuma tarefa ligada a esta meta.
              </p>
              <div className="mt-3 flex flex-col items-center gap-2 sm:flex-row sm:justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  nativeButton={false}
                  render={<Link href="/plano-de-acao" />}
                >
                  <ListTodo className="mr-1.5 h-3.5 w-3.5" />
                  Criar tarefa manual
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  nativeButton={false}
                  render={<Link href="/plano-de-acao/sugestoes" />}
                >
                  <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                  Ver sugestões automáticas
                </Button>
              </div>
            </div>
          ) : (
            <ul className="space-y-2">
              {linkedTasks.map((task) => (
                <li
                  key={task.id}
                  className="flex items-start gap-3 rounded-md border border-transparent bg-muted/30 px-3 py-2 text-sm hover:border-border"
                >
                  <span className="mt-0.5 font-mono text-xs tabular-nums text-muted-foreground">
                    #{task.number}
                  </span>
                  <div className="flex-1">
                    <p className="font-medium">{task.title}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <TaskPriorityChip priority={task.priority} />
                      <Badge variant="outline">{task.category}</Badge>
                      <TaskStatusPill status={task.status} />
                      <TaskDeadlineBadge task={task} />
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
