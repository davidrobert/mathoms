import { describe, expect, it } from "vitest";

import {
  DECISION_STATUS_LABEL,
  decisionStatusFilterLabel,
  findSupersededBy,
  formatDecisionDate,
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
    target_field: null,
    target_value: null,
    target_value_type: null,
    context_snapshot: null,
    impact_1y_brl: null,
    impact_10y_brl: null,
    horizon: "short_6_12m",
    priority: null,
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

// ADR-214 — `nextDecisionCode` removido (server gera o code via
// pg_advisory_xact_lock). Bloco describe deletado; cobertura migrou
// para `backend/tests/test_decision_use_cases.py::test_create_decision_auto_generates_code_when_omitted`.

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
