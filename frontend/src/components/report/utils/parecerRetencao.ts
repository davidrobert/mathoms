import type { PlannerReviewResponse } from "@/lib/api";

/** A40.l22 — quantos itens o parecer gerou e retiveram antes de publicar.
 *
 * Gateado pelo `outcome` (ADR-366 §D1 — discriminante que o cliente consome
 * direto), **nunca** pelo contador. `retention` também acompanha o desfecho
 * `retido`, onde a contagem é 0 por invariante (nada foi removido: o parecer
 * inteiro ficou fora) e a superfície de sinal é outra. Ler o contador cru
 * faria o sinal de retenção PARCIAL vazar para o estado retido inteiro, que a
 * lane decidiu não sinalizar duas vezes.
 */
export function parecerItensRetidos(
  data: PlannerReviewResponse | null | undefined,
): number {
  if (!data || data.outcome !== "entregue_com_retencao") return 0;
  return Math.max(0, data.retention?.items_dropped_count ?? 0);
}
