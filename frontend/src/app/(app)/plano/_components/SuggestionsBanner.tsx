"use client";

import Link from "next/link";
import { ArrowRight, Lightbulb } from "lucide-react";

import { Button } from "@/components/ui/button";

import { useSuggestionsCount } from "./useSuggestionsCount";

interface SuggestionsBannerProps {
  workspaceId: string | undefined;
}

/** Direção E · Onda 4 — banner de sugestões pendentes em /plano.
 *
 * Só renderiza quando há sugestões pendentes (count > 0). Severidade
 * cresce com volume: ≤3 = info, ≥4 = warning. Click leva ao inbox
 * em /acao (rota ativa desde Onda 6, ADR-152).
 *
 * Fonte de dados é stub até Onda 5 (Suggestion full-stack). Componente
 * está pronto para "ligar" no backend trocando só o hook.
 */
export function SuggestionsBanner({ workspaceId }: SuggestionsBannerProps) {
  const { count, loading } = useSuggestionsCount(workspaceId);
  if (loading || count === 0) return null;
  const tone = count >= 4 ? "warning" : "info";
  return (
    <div
      role="status"
      aria-live="polite"
      className={[
        "mb-6 flex items-start justify-between gap-3 rounded-lg border px-4 py-3",
        tone === "warning"
          ? "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-100"
          : "border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900/40 dark:bg-sky-900/20 dark:text-sky-100",
      ].join(" ")}
    >
      <div className="flex items-start gap-3">
        <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="text-sm font-medium">
            {count === 1
              ? "1 sugestão pendente do último relatório"
              : `${count} sugestões pendentes do último relatório`}
          </p>
          <p className="mt-0.5 text-xs opacity-80">
            Revise, aceite ou descarte em /acao para virarem decisões e tarefas.
          </p>
        </div>
      </div>
      <Button
        size="sm"
        variant="outline"
        nativeButton={false}
        render={<Link href="/acao" />}
        className="shrink-0"
      >
        Revisar
        <ArrowRight className="ml-1 h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
