"use client";

import Link from "next/link";
import { ArrowRight, Target } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { MonetaryValue } from "@/components/report/MonetaryValue";
import {
  ifMonthlyContributionDisplay,
  type IFGoalResponse,
} from "@/lib/api";

import type { IFProgress } from "./usePlanoOverview";

interface IFHeroCardProps {
  goal: IFGoalResponse;
  progress: IFProgress | null;
  /** Onda 7 #4 (ADR-156) — patrimônio vem de `usePlanoOverview.patrimonio_snapshot.value`. */
  patrimonio: number | null;
}

export function IFHeroCard({ goal, progress, patrimonio }: IFHeroCardProps) {
  return (
    <Card className="mb-6">
      <CardContent className="py-6">
        <IFHeroHeader goal={goal} />
        {progress && patrimonio != null && (
          <IFHeroProgress
            goal={goal}
            progress={progress}
            patrimonio={patrimonio}
          />
        )}
        <div className="mt-6 border-t border-border" />
        <IFHeroKPIs goal={goal} />
        <IFHeroParams goal={goal} />
      </CardContent>
    </Card>
  );
}

function IFHeroHeader({ goal }: { goal: IFGoalResponse }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h2 className="font-heading text-lg font-semibold leading-tight">
          Independência Financeira
        </h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Vigente desde{" "}
          {new Date(goal.effective_from).toLocaleDateString("pt-BR")}
          {goal.is_template && (
            <Badge variant="secondary" className="ml-2 text-[10px]">
              Template — personalize
            </Badge>
          )}
        </p>
      </div>
      <Button
        variant="ghost"
        size="sm"
        nativeButton={false}
        render={<Link href="/plano/meta-if" />}
      >
        Revisar <ArrowRight className="ml-1 h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

function IFHeroProgress({
  goal,
  progress,
  patrimonio,
}: {
  goal: IFGoalResponse;
  progress: IFProgress;
  patrimonio: number;
}) {
  const meta = goal.derived.if_meta_brl;
  return (
    <div className="mt-5">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div className="min-w-0">
          <MonetaryValue
            value={patrimonio}
            size="hero"
            className="block leading-none"
            data-testid="if-hero-patrimonio"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            de <MonetaryValue value={meta} />
          </p>
        </div>
        <p className="font-mono text-2xl font-semibold tabular-nums">
          {progress.pct.toFixed(1)}%
        </p>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-gradient-to-r from-[var(--brand-info)] to-[var(--brand-accent)] transition-all duration-700"
          style={{ width: `${Math.min(progress.pct, 100)}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        Faltam <MonetaryValue value={progress.faltante} /> para a meta
      </p>
    </div>
  );
}

function IFHeroKPIs({ goal }: { goal: IFGoalResponse }) {
  const i = goal.inputs;
  const d = goal.derived;
  const aporteDisplay = ifMonthlyContributionDisplay(d);
  const showCenarioZero =
    d.aporte_mensal_com_patrimonio_atual_brl != null &&
    d.patrimonio_atual_utilizado_brl != null &&
    d.aporte_mensal_com_patrimonio_atual_brl !==
      d.aporte_necessario_mensal_brl;

  return (
    <dl className="mt-6 grid grid-cols-1 divide-y divide-border sm:grid-cols-3 sm:divide-y-0 sm:divide-x">
      <KPIColumn
        label="Patrimônio-alvo"
        value={<MonetaryValue value={d.if_meta_brl} />}
        position="first"
      />
      <KPIColumn
        label="Renda passiva projetada"
        value={
          <>
            <MonetaryValue value={i.renda_passiva_mensal_brl} />
            /mês
          </>
        }
        position="middle"
      />
      <KPIColumn
        label="Aporte mensal necessário"
        value={
          <>
            <MonetaryValue value={aporteDisplay} />
            /mês
          </>
        }
        position="last"
        footnote={
          showCenarioZero && d.patrimonio_atual_utilizado_brl != null ? (
            <>
              partindo de zero:{" "}
              <MonetaryValue value={d.aporte_necessario_mensal_brl} />
              /mês
            </>
          ) : undefined
        }
      />
    </dl>
  );
}

interface KPIColumnProps {
  label: string;
  value: React.ReactNode;
  position: "first" | "middle" | "last";
  footnote?: React.ReactNode;
}

function KPIColumn({ label, value, position, footnote }: KPIColumnProps) {
  const padding =
    position === "first"
      ? "py-3 sm:py-0 sm:pr-6"
      : position === "last"
        ? "py-3 sm:py-0 sm:pl-6"
        : "py-3 sm:py-0 sm:px-6";
  return (
    <div className={padding}>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-lg font-medium tabular-nums">{value}</dd>
      {footnote && (
        <p className="mt-0.5 text-[11px] text-muted-foreground">{footnote}</p>
      )}
    </div>
  );
}

function IFHeroParams({ goal }: { goal: IFGoalResponse }) {
  const i = goal.inputs;
  const d = goal.derived;
  const conservadoraPct = (i.taxa_retirada_conservadora_pct ?? 4.0).toFixed(1);
  return (
    <details className="group mt-5">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ChevronIcon />
        Parâmetros do cálculo
      </summary>
      <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-xs sm:grid-cols-4">
        <ParamItem
          label="TRS operacional"
          value={`${i.trs_pct.toFixed(1)}% a.a.`}
        />
        <ParamItem
          label="Retorno real"
          value={`${i.retorno_real_anual_pct.toFixed(1)}% a.a.`}
        />
        <ParamItem label="Horizonte" value={`${i.horizonte_anos} anos`} />
        <ParamItem
          label={`Meta conservadora (${conservadoraPct}%)`}
          value={<MonetaryValue value={d.if_meta_conservadora_brl} />}
        />
      </dl>
    </details>
  );
}

function ParamItem({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 font-mono tabular-nums">{value}</dd>
    </div>
  );
}

function ChevronIcon() {
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

export function IFEmptyHero() {
  return (
    <Card className="mb-6 border-dashed">
      <CardContent className="py-0">
        <EmptyState
          icon={Target}
          title="Configure sua meta de Independência Financeira"
          description="Defina renda passiva-alvo, retorno esperado e horizonte. A partir daí o Mathoms calcula patrimônio-alvo, aporte necessário e acompanha seu progresso a cada relatório."
          layout="hero"
          ctas={[{ label: "Começar", href: "/plano/meta-if/wizard" }]}
        />
      </CardContent>
    </Card>
  );
}
