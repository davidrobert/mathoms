import { Clock } from "lucide-react";

import { Alert } from "./ui/Alert";

/**
 * Banner de defasagem do IRPF (Lane A8.3 / S7). Disparado quando a
 * declaração tem 15+ meses de atraso vs reference_date — TRS efetiva
 * pode estar refletindo carteira antiga, sem mudanças recentes.
 *
 * Defasagem típica de 4-5m (ano-base AAAA declarado em abril/AAAA+1) é
 * normal; a partir de 12-15m, sinal real de "desatualizado".
 */
export interface DefasagemWarningBannerProps {
  ano: number | null;
  meses: number;
}

export function DefasagemWarningBanner({ ano, meses }: DefasagemWarningBannerProps) {
  const anoLabel = ano ?? "—";
  return (
    <Alert severity="warning" icon={<Clock className="h-4 w-4" aria-hidden="true" />}>
      <p>
        <strong>IRPF de {anoLabel} desatualizado.</strong> A TRS efetiva usa rendimentos
        declarados há {meses} meses; mudanças recentes na carteira não estão refletidas.
        Importe a declaração mais recente para recalcular.
      </p>
      <p style={{ marginTop: 8 }}>
        <a
          href="/documents"
          style={{ color: "var(--brand-primary)", textDecoration: "underline" }}
        >
          Importar IRPF mais recente
        </a>
      </p>
    </Alert>
  );
}
