"use client";

import { useMemo, useState } from "react";
import { Plus, Scale } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useDecisions } from "@/hooks/useDecisions";
import { ApiError, type Decision } from "@/lib/api";

import { DecisionCard } from "./DecisionCard";
import {
  DecisionFormDialog,
  type DecisionFormMode,
} from "./DecisionFormDialog";
import { DecisionSupersedeDialog } from "./DecisionSupersedeDialog";
import {
  type DecisionStatusFilter,
  STATUS_FILTER_ORDER,
  decisionStatusFilterLabel,
  nextDecisionCode,
} from "./decisionsCopy";

interface DecisionsSectionProps {
  workspaceId: string;
}

export function DecisionsSection({ workspaceId }: DecisionsSectionProps) {
  const decisionsState = useDecisions(workspaceId);
  const { decisions, loading, error, create, execute, update, supersede } =
    decisionsState;
  const [filter, setFilter] = useState<DecisionStatusFilter>("Todas");
  const [formMode, setFormMode] = useState<DecisionFormMode | null>(null);
  const [supersedeTarget, setSupersedeTarget] = useState<Decision | null>(null);

  const filtered = useFilteredDecisions(decisions, filter);
  const handleNew = () =>
    setFormMode({ kind: "create", defaultCode: nextDecisionCode(decisions) });
  const handleEdit = (decision: Decision) =>
    setFormMode({ kind: "edit", decision });
  const handleMarkDecided = async (decisionId: string) =>
    markDecided(decisionId, update);

  return (
    <section className="mt-8">
      <DecisionsHeader
        total={decisions.length}
        pending={countByStatus(decisions, "Pendente")}
        onNew={handleNew}
      />
      {decisions.length > 0 && (
        <StatusFilters value={filter} onChange={setFilter} />
      )}
      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      <DecisionsBody
        loading={loading}
        decisions={decisions}
        filtered={filtered}
        onNew={handleNew}
        onEdit={handleEdit}
        onSupersede={setSupersedeTarget}
        onMarkDecided={handleMarkDecided}
        onExecute={execute}
      />
      {formMode && (
        <DecisionFormDialog
          open
          onOpenChange={(open) => !open && setFormMode(null)}
          mode={formMode}
          onCreate={create}
          onUpdate={update}
        />
      )}
      {supersedeTarget && (
        <DecisionSupersedeDialog
          open
          onOpenChange={(open) => !open && setSupersedeTarget(null)}
          oldDecision={supersedeTarget}
          defaultCode={nextDecisionCode(decisions)}
          onCreate={create}
          onSupersede={supersede}
        />
      )}
    </section>
  );
}

function useFilteredDecisions(
  decisions: ReadonlyArray<Decision>,
  filter: DecisionStatusFilter,
): Decision[] {
  return useMemo(() => {
    const sorted = sortDecisions(decisions);
    return filter === "Todas"
      ? sorted
      : sorted.filter((d) => d.status === filter);
  }, [decisions, filter]);
}

async function markDecided(
  decisionId: string,
  update: (id: string, payload: { status: "Decidido" }) => Promise<void>,
): Promise<void> {
  try {
    await update(decisionId, { status: "Decidido" });
  } catch (err) {
    const msg = err instanceof ApiError ? err.detail : "Erro";
    toast.error(msg);
    throw err;
  }
}

interface DecisionsBodyProps {
  loading: boolean;
  decisions: ReadonlyArray<Decision>;
  filtered: ReadonlyArray<Decision>;
  onNew: () => void;
  onEdit: (decision: Decision) => void;
  onSupersede: (decision: Decision) => void;
  onMarkDecided: (decisionId: string) => Promise<void>;
  onExecute: (decisionId: string) => Promise<void>;
}

function DecisionsBody({
  loading,
  decisions,
  filtered,
  onNew,
  onEdit,
  onSupersede,
  onMarkDecided,
  onExecute,
}: DecisionsBodyProps) {
  if (loading) {
    return <p className="mt-3 text-sm text-muted-foreground">Carregando…</p>;
  }
  if (decisions.length === 0) {
    return <DecisionsEmptyState onNew={onNew} />;
  }
  if (filtered.length === 0) {
    return (
      <p className="mt-3 text-sm text-muted-foreground">
        Nenhuma decisão neste filtro.
      </p>
    );
  }
  return (
    <ul className="mt-4 grid grid-cols-1 gap-3">
      {filtered.map((d) => (
        <li key={d.id}>
          <DecisionCard
            decision={d}
            allDecisions={decisions}
            onEdit={onEdit}
            onSupersede={onSupersede}
            onMarkDecided={onMarkDecided}
            onExecute={onExecute}
          />
        </li>
      ))}
    </ul>
  );
}

interface DecisionsHeaderProps {
  total: number;
  pending: number;
  onNew: () => void;
}

function DecisionsHeader({ total, pending, onNew }: DecisionsHeaderProps) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <Scale className="h-3.5 w-3.5" />
        Decisões de plano
        {total > 0 && (
          <span className="ml-1 font-mono text-xs tabular-nums normal-case">
            ({total})
          </span>
        )}
        {pending > 0 && (
          <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium normal-case text-amber-900 dark:bg-amber-900/30 dark:text-amber-200">
            {pending} a decidir
          </span>
        )}
      </h2>
      <Button size="sm" variant="outline" onClick={onNew}>
        <Plus className="mr-1 h-3.5 w-3.5" />
        Nova decisão
      </Button>
    </div>
  );
}

interface StatusFiltersProps {
  value: DecisionStatusFilter;
  onChange: (next: DecisionStatusFilter) => void;
}

function StatusFilters({ value, onChange }: StatusFiltersProps) {
  return (
    <div
      role="tablist"
      aria-label="Filtrar decisões"
      className="flex flex-wrap gap-2"
    >
      {STATUS_FILTER_ORDER.map((option) => {
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
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-transparent text-foreground border-border hover:bg-muted",
            ].join(" ")}
          >
            {decisionStatusFilterLabel(option)}
          </button>
        );
      })}
    </div>
  );
}

function DecisionsEmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/20 px-4 py-8 text-center">
      <Scale className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
      <p className="text-sm font-medium">
        Nenhuma decisão de plano registrada.
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Quando mudar alocação alvo, aporte mensal ou objetivo de IF, registre
        aqui — você terá histórico do porquê.
      </p>
      <Button size="sm" variant="outline" className="mt-4" onClick={onNew}>
        <Plus className="mr-1 h-3.5 w-3.5" />
        Registrar primeira decisão
      </Button>
    </div>
  );
}

function sortDecisions(decisions: ReadonlyArray<Decision>): Decision[] {
  return [...decisions].sort((a, b) => {
    const ra = statusRank(a.status);
    const rb = statusRank(b.status);
    if (ra !== rb) return ra - rb;
    return b.created_at.localeCompare(a.created_at);
  });
}

function statusRank(status: Decision["status"]): number {
  switch (status) {
    case "Pendente":
      return 0;
    case "Decidido":
      return 1;
    case "Executado":
      return 2;
    case "Superseded":
      return 3;
    case "Descartado":
      return 4;
  }
}

function countByStatus(
  decisions: ReadonlyArray<Decision>,
  status: Decision["status"],
): number {
  return decisions.filter((d) => d.status === status).length;
}
