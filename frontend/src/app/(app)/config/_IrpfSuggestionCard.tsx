"use client";

import { Plus, X, AlertTriangle } from "lucide-react";

import type { IrpfSuggestion } from "@/lib/api";
import { bankLabel } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface Props {
  suggestion: IrpfSuggestion;
  collisionAccountLabel?: string;
  onAccept: (suggestion: IrpfSuggestion) => void;
  onDismiss: (suggestion: IrpfSuggestion) => void;
  isBusy?: boolean;
}

export function IrpfSuggestionCard({
  suggestion,
  collisionAccountLabel,
  onAccept,
  onDismiss,
  isBusy = false,
}: Props) {
  const isPartial = suggestion.match_kind === "partial_collision";
  const inst = bankLabel(suggestion.institution_code);
  const acceptLabel = isPartial ? "Comparar e adicionar" : "Adicionar";
  return (
    <div
      role="group"
      aria-label={`Sugestão IRPF ${suggestion.irpf_year} — ${inst}`}
      tabIndex={0}
      className="rounded-lg border border-border/60 bg-muted/40 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
      data-testid={`irpf-suggestion-${suggestion.institution_code}-${suggestion.account_number_norm ?? "nonum"}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge
          variant="secondary"
          className="bg-info-financial/15 text-info-financial"
          aria-label={`Sugestão do IRPF ${suggestion.irpf_year}`}
        >
          IRPF {suggestion.irpf_year}
        </Badge>
        <span className="font-medium">{inst}</span>
        <span className="text-muted-foreground">{suggestion.account_type}</span>
        {suggestion.agency && (
          <span className="text-muted-foreground">Ag: {suggestion.agency}</span>
        )}
        {suggestion.account_number_raw && (
          <span className="text-muted-foreground">
            Cc: {suggestion.account_number_raw}
          </span>
        )}
        {suggestion.cpf_titular_masked && (
          <span className="text-xs text-muted-foreground">
            · CPF {suggestion.cpf_titular_masked}
          </span>
        )}
      </div>
      {isPartial && collisionAccountLabel && (
        <p className="mt-1 flex items-center gap-1 text-xs text-amber-700 dark:text-amber-400">
          <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
          Possível duplicata de {collisionAccountLabel} — confirme antes de adicionar.
        </p>
      )}
      <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
        <Button
          size="sm"
          variant={isPartial ? "outline" : "secondary"}
          onClick={() => onAccept(suggestion)}
          disabled={isBusy}
          className="w-full sm:w-auto"
        >
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          {acceptLabel}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onDismiss(suggestion)}
          disabled={isBusy}
          className="w-full text-muted-foreground sm:w-auto"
          aria-label={`Descartar sugestão ${inst} ${suggestion.account_number_raw ?? ""}`}
        >
          <X className="mr-1.5 h-3.5 w-3.5" />
          Descartar
        </Button>
      </div>
    </div>
  );
}
