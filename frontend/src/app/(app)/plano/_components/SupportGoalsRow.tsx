"use client";

import { DollarSign, PieChart, Wallet } from "lucide-react";

import type {
  AlocacaoGoalResponse,
  AporteGoalResponse,
  DolarGoalResponse,
} from "@/lib/api";
import { formatCurrency, formatUSDPtBR } from "@/lib/format";
import { SectionHeading } from "@/components/ui/SectionHeading";

import { GoalCard, type GoalCardProps } from "./GoalCard";

interface SupportGoalsRowProps {
  aporteGoal: AporteGoalResponse | null;
  dolarGoal: DolarGoalResponse | null;
  alocacaoGoal: AlocacaoGoalResponse | null;
}

export function SupportGoalsRow({
  aporteGoal,
  dolarGoal,
  alocacaoGoal,
}: SupportGoalsRowProps) {
  const cards: GoalCardProps[] = [
    aporteCardProps(aporteGoal),
    dolarCardProps(dolarGoal),
    alocacaoCardProps(alocacaoGoal),
  ];
  return (
    <section className="mb-6">
      <SectionHeading label="Metas de suporte" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((p) => (
          <GoalCard key={p.title} {...p} />
        ))}
      </div>
    </section>
  );
}

function aporteCardProps(goal: AporteGoalResponse | null): GoalCardProps {
  return {
    icon: Wallet,
    title: "Aportes",
    density: "compact",
    configured: !!goal,
    href: goal ? "/plano/aportes" : "/plano/aportes/wizard",
    value: goal
      ? `${formatCurrency(goal.inputs.meta_aporte_mensal_brl)}/mês`
      : undefined,
    subtitle: goal ? `Dia ${goal.inputs.dia_aporte}` : undefined,
  };
}

function dolarCardProps(goal: DolarGoalResponse | null): GoalCardProps {
  return {
    icon: DollarSign,
    title: "Dolarização",
    density: "compact",
    configured: !!goal,
    href: goal ? "/plano/dolarizacao" : "/plano/dolarizacao/wizard",
    value: goal ? formatUSDPtBR(goal.inputs.meta_usd) : undefined,
    subtitle: goal
      ? `~${goal.derived.horizonte_estimado_meses} meses`
      : undefined,
  };
}

function alocacaoCardProps(goal: AlocacaoGoalResponse | null): GoalCardProps {
  const rf = goal
    ? goal.inputs.rf_pos_pct + goal.inputs.rf_pre_pct + goal.inputs.rf_ipca_pct
    : 0;
  const rv = goal ? goal.inputs.acoes_br_pct + goal.inputs.acoes_int_pct : 0;
  return {
    icon: PieChart,
    title: "Alocação",
    density: "compact",
    configured: !!goal,
    href: goal ? "/plano/alocacao" : "/plano/alocacao/wizard",
    value: goal ? `RF ${rf}% · RV ${rv}%` : undefined,
    subtitle: goal
      ? `FIIs ${goal.inputs.fiis_pct}% · Caixa ${goal.inputs.caixa_pct}%`
      : undefined,
  };
}
