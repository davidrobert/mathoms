"use client";

import { useEffect, useState } from "react";

import { ApiError, getPlannerReview } from "@/lib/api";
import { parecerItensRetidos } from "../utils/parecerRetencao";
import {
  MEASURING,
  UNMEASURED,
  measured,
  type MeasuredCount,
} from "../utils/measuredCount";

/** A40.l22 — itens do parecer retidos na conferência, para o banner agregado.
 *
 * Mesmo `GET .../planner-review` que a `SParecerSection` já faz. Refetch em vez
 * de içar o estado até o `ReportShell` de propósito: o `MigratedSection` é um
 * dispatcher deliberadamente desacoplado do shell, e threadar o aggregate por
 * ele daria a prop a 15 seções para 1 usar. Não há divergência possível — é a
 * mesma resposta do mesmo endpoint, e o contador é derivado por
 * `parecerItensRetidos` nos dois lados (produtor único da regra).
 *
 * PD-6 (RV6-22) — 404 e falha de rede deixam de ser o mesmo fato. 404 (nunca
 * gerado / free) é ausência POR CONSTRUÇÃO, logo zero medido: o banner perde
 * uma LINHA e a seção, superfície autoritativa, segue declarando a retenção.
 * Qualquer outra falha é `unknown` — não sabemos se há itens retidos, e o
 * relatório não pode afirmar que não há.
 */
function classifyRetidoError(err: unknown): MeasuredCount {
  if (err instanceof ApiError && err.status === 404) return measured(0);
  return UNMEASURED;
}

function fetchRetidoCount(
  workspaceId: string,
  reportId: string,
  apply: (value: MeasuredCount) => void,
): () => void {
  let cancelled = false;
  getPlannerReview(workspaceId, reportId)
    .then((data) => {
      if (!cancelled) apply(measured(parecerItensRetidos(data)));
    })
    .catch((err: unknown) => {
      if (!cancelled) apply(classifyRetidoError(err));
    });
  return () => {
    cancelled = true;
  };
}

export function useParecerRetidoCount(
  workspaceId: string | undefined,
  reportId: string | undefined,
): MeasuredCount {
  const [value, setValue] = useState<MeasuredCount>(MEASURING);

  useEffect(() => {
    // Sem par (workspace, report) não há parecer a conferir: o sinal está
    // desligado por construção, o que é zero medido — não falha de medição.
    if (!workspaceId || !reportId) {
      setValue(measured(0));
      return;
    }
    setValue(MEASURING);
    return fetchRetidoCount(workspaceId, reportId, setValue);
  }, [workspaceId, reportId]);

  return value;
}
