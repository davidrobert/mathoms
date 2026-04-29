import type { Decision, DecisionStatus } from "@/lib/api";

export type DecisionStatusFilter = DecisionStatus | "Todas";

export const DECISION_STATUS_LABEL: Record<DecisionStatus, string> = {
  Pendente: "A decidir",
  Decidido: "Em vigor",
  Executado: "Aplicada",
  Descartado: "Descartada",
  Superseded: "Substituída",
};

export const DECISION_STATUS_BADGE_CLASS: Record<DecisionStatus, string> = {
  Pendente:
    "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200",
  Decidido:
    "bg-sky-100 text-sky-900 dark:bg-sky-900/30 dark:text-sky-200",
  Executado:
    "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200",
  Descartado:
    "bg-zinc-200 text-zinc-700 dark:bg-zinc-700/50 dark:text-zinc-200",
  Superseded:
    "bg-violet-100 text-violet-900 dark:bg-violet-900/30 dark:text-violet-200",
};

export const STATUS_FILTER_ORDER: ReadonlyArray<DecisionStatusFilter> = [
  "Todas",
  "Pendente",
  "Decidido",
  "Executado",
  "Superseded",
  "Descartado",
];

export function decisionStatusFilterLabel(s: DecisionStatusFilter): string {
  return s === "Todas" ? "Todas" : DECISION_STATUS_LABEL[s];
}

export function nextDecisionCode(decisions: ReadonlyArray<Decision>): string {
  const numericCodes = decisions
    .map((d) => d.code.match(/^D(\d+)$/)?.[1])
    .filter((m): m is string => Boolean(m))
    .map((m) => parseInt(m, 10));
  const next = numericCodes.length === 0 ? 1 : Math.max(...numericCodes) + 1;
  return `D${String(next).padStart(2, "0")}`;
}

export function findSupersededBy(
  decisions: ReadonlyArray<Decision>,
  decisionId: string,
): Decision | null {
  return decisions.find((d) => d.supersedes_id === decisionId) ?? null;
}

export function formatDecisionDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}
