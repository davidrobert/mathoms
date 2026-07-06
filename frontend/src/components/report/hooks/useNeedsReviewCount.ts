"use client";

import { useEffect, useState } from "react";

import { listDocuments } from "@/lib/api";
import { isClassificationUncertain } from "@/app/(app)/documents/_components/classificationHints";

async function countUncertainDocs(workspaceId: string): Promise<number> {
  const resp = await listDocuments(workspaceId);
  return (resp?.documents ?? []).filter(isClassificationUncertain).length;
}

/** A28.l9 — conta documentos com classificação incerta (needs_review ou
 * confidence baixa sem extração OK) para o `<ReportDataQualityBanner/>`.
 *
 * Mesmo predicado do filtro "uncertain" da página /documents — o número do
 * banner bate com o que o usuário encontra ao clicar no CTA. Falha de rede
 * degrada silenciosamente para 0 (banner perde 1 sinal, não quebra).
 */
export function useNeedsReviewCount(workspaceId: string | undefined): number {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;
    countUncertainDocs(workspaceId)
      .then((n) => {
        if (!cancelled) setCount(n);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  return count;
}
