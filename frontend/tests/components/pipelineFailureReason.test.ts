import { describe, it, expect } from "vitest";

import {
  FAILURE_REASONS_CONHECIDOS,
  messageForFailureReason,
} from "@/lib/pipelineFailureReason";
import { buildUserFacingError } from "@/lib/pipelineErrorMessages";

// A40.l27 — `failure_reason` era coluna write-only desde 2026-05: a ADR-172 decidiu que a
// UI mostraria mensagem honesta e o campo nunca saiu do DB. Sem este reader os 4 valores do
// vocabulário são legíveis só por SQL.
describe("messageForFailureReason", () => {
  it("cobre os 4 valores do vocabulário do backend", () => {
    // Espelha `ALL_REASONS` de `backend/app/services/pipeline/pipeline_failure_reasons.py`.
    expect([...FAILURE_REASONS_CONHECIDOS].sort()).toEqual([
      "dispatch_failed",
      "dispatch_unconfirmed",
      "heartbeat_timeout",
      "run_setup_failed",
    ]);
  });

  it.each(FAILURE_REASONS_CONHECIDOS)("dá headline e hint para %s", (reason) => {
    const msg = messageForFailureReason(reason);
    expect(msg?.headline).toBeTruthy();
    expect(msg?.hint).toBeTruthy();
  });

  it("não menciona etapa para motivos em que nenhum stage rodou", () => {
    // O defeito que este reader existe para evitar: sem ele o card cai em
    // `buildUserFacingError(undefined, null)` e afirma "travou no estágio inicial" —
    // duas coisas falsas, porque não houve estágio e o run nunca começou.
    for (const reason of ["dispatch_failed", "dispatch_unconfirmed", "run_setup_failed"]) {
      const texto = JSON.stringify(messageForFailureReason(reason));
      expect(texto).not.toMatch(/etapa|estágio/i);
    }
  });

  it("distingue dispatch_failed de dispatch_unconfirmed", () => {
    // Colapsar os dois destrói o sinal de postmortem (ADR-359 §3): num sabemos QUE o
    // enqueue falhou, no outro só que não há dono.
    const falhou = messageForFailureReason("dispatch_failed");
    const naoConfirmado = messageForFailureReason("dispatch_unconfirmed");
    expect(falhou?.headline).not.toEqual(naoConfirmado?.headline);
  });

  it("devolve null para ausente, vazio e desconhecido — caller mantém o texto do stage", () => {
    expect(messageForFailureReason(null)).toBeNull();
    expect(messageForFailureReason(undefined)).toBeNull();
    expect(messageForFailureReason("")).toBeNull();
    expect(messageForFailureReason("motivo_que_nao_existe")).toBeNull();
  });

  it("o fallback do card segue funcionando quando não há failure_reason", () => {
    // Prova que a precedência não sequestra o caminho antigo: com `failure_reason` nulo o
    // card continua derivando a mensagem do erro do stage.
    const doStage = buildUserFacingError("boom", "extract_statements");
    expect(messageForFailureReason(null) ?? doStage).toBe(doStage);
  });
});
