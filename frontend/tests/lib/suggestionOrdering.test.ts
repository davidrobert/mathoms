/**
 * Tests — ordering metodológico + caps de display (ADR-290 F3).
 *
 * Substitui os testes do `suggestionSortComparator` (ADR-161) que vivia em
 * InboxTab — o ordering agora é compartilhado pelas 3 superfícies.
 * Snapshot do aceite F3: danger no topo independente de qualquer filtro.
 */
import { describe, expect, it } from "vitest";

import type { Suggestion } from "@/lib/api";
import {
  ACTIONABLE_DISPLAY_CAP,
  methodologicalGate,
  partitionForDisplay,
  suggestionPriorityComparator,
} from "@/lib/suggestionOrdering";

function makeSug(overrides: Partial<Suggestion> & { id: string }): Suggestion {
  return {
    workspace_id: "ws",
    report_id: null,
    section_id: "S2",
    kind: "parecer_planejador",
    category: null,
    origin: "llm",
    severity: "warning",
    title: "t",
    rationale: "r",
    amount_brl: null,
    dedup_key: `dedup-${overrides.id}`,
    status: "Pendente",
    accepted_decision_id: null,
    accepted_decision_code: null,
    dismissed_reason: null,
    accepted_at: null,
    dismissed_at: null,
    created_at: "2026-01-01",
    updated_at: "2026-01-01",
    ...overrides,
  };
}

describe("suggestionPriorityComparator", () => {
  it("danger vem antes de warning vem antes de info", () => {
    const list = [
      makeSug({ id: "a", severity: "info" }),
      makeSug({ id: "b", severity: "danger" }),
      makeSug({ id: "c", severity: "warning" }),
    ];
    const sorted = [...list].sort(suggestionPriorityComparator);
    expect(sorted.map((s) => s.severity)).toEqual(["danger", "warning", "info"]);
  });

  it("danger no topo independente de gate/impacto (não filtrável)", () => {
    const list = [
      makeSug({ id: "fiscal-alto", severity: "warning", section_id: "S8", amount_brl: "900000.00" }),
      makeSug({ id: "danger-fiscal", severity: "danger", section_id: "S8" }),
      makeSug({ id: "protecao", severity: "warning", section_id: "S9" }),
    ];
    const sorted = [...list].sort(suggestionPriorityComparator);
    expect(sorted[0].id).toBe("danger-fiscal");
  });

  it("mesma severidade: gate metodológico ordena proteção → alocação → fiscal", () => {
    const list = [
      makeSug({ id: "fiscal", section_id: "S_IRPF_OTIMIZACAO" }),
      makeSug({ id: "alocacao", section_id: "S3" }),
      makeSug({ id: "protecao", section_id: "S9" }),
      makeSug({ id: "if", section_id: "S7" }),
    ];
    const sorted = [...list].sort(suggestionPriorityComparator);
    expect(sorted.map((s) => s.id)).toEqual(["protecao", "alocacao", "if", "fiscal"]);
  });

  it("dentro do gate: sem valor antes (gap não-quantificado), depois impacto desc", () => {
    const list = [
      makeSug({ id: "menor", section_id: "S9", amount_brl: "1000.00" }),
      makeSug({ id: "maior", section_id: "S9", amount_brl: "50000.00" }),
      makeSug({ id: "sem-valor", section_id: "S9", amount_brl: null }),
    ];
    const sorted = [...list].sort(suggestionPriorityComparator);
    expect(sorted.map((s) => s.id)).toEqual(["sem-valor", "maior", "menor"]);
  });

  it("empate total: created_at desc (estável)", () => {
    const list = [
      makeSug({ id: "velho", created_at: "2026-01-01" }),
      makeSug({ id: "novo", created_at: "2026-03-01" }),
    ];
    const sorted = [...list].sort(suggestionPriorityComparator);
    expect(sorted.map((s) => s.id)).toEqual(["novo", "velho"]);
  });
});

describe("methodologicalGate", () => {
  it("deterministic usa category; llm usa section_id; desconhecido vai pro fim", () => {
    expect(
      methodologicalGate(makeSug({ id: "d", origin: "deterministic", category: "endividamento" })),
    ).toBe(2);
    expect(methodologicalGate(makeSug({ id: "l", origin: "llm", section_id: "S1" }))).toBe(1);
    expect(methodologicalGate(makeSug({ id: "x", origin: "llm", section_id: "S_parecer" }))).toBe(6);
    expect(
      methodologicalGate(makeSug({ id: "y", origin: "deterministic", category: "futura" })),
    ).toBe(6);
  });
});

describe("partitionForDisplay", () => {
  it("info fica fora do cap; acionáveis acima de 12 vão pro overflow", () => {
    const actionable = Array.from({ length: 15 }, (_, i) =>
      makeSug({ id: `w${i}`, severity: "warning" }),
    );
    const info = Array.from({ length: 4 }, (_, i) =>
      makeSug({ id: `i${i}`, severity: "info" }),
    );
    const { primary, overflow, informative } = partitionForDisplay([...info, ...actionable]);
    expect(primary).toHaveLength(ACTIONABLE_DISPLAY_CAP);
    expect(overflow).toHaveLength(3);
    expect(informative).toHaveLength(4);
  });

  it("overflow nunca contém danger (cap ≤2 danger garante topo)", () => {
    const dangers = [
      makeSug({ id: "d1", severity: "danger" }),
      makeSug({ id: "d2", severity: "danger" }),
    ];
    const warnings = Array.from({ length: 14 }, (_, i) =>
      makeSug({ id: `w${i}`, severity: "warning" }),
    );
    const { primary, overflow } = partitionForDisplay([...warnings, ...dangers]);
    expect(primary.slice(0, 2).map((s) => s.severity)).toEqual(["danger", "danger"]);
    expect(overflow.every((s) => s.severity !== "danger")).toBe(true);
  });
});
