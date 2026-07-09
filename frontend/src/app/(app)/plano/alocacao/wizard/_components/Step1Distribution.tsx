"use client";

import { AlocacaoDistributionFields } from "./AlocacaoDistributionFields";
import type { AlocacaoProgressState } from "./AlocacaoProgress";
import type { Pcts } from "./constants";

interface Step1DistributionProps {
  pcts: Pcts;
  onChange: (next: Pcts) => void;
  soma: number;
  progressState: AlocacaoProgressState;
  onCompleteWithCaixa: () => void;
}

export function Step1Distribution({
  pcts,
  onChange,
  soma,
  progressState,
  onCompleteWithCaixa,
}: Step1DistributionProps) {
  return (
    <div>
      <h2 className="text-lg font-semibold">Distribua seus investimentos</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Defina a alocação percentual ideal por classe de ativo. A soma precisa
        fechar em 100% — use “Completar com Caixa” para o resíduo.
      </p>

      <div className="mt-6">
        <AlocacaoDistributionFields
          pcts={pcts}
          onChange={onChange}
          soma={soma}
          progressState={progressState}
          onCompleteWithCaixa={onCompleteWithCaixa}
        />
      </div>
    </div>
  );
}
