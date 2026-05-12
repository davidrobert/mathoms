// A11.W5 · ADR-110 · ADR-192 · S9-T05 — client-side audit log helpers.
//
// Decision (sre-devops review): em vez de criar endpoint backend novo
// para "policy_ref reveal", usamos log estruturado client-side via
// `apiFetch('/audit/log', POST)`. O endpoint `/audit/log` é genérico e
// já existe para outros eventos (ou degrada gracefully via console.warn
// se 404). Backend redige `policy_ref` raw em INFO via
// `SENSITIVE_FIELD_SUBSTRINGS` (ADR-110); este helper nunca envia o
// valor raw — apenas IDs.

import { apiFetch, ApiError } from "./api/core";

export interface PolicyRefRevealedEvent {
  workspace_id: string;
  protection_id: string;
}

function handleAuditError(payload: AuditPayload) {
  return (err: unknown): void => {
    if (err instanceof ApiError && err.status === 404) {
      // Endpoint não existe ainda — backend roadmap. Loga local.
      console.info("[audit]", payload);
      return;
    }
    console.warn("[audit] falha ao enviar log:", err);
  };
}

interface AuditPayload {
  event: string;
  workspace_id: string;
  protection_id?: string;
  occurred_at: string;
}

/** Registra o evento `mathoms.protection.policy_ref_revealed`. */
export function logProtectionPolicyRefRevealed(
  event: PolicyRefRevealedEvent,
): void {
  const payload: AuditPayload = {
    event: "mathoms.protection.policy_ref_revealed",
    workspace_id: event.workspace_id,
    protection_id: event.protection_id,
    occurred_at: new Date().toISOString(),
  };
  // Fire-and-forget: nunca bloqueia a UI. Degrada para console se 404.
  void apiFetch<void>(`/audit/log`, {
    method: "POST",
    body: JSON.stringify(payload),
  }).catch(handleAuditError(payload));
}
