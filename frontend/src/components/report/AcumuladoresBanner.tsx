import { TrendingUp } from "lucide-react";

import { Alert } from "./ui/Alert";

/**
 * Banner explicativo (Lane A8.3 / S7) quando >40% da carteira de renda
 * está em ETFs/fundos acumuladores (BOVA11, IVVB11, IVV, ...). Esses
 * ativos geram retorno por valorização — a TRS efetiva os subestima
 * como geradores de renda. Banner fecha o loop visual com o card
 * "Em acumuladores" (que assume tom warning quando o threshold cruza).
 */
export interface AcumuladoresBannerProps {
  pct: number;
}

export function AcumuladoresBanner({ pct }: AcumuladoresBannerProps) {
  const pctLabel = pct.toFixed(0);
  return (
    <Alert severity="info" icon={<TrendingUp className="h-4 w-4" aria-hidden="true" />}>
      <p>
        <strong>{pctLabel}% da sua carteira de renda está em ativos sem distribuição</strong>{" "}
        (BOVA11, IVVB11, IVV e similares). Esses ativos geram retorno por valorização,
        não dividendo — a TRS efetiva os subestima como geradores de renda. O sinal
        correto está na alocação alvo (S3), não nesta métrica.
      </p>
    </Alert>
  );
}
