/**
 * A40.l87 — o card da pausa tem de sobreviver ao RELOAD. Antes, `activeRun` saía só de
 * `ACTIVE_STATUSES` (que não inclui `needs_review`), então quem recarregava perdia o
 * `NeedsReviewCard` e ganhava o `TriggerCard` convidando a disparar por cima.
 */
import { describe, expect, it } from "vitest";

import {
  ACTIVE_STATUSES,
  resolveActiveRun,
} from "@/app/(app)/pipeline/_components/resolveActiveRun";
import { makeRun } from "../factories";

describe("resolveActiveRun", () => {
  it("a pausa é resolvida na carga, não só ao vivo", () => {
    const pausado = makeRun({ status: "needs_review", paused_at_stage: "analyze_finances" });
    expect(resolveActiveRun([makeRun({ status: "completed" }), pausado])?.id).toBe(pausado.id);
  });

  it("run com executor vivo ganha do pausado", () => {
    const rodando = makeRun({ status: "running" });
    const pausado = makeRun({ status: "needs_review" });
    expect(resolveActiveRun([pausado, rodando])?.id).toBe(rodando.id);
  });

  it("histórico terminal não vira run ativo", () => {
    expect(resolveActiveRun([makeRun({ status: "cancelled" }), makeRun({ status: "failed" })])).toBeNull();
  });

  it("a pausa fica FORA de ACTIVE_STATUSES — ela não segura executor", () => {
    expect(ACTIVE_STATUSES.has("needs_review")).toBe(false);
  });
});
