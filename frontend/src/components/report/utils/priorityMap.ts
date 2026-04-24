/**
 * ADR-117 · Fase 6 — mapeamento efforto (S/R/O) → prioridade (alta/media/baixa).
 *
 * O E5 atual já classifica tarefas por esforço (`essencial: S|R|O`). A UI
 * premium quer `PriorityBadge` com alta/media/baixa. Esta conversão é a
 * regra de produto decidida na Fase 0 (GAPS.md Tabela C #19).
 */
import type { Effort, PriorityLevel } from "@/components/report/ui";

const MAP: Record<Effort, PriorityLevel> = {
  S: "alta",
  R: "media",
  O: "baixa",
};

export function priorityFromEffort(effort: Effort | string | undefined): PriorityLevel | undefined {
  if (!effort) return undefined;
  const key = String(effort).toUpperCase();
  return (MAP as Record<string, PriorityLevel>)[key];
}
