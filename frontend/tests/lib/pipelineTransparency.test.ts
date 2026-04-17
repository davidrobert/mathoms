import { describe, it, expect } from "vitest";
import {
  reviewPauseImpactHint,
  stageLlmFootnote,
} from "@/lib/pipelineTransparency";

describe("reviewPauseImpactHint", () => {
  it("E4 menciona categorias e recomendações", () => {
    expect(reviewPauseImpactHint("E4")).toMatch(/categorias/);
  });
  it("E7-review menciona categorias", () => {
    expect(reviewPauseImpactHint("E7-review")).toMatch(/categorias/);
  });
  it("E3 menciona transações e saldos", () => {
    expect(reviewPauseImpactHint("E3")).toMatch(/transações/);
  });
  it("fallback sem stage", () => {
    expect(reviewPauseImpactHint(null).length).toBeGreaterThan(20);
  });
});

describe("stageLlmFootnote", () => {
  it("retorna texto para E1", () => {
    expect(stageLlmFootnote("E1")).toContain("IA");
  });
  it("null para E3", () => {
    expect(stageLlmFootnote("E3")).toBeNull();
  });
});
