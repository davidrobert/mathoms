"use client";

/**
 * /plano — overview do plano financeiro do workspace (F8.1 + F8.5).
 *
 * Dashboard multi-goal:
 * - Grid 2x2 com status cards para IF, Aportes, Dolarizacao, Alocacao
 * - Banner CTA quando 0 goals configuradas
 * - Barra de progresso IF + KPI cards + tarefas (backward compat)
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  DollarSign,
  ListTodo,
  PieChart,
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
  getAporteGoal,
  getDolarGoal,
  getAlocacaoGoal,
  computeIFGoal,
  ifMonthlyContributionDisplay,
  listReports,
  listTasksForGoal,
  ApiError,
  type IFGoalResponse,
  type AporteGoalResponse,
  type DolarGoalResponse,
  type AlocacaoGoalResponse,
  type TaskResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { TaskPriorityChip } from "@/components/tasks/TaskPriorityChip";
import { TaskStatusPill } from "@/components/tasks/TaskStatusPill";
import { TaskDeadlineBadge } from "@/components/tasks/TaskDeadlineBadge";


interface GoalStatus {
  ifGoal: IFGoalResponse | null;
  aporteGoal: AporteGoalResponse | null;
  dolarGoal: DolarGoalResponse | null;
  alocacaoGoal: AlocacaoGoalResponse | null;
}

export default function PlanoPage() {
  const { workspace, isLoading: wsLoading } = useWorkspace();
  const [goals, setGoals] = useState<GoalStatus>({
    ifGoal: null,
    aporteGoal: null,
    dolarGoal: null,
    alocacaoGoal: null,
  });
  const [linkedTasks, setLinkedTasks] = useState<TaskResponse[]>([]);
  const [progress, setProgress] = useState<{
    pct: number;
    faltante: number;
    patrimonio: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspace?.id) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        // Fetch all 4 goals in parallel
        const [ifResult, aporteResult, dolarResult, alocacaoResult] =
          await Promise.allSettled([
            getIFGoal(workspace!.id),
            getAporteGoal(workspace!.id),
            getDolarGoal(workspace!.id),
            getAlocacaoGoal(workspace!.id),
          ]);

        if (cancelled) return;

        const ifGoal =
          ifResult.status === "fulfilled" ? ifResult.value : null;
        const aporteGoal =
          aporteResult.status === "fulfilled" ? aporteResult.value : null;
        const dolarGoal =
          dolarResult.status === "fulfilled" ? dolarResult.value : null;
        const alocacaoGoal =
          alocacaoResult.status === "fulfilled"
            ? alocacaoResult.value
            : null;

        setGoals({ ifGoal, aporteGoal, dolarGoal, alocacaoGoal });

        // IF-specific: tasks + progress
        if (ifGoal) {
          const [tasksResult, progressResult] = await Promise.allSettled([
            listTasksForGoal(workspace!.id, ifGoal.id, false),
            loadProgress(workspace!.id, ifGoal),
          ]);

          if (cancelled) return;

          if (tasksResult.status === "fulfilled") {
            setLinkedTasks(tasksResult.value.tasks);
          }
          if (progressResult.status === "fulfilled" && progressResult.value) {
            setProgress(progressResult.value);
          }
        }
      } catch (err: unknown) {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "Erro ao carregar o plano. Tente novamente."
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [workspace?.id]);

  async function loadProgress(
    wsId: string,
    goalData: IFGoalResponse
  ): Promise<{ pct: number; faltante: number; patrimonio: number } | null> {
    try {
      const { reports } = await listReports(workspace!.id);
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
      // Progresso is nice-to-have
    }
    return null;
  }

  const configuredCount = [
    goals.ifGoal,
    goals.aporteGoal,
    goals.dolarGoal,
    goals.alocacaoGoal,
  ].filter(Boolean).length;

  // ---- Loading ----

  if (wsLoading || (workspace?.id && loading)) {
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

  // ---- Error ----

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

  // ---- No workspace ----

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

  // ---- Main view ----

  const goal = goals.ifGoal;
  const d = goal?.derived;
  const i = goal?.inputs;

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader
        title="Meu Plano"
        description="Metas financeiras e progresso"
        actions={
          goal ? (
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

      {/* Banner CTA when no goals configured */}
      {configuredCount === 0 && (
        <Card className="mb-6 border-dashed">
          <CardContent className="py-8">
            <div className="mx-auto max-w-lg text-center">
              <Target className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
              <h2 className="text-lg font-semibold">
                Configure suas metas financeiras
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Configure suas metas financeiras para gerar relatorios
                completos e acompanhar seu progresso.
              </p>
              <Button
                nativeButton={false}
                render={<Link href="/plano/meta-if/wizard" />}
                className="mt-6"
              >
                Comecar <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Goals overview grid (2x2) */}
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Meta IF */}
        <GoalCard
          icon={Target}
          title="Meta IF"
          configured={!!goals.ifGoal}
          href={goals.ifGoal ? "/plano/meta-if" : "/plano/meta-if/wizard"}
          value={
            goals.ifGoal
              ? formatCurrency(goals.ifGoal.derived.if_meta_brl)
              : undefined
          }
          subtitle={
            goals.ifGoal
              ? `Renda ${formatCurrency(goals.ifGoal.inputs.renda_passiva_mensal_brl)}/mes`
              : undefined
          }
        />

        {/* Aportes */}
        <GoalCard
          icon={Wallet}
          title="Aportes"
          configured={!!goals.aporteGoal}
          href={goals.aporteGoal ? "/plano/aportes" : "/plano/aportes/wizard"}
          value={
            goals.aporteGoal
              ? `${formatCurrency(goals.aporteGoal.inputs.meta_aporte_mensal_brl)}/mes`
              : undefined
          }
          subtitle={
            goals.aporteGoal
              ? `Dia ${goals.aporteGoal.inputs.dia_aporte}`
              : undefined
          }
        />

        {/* Dolarizacao */}
        <GoalCard
          icon={DollarSign}
          title="Dolarizacao"
          configured={!!goals.dolarGoal}
          href={
            goals.dolarGoal
              ? "/plano/dolarizacao"
              : "/plano/dolarizacao/wizard"
          }
          value={
            goals.dolarGoal
              ? `US$ ${goals.dolarGoal.inputs.meta_usd.toLocaleString("pt-BR")}`
              : undefined
          }
          subtitle={
            goals.dolarGoal
              ? `~${goals.dolarGoal.derived.horizonte_estimado_meses} meses`
              : undefined
          }
        />

        {/* Alocacao */}
        <GoalCard
          icon={PieChart}
          title="Alocacao"
          configured={!!goals.alocacaoGoal}
          href={
            goals.alocacaoGoal
              ? "/plano/alocacao"
              : "/plano/alocacao/wizard"
          }
          value={
            goals.alocacaoGoal
              ? `RF ${goals.alocacaoGoal.inputs.renda_fixa_pct}% · RV ${goals.alocacaoGoal.inputs.acoes_pct}%`
              : undefined
          }
          subtitle={
            goals.alocacaoGoal
              ? `Imov ${goals.alocacaoGoal.inputs.imoveis_reits_pct}% · USD ${goals.alocacaoGoal.inputs.liquidez_usd_pct}%`
              : undefined
          }
        />
      </div>

      {/* IF progress bar (backward compat) */}
      {goal && d && i && (
        <>
          {progress && (
            <Card className="mb-6">
              <CardContent className="py-5">
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    Progresso:{" "}
                    <span className="font-mono tabular-nums font-medium text-foreground">
                      {formatCurrency(progress.patrimonio)}
                    </span>{" "}
                    de{" "}
                    <span className="font-mono tabular-nums font-medium text-foreground">
                      {formatCurrency(d.if_meta_brl)}
                    </span>
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
                  Faltam{" "}
                  <span className="font-mono tabular-nums font-medium">
                    {formatCurrency(progress.faltante)}
                  </span>{" "}
                  para a meta
                </p>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <KPICard
              label="Patrimonio-alvo (IF)"
              value={formatCurrency(d.if_meta_brl)}
              icon={Target}
            />
            <KPICard
              label="Renda passiva projetada"
              value={`${formatCurrency(i.renda_passiva_mensal_brl)}/mes`}
              icon={TrendingUp}
            />
            <KPICard
              label="Aporte mensal necessario"
              value={`${formatCurrency(ifMonthlyContributionDisplay(d))}/mes`}
              icon={Wallet}
            />
          </div>
          {d.aporte_mensal_com_patrimonio_atual_brl != null &&
            d.patrimonio_atual_utilizado_brl != null &&
            d.aporte_mensal_com_patrimonio_atual_brl !==
              d.aporte_necessario_mensal_brl && (
              <p className="-mt-2 mb-6 text-xs text-muted-foreground">
                Considera patrimonio liquido do ultimo relatorio (
                {formatCurrency(d.patrimonio_atual_utilizado_brl)}). Cenario
                partindo de zero:{" "}
                <span className="font-mono tabular-nums">
                  {formatCurrency(d.aporte_necessario_mensal_brl)}/mes
                </span>
                .
              </p>
            )}

          <Card className="mt-6">
            <CardContent className="py-6">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Parametros atuais
              </h2>
              <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm md:grid-cols-4">
                <div>
                  <dt className="text-muted-foreground">TRS operacional</dt>
                  <dd className="mt-1 font-mono tabular-nums">
                    {i.trs_pct.toFixed(1)}% a.a.
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">
                    Retorno real esperado
                  </dt>
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
                    Meta conservadora (
                    {(i.taxa_retirada_conservadora_pct ?? 4.0).toFixed(1)}%)
                  </dt>
                  <dd className="mt-1 font-mono tabular-nums">
                    {formatCurrency(d.if_meta_conservadora_brl)}
                  </dd>
                </div>
              </dl>
              <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                <Badge variant="outline">Vigente desde</Badge>
                <span>
                  {new Date(goal.effective_from).toLocaleDateString("pt-BR")}
                </span>
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
                      Ver sugestoes automaticas
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
        </>
      )}
    </div>
  );
}


// ─── Goal Status Card ────────────────────────────────────────────────

function GoalCard({
  icon: Icon,
  title,
  configured,
  href,
  value,
  subtitle,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  configured: boolean;
  href: string;
  value?: string;
  subtitle?: string;
}) {
  return (
    <Card className="transition-colors hover:border-border">
      <Link href={href} className="block">
        <CardContent className="flex items-start gap-4 py-5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
            <Icon className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold">{title}</h3>
              {configured ? (
                <Badge variant="outline" className="text-xs">
                  Configurada
                </Badge>
              ) : (
                <Badge variant="secondary" className="text-xs">
                  Pendente
                </Badge>
              )}
            </div>
            {configured && value ? (
              <>
                <p className="mt-1 font-mono text-sm tabular-nums font-medium">
                  {value}
                </p>
                {subtitle && (
                  <p className="text-xs text-muted-foreground">{subtitle}</p>
                )}
              </>
            ) : (
              <p className="mt-1 text-xs text-muted-foreground">
                Clique para configurar
              </p>
            )}
          </div>
          <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
        </CardContent>
      </Link>
    </Card>
  );
}
