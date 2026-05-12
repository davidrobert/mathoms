"use client";

// A11.W5 · ADR-192 · S9-T05 — converte um `RiskInferred` (auto-inferência
// do bundle) em `Risk` persistente via `POST /risks`.
//
// **Idempotência (data-engineer review):** o `Risk.code` é derivado de
// `source_calculator` (ex.: `auto:life_insurance_coverage_ideal`).
// Backend tem constraint unique `(workspace_id, code)` — duplo-click
// retorna 409 e o hook trata gracefully retornando o registro existente
// via reload silencioso. Client também memoiza `acceptedKeys` para
// desabilitar UI imediatamente após o primeiro click (UX).
//
// Não toca `AcoesMitigacaoCard.tsx` (T04 owns) — exposição é via prop
// callback que `S9RiscosSection.tsx` pode hookar com TODO de integração.

import { useCallback, useState, type Dispatch, type SetStateAction } from "react";

import {
  ApiError,
  createRisk,
  type Risk,
  type RiskInferred,
} from "@/lib/api";

export interface UseAcceptInferredRiskState {
  /** Set de `source_calculator` já aceitos (memo + persistido em sessionStorage). */
  acceptedKeys: ReadonlySet<string>;
  /** Operações em curso por `source_calculator`. */
  pending: ReadonlySet<string>;
  accept: (inferred: RiskInferred) => Promise<Risk | null>;
}

const STORAGE_KEY_PREFIX = "mathoms_accepted_inferred_risks";

function loadAccepted(workspaceId: string | undefined): Set<string> {
  if (typeof window === "undefined" || !workspaceId) return new Set();
  try {
    const raw = sessionStorage.getItem(`${STORAGE_KEY_PREFIX}:${workspaceId}`);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? new Set(parsed) : new Set();
  } catch {
    return new Set();
  }
}

function saveAccepted(workspaceId: string, keys: Set<string>): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(
      `${STORAGE_KEY_PREFIX}:${workspaceId}`,
      JSON.stringify(Array.from(keys)),
    );
  } catch {
    // sessionStorage cheio/desabilitado — ignorar; UI continua funcionando.
  }
}

function inferredToRiskPayload(inferred: RiskInferred) {
  return {
    code: `auto:${inferred.source_calculator}`,
    name: inferred.name,
    rationale: inferred.rationale,
    impact_level: "médio" as const,
    impact_brl: inferred.estimated_impact_brl ?? null,
    status: "Ativo" as const,
  };
}

type SetState<T> = Dispatch<SetStateAction<T>>;

function addToSet<T>(setter: SetState<Set<T>>, key: T): void {
  setter((prev) => {
    const next = new Set(prev);
    next.add(key);
    return next;
  });
}

function removeFromSet<T>(setter: SetState<Set<T>>, key: T): void {
  setter((prev) => {
    const next = new Set(prev);
    next.delete(key);
    return next;
  });
}

function markAccepted(
  workspaceId: string,
  key: string,
  setAcceptedKeys: SetState<Set<string>>,
): void {
  setAcceptedKeys((prev) => {
    const next = new Set(prev);
    next.add(key);
    saveAccepted(workspaceId, next);
    return next;
  });
}

interface AcceptDeps {
  workspaceId: string;
  acceptedKeys: Set<string>;
  pending: Set<string>;
  setAcceptedKeys: SetState<Set<string>>;
  setPending: SetState<Set<string>>;
}

function handleAcceptError(
  err: unknown,
  key: string,
  deps: AcceptDeps,
): null {
  if (err instanceof ApiError && err.status === 409) {
    // 409 (já existe) — sucesso silencioso para idempotência.
    markAccepted(deps.workspaceId, key, deps.setAcceptedKeys);
    return null;
  }
  throw err;
}

async function performAccept(
  inferred: RiskInferred,
  deps: AcceptDeps,
): Promise<Risk | null> {
  const key = inferred.source_calculator;
  if (deps.acceptedKeys.has(key) || deps.pending.has(key)) return null;
  addToSet(deps.setPending, key);
  try {
    const created = await createRisk(deps.workspaceId, inferredToRiskPayload(inferred));
    markAccepted(deps.workspaceId, key, deps.setAcceptedKeys);
    return created;
  } catch (err) {
    return handleAcceptError(err, key, deps);
  } finally {
    removeFromSet(deps.setPending, key);
  }
}

export function useAcceptInferredRisk(
  workspaceId: string | undefined,
): UseAcceptInferredRiskState {
  const [acceptedKeys, setAcceptedKeys] = useState<Set<string>>(() => loadAccepted(workspaceId));
  const [pending, setPending] = useState<Set<string>>(() => new Set());
  const accept = useCallback(
    async (inferred: RiskInferred): Promise<Risk | null> => {
      if (!workspaceId) return null;
      return performAccept(inferred, {
        workspaceId,
        acceptedKeys,
        pending,
        setAcceptedKeys,
        setPending,
      });
    },
    [workspaceId, acceptedKeys, pending],
  );
  return { acceptedKeys, pending, accept };
}
