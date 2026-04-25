import { describe, expect, it } from "vitest";
import { isPipelineLlmStage } from "@/lib/pipelineLlmStages";

describe("isPipelineLlmStage", () => {
  it("identifica as mesmas etapas que pipeline/orchestrator.LLM_STAGES", () => {
    expect(isPipelineLlmStage("E1")).toBe(true);
    expect(isPipelineLlmStage("E1.5")).toBe(true);
    expect(isPipelineLlmStage("E2-llm")).toBe(true);
    expect(isPipelineLlmStage("E7-review")).toBe(true);
  });

  it("retorna false para etapas determinísticas", () => {
    expect(isPipelineLlmStage("E0-unlock")).toBe(false);
    expect(isPipelineLlmStage("E2")).toBe(false);
    expect(isPipelineLlmStage("E3")).toBe(false);
  });

  it("aceita também os nomes descritivos pós-F9.2", () => {
    expect(isPipelineLlmStage("extract_members")).toBe(true);
    expect(isPipelineLlmStage("extract_baseline")).toBe(true);
    expect(isPipelineLlmStage("extract_with_llm")).toBe(true);
    expect(isPipelineLlmStage("review_finances")).toBe(true);
    expect(isPipelineLlmStage("unlock_documents")).toBe(false);
    expect(isPipelineLlmStage("reconcile_transactions")).toBe(false);
  });
});
