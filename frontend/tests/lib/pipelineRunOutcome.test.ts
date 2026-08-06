/**
 * Tabela de decisão da A40.l21 como código (ADR-357).
 *
 * O teste que importa é a matriz {nome de evento} × {status}: o writer da
 * A40.l18 ainda não existe e pode chamar `publish_run_completed` OU
 * `publish_run_failed` com `status:"partial_failure"` — o leitor tem que dar a
 * mesma resposta nos dois casos.
 */
import { describe, expect, it } from "vitest";
import type { PipelineEvent, PipelineRunStatus } from "@/lib/api";
import {
  isDeliveredRun,
  runStatusFromEvent,
  terminalRunOutcome,
} from "@/lib/pipelineRunOutcome";

const ev = (e: Partial<PipelineEvent>): PipelineEvent =>
  ({ event: "run_completed", ...e }) as PipelineEvent;

describe("runStatusFromEvent — matriz evento × status", () => {
  const EVENT_NAMES = ["run_completed", "run_failed"] as const;
  const STATUSES: PipelineRunStatus[] = [
    "completed",
    "partial_failure",
    "failed",
    "cancelled",
  ];

  for (const event of EVENT_NAMES) {
    for (const status of STATUSES) {
      it(`${event} carregando status ${status} → ${status}`, () => {
        expect(runStatusFromEvent(ev({ event, status }))).toBe(status);
      });
    }
  }

  // A asserção que mata a mutação "simplifica de volta para switch(ev.event)".
  it("run_failed com status partial_failure NÃO é failed", () => {
    expect(runStatusFromEvent(ev({ event: "run_failed", status: "partial_failure" })))
      .toBe("partial_failure");
  });

  it("sem status → cai no nome do evento (writer que esqueceu o parâmetro)", () => {
    expect(runStatusFromEvent(ev({ event: "run_completed" }))).toBe("completed");
    expect(runStatusFromEvent(ev({ event: "run_failed" }))).toBe("failed");
    expect(runStatusFromEvent(ev({ event: "run_cancelled" }))).toBe("cancelled");
  });

  it("evento de stage não sequestra o desfecho do run", () => {
    // `status` é reusado com semântica de stage; `stage` é o discriminador.
    const stageEvent = ev({ event: "stage_completed", stage: "E3", status: "completed" });
    expect(runStatusFromEvent(stageEvent)).toBeNull();
  });

  it("evento desconhecido sem status → null (não inventa desfecho)", () => {
    expect(runStatusFromEvent(ev({ event: "run_degraded" }))).toBeNull();
  });
});

describe("terminalRunOutcome", () => {
  it("partial_failure leva ao entregável, igual a completed", () => {
    expect(terminalRunOutcome("partial_failure")?.redirectToReports).toBe(true);
    expect(terminalRunOutcome("completed")?.redirectToReports).toBe(true);
  });

  it("partial_failure é warning, não error", () => {
    expect(terminalRunOutcome("partial_failure")?.toast).toBe("warning");
    expect(terminalRunOutcome("failed")?.toast).toBe("error");
  });

  it("partial_failure declara a ressalva no texto", () => {
    const out = terminalRunOutcome("partial_failure");
    expect(out?.title).toBe("Relatório gerado com ressalva");
    expect(out?.description).toMatch(/não foi concluída/);
  });

  it("failed não redireciona para o relatório", () => {
    expect(terminalRunOutcome("failed")?.redirectToReports).toBe(false);
  });

  it("copy do usuário não vaza jargão técnico", () => {
    for (const s of ["completed", "partial_failure", "failed", "cancelled"]) {
      const out = terminalRunOutcome(s)!;
      expect(`${out.title} ${out.description ?? ""}`).not.toMatch(
        /pipeline|stage|LLM|E[0-9]/i,
      );
    }
  });

  it("status não-terminal não produz desfecho", () => {
    for (const s of ["pending", "running", "resuming", "needs_review"]) {
      expect(terminalRunOutcome(s)).toBeNull();
    }
  });
});

describe("isDeliveredRun", () => {
  it("completed e partial_failure entregaram relatório", () => {
    expect(isDeliveredRun("completed")).toBe(true);
    expect(isDeliveredRun("partial_failure")).toBe(true);
  });

  it("os demais não", () => {
    for (const s of ["pending", "running", "resuming", "failed", "cancelled", "needs_review"]) {
      expect(isDeliveredRun(s)).toBe(false);
    }
  });
});
