"use client";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

import { AlocacaoSummary } from "./AlocacaoSummary";
import { REBAL_OPTIONS, type Pcts } from "./constants";

interface Step3RebalanceProps {
  rebalanceamento: string;
  onChangeRebalanceamento: (v: string) => void;
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
        Com qual frequencia voce pretende rebalancear a carteira?
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {REBAL_OPTIONS.map((opt) => (
          <Button
            key={opt}
            variant={rebalanceamento === opt ? "default" : "outline"}
            size="sm"
            onClick={() => onChangeRebalanceamento(opt)}
            type="button"
          >
            {opt}
          </Button>
        ))}
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
