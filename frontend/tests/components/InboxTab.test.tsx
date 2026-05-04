/**
 * Tests — computeNextDecisionCode (Direção E · Onda 5)
 *        + suggestionSortComparator (ADR-161 · Onda 8 #4).
 *
 * Funções puras usadas pelo InboxTab.
 */
import { describe, expect, it } from "vitest";

import {
  computeNextDecisionCode,
  suggestionSortComparator,
} from "@/app/(app)/acao/_components/InboxTab";
import type { Suggestion } from "@/lib/api";

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

// Helper para construir Suggestion mínima nos testes do comparator.
function makeSug(
  id: string,
  severity: "danger" | "warning" | "info",
  created_at: string,
): Suggestion {
  return {
    id,
    workspace_id: "ws",
    report_id: null,
    section_id: "S2",
    kind: "trs_desalinhada",
    category: null,
    origin: "deterministic",
    severity,
    title: "t",
    rationale: "r",
    amount_brl: null,
    status: "Pendente",
    accepted_decision_id: null,
    dismissed_reason: null,
    accepted_at: null,
    dismissed_at: null,
    created_at,
    updated_at: created_at,
  };
}

describe("suggestionSortComparator", () => {
  it("danger vem antes de warning vem antes de info", () => {
    const list = [
      makeSug("a", "info", "2026-01-01"),
      makeSug("b", "danger", "2026-01-01"),
      makeSug("c", "warning", "2026-01-01"),
    ];
    const sorted = [...list].sort(suggestionSortComparator);
    expect(sorted.map((s) => s.severity)).toEqual([
      "danger",
      "warning",
      "info",
    ]);
  });

  it("entre mesma severity, mais recente primeiro", () => {
    const list = [
      makeSug("velho", "warning", "2026-01-01"),
      makeSug("novo", "warning", "2026-03-01"),
      makeSug("medio", "warning", "2026-02-01"),
    ];
    const sorted = [...list].sort(suggestionSortComparator);
    expect(sorted.map((s) => s.id)).toEqual(["novo", "medio", "velho"]);
  });

  it("severity desconhecida vai para o fim", () => {
    const list = [
      makeSug("ok", "info", "2026-01-01"),
      // @ts-expect-error — testando severity inválida
      makeSug("bad", "x", "2026-01-01"),
    ];
    const sorted = [...list].sort(suggestionSortComparator);
    expect(sorted[0].id).toBe("ok");
  });
});
