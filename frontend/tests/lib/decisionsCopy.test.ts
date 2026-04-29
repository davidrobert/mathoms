import { describe, expect, it } from "vitest";

import {
  DECISION_STATUS_LABEL,
  decisionStatusFilterLabel,
  findSupersededBy,
  formatDecisionDate,
  nextDecisionCode,
} from "@/app/(app)/plano/_components/decisionsCopy";
import type { Decision } from "@/lib/api";

function makeDecision(overrides: Partial<Decision>): Decision {
  return {
    id: "id-1",
    workspace_id: "ws-1",
    code: "D01",
    title: "Decisão 1",
    rationale: null,
    amount_brl: null,
    status: "Pendente",
    supersedes_id: null,
    decided_at: null,
    executed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("DECISION_STATUS_LABEL", () => {
  it("traduz estados técnicos para PT-BR de leigo", () => {
    expect(DECISION_STATUS_LABEL.Pendente).toBe("A decidir");
    expect(DECISION_STATUS_LABEL.Decidido).toBe("Em vigor");
    expect(DECISION_STATUS_LABEL.Executado).toBe("Aplicada");
    expect(DECISION_STATUS_LABEL.Superseded).toBe("Substituída");
    expect(DECISION_STATUS_LABEL.Descartado).toBe("Descartada");
  });
});

describe("decisionStatusFilterLabel", () => {
  it("retorna 'Todas' para o filtro pseudo-status", () => {
    expect(decisionStatusFilterLabel("Todas")).toBe("Todas");
  });
  it("delega ao label de status para outros valores", () => {
    expect(decisionStatusFilterLabel("Pendente")).toBe("A decidir");
  });
});

describe("nextDecisionCode", () => {
  it("retorna D01 quando não há decisões", () => {
    expect(nextDecisionCode([])).toBe("D01");
  });
  it("incrementa o maior código numérico encontrado", () => {
    const decisions = [
      makeDecision({ id: "1", code: "D01" }),
      makeDecision({ id: "2", code: "D05" }),
      makeDecision({ id: "3", code: "D03" }),
    ];
    expect(nextDecisionCode(decisions)).toBe("D06");
  });
  it("ignora códigos não numéricos no padrão D\\d+", () => {
    const decisions = [
      makeDecision({ id: "1", code: "D02" }),
      makeDecision({ id: "2", code: "X99" }),
      makeDecision({ id: "3", code: "ad-hoc" }),
    ];
    expect(nextDecisionCode(decisions)).toBe("D03");
  });
  it("zero-padda para 2 dígitos", () => {
    const decisions = [makeDecision({ code: "D08" })];
    expect(nextDecisionCode(decisions)).toBe("D09");
  });
});

describe("findSupersededBy", () => {
  it("retorna a decisão que aponta para o id dado via supersedes_id", () => {
    const old = makeDecision({ id: "old", code: "D06" });
    const newer = makeDecision({
      id: "new",
      code: "D15",
      supersedes_id: "old",
    });
    expect(findSupersededBy([old, newer], "old")).toEqual(newer);
  });
  it("retorna null quando não há sucessora", () => {
    const decisions = [makeDecision({ id: "a", supersedes_id: null })];
    expect(findSupersededBy(decisions, "a")).toBeNull();
  });
});

describe("formatDecisionDate", () => {
  it("retorna '—' para null", () => {
    expect(formatDecisionDate(null)).toBe("—");
  });
  it("formata ISO em pt-BR (dd/mm/aaaa)", () => {
    const formatted = formatDecisionDate("2026-03-12T00:00:00Z");
    expect(formatted).toMatch(/\d{2}\/\d{2}\/\d{4}/);
  });
});
