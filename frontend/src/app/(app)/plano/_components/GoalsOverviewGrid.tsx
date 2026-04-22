"use client";

import { DollarSign, PieChart, Target, Wallet } from "lucide-react";

import type {
  AlocacaoGoalResponse,
  AporteGoalResponse,
  DolarGoalResponse,
  IFGoalResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

import { GoalCard } from "./GoalCard";

interface GoalsOverviewGridProps {
  ifGoal: IFGoalResponse | null;
  aporteGoal: AporteGoalResponse | null;
  dolarGoal: DolarGoalResponse | null;
  alocacaoGoal: AlocacaoGoalResponse | null;
}

export function GoalsOverviewGrid({
  ifGoal,
  aporteGoal,
  dolarGoal,
  alocacaoGoal,
}: GoalsOverviewGridProps) {
  return (
    <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
      <GoalCard
        icon={Target}
        title="Meta IF"
        configured={!!ifGoal}
        href={ifGoal ? "/plano/meta-if" : "/plano/meta-if/wizard"}
        value={
          ifGoal ? formatCurrency(ifGoal.derived.if_meta_brl) : undefined
        }
        subtitle={
          ifGoal
            ? `Renda ${formatCurrency(ifGoal.inputs.renda_passiva_mensal_brl)}/mes`
            : undefined
        }
      />

      <GoalCard
        icon={Wallet}
        title="Aportes"
        configured={!!aporteGoal}
        href={aporteGoal ? "/plano/aportes" : "/plano/aportes/wizard"}
        value={
          aporteGoal
            ? `${formatCurrency(aporteGoal.inputs.meta_aporte_mensal_brl)}/mes`
            : undefined
        }
        subtitle={
          aporteGoal ? `Dia ${aporteGoal.inputs.dia_aporte}` : undefined
        }
      />

      <GoalCard
        icon={DollarSign}
        title="Dolarizacao"
        configured={!!dolarGoal}
        href={
          dolarGoal ? "/plano/dolarizacao" : "/plano/dolarizacao/wizard"
        }
        value={
          dolarGoal
            ? `US$ ${dolarGoal.inputs.meta_usd.toLocaleString("pt-BR")}`
            : undefined
        }
        subtitle={
          dolarGoal
            ? `~${dolarGoal.derived.horizonte_estimado_meses} meses`
            : undefined
        }
      />

      <GoalCard
        icon={PieChart}
        title="Alocacao"
        configured={!!alocacaoGoal}
        href={alocacaoGoal ? "/plano/alocacao" : "/plano/alocacao/wizard"}
        value={
          alocacaoGoal
            ? `RF ${alocacaoGoal.inputs.renda_fixa_pct}% · RV ${alocacaoGoal.inputs.acoes_pct}%`
            : undefined
        }
        subtitle={
          alocacaoGoal
            ? `Imov ${alocacaoGoal.inputs.imoveis_reits_pct}% · USD ${alocacaoGoal.inputs.liquidez_usd_pct}%`
            : undefined
        }
      />
    </div>
  );
}
