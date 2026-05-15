"use client";

import { useMemo, useState } from "react";
import { Plus, Scale } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { SegmentedTabs } from "@/components/ui/SegmentedTabs";
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
  // ADR-214 — code é server-generated; modo create não precisa de defaultCode.
  const handleNew = () => setFormMode({ kind: "create" });
  const handleEdit = (decision: Decision) =>
    setFormMode({ kind: "edit", decision });
  const handleMarkDecided = async (decisionId: string) =>
    markDecided(decisionId, update);

  const pendingCount = countByStatus(decisions, "Pendente");
  const pendingBadge =
    pendingCount > 0 ? (
      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-900 dark:bg-amber-900/30 dark:text-amber-200">
        {pendingCount} a decidir
      </span>
    ) : undefined;

  return (
    <section className="mt-8">
      <SectionHeading
        icon={Scale}
        label="Decisões de plano"
        count={decisions.length > 0 ? decisions.length : undefined}
        badge={pendingBadge}
        action={
          <Button size="sm" variant="outline" onClick={handleNew}>
            <Plus className="mr-1 h-3.5 w-3.5" />
            Nova decisão
          </Button>
        }
      />
      {decisions.length > 0 && (
        <StatusFilters value={filter} onChange={setFilter} />
      )}
      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      <DecisionsBody
        loading={loading}
        decisions={decisions}
        filtered={filtered}
        workspaceId={workspaceId}
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
  workspaceId: string;
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
  workspaceId,
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
            workspaceId={workspaceId}
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



function StatusFilters({ value, onChange }: { value: DecisionStatusFilter; onChange: (next: DecisionStatusFilter) => void }) {
  const options = STATUS_FILTER_ORDER.map((o) => ({ value: o, label: decisionStatusFilterLabel(o) }));
  return (
    <SegmentedTabs
      value={value}
      onChange={onChange}
      options={options}
      ariaLabel="Filtrar decisões"
    />
  );
}

function DecisionsEmptyState({ onNew }: { onNew: () => void }) {
  return (
    <EmptyState
      icon={Scale}
      title="Nenhuma decisão de plano registrada."
      description="Quando mudar alocação alvo, aporte mensal ou objetivo de IF, registre aqui — você terá histórico do porquê."
      layout="inline"
      ctas={[{ label: "Registrar primeira decisão", onClick: onNew, variant: "secondary" }]}
    />
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
