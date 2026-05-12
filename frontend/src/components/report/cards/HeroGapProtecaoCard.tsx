"use client";

import { AlertOctagon, ShieldCheck } from "lucide-react";

import { MonetaryValue } from "../MonetaryValue";
import { ReportCard } from "../ReportCard";
import {
  CATEGORY_LABELS,
  fiduciaryDisclaimer,
  type ProtectionBundle,
  type ProtectionCategory,
} from "./protectionBundle.types";

interface HeroGapProtecaoCardProps {
  bundle: ProtectionBundle | undefined;
  effectiveDate?: string | null;
}

interface AggregatedGap {
  totalActual: number;
  totalIdeal: number | null;
  totalGap: number | null;
  categoriesWithGap: ProtectionCategory[];
  state: "empty" | "covered" | "partial" | "critical";
}

interface GapTotals {
  totalActual: number;
  totalIdeal: number | null;
  totalGap: number | null;
  categoriesWithGap: ProtectionCategory[];
}

function sumGapAnalysis(gapAnalysis: ProtectionBundle["gap_analysis"]): GapTotals {
  let totalActual = 0;
  let totalIdeal: number | null = null;
  let totalGap: number | null = null;
  const categoriesWithGap: ProtectionCategory[] = [];
  for (const [key, value] of Object.entries(gapAnalysis)) {
    totalActual += value.actual_brl ?? 0;
    if (value.ideal_brl !== null && value.ideal_brl !== undefined) {
      totalIdeal = (totalIdeal ?? 0) + value.ideal_brl;
    }
    if (value.gap_brl !== null && value.gap_brl !== undefined && value.gap_brl > 0) {
      totalGap = (totalGap ?? 0) + value.gap_brl;
      categoriesWithGap.push(key as ProtectionCategory);
    }
  }
  return { totalActual, totalIdeal, totalGap, categoriesWithGap };
}

function aggregateGap(bundle: ProtectionBundle | undefined): AggregatedGap {
  if (!bundle || bundle.policies.length === 0) {
    return { totalActual: 0, totalIdeal: null, totalGap: null, categoriesWithGap: [], state: "empty" };
  }
  const gapAnalysis = bundle.gap_analysis ?? {};
  const totals = sumGapAnalysis(gapAnalysis);
  if (Object.keys(gapAnalysis).length === 0) {
    totals.totalActual = bundle.policies.reduce((acc, p) => acc + (p.coverage_brl ?? 0), 0);
  }
  return { ...totals, state: deriveState(totals.totalGap, totals.categoriesWithGap.length, totals.totalActual) };
}

function deriveState(
  totalGap: number | null,
  categoriesGapCount: number,
  totalActual: number,
): AggregatedGap["state"] {
  if (totalGap !== null && totalGap > 0 && categoriesGapCount >= 2) return "critical";
  if (totalGap !== null && totalGap > 0) return "partial";
  if (totalActual > 0) return "covered";
  return "empty";
}

function GapKpiRow({ agg }: { agg: AggregatedGap }) {
  return (
    <dl className="grid gap-4 sm:grid-cols-3">
      <KpiCell label="Capital segurado">
        <MonetaryValue value={agg.totalActual} size="kpi" compact data-testid="hero-gap-actual" />
      </KpiCell>
      <KpiCell label="Recomendado">
        {agg.totalIdeal === null ? (
          <span className="font-mono text-sm text-[var(--surface-muted-foreground)]">a calcular</span>
        ) : (
          <MonetaryValue value={agg.totalIdeal} size="kpi" compact data-testid="hero-gap-ideal" />
        )}
      </KpiCell>
      <KpiCell label="Gap">
        {agg.totalGap === null ? (
          <span className="font-mono text-sm text-[var(--surface-muted-foreground)]">—</span>
        ) : (
          <MonetaryValue value={agg.totalGap} size="kpi" compact signed data-testid="hero-gap-delta" />
        )}
      </KpiCell>
    </dl>
  );
}

function KpiCell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">{label}</dt>
      <dd className="mt-1">{children}</dd>
    </div>
  );
}

function GapCategoriesLine({ categories }: { categories: ProtectionCategory[] }) {
  if (categories.length === 0) return null;
  return (
    <p className="text-xs text-[var(--surface-muted-foreground)]">
      Categorias com gap material:{" "}
      <span className="font-medium text-[var(--surface-foreground)]">
        {categories.map((c) => CATEGORY_LABELS[c] ?? c).join(", ")}
      </span>
      .
    </p>
  );
}

/** S9-T04 (ADR-192 §D4) — KPI protagonista da Seção 9.
 *
 * "Capital segurado R$ X · Recomendado R$ Y · Gap R$ Z" com 4 estados
 * (empty/covered/partial/critical) e disclaimer fiduciário canônico.
 *
 * TODO: dados reais virão de T03 — gap_analysis + methodology_thresholds
 * vêm vazios até T03 mergear.
 */
export function HeroGapProtecaoCard({ bundle, effectiveDate }: HeroGapProtecaoCardProps) {
  const agg = aggregateGap(bundle);
  const isCritical = agg.state === "critical";
  const Icon = isCritical ? AlertOctagon : ShieldCheck;
  const iconColor = isCritical ? "text-[var(--semantic-loss)]" : "text-[var(--semantic-gain)]";
  const variant = isCritical ? "critical" : agg.state === "partial" ? "warn" : agg.state === "covered" ? "success" : "neutral";

  return (
    <ReportCard variant={variant} size="full" title="Gap de Proteção" headerRight={<Icon className={`h-6 w-6 ${iconColor}`} aria-hidden="true" />}>
      <section role="region" aria-labelledby="hero-gap-protecao-title" aria-describedby="hero-gap-protecao-disclaimer" className="space-y-4">
        <h4 id="hero-gap-protecao-title" className="sr-only">Resumo do gap de cobertura de seguros</h4>
        {agg.state === "empty" ? (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Nenhuma apólice cadastrada ainda. Cadastre seguros de vida, invalidez e patrimoniais para calcular sua exposição real.
          </p>
        ) : (
          <GapKpiRow agg={agg} />
        )}
        <GapCategoriesLine categories={agg.categoriesWithGap} />
        <p id="hero-gap-protecao-disclaimer" className="rounded-md bg-[var(--surface-muted)] p-3 text-[0.7rem] leading-relaxed text-[var(--surface-muted-foreground)]">
          {fiduciaryDisclaimer("wealth management", effectiveDate)}
        </p>
      </section>
    </ReportCard>
  );
}
