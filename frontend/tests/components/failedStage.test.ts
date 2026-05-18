import { describe, it, expect } from "vitest";

import { deriveFailedStage } from "@/app/(app)/pipeline/_components/failedStage";

const baseRun = {
  failed_at_stage: null as string | null,
  stage_logs: [] as Array<{ stage: string; status: string }>,
};

describe("deriveFailedStage", () => {
  it("prefere failed_at_stage quando presente", () => {
    expect(
      deriveFailedStage({
        failed_at_stage: "extract_statements",
        stage_logs: [
          { stage: "extract_invoices", status: "failed" } as never,
        ],
      }),
    ).toBe("extract_statements");
  });

  it("deriva do último stage_log com status=failed quando failed_at_stage é null", () => {
    expect(
      deriveFailedStage({
        ...baseRun,
        stage_logs: [
          { stage: "route_documents", status: "completed" } as never,
          { stage: "extract_invoices", status: "failed" } as never,
        ],
      }),
    ).toBe("extract_invoices");
  });

  it("retorna null quando não há failed_at_stage nem stage_log com status=failed (crash Celery on_failure)", () => {
    expect(
      deriveFailedStage({
        ...baseRun,
        stage_logs: [
          { stage: "route_documents", status: "completed" } as never,
        ],
      }),
    ).toBeNull();
  });

  it("retorna null para run vazio (falha antes de qualquer etapa)", () => {
    expect(deriveFailedStage(baseRun)).toBeNull();
  });
});
