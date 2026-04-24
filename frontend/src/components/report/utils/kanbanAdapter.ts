/**
 * ADR-117/123 · Fase 6 — adapter tarefas[] do E5 → KanbanItem[].
 *
 * Deriva:
 * - coluna: "concluido" se status === "feito"; "em_andamento" se hoje
 *           contém a_fazer com deadline na última semana; "a_fazer" default
 * - prioridade: S→alta, R→media, O→baixa (mapeamento da decisão Q13 —
 *               mas até LLM em E5, usamos efforto como proxy)
 * - prazo_iso: string ISO se `prazo` existe no item
 * - categoria: categoria textual se presente
 */
import type { KanbanItem, KanbanColumn } from "@/components/report/ui";
import type { PriorityLevel } from "@/components/report/ui";
import type { ReportAnalysisData } from "@/lib/api";

type RawTarefa = {
  readonly id?: string | number;
  readonly titulo?: string;
  readonly descricao?: string;
  readonly essencial?: "S" | "R" | "O" | string;
  readonly status?: string;
  readonly prazo?: string;
  readonly categoria?: string;
};

const EFFORT_TO_PRIORITY: Record<string, PriorityLevel> = {
  S: "alta",
  R: "media",
  O: "baixa",
};

function mapPrioridade(essencial: string | undefined): PriorityLevel | undefined {
  if (!essencial) return undefined;
  return EFFORT_TO_PRIORITY[essencial.toUpperCase()];
}

function mapColuna(status: string | undefined): KanbanColumn {
  const s = (status ?? "").toLowerCase();
  if (s === "feito" || s === "concluido" || s === "concluída" || s === "done") {
    return "concluido";
  }
  if (s === "em_andamento" || s === "em andamento" || s === "doing") {
    return "em_andamento";
  }
  return "a_fazer";
}

export function adaptTarefasToKanban(
  data: ReportAnalysisData,
): readonly KanbanItem[] {
  const raw = Array.isArray(data.tarefas) ? (data.tarefas as RawTarefa[]) : [];
  return raw
    .filter((t) => typeof t.titulo === "string" && t.titulo.length > 0)
    .map((t, i) => ({
      id: String(t.id ?? `tarefa-${i}`),
      titulo: String(t.titulo),
      coluna: mapColuna(t.status),
      prioridade: mapPrioridade(t.essencial as string | undefined),
      prazoIso: typeof t.prazo === "string" ? t.prazo : undefined,
      categoria: typeof t.categoria === "string" ? t.categoria : undefined,
    }));
}
