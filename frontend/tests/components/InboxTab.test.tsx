/**
 * Tests — computeNextDecisionCode (Direção E · Onda 5).
 *
 * Função pura usada pelo InboxTab para sugerir o próximo código `D{N+1}`
 * ao aceitar uma sugestão.
 */
import { describe, expect, it } from "vitest";

import { computeNextDecisionCode } from "@/app/(app)/acao/_components/InboxTab";

describe("computeNextDecisionCode", () => {
  it("retorna D01 quando não há decisões", () => {
    expect(computeNextDecisionCode([])).toBe("D01");
  });

  it("retorna próximo após o maior existente", () => {
    expect(computeNextDecisionCode(["D01", "D02", "D03"])).toBe("D04");
  });

  it("preenche com zero (D{NN})", () => {
    expect(computeNextDecisionCode(["D01"])).toBe("D02");
    expect(computeNextDecisionCode(["D09"])).toBe("D10");
  });

  it("ignora códigos não-numéricos", () => {
    expect(computeNextDecisionCode(["D-XX", "D01"])).toBe("D02");
  });

  it("encontra o maior, mesmo fora de ordem", () => {
    expect(computeNextDecisionCode(["D03", "D01", "D02"])).toBe("D04");
  });
});
