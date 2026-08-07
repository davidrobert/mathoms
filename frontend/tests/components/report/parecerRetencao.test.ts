/**
 * A40.l22 — `parecerItensRetidos`: o contador é gateado pelo DESFECHO.
 *
 * A mutação que este arquivo mata é a que um refactor de simplificação faz
 * naturalmente: trocar o corpo por `data.retention?.items_dropped_count ?? 0`,
 * "porque `retention` só existe quando houve retenção". Não é verdade —
 * `retention` acompanha também `outcome === "retido"` (o validator do DTO a
 * EXIGE lá, `response.py::_outcome_matches_payload`). Sem o gate, o sinal de
 * retenção PARCIAL passa a aparecer no estado retido inteiro, que a lane
 * decidiu não sinalizar duas vezes.
 */
import { describe, expect, it } from "vitest";

import { parecerItensRetidos } from "@/components/report/utils/parecerRetencao";
import type { PlannerReviewResponse } from "@/lib/api";

function response(over: Partial<PlannerReviewResponse>): PlannerReviewResponse {
  return {
    id: "pr-1",
    workspace_id: "ws-1",
    pipeline_run_id: "run-1",
    status: "Gerado",
    persona_hash: "a".repeat(64),
    manifest_version: "1.0",
    schema_version: "1.0",
    model_id: "anthropic/claude-sonnet-4",
    tier_at_generation: "premium",
    items_shown_count: 5,
    items_gated_count: 0,
    cost_usd_cents: 1,
    created_at: "2026-08-07T00:00:00Z",
    published_at: null,
    superseded_at: null,
    supersedes_id: null,
    superseded_by_id: null,
    immutable_hash: null,
    outcome: "entregue",
    retention: null,
    content: null,
    ...over,
  };
}

describe("parecerItensRetidos", () => {
  it("conta no desfecho parcial", () => {
    const data = response({
      outcome: "entregue_com_retencao",
      retention: { reason: "parecer.citacao_nao_confirmada", items_dropped_count: 3 },
    });
    expect(parecerItensRetidos(data)).toBe(3);
  });

  it("é 0 no retido inteiro — mesmo se o contador vier preenchido", () => {
    // `retido` tem `retention` por contrato do DTO; a contagem lá é 0 por
    // invariante da persistência, mas o gate não pode DEPENDER disso: um
    // produtor que a preencha por engano não deve acender o sinal parcial.
    const data = response({
      outcome: "retido",
      retention: { reason: "parecer.sigilo", items_dropped_count: 4 },
    });
    expect(parecerItensRetidos(data)).toBe(0);
  });

  it("é 0 no parecer íntegro, mesmo com `retention` presente por engano", () => {
    const data = response({
      outcome: "entregue",
      retention: { reason: "parecer.citacao_nao_confirmada", items_dropped_count: 2 },
    });
    expect(parecerItensRetidos(data)).toBe(0);
  });

  it("tolera ausência: sem `retention`, sem dado, negativo", () => {
    expect(parecerItensRetidos(response({ outcome: "entregue_com_retencao" }))).toBe(0);
    expect(parecerItensRetidos(null)).toBe(0);
    expect(parecerItensRetidos(undefined)).toBe(0);
    const negativo = response({
      outcome: "entregue_com_retencao",
      retention: { reason: "parecer.sigilo", items_dropped_count: -1 },
    });
    expect(parecerItensRetidos(negativo)).toBe(0);
  });
});
