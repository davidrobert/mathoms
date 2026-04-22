"use client";

import { Target, TrendingUp, Wallet } from "lucide-react";

import { KPICard } from "@/components/KPICard";
import {
  ifMonthlyContributionDisplay,
  type IFGoalResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

interface IFKPIsRowProps {
  goal: IFGoalResponse;
}

export function IFKPIsRow({ goal }: IFKPIsRowProps) {
  const i = goal.inputs;
  const d = goal.derived;
  const showCenarioZero =
    d.aporte_mensal_com_patrimonio_atual_brl != null &&
    d.patrimonio_atual_utilizado_brl != null &&
    d.aporte_mensal_com_patrimonio_atual_brl !==
      d.aporte_necessario_mensal_brl;

  return (
    <>
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
      {showCenarioZero && d.patrimonio_atual_utilizado_brl != null && (
        <p className="-mt-2 mb-6 text-xs text-muted-foreground">
          Considera patrimonio liquido do ultimo relatorio (
          {formatCurrency(d.patrimonio_atual_utilizado_brl)}). Cenario partindo
          de zero:{" "}
          <span className="font-mono tabular-nums">
            {formatCurrency(d.aporte_necessario_mensal_brl)}/mes
          </span>
          .
        </p>
      )}
    </>
  );
}
