import { describe, expect, it } from "vitest";
import type { PipelineEvent } from "@/lib/api";
import {
  parseStageActivityEvent,
  resolveStageName,
} from "@/lib/pipelineStageNames";

describe("resolveStageName", () => {
  it("traduz cada legacy stage para o descritivo equivalente", () => {
    // E0-audit removido em ADR-213 (sunset stage audit_documents).
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
    expect(resolveStageName("E6-parecer")).toBe("review_finances_holistic");
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

describe("parseStageActivityEvent", () => {
  const baseEvent = (over: Partial<PipelineEvent> = {}): PipelineEvent => ({
    event: "stage_activity",
    run_id: "run-1",
    ...over,
  });

  it("normaliza stage legacy → descritivo (regressão guard F9.2)", () => {
    // Bug 2026-04-25: emissor passa "E2-extratos" mas stage_logs[].stage
    // já está em "extract_statements". Sem normalização aqui, o filtro
    // do StageRow nunca bate e o painel LiveStepProgress some.
    const out = parseStageActivityEvent(
      baseEvent({
        stage: "E2-extratos",
        detail: { file: "itau_202401.pdf", items_done: 1, items_total: 3 },
      }),
    );
    expect(out).not.toBeNull();
    expect(out?.stage).toBe("extract_statements");
    expect(out?.file).toBe("itau_202401.pdf");
    expect(out?.itemsDone).toBe(1);
    expect(out?.itemsTotal).toBe(3);
  });

  it("stage descritivo passa through sem alteração", () => {
    const out = parseStageActivityEvent(
      baseEvent({
        stage: "extract_with_llm",
        detail: { file: "btg.pdf", phase: "awaiting_llm" },
      }),
    );
    expect(out?.stage).toBe("extract_with_llm");
    expect(out?.phase).toBe("awaiting_llm");
  });

  it("retorna null para eventos não-stage_activity", () => {
    expect(
      parseStageActivityEvent(baseEvent({ event: "stage_started", stage: "E1" })),
    ).toBeNull();
  });

  it("retorna null quando stage está ausente", () => {
    expect(parseStageActivityEvent(baseEvent({ stage: undefined }))).toBeNull();
  });

  it("ignora detail.phase inválido", () => {
    const out = parseStageActivityEvent(
      baseEvent({
        stage: "E1.5",
        detail: { phase: "phase_inventada" },
      }),
    );
    expect(out?.phase).toBeUndefined();
  });

  it("type-narrowing rejeita campos com tipo errado", () => {
    const out = parseStageActivityEvent(
      baseEvent({
        stage: "E2-extratos",
        // @ts-expect-error — proposital: input mal-formado do WS
        detail: { file: 42, items_done: "tres" },
      }),
    );
    expect(out?.file).toBeUndefined();
    expect(out?.itemsDone).toBeUndefined();
  });
});
