"use client";

import { Separator } from "@/components/ui/separator";
import type { RebalanceamentoModo } from "@/lib/api";

import { AlocacaoSummary } from "./AlocacaoSummary";
import { RebalanceamentoModeSelector } from "./RebalanceamentoModeSelector";
import { type Pcts } from "./constants";

interface Step3RebalanceProps {
  rebalanceamento: RebalanceamentoModo;
  onChangeRebalanceamento: (v: RebalanceamentoModo) => void;
  pcts: Pcts;
  instrumentosRf: string;
  instrumentosRv: string;
}

export function Step3Rebalance({
  rebalanceamento,
  onChangeRebalanceamento,
  pcts,
  instrumentosRf,
  instrumentosRv,
}: Step3RebalanceProps) {
  return (
    <div>
      <h2 className="text-lg font-semibold">Rebalanceamento</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Como você pretende reequilibrar a carteira quando ela sair do alvo?
        Rebalancear é direcionar os próximos aportes — não vender.
      </p>

      <div className="mt-4">
        <RebalanceamentoModeSelector
          value={rebalanceamento}
          onChange={onChangeRebalanceamento}
        />
      </div>

      <Separator className="my-4" />

      <AlocacaoSummary
        pcts={pcts}
        instrumentosRf={instrumentosRf}
        instrumentosRv={instrumentosRv}
        rebalanceamento={rebalanceamento}
      />
    </div>
  );
}
