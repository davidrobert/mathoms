"use client";

// A7.2a · ADR-136 — Plano de Ação (Decisões editoriais).
// Lista as decisões do workspace ordenadas por code, com filtro por status
// e CTA "Marcar como executada" para Decisões em status "Decidido".

import { useMemo, useState } from "react";

import { ReportSection } from "../../ReportSection";
import { MonetaryValue } from "../../MonetaryValue";
import { useDecisions } from "@/hooks/useDecisions";
import type { Decision, DecisionStatus } from "@/lib/api";

const STATUS_FILTERS: ReadonlyArray<DecisionStatus | "Todos"> = [
  "Todos",
  "Pendente",
  "Decidido",
  "Executado",
  "Superseded",
];

const STATUS_BADGE_CLASS: Record<DecisionStatus, string> = {
  Pendente: "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200",
  Decidido: "bg-sky-100 text-sky-900 dark:bg-sky-900/30 dark:text-sky-200",
  Executado: "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200",
  Descartado: "bg-zinc-200 text-zinc-700 dark:bg-zinc-700/50 dark:text-zinc-200",
  Superseded: "bg-violet-100 text-violet-900 dark:bg-violet-900/30 dark:text-violet-200",
};

interface PlanoDeAcaoSectionProps {
  workspaceId: string | undefined;
}

/** F9 · A7.2a · ADR-136 — Tabela do Plano de Ação (decisions aggregate). */
export function PlanoDeAcaoSection({ workspaceId }: PlanoDeAcaoSectionProps) {
  const { decisions, loading, error, execute } = useDecisions(workspaceId);
  const [statusFilter, setStatusFilter] = useState<DecisionStatus | "Todos">("Todos");

  const filtered = useMemo(
    () =>
      statusFilter === "Todos"
        ? decisions
        : decisions.filter((d) => d.status === statusFilter),
    [decisions, statusFilter],
  );

  return (
    <ReportSection id="plano_de_acao" title="Plano de Ação">
      <div className="md:col-span-2 flex flex-col gap-4">
        <StatusFilters value={statusFilter} onChange={setStatusFilter} />
        {error && (
          <p className="text-sm text-[var(--semantic-danger)]">{error}</p>
        )}
        {loading ? (
          <p className="text-sm text-[var(--surface-muted-foreground)]">Carregando…</p>
        ) : (
          <DecisionTable rows={filtered} onExecute={execute} />
        )}
      </div>
    </ReportSection>
  );
}

interface StatusFiltersProps {
  value: DecisionStatus | "Todos";
  onChange: (next: DecisionStatus | "Todos") => void;
}

function StatusFilters({ value, onChange }: StatusFiltersProps) {
  return (
    <div role="tablist" aria-label="Filtrar decisões por status" className="flex flex-wrap gap-2">
      {STATUS_FILTERS.map((option) => {
        const active = value === option;
        return (
          <button
            type="button"
            role="tab"
            aria-selected={active}
            key={option}
            onClick={() => onChange(option)}
            className={[
              "px-3 py-1 rounded-full text-xs font-medium transition-colors border",
              active
                ? "bg-[var(--brand-primary)] text-white border-[var(--brand-primary)]"
                : "bg-transparent text-[var(--surface-foreground)] border-[var(--surface-border)] hover:bg-[var(--surface-muted)]",
            ].join(" ")}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}

interface DecisionTableProps {
  rows: Decision[];
  onExecute: (decisionId: string) => Promise<void>;
}

function DecisionTable({ rows, onExecute }: DecisionTableProps) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Nenhuma decisão registrada nesse filtro.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase text-[var(--surface-muted-foreground)]">
            <th className="py-2 pr-4">Code</th>
            <th className="py-2 pr-4">Título</th>
            <th className="py-2 pr-4">Valor</th>
            <th className="py-2 pr-4">Status</th>
            <th className="py-2 pr-4">Supersede</th>
            <th className="py-2 pr-4">Decidida</th>
            <th className="py-2 pr-4">Executada</th>
            <th className="py-2 pr-4 sr-only">Ações</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((d) => (
            <DecisionRow key={d.id} decision={d} onExecute={onExecute} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface DecisionRowProps {
  decision: Decision;
  onExecute: (decisionId: string) => Promise<void>;
}

function DecisionRow({ decision, onExecute }: DecisionRowProps) {
  const amount = decision.amount_brl !== null ? Number(decision.amount_brl) : null;
  return (
    <tr className="border-t border-[var(--surface-border)]">
      <td className="py-2 pr-4 font-mono text-xs">{decision.code}</td>
      <td className="py-2 pr-4">{decision.title}</td>
      <td className="py-2 pr-4">
        <MonetaryValue value={amount} hideSymbol={false} />
      </td>
      <td className="py-2 pr-4">
        <StatusBadge status={decision.status} />
      </td>
      <td className="py-2 pr-4 text-xs text-[var(--surface-muted-foreground)]">
        {decision.supersedes_id ? "supersedes" : "—"}
      </td>
      <td className="py-2 pr-4 text-xs">{decision.decided_at ?? "—"}</td>
      <td className="py-2 pr-4 text-xs">{decision.executed_at ?? "—"}</td>
      <td className="py-2 pr-4 text-right">
        {decision.status === "Decidido" && (
          <ExecuteButton decisionId={decision.id} onExecute={onExecute} />
        )}
      </td>
    </tr>
  );
}

interface StatusBadgeProps {
  status: DecisionStatus;
}

function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        STATUS_BADGE_CLASS[status],
      ].join(" ")}
    >
      {status}
    </span>
  );
}

interface ExecuteButtonProps {
  decisionId: string;
  onExecute: (decisionId: string) => Promise<void>;
}

function ExecuteButton({ decisionId, onExecute }: ExecuteButtonProps) {
  const [busy, setBusy] = useState(false);
  const handle = async () => {
    setBusy(true);
    try {
      await onExecute(decisionId);
    } finally {
      setBusy(false);
    }
  };
  return (
    <button
      type="button"
      disabled={busy}
      onClick={handle}
      className="text-xs px-2 py-1 rounded border border-[var(--surface-border)] hover:bg-[var(--surface-muted)] disabled:opacity-50"
    >
      {busy ? "Executando…" : "Marcar como executada"}
    </button>
  );
}
