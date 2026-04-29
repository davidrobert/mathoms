"use client";

import { AlertTriangle, Clock, RefreshCw } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { formatFreshness, freshnessVariant } from "./dashboardHelpers";

export function HeaderActions({
  dataFreshness,
  loading,
  onRefresh,
}: {
  dataFreshness: string | null | undefined;
  loading: boolean;
  onRefresh: () => void;
}) {
  const variant = freshnessVariant(dataFreshness ?? null);
  return (
    <div className="flex items-center gap-3">
      {dataFreshness ? (
        <StatusBadge variant={variant}>
          <Clock className="mr-1 h-3 w-3" />
          {formatFreshness(dataFreshness)}
        </StatusBadge>
      ) : !loading ? (
        <StatusBadge variant="warning">
          <AlertTriangle className="mr-1 h-3 w-3" />
          Sem dados
        </StatusBadge>
      ) : null}
      <button
        onClick={onRefresh}
        disabled={loading}
        className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-50"
        aria-label="Atualizar dashboard"
      >
        <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
      </button>
    </div>
  );
}
