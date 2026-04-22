"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Pagination({
  total,
  page,
  totalPages,
  onGoPage,
}: {
  total: number;
  page: number;
  totalPages: number;
  onGoPage: (p: number) => void;
}) {
  return (
    <div className="mt-4 flex items-center justify-between">
      <p className="text-sm tabular-nums text-muted-foreground">
        {total.toLocaleString("pt-BR")} transação(ões) — página {page} de {totalPages}
      </p>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onGoPage(page - 1)}>
          <ChevronLeft className="mr-1 h-3.5 w-3.5" />
          Anterior
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onGoPage(page + 1)}
        >
          Próxima
          <ChevronRight className="ml-1 h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
