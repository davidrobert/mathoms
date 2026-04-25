import { describe, expect, it } from "vitest";
import { resolveStageName } from "@/lib/pipelineStageNames";

describe("resolveStageName", () => {
  it("traduz cada legacy stage para o descritivo equivalente", () => {
    expect(resolveStageName("E0-audit")).toBe("audit_documents");
    expect(resolveStageName("E0-unlock")).toBe("unlock_documents");
    expect(resolveStageName("E0-route")).toBe("route_documents");
    expect(resolveStageName("E1")).toBe("extract_members");
    expect(resolveStageName("E1.5")).toBe("extract_baseline");
    expect(resolveStageName("E1.5c")).toBe("consolidate_baseline");
    expect(resolveStageName("E2-faturas")).toBe("extract_invoices");
    expect(resolveStageName("E2-extratos")).toBe("extract_statements");
    expect(resolveStageName("E2-llm")).toBe("extract_with_llm");
    expect(resolveStageName("E3")).toBe("reconcile_transactions");
    expect(resolveStageName("E4")).toBe("categorize_transactions");
    expect(resolveStageName("E5")).toBe("analyze_finances");
    expect(resolveStageName("E5.N")).toBe("generate_narratives");
    expect(resolveStageName("E7-crossval")).toBe("validate_cross");
    expect(resolveStageName("E7-review")).toBe("review_finances");
    expect(resolveStageName("E7-apply")).toBe("apply_review");
  });

  it("descritivo passa through (idempotente)", () => {
    expect(resolveStageName("extract_statements")).toBe("extract_statements");
    expect(resolveStageName("analyze_finances")).toBe("analyze_finances");
  });

  it("strings desconhecidas passam through", () => {
    expect(resolveStageName("foo")).toBe("foo");
    expect(resolveStageName("")).toBe("");
  });
});
