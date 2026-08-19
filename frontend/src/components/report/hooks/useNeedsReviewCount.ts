"use client";

import { useEffect, useState } from "react";

import { listDocuments } from "@/lib/api";
import { isClassificationUncertain } from "@/app/(app)/documents/_components/classificationHints";
import {
  MEASURING,
  UNMEASURED,
  measured,
  type MeasuredCount,
} from "../utils/measuredCount";

async function countUncertainDocs(workspaceId: string): Promise<number> {
  const resp = await listDocuments(workspaceId);
  return (resp?.documents ?? []).filter(isClassificationUncertain).length;
}

/** A28.l9 — conta documentos com classificação incerta (needs_review ou
 * confidence baixa sem extração OK) para o `<ReportDataQualityBanner/>`.
 *
 * Mesmo predicado do filtro "uncertain" da página /documents — o número do
 * banner bate com o que o usuário encontra ao clicar no CTA.
 *
 * PD-6 (RV6-22) — falha de rede devolve `unknown`, NÃO zero. O banner é lido
 * também no PDF ([[ADR-129]]: Playwright sobre esta mesma rota, onde o efeito
 * roda de verdade), e ali um 5xx transitório publicaria "sem pendências" num
 * artefato que o cliente arquiva. Sem workspace ainda não há o que medir —
 * também `unknown`, nunca uma afirmação de ausência.
 */
function fetchUncertainCount(
  workspaceId: string,
  apply: (value: MeasuredCount) => void,
): () => void {
  let cancelled = false;
  countUncertainDocs(workspaceId)
    .then((n) => {
      if (!cancelled) apply(measured(n));
    })
    .catch(() => {
      if (!cancelled) apply(UNMEASURED);
    });
  return () => {
    cancelled = true;
  };
}

export function useNeedsReviewCount(
  workspaceId: string | undefined,
): MeasuredCount {
  const [value, setValue] = useState<MeasuredCount>(MEASURING);

  useEffect(() => {
    if (!workspaceId) {
      setValue(UNMEASURED);
      return;
    }
    setValue(MEASURING);
    return fetchUncertainCount(workspaceId, setValue);
  }, [workspaceId]);

  return value;
}
