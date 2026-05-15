/**
 * Tests — suggestionSortComparator (ADR-161 · Onda 8 #4).
 *
 * ADR-214 — `computeNextDecisionCode` deletado (server gera code);
 * o bloco describe correspondente migrou para o backend.
 */
import { describe, expect, it } from "vitest";

import { suggestionSortComparator } from "@/app/(app)/acao/_components/InboxTab";
import type { Suggestion } from "@/lib/api";

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
    dedup_key: `dedup-${id}`,
    status: "Pendente",
    accepted_decision_id: null,
    accepted_decision_code: null,
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
