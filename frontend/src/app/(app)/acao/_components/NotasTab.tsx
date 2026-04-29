"use client";

import { StickyNote } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

interface NotasTabProps {
  workspaceId: string;
}

/** Direção E · Onda 6 — Notas livres do workspace em /acao.
 *
 * Conteúdo real depende da nova tabela `workspace_notes` (Onda 1 da
 * Direção E) que substituirá `report_notes` (ADR-123, parcialmente
 * superseded por ADR-151). Por enquanto, empty state.
 */
export function NotasTab({ workspaceId }: NotasTabProps) {
  void workspaceId;
  return (
    <Card>
      <CardContent className="py-12">
        <div className="mx-auto max-w-md text-center">
          <StickyNote className="mx-auto mb-4 h-10 w-10 text-muted-foreground/50" />
          <h2 className="font-heading text-lg font-semibold">
            Notas em construção
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Notas livres por workspace (decisões em rascunho,
            observações da família, contexto que não cabe em decisão
            ou tarefa) virão aqui após a migração de
            <code className="mx-1 rounded bg-muted px-1.5 py-0.5 text-xs">
              report_notes
            </code>
            para
            <code className="ml-1 rounded bg-muted px-1.5 py-0.5 text-xs">
              workspace_notes
            </code>
            .
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
