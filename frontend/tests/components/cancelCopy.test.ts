/**
 * ADR-417 D4 — interromper um run que EXECUTA e descartar um que está PAUSADO são
 * atos diferentes. O texto único descrevia só o primeiro ("interrompido ao final da
 * etapa em execução"), e numa pausa não há etapa executando.
 */
import { describe, expect, it } from "vitest";

import {
  cancelCopyFor,
  foiDescartadoNaConferencia,
} from "@/app/(app)/pipeline/_components/cancelCopy";
import { makeRun } from "../factories";

const pausado = (n = 2) =>
  makeRun({
    status: "needs_review",
    paused_at_stage: "analyze_finances",
    completed_at: null,
  });

describe("cancelCopyFor", () => {
  it("run em execução mantém a copy de interrupção", () => {
    const copy = cancelCopyFor(makeRun({ status: "running" }), {
      pendingCount: 0,
      runs: [makeRun({ report_id: "rel-1" })],
    });
    expect(copy.confirmLabel).toBe("Cancelar execução");
    expect(copy.description).toContain("etapa em execução");
  });

  it("pausa troca o verbo e não fala de etapa em execução", () => {
    const copy = cancelCopyFor(pausado(), {
      pendingCount: 2,
      runs: [makeRun({ report_id: "rel-1" })],
    });
    expect(copy.title).toBe("Descartar este processamento?");
    expect(copy.confirmLabel).toBe("Descartar");
    expect(copy.description).not.toContain("etapa em execução");
    expect(copy.description).toContain("2 conferências pendentes");
  });

  it("sem relatório anterior, a copy não promete que algo continua valendo", () => {
    const copy = cancelCopyFor(pausado(), {
      pendingCount: 1,
      runs: [makeRun({ report_id: null })],
    });
    expect(copy.description).toContain("nenhum relatório foi gerado ainda");
    expect(copy.description).not.toContain("continua valendo");
  });

  it("com relatório anterior, responde a pergunta que mais pesa na decisão", () => {
    const copy = cancelCopyFor(pausado(), {
      pendingCount: 1,
      runs: [makeRun({ report_id: "rel-1" })],
    });
    expect(copy.description).toContain("relatório atual continua valendo");
  });

  it("não promete retomar de onde parou — `_resolve_base_run` sobre run cancelado não foi medido", () => {
    const copy = cancelCopyFor(pausado(), {
      pendingCount: 1,
      runs: [makeRun({ report_id: "rel-1" })],
    });
    expect(copy.description).not.toMatch(/de onde parou|continuar de onde/i);
  });
});

describe("foiDescartadoNaConferencia", () => {
  it("lê o estado GRAVADO no instante terminal", () => {
    expect(
      foiDescartadoNaConferencia(
        makeRun({ status: "cancelled", cancelled_from_status: "needs_review" }),
      ),
    ).toBe(true);
  });

  it("interrompido em execução não é descarte, MESMO com `paused_at_stage` preenchido", () => {
    // O caso que refutou a derivação: ninguém zera `paused_at_stage`, então ele
    // sobrevive à retomada. Só o estado gravado discrimina.
    expect(
      foiDescartadoNaConferencia(
        makeRun({
          status: "cancelled",
          cancelled_from_status: "running",
          paused_at_stage: "analyze_finances",
        }),
      ),
    ).toBe(false);
  });

  it("row legada (`null`) é desconhecida, nunca interrompida", () => {
    expect(
      foiDescartadoNaConferencia(
        makeRun({
          status: "cancelled",
          cancelled_from_status: null,
          paused_at_stage: "analyze_finances",
        }),
      ),
    ).toBe(false);
  });

  it("pausa ainda viva não é descarte", () => {
    expect(
      foiDescartadoNaConferencia(makeRun({ status: "needs_review", cancelled_from_status: null })),
    ).toBe(false);
  });
});
