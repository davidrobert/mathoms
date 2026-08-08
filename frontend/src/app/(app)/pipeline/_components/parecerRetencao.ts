import type { PipelineRunResponse } from "@/lib/api";

/** A40.l22 — retenção do parecer lida do run, para a superfície operacional.
 *
 * Irmão de `deriveDegradedStage`: o /pipeline não consulta o aggregate
 * `PlannerReview` (seriam N requests na lista de runs) — lê o que o próprio run
 * já carrega. O desfecho RETIDO INTEIRO já tem voz aqui: o stage não entrega,
 * `resolve_stage_outcome` o marca `degraded` e `degradedRunCaveat` fala por ele.
 * O que era mudo é o PARCIAL: o stage entrega, o run fecha `completed`, e a
 * perda de itens não aparecia em nenhuma superfície operacional.
 */

/** Nomes aceitos do stage do parecer — legado e descritivo (ADR-093).
 *  `stage_logs.stage` grava o descritivo desde F9.6, mas rows antigas seguem
 *  legíveis e a lista de runs mostra histórico. */
const PARECER_STAGES = new Set(["review_finances_holistic", "E6-parecer"]);

function itensRetidosDoStage(summary: Record<string, unknown> | null): number {
  // Somente o INTEIRO de `items_dropped`. `output_summary` é o detail cru do
  // stage e carrega prosa de operador (`reason`, `retention_trigger`,
  // `error_detail`); ler qualquer string daqui vazaria vocabulário interno
  // para a tela — o mesmo defeito que a ADR-366 §D3 fechou no endpoint.
  const verification = summary?.["evidencia_verification"];
  if (typeof verification !== "object" || verification === null) return 0;
  const raw = (verification as Record<string, unknown>)["items_dropped"];
  return typeof raw === "number" && Number.isFinite(raw) && raw > 0 ? Math.trunc(raw) : 0;
}

/** Itens retidos num run que ENTREGOU o parecer; 0 quando não entregou.
 *
 * O stage degradado é excluído porque lá `items_dropped` pertence ao desfecho
 * retido inteiro (0 por invariante na persistência, mas o summary é do stage,
 * não do aggregate) — contá-lo diria "N itens retidos" num parecer que saiu
 * inteiro de fora.
 */
export function parecerItensRetidosNoRun(
  run: Pick<PipelineRunResponse, "stage_logs">,
): number {
  const log = run.stage_logs.find(
    (s) => PARECER_STAGES.has(s.stage) && s.status === "completed",
  );
  return log ? itensRetidosDoStage(log.output_summary) : 0;
}
