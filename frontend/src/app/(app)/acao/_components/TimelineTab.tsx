"use client";

import { CalendarClock } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

interface TimelineTabProps {
  workspaceId: string;
}

/** Direção E · Onda 6 — Timeline de próximos 15 dias em /acao.
 *
 * Conteúdo real (consume `dashboard.proximos_15d` via report data)
 * será adicionado quando o pipeline E5 expor um endpoint dedicado
 * fora do contexto de relatório. Por enquanto, empty state.
 *
 * Originalmente vinha do Tático T5 (removido em ADR-151) que lia
 * direto do snapshot. Adapter `timelineAdapter.ts` continua disponível
 * para reuso quando a fonte de dados for definida.
 */
export function TimelineTab({ workspaceId }: TimelineTabProps) {
  void workspaceId;
  return (
    <Card>
      <CardContent className="py-12">
        <div className="mx-auto max-w-md text-center">
          <CalendarClock className="mx-auto mb-4 h-10 w-10 text-muted-foreground/50" />
          <h2 className="font-heading text-lg font-semibold">
            Timeline em construção
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Linha do tempo dos próximos 15 dias (aportes vencendo,
            tarefas urgentes, eventos fiscais) virá aqui assim que
            uma fonte estável estiver definida fora do contexto do
            relatório.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
