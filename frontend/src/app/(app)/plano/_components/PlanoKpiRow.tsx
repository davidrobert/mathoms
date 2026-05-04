"use client";

import Link from "next/link";
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
 *
 * Onda 10 #2 — quando há um Report disponível, cada KPI vira link para
 * a seção do relatório que aprofunda o número (Patrimônio → §S1, IF →
 * §S7, Aporte → §S2). Padrão de scroll+highlight reusado de Onda 7 #3.
 */
export function PlanoKpiRow({
  patrimonioSnapshot,
  ifGoal,
  ifProgress,
  aporteGoal,
  loading,
}: PlanoKpiRowProps) {
  if (loading) return <KpiRowSkeleton />;
  const reportId = patrimonioSnapshot?.sourceReportId ?? null;
  return (
    <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
      <KpiLinkCard
        reportId={reportId}
        sectionId="S1"
        label="Patrimônio líquido"
      >
        <KPICard
          label="Patrimônio líquido"
          value={formatPatrimonio(patrimonioSnapshot)}
          icon={Wallet}
          emphasis="primary"
        />
      </KpiLinkCard>
      <KpiLinkCard reportId={reportId} sectionId="S7" label="Progresso IF">
        <KPICard
          label="Progresso IF"
          value={formatIfProgress(ifProgress)}
          icon={Target}
          emphasis="secondary"
        />
      </KpiLinkCard>
      <KpiLinkCard
        reportId={reportId}
        sectionId="S2"
        label="Aporte mensal alvo"
      >
        <KPICard
          label="Aporte mensal alvo"
          value={formatAporteMeta(ifGoal, aporteGoal)}
          icon={TrendingUp}
          emphasis="secondary"
        />
      </KpiLinkCard>
    </div>
  );
}

interface KpiLinkCardProps {
  reportId: string | null;
  sectionId: string;
  label: string;
  children: React.ReactNode;
}

function KpiLinkCard({
  reportId,
  sectionId,
  label,
  children,
}: KpiLinkCardProps) {
  if (!reportId) return <>{children}</>;
  return (
    <Link
      href={`/reports/${reportId}#${sectionId}`}
      aria-label={`${label} — ver no relatório §${sectionId}`}
      className="block rounded-[var(--radius-card)] transition-shadow hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
    >
      {children}
    </Link>
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
