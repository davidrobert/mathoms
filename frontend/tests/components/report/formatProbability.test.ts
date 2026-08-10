/**
 * Regra de arredondamento da probabilidade do MC (A40.l25).
 *
 * A PARIDADE com o narrador Python é gateada por
 * `dev/check_probabilidade_parity.py` (pre-commit, roda em todo PR). Este
 * arquivo trava a REGRA — sem ele, os dois lados podem derivar juntos para a
 * convenção errada e o gate de paridade passa verde sobre o erro.
 */
import { describe, expect, it } from "vitest";

import { formatProbability } from "@/components/report/utils/probabilidade";

describe("formatProbability", () => {
  it.each([
    [0.025, "3%"],
    [0.045, "5%"],
    [0.105, "11%"],
    [0.024999, "2%"],
    [0.31, "31%"],
    [0.3, "30%"],
  ])("arredonda meio-para-cima: %s → %s", (prob, esperado) => {
    expect(formatProbability(prob)).toBe(esperado);
  });

  it.each([
    [0, "0%"],
    [1, "100%"],
    [0.0001, "<1%"],
    [0.9999, ">99%"],
  ])("guard tem precedência sobre o arredondamento: %s → %s", (prob, esperado) => {
    expect(formatProbability(prob)).toBe(esperado);
  });
});
