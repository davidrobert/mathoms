import { describe, expect, it } from "vitest";
import {
  computePhaseProgress,
  computePhaseStates,
  PIPELINE_PHASES,
  phaseOfStage,
} from "@/lib/pipelinePhases";

describe("computePhaseProgress", () => {
  it("retorna 0 quando run sem stage_logs e sem fase ativa", () => {
    const states = computePhaseStates([], null, "pending");
    expect(computePhaseProgress(states)).toBe(0);
  });

  it("fase 1 ativa sem sub-stages registrados conta como 0.5/4 = 12-13%", () => {
    const states = computePhaseStates([], "E0-route", "running");
    const pct = computePhaseProgress(states);
    expect(pct).toBeGreaterThanOrEqual(12);
    expect(pct).toBeLessThanOrEqual(13);
  });

  it("fase 2 ativa com sub-stages concluídos = 50% (não 100%)", () => {
    // Reproduz o bug do screenshot: phase 1 completa, phase 2 active com
    // todos os sub-stages registrados como completed e próxima phase 3
    // ainda não inseriu rows em stage_logs.
    const phase1Stages = PIPELINE_PHASES[0].stages;
    const phase2Stages = PIPELINE_PHASES[1].stages;
    const stageLogs = [
      ...phase1Stages.map((s) => ({ stage: s, status: "completed" })),
      ...phase2Stages.map((s) => ({ stage: s, status: "completed" })),
    ];
    // current_stage aponta para uma stage de fase 2 (ainda em phase 2 por
    // mais um beat antes do backend transicionar para phase 3).
    const states = computePhaseStates(stageLogs, phase2Stages[0], "running");
    // Phase 1: completed (1.0); Phase 2: active com ratio 1.0 → 1.0;
    // Phases 3-4: pending → 0. Total = 2.0 / 4 = 50%.
    expect(computePhaseProgress(states)).toBe(50);
  });

  it("avança proporcionalmente à medida que fases concluem", () => {
    // Phase 1 inteira concluída; phase 2 começou.
    const phase1Stages = PIPELINE_PHASES[0].stages;
    const phase2Stages = PIPELINE_PHASES[1].stages;
    const stageLogs = [
      ...phase1Stages.map((stage) => ({ stage, status: "completed" })),
      { stage: phase2Stages[0], status: "running" },
    ];
    const states = computePhaseStates(stageLogs, phase2Stages[0], "running");
    // 1 phase completed (1.0) + active phase (0.5 + 0.5 × 0/1 = 0.5) → 1.5/4 = 37.5% → 38
    expect(computePhaseProgress(states)).toBeGreaterThanOrEqual(37);
    expect(computePhaseProgress(states)).toBeLessThanOrEqual(38);
  });

  it("run completo (4/4 fases) = 100%", () => {
    const allStages = PIPELINE_PHASES.flatMap((p) => p.stages);
    const stageLogs = allStages.map((stage) => ({ stage, status: "completed" }));
    const states = computePhaseStates(stageLogs, null, "completed");
    expect(computePhaseProgress(states)).toBe(100);
  });

  it("fase ativa com metade dos sub-stages concluídos pondera contribuição", () => {
    // Phase 1 done; phase 2 ativa com 3 completed + 1 running em logs (4 total).
    const phase2Stages = PIPELINE_PHASES[1].stages;
    const stageLogs = [
      ...PIPELINE_PHASES[0].stages.map((s) => ({ stage: s, status: "completed" })),
      ...phase2Stages.slice(0, 3).map((s) => ({ stage: s, status: "completed" })),
      { stage: phase2Stages[3], status: "running" },
    ];
    const states = computePhaseStates(stageLogs, phase2Stages[3], "running");
    // Phase 1 completed → 1.0
    // Phase 2 active: completedStages=3, totalStages=4 (apenas o que está em logs)
    //   → ratio 0.75 → 0.5 + 0.5*0.75 = 0.875
    // Total: (1.0 + 0.875) / 4 = 46.875% → arredonda para 47.
    expect(computePhaseProgress(states)).toBe(47);
  });

  it("fase falhada conta apenas o ratio do que foi concluído", () => {
    // Phase 2 falhou após 2 stages completed; phase 1 também tem logs.
    // Nota: `computePhaseStates` marca fases prévias como pending quando o
    // run inteiro está failed (status do run domina). Aqui validamos só a
    // contribuição da fase failed em si.
    const phase2Stages = PIPELINE_PHASES[1].stages;
    const stageLogs = [
      ...PIPELINE_PHASES[0].stages.map((s) => ({ stage: s, status: "completed" })),
      ...phase2Stages.slice(0, 2).map((s) => ({ stage: s, status: "completed" })),
      { stage: phase2Stages[2], status: "failed" },
    ];
    const states = computePhaseStates(stageLogs, phase2Stages[2], "failed");
    // Phase 2: status="failed", ratio = 2/3 = 0.667 → 0.667 contribuição
    // Phases 1, 3, 4: pending (run failed dominante) → 0
    // Total = 0.667/4 = 16.67% → 17.
    expect(computePhaseProgress(states)).toBe(17);
  });

  // Regressão: pós-F9.2 STAGE_REGISTRY usa nomes descritivos
  // (review_finances_holistic, etc.). Antes, PIPELINE_PHASES só tinha legacy
  // keys (E*), então qualquer stage descritivo caía no fallback "reading" e
  // gerava mensagem "Não conseguimos completar a etapa de lendo os dados".
  it.each([
    // audit_documents removido em ADR-213 (sunset stage).
    ["unlock_documents", "preparing"],
    ["route_documents", "preparing"],
    ["extract_members", "reading"],
    ["extract_baseline", "reading"],
    ["consolidate_baseline", "reading"],
    ["extract_irpf_full", "reading"],
    ["extract_statements", "reading"],
    ["extract_invoices", "reading"],
    ["extract_with_llm", "reading"],
    ["reconcile_transactions", "organizing"],
    ["categorize_transactions", "organizing"],
    ["analyze_finances", "organizing"],
    ["generate_narratives", "organizing"],
    ["validate_cross", "reporting"],
    ["review_finances_holistic", "reporting"],
  ])("descriptive stage %s → phase %s (ADR-093)", (stage, expected) => {
    expect(phaseOfStage(stage)).toBe(expected);
  });

  // ─── ADR-357 / A40.l21 — run degradado é terminal e entregue ───

  const allStagesWith = (degradedStage: string) =>
    PIPELINE_PHASES.flatMap((p) =>
      p.stages.map((s) => ({
        stage: s,
        status: s === degradedStage ? "degraded" : "completed",
      })),
    );

  it("partial_failure não pinta nenhuma fase de falha", () => {
    const states = computePhaseStates(
      allStagesWith("review_finances_holistic"),
      null,
      "partial_failure",
    );
    expect(states.every((s) => s.status !== "failed")).toBe(true);
  });

  // Mata a mutação plausível "completa a exaustividade" em
  // `stageLogs.find(s => s.status === "failed" || s.status === "degraded")`.
  it("etapa degradada não marca a fase como falhada", () => {
    const states = computePhaseStates(
      allStagesWith("review_finances_holistic"),
      null,
      "partial_failure",
    );
    const reporting = states.find((s) => s.phase.id === "reporting")!;
    expect(reporting.status).toBe("completed");
  });

  it("fase sem logs próprios fecha num run parcial (não fica pendente)", () => {
    // Só as fases 1-3 têm logs; a 4 não registrou nenhuma etapa.
    const logs = PIPELINE_PHASES.slice(0, 3).flatMap((p) =>
      p.stages.map((s) => ({ stage: s, status: "completed" })),
    );
    const states = computePhaseStates(logs, null, "partial_failure");
    expect(states.find((s) => s.phase.id === "reporting")!.status).toBe("completed");
  });

  it("run parcial chega a 100% — entregou", () => {
    const states = computePhaseStates(
      allStagesWith("review_finances_holistic"),
      null,
      "partial_failure",
    );
    expect(computePhaseProgress(states)).toBe(100);
  });

  it("run failed continua pintando a fase da etapa que falhou", () => {
    const logs = PIPELINE_PHASES.flatMap((p) =>
      p.stages.map((s) => ({
        stage: s,
        status: s === "reconcile_transactions" ? "failed" : "completed",
      })),
    );
    const states = computePhaseStates(logs, null, "failed");
    expect(states.find((s) => s.phase.id === "organizing")!.status).toBe("failed");
  });

  it("monotônico: progresso nunca decresce conforme stages adicionam", () => {
    const phase2Stages = PIPELINE_PHASES[1].stages;
    let prev = 0;
    for (let i = 0; i <= phase2Stages.length; i++) {
      const stageLogs = [
        ...PIPELINE_PHASES[0].stages.map((s) => ({ stage: s, status: "completed" })),
        ...phase2Stages.slice(0, i).map((s) => ({ stage: s, status: "completed" })),
      ];
      const states = computePhaseStates(stageLogs, phase2Stages[i] ?? null, "running");
      const pct = computePhaseProgress(states);
      expect(pct).toBeGreaterThanOrEqual(prev);
      prev = pct;
    }
  });
});
