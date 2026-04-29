"use client";

import { Target, TrendingUp, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { KPICard } from "@/components/KPICard";
import type {
  AporteGoalResponse,
  IFGoalResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

import type { IFProgress, PatrimonioSnapshot } from "./usePlanoOverview";

interface PlanoKpiRowProps {
  /** Onda 7 #4 (ADR-156) — fonte única de patrimônio em /plano. */
  patrimonioSnapshot: PatrimonioSnapshot | null;
  ifGoal: IFGoalResponse | null;
  ifProgress: IFProgress | null;
  aporteGoal: AporteGoalResponse | null;
  loading: boolean;
}

/** Direção E · Onda 4 — KPIs row no topo de /plano (executive summary).
 *
 * 3 KPIs essenciais: patrimônio líquido (do último relatório),
 * progresso da IF (se meta configurada), aporte mensal alvo (se meta
 * configurada). Cada KPI degrada para "—" se a fonte não está pronta.
 */
export function PlanoKpiRow({
  patrimonioSnapshot,
  ifGoal,
  ifProgress,
  aporteGoal,
  loading,
}: PlanoKpiRowProps) {
  if (loading) return <KpiRowSkeleton />;
  return (
    <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
      <KPICard
        label="Patrimônio líquido"
        value={formatPatrimonio(patrimonioSnapshot)}
        icon={Wallet}
        emphasis="primary"
      />
      <KPICard
        label="Progresso IF"
        value={formatIfProgress(ifProgress)}
        icon={Target}
        emphasis="secondary"
      />
      <KPICard
        label="Aporte mensal alvo"
        value={formatAporteMeta(ifGoal, aporteGoal)}
        icon={TrendingUp}
        emphasis="secondary"
      />
    </div>
  );
}

function KpiRowSkeleton() {
  const skeletons: LucideIcon[] = [Wallet, Target, TrendingUp];
  return (
    <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
      {skeletons.map((Icon, i) => (
        <KPICard key={i} label="" value="" icon={Icon} loading />
      ))}
    </div>
  );
}

function formatPatrimonio(snapshot: PatrimonioSnapshot | null): string {
  return snapshot == null ? "—" : formatCurrency(snapshot.value);
}

function formatIfProgress(progress: IFProgress | null): string {
  return progress == null ? "—" : `${progress.pct.toFixed(1)}%`;
}

function formatAporteMeta(
  ifGoal: IFGoalResponse | null,
  aporteGoal: AporteGoalResponse | null,
): string {
  const fromAporte = aporteGoal?.inputs.meta_aporte_mensal_brl;
  if (fromAporte != null) return `${formatCurrency(fromAporte)}/mês`;
  const fromIf = ifGoal?.derived.aporte_necessario_mensal_brl;
  if (fromIf != null) return `${formatCurrency(fromIf)}/mês`;
  return "—";
}
