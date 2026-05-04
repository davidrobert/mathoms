"use client";

import { useState } from "react";
import { toast } from "sonner";
import { ArrowRight, Pencil, Replace } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { MonetaryValue } from "@/components/report/MonetaryValue";
import { ApiError, type Decision, type DecisionStatus } from "@/lib/api";

import { DecisionStatusBadge } from "./DecisionStatusBadge";
import { findSupersededBy, formatDecisionDate } from "./decisionsCopy";

interface DecisionCardProps {
  decision: Decision;
  allDecisions: ReadonlyArray<Decision>;
  onEdit: (decision: Decision) => void;
  onSupersede: (decision: Decision) => void;
  onMarkDecided: (decisionId: string) => Promise<void>;
  onExecute: (decisionId: string) => Promise<void>;
}

export function DecisionCard({
  decision,
  allDecisions,
  onEdit,
  onSupersede,
  onMarkDecided,
  onExecute,
}: DecisionCardProps) {
  return (
    <Card className="transition-colors hover:border-border">
      <CardContent className="flex flex-col gap-3 py-4">
        <DecisionCardHeader decision={decision} />
        <p className="text-sm font-medium leading-snug">{decision.title}</p>
        {decision.rationale && (
          <p className="text-xs text-muted-foreground line-clamp-2">
            {decision.rationale}
          </p>
        )}
        <DecisionDates decision={decision} />
        <DecisionRelations decision={decision} allDecisions={allDecisions} />
        <DecisionActions
          decision={decision}
          onEdit={onEdit}
          onSupersede={onSupersede}
          onMarkDecided={onMarkDecided}
          onExecute={onExecute}
        />
      </CardContent>
    </Card>
  );
}

function DecisionCardHeader({ decision }: { decision: Decision }) {
  const amount =
    decision.amount_brl !== null ? Number(decision.amount_brl) : null;
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-muted-foreground">
          {decision.code}
        </span>
        <DecisionStatusBadge status={decision.status} />
      </div>
      {amount !== null && (
        <p className="text-sm font-medium">
          <MonetaryValue value={amount} />
        </p>
      )}
    </div>
  );
}

function DecisionDates({ decision }: { decision: Decision }) {
  const decided = formatDecisionDate(decision.decided_at);
  const executed = formatDecisionDate(decision.executed_at);
  return (
    <p className="text-[11px] text-muted-foreground">
      {decision.decided_at && <>Decidida em {decided}</>}
      {decision.decided_at && decision.executed_at && <> · </>}
      {decision.executed_at && <>Aplicada em {executed}</>}
      {!decision.decided_at && !decision.executed_at && (
        <>Registrada em {formatDecisionDate(decision.created_at)}</>
      )}
    </p>
  );
}

interface DecisionRelationsProps {
  decision: Decision;
  allDecisions: ReadonlyArray<Decision>;
}

function DecisionRelations({ decision, allDecisions }: DecisionRelationsProps) {
  const successor =
    decision.status === "Superseded"
      ? findSupersededBy(allDecisions, decision.id)
      : null;
  const predecessor = decision.supersedes_id
    ? allDecisions.find((d) => d.id === decision.supersedes_id) ?? null
    : null;

  if (!successor && !predecessor) return null;

  return (
    <div className="flex flex-col gap-1 text-[11px]">
      {predecessor && (
        <p className="text-muted-foreground">
          Substitui{" "}
          <span className="font-mono">{predecessor.code}</span> —{" "}
          <span className="text-foreground">{predecessor.title}</span>
        </p>
      )}
      {successor && (
        <p className="text-muted-foreground">
          Substituída por{" "}
          <span className="font-mono">{successor.code}</span> —{" "}
          <span className="text-foreground">{successor.title}</span>
        </p>
      )}
    </div>
  );
}

interface DecisionActionsProps {
  decision: Decision;
  onEdit: (decision: Decision) => void;
  onSupersede: (decision: Decision) => void;
  onMarkDecided: (decisionId: string) => Promise<void>;
  onExecute: (decisionId: string) => Promise<void>;
}

type ActionKind = "decide" | "execute";

function useAsyncAction() {
  const [busy, setBusy] = useState<ActionKind | null>(null);
  const run = (kind: ActionKind, fn: () => Promise<void>) => {
    setBusy(kind);
    fn()
      .then(() => toast.success(SUCCESS_LABEL[kind]))
      .catch((err) => {
        const msg = err instanceof ApiError ? err.detail : "Erro";
        toast.error(msg);
      })
      .finally(() => setBusy(null));
  };
  return { busy, run };
}

const SUCCESS_LABEL: Record<ActionKind, string> = {
  decide: "Decisão marcada em vigor",
  execute: "Decisão aplicada",
};

function DecisionActions(props: DecisionActionsProps) {
  const { busy, run } = useAsyncAction();
  return (
    <div className="mt-1 flex flex-wrap items-center gap-2">
      <PrimaryActions {...props} busy={busy} run={run} />
      <SecondaryActions {...props} />
    </div>
  );
}

function canEdit(status: DecisionStatus): boolean {
  return status === "Pendente" || status === "Decidido";
}

interface PrimaryActionsProps extends DecisionActionsProps {
  busy: ActionKind | null;
  run: (kind: ActionKind, fn: () => Promise<void>) => void;
}

function PrimaryActions({
  decision,
  onMarkDecided,
  onExecute,
  busy,
  run,
}: PrimaryActionsProps) {
  if (decision.status === "Pendente") {
    return (
      <PrimaryActionButton
        label={busy === "decide" ? "Marcando…" : "Marcar em vigor"}
        disabled={busy !== null}
        onClick={() => run("decide", () => onMarkDecided(decision.id))}
      />
    );
  }
  if (decision.status === "Decidido") {
    return (
      <PrimaryActionButton
        label={busy === "execute" ? "Aplicando…" : "Marcar aplicada"}
        disabled={busy !== null}
        onClick={() => run("execute", () => onExecute(decision.id))}
      />
    );
  }
  return null;
}

function SecondaryActions({ decision, onEdit, onSupersede }: DecisionActionsProps) {
  return (
    <>
      {canEdit(decision.status) && (
        <Button size="sm" variant="ghost" onClick={() => onEdit(decision)}>
          <Pencil className="mr-1 h-3.5 w-3.5" />
          Editar
        </Button>
      )}
      {decision.status === "Decidido" && (
        <Button size="sm" variant="ghost" onClick={() => onSupersede(decision)}>
          <Replace className="mr-1 h-3.5 w-3.5" />
          Substituir
        </Button>
      )}
    </>
  );
}

interface PrimaryActionButtonProps {
  label: string;
  disabled: boolean;
  onClick: () => void;
}

function PrimaryActionButton({ label, disabled, onClick }: PrimaryActionButtonProps) {
  return (
    <Button size="sm" variant="default" disabled={disabled} onClick={onClick}>
      {label}
      <ArrowRight className="ml-1 h-3 w-3" />
    </Button>
  );
}
