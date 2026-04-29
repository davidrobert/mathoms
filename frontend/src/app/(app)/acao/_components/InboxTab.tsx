"use client";

import Link from "next/link";
import { Lightbulb, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface InboxTabProps {
  workspaceId: string;
}

/** Direção E · Onda 6 — Inbox de sugestões pendentes em /acao.
 *
 * Conteúdo real (lista de Suggestions com Aceitar/Modificar/Descartar)
 * chega na Onda 5 (aggregate Suggestion full-stack). Por enquanto:
 * empty state ensinante explica o que vai aparecer aqui.
 *
 * Link "Ver sugestões de tarefas (LLM)" mantém acesso à fila legada
 * (E5.N TaskSuggestion) que já existia em /plano-de-acao/sugestoes —
 * é coisa diferente da Suggestion futura, mas compartilha a metáfora.
 */
export function InboxTab({ workspaceId }: InboxTabProps) {
  void workspaceId;
  return (
    <Card>
      <CardContent className="py-12">
        <div className="mx-auto max-w-md text-center">
          <Lightbulb className="mx-auto mb-4 h-10 w-10 text-muted-foreground/50" />
          <h2 className="font-heading text-lg font-semibold">
            Sem sugestões pendentes
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Após cada relatório, sugestões acionáveis (mudanças de
            alocação, ajustes de aporte, atenção a fluxo) aparecerão aqui
            para você aceitar, modificar ou descartar — viram decisões e
            tarefas ligadas à origem no relatório.
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-6"
            nativeButton={false}
            render={<Link href="/acao/sugestoes" />}
          >
            <Sparkles className="mr-1.5 h-3.5 w-3.5" />
            Ver sugestões de tarefas (LLM)
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
