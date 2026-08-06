import { describe, it, expect } from "vitest";

import { makePartialRun, makeRun, makeStageLog } from "../factories";
import { deriveFailedStage } from "@/app/(app)/pipeline/_components/failedStage";
import {
  degradedRunCaveat,
  deriveDegradedStage,
} from "@/app/(app)/pipeline/_components/degradedStage";

describe("deriveDegradedStage", () => {
  it("acha a etapa que não entregou", () => {
    expect(deriveDegradedStage(makePartialRun())).toBe("review_finances_holistic");
  });

  it("run sem etapa degradada devolve null", () => {
    expect(deriveDegradedStage(makeRun())).toBeNull();
  });

  // Alimenta `from_stage`, que roda a cauda inteira a partir dali: pegar a
  // PRIMEIRA degradada cobre as demais. Um refactor "pega a última" estreitaria
  // o reprocessamento e deixaria lacuna sem caminho de volta.
  it("com duas degradadas, devolve a primeira — from_stage cobre a cauda", () => {
    const run = makePartialRun({
      stage_logs: [
        makeStageLog({ stage: "generate_narratives", status: "degraded" }),
        makeStageLog({ stage: "review_finances_holistic", status: "degraded" }),
      ],
    });
    expect(deriveDegradedStage(run)).toBe("generate_narratives");
  });

  // ADR-357 §3: `failed_at_stage` fica nulo em degradação, e a etapa degradada
  // grava `degraded` — se `deriveFailedStage` a achasse, o run voltaria a ser
  // pintado como falha em todos os consumidores.
  it("deriveFailedStage continua cego à etapa degradada", () => {
    expect(deriveFailedStage(makePartialRun())).toBeNull();
  });
});

describe("degradedRunCaveat", () => {
  it.each([
    ["review_finances_holistic", /parecer do planejador/],
    ["E6-parecer", /parecer do planejador/],
    ["generate_narratives", /análises e comentários/],
    ["validate_cross", /consistência dos números/],
  ])("%s → frase própria", (stage, pattern) => {
    const run = makePartialRun({
      stage_logs: [makeStageLog({ stage, status: "degraded" })],
    });
    expect(degradedRunCaveat(run)).toMatch(pattern);
  });

  // Os 3 add-ons são independentes: nomear um só mentiria sobre o número de
  // lacunas.
  it("dois add-ons degradados não afirmam uma lacuna só", () => {
    const run = makePartialRun({
      stage_logs: [
        makeStageLog({ stage: "generate_narratives", status: "degraded" }),
        makeStageLog({ stage: "review_finances_holistic", status: "degraded" }),
      ],
    });
    expect(degradedRunCaveat(run)).toBe(
      "Relatório gerado, sem algumas das análises finais.",
    );
  });

  it("etapa degradável desconhecida cai em frase genérica verdadeira", () => {
    const run = makePartialRun({
      stage_logs: [makeStageLog({ stage: "stage_futuro", status: "degraded" })],
    });
    expect(degradedRunCaveat(run)).toBe(
      "Relatório gerado, com uma etapa final incompleta.",
    );
  });

  it("toda frase afirma que o relatório existe e não vaza jargão", () => {
    for (const stage of [
      "review_finances_holistic",
      "generate_narratives",
      "validate_cross",
      "stage_futuro",
    ]) {
      const caveat = degradedRunCaveat(
        makePartialRun({ stage_logs: [makeStageLog({ stage, status: "degraded" })] }),
      );
      expect(caveat).toMatch(/^Relatório gerado/);
      expect(caveat).not.toMatch(/pipeline|stage|LLM|E[0-9]|falh/i);
    }
  });
});
