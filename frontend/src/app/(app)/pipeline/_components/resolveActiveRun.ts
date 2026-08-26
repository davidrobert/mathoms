/** Qual run o topo da página está mostrando (A40.l87 · ADR-417 D5).
 *
 * `ACTIVE_STATUSES` é o predicado de "tem executor" e por isso NÃO inclui a pausa. Mas
 * ela precisa aparecer na **carga**, não só ao vivo: até 2026-08-26 o card da pausa só
 * existia enquanto o evento WebSocket chegava, e quem recarregava a página perdia o
 * `NeedsReviewCard` e ganhava o `TriggerCard` convidando a disparar por cima — a rampa
 * de orfanamento inteira numa tela.
 */
import type { PipelineRunResponse } from "@/lib/api";

export const ACTIVE_STATUSES = new Set(["pending", "running", "resuming"]);

/** Run com executor vivo ganha do pausado: se os dois existem, o que roda é o sinal
 *  mais forte — e depois do 409 do trigger essa coexistência é transitória. */
export function resolveActiveRun(
  runs: PipelineRunResponse[],
): PipelineRunResponse | null {
  return (
    runs.find((r) => ACTIVE_STATUSES.has(r.status)) ??
    runs.find((r) => r.status === "needs_review") ??
    null
  );
}
