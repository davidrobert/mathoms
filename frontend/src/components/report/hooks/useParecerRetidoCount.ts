"use client";

import { useEffect, useState } from "react";

import { getPlannerReview } from "@/lib/api";
import { parecerItensRetidos } from "../utils/parecerRetencao";

/** A40.l22 — itens do parecer retidos na conferência, para o banner agregado.
 *
 * Mesmo `GET .../planner-review` que a `SParecerSection` já faz. Refetch em vez
 * de içar o estado até o `ReportShell` de propósito: o `MigratedSection` é um
 * dispatcher deliberadamente desacoplado do shell, e threadar o aggregate por
 * ele daria a prop a 15 seções para 1 usar. Não há divergência possível — é a
 * mesma resposta do mesmo endpoint, e o contador é derivado por
 * `parecerItensRetidos` nos dois lados (produtor único da regra).
 *
 * 404 (nunca gerado / free) e falha de rede degradam para 0: o banner perde uma
 * LINHA, e a seção — que faz o próprio fetch e é a superfície autoritativa —
 * segue declarando a retenção.
 */
function fetchRetidoCount(
  workspaceId: string,
  reportId: string,
  apply: (n: number) => void,
): () => void {
  let cancelled = false;
  getPlannerReview(workspaceId, reportId)
    .then((data) => {
      if (!cancelled) apply(parecerItensRetidos(data));
    })
    .catch(() => {});
  return () => {
    cancelled = true;
  };
}

export function useParecerRetidoCount(
  workspaceId: string | undefined,
  reportId: string | undefined,
): number {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!workspaceId || !reportId) return;
    return fetchRetidoCount(workspaceId, reportId, setCount);
  }, [workspaceId, reportId]);

  return count;
}
