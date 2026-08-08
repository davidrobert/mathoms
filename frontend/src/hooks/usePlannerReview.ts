"use client";

// ADR-199 / ADR-208 — hook do aggregate PlannerReview.
//
// Single-fetch (não há list): carrega o parecer mais recente do report.
// 404 com code=not_generated_yet vira `state: 'not_generated'` para a UI
// renderizar placeholder educativo sem exibir erro técnico.

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  getErrorCode,
  getPlannerReview,
  type ParecerAbsenceCode,
  type ParecerPlanejadorContent,
  type PlannerReviewResponse,
} from "@/lib/api";

export type PlannerReviewState =
  | { kind: "loading" }
  // `code` diz QUAL ausência (ADR-366 §D6). Nunca `report_not_found`: aquele diz
  // que o RELATÓRIO não existe, não que o parecer falta, e vai para `error`.
  | { kind: "not_generated"; code: ParecerAbsenceCode }
  // Gerado e retido por qualidade/política (ADR-366): 200 com `content: null`.
  // Discriminado pelo `outcome` do payload, NÃO por 404 — 404 continua sendo
  // ausência ("nunca rodou" / free), que é outra coisa e outra copy.
  | { kind: "retained"; data: PlannerReviewResponse }
  | {
      kind: "ready";
      data: PlannerReviewResponse;
      content: ParecerPlanejadorContent;
    }
  | { kind: "error"; message: string };

export interface UsePlannerReviewResult {
  state: PlannerReviewState;
  reload: () => Promise<void>;
}

function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    return err.detail;
  }
  return "Erro ao carregar parecer.";
}

const SECTION_ABSENCE_CODES: readonly ParecerAbsenceCode[] = [
  "not_generated_yet",
  "generation_unavailable",
  "parecer_artifact_missing",
  "tier_gated",
];

// `report_not_found` sai por ser CONHECIDO e semanticamente errado aqui: ele diz
// que o RELATÓRIO não existe, e a seção diria "parecer ainda não gerado" numa
// página cujo relatório não resolve — descrevendo o defeito errado para quem só
// pode agir sobre ele. Devolve `null` ⇒ estado de erro.
//
// Código DESCONHECIDO segue caindo no conservador, e a razão original continua
// válida: o servidor pode ganhar membro antes do cliente, e nesse intervalo copy
// genérica é melhor que erro. Só o caso nomeado muda de destino.
function absenceCode(err: ApiError): ParecerAbsenceCode | null {
  const code = getErrorCode(err);
  if (code === "report_not_found") return null;
  return SECTION_ABSENCE_CODES.find((c) => c === code) ?? "not_generated_yet";
}

// `content` não-nulo é estreitado aqui, uma vez, em vez de em cada leitor.
function toState(data: PlannerReviewResponse): PlannerReviewState {
  return data.content
    ? { kind: "ready", data, content: data.content }
    : { kind: "retained", data };
}

async function _doFetch(
  workspaceId: string,
  reportId: string,
  setState: (s: PlannerReviewState) => void,
): Promise<void> {
  setState({ kind: "loading" });
  try {
    setState(toState(await getPlannerReview(workspaceId, reportId)));
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      const code = absenceCode(err);
      if (code) {
        setState({ kind: "not_generated", code });
        return;
      }
    }
    setState({ kind: "error", message: describeError(err) });
  }
}

function _fetch_state(
  workspaceId: string | undefined,
  reportId: string | undefined,
  setState: (s: PlannerReviewState) => void,
): () => Promise<void> {
  return async () => {
    if (!workspaceId || !reportId) {
      setState({ kind: "not_generated", code: "not_generated_yet" });
      return;
    }
    await _doFetch(workspaceId, reportId, setState);
  };
}

export function usePlannerReview(
  workspaceId: string | undefined,
  reportId: string | undefined,
): UsePlannerReviewResult {
  const [state, setState] = useState<PlannerReviewState>({ kind: "loading" });
  const reload = useCallback(_fetch_state(workspaceId, reportId, setState), [
    workspaceId,
    reportId,
  ]);
  useEffect(() => {
    void reload();
  }, [reload]);
  return { state, reload };
}
