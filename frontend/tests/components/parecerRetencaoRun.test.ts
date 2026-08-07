/**
 * A40.l22 — `parecerItensRetidosNoRun`: a leitura do run na superfície
 * operacional (`/pipeline`).
 *
 * Três mutações plausíveis morrem aqui:
 *
 * 1. **Aceitar o stage degradado** — `stage_logs.find(s => PARECER.has(s.stage))`
 *    sem o filtro `status === "completed"`. O run degradado é o desfecho RETIDO
 *    INTEIRO, que já tem voz (`degradedRunCaveat`); contá-lo diria "N itens
 *    retidos" num parecer que saiu inteiro de fora.
 * 2. **Perder o nome legado** — trocar o `Set` por igualdade com
 *    `"review_finances_holistic"`. Rows antigas gravam `E6-parecer` (ADR-093) e
 *    a lista de runs mostra histórico.
 * 3. **Ler prosa** — puxar `reason`/`retention_trigger` do `output_summary`, que
 *    é o `detail` CRU do stage e carrega vocabulário de operador.
 */
import { describe, expect, it } from "vitest";

import { parecerItensRetidosNoRun } from "@/app/(app)/pipeline/_components/parecerRetencao";
import { makeRun, makeStageLog } from "../factories";

const PROSA_DE_OPERADOR = "evidencia unverified (severidade alta): risco:3";

function runComParecer(
  over: { stage?: string; status?: string; summary?: Record<string, unknown> | null } = {},
) {
  return makeRun({
    stage_logs: [
      makeStageLog({ stage: "analyze_finances", status: "completed" }),
      makeStageLog({
        stage: over.stage ?? "review_finances_holistic",
        status: (over.status ?? "completed") as never,
        output_summary: over.summary === undefined ? { evidencia_verification: { items_dropped: 2 } } : over.summary,
      }),
    ],
  });
}

describe("parecerItensRetidosNoRun", () => {
  it("lê o inteiro do stage do parecer que ENTREGOU", () => {
    expect(parecerItensRetidosNoRun(runComParecer())).toBe(2);
  });

  it("aceita o nome legado do stage (ADR-093)", () => {
    expect(parecerItensRetidosNoRun(runComParecer({ stage: "E6-parecer" }))).toBe(2);
  });

  it("ignora o stage DEGRADADO — ali a retenção é do parecer inteiro", () => {
    expect(parecerItensRetidosNoRun(runComParecer({ status: "degraded" }))).toBe(0);
    expect(parecerItensRetidosNoRun(runComParecer({ status: "failed" }))).toBe(0);
  });

  it("é 0 sem o bloco de verificação, e nunca deriva de prosa", () => {
    const semBloco = runComParecer({
      summary: { reason: PROSA_DE_OPERADOR, retention_reason: "parecer.citacao_nao_confirmada" },
    });
    expect(parecerItensRetidosNoRun(semBloco)).toBe(0);
  });

  it("fail-closed em tipo inesperado: string, NaN, negativo, null", () => {
    for (const raw of ["2", NaN, -3, null, undefined, {}]) {
      const run = runComParecer({ summary: { evidencia_verification: { items_dropped: raw } } });
      expect(parecerItensRetidosNoRun(run)).toBe(0);
    }
    expect(parecerItensRetidosNoRun(runComParecer({ summary: null }))).toBe(0);
  });

  it("é 0 no run sem stage de parecer", () => {
    expect(parecerItensRetidosNoRun(makeRun())).toBe(0);
  });
});
