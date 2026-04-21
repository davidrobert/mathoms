"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/Spinner";

type ReviewFilter = "all" | "uncertain";

function UncertainFilter({
  count,
  active,
  onToggle,
}: {
  count: number;
  active: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <span className="text-sm text-foreground/85">
        <span className="font-medium text-warning">{count}</span>{" "}
        {count === 1
          ? "documento precisa de revisão da classificação"
          : "documentos precisam de revisão da classificação"}
      </span>
      <Button
        type="button"
        variant={active ? "secondary" : "outline"}
        size="sm"
        onClick={onToggle}
        aria-pressed={active}
      >
        {active ? "Mostrar todos" : "Mostrar só estes"}
      </Button>
    </>
  );
}

function ReclassifyButton({
  reclassifying,
  onClick,
}: {
  reclassifying: boolean;
  onClick: () => void;
}) {
  return (
    <Button
      variant="outline"
      size="sm"
      className="shrink-0 self-start sm:self-auto"
      onClick={onClick}
      disabled={reclassifying}
      title="Re-executa o classificador de conteúdo em todos os documentos (útil após atualizações de regras ou upload com extensão errada)"
    >
      {reclassifying ? (
        <span className="inline-flex items-center gap-2">
          <Spinner size="sm" />
          Reclassificando...
        </span>
      ) : (
        <span className="inline-flex items-center gap-2">
          <RefreshCw className="h-3.5 w-3.5" />
          Reclassificar documentos
        </span>
      )}
    </Button>
  );
}

export function FilterReclassifyBar({
  totalDocs,
  uncertainCount,
  reviewFilter,
  onToggleFilter,
  reclassifying,
  onReclassify,
}: {
  totalDocs: number;
  uncertainCount: number;
  reviewFilter: ReviewFilter;
  onToggleFilter: () => void;
  reclassifying: boolean;
  onReclassify: () => void;
}) {
  return (
    <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-h-9 flex-wrap items-center gap-2">
        {uncertainCount > 0 ? (
          <UncertainFilter
            count={uncertainCount}
            active={reviewFilter === "uncertain"}
            onToggle={onToggleFilter}
          />
        ) : (
          <span className="text-sm text-muted-foreground">
            {totalDocs} {totalDocs === 1 ? "documento" : "documentos"} na lista
          </span>
        )}
      </div>
      <ReclassifyButton reclassifying={reclassifying} onClick={onReclassify} />
    </div>
  );
}
