"use client";

import Link from "next/link";
import { ArrowRight, Lightbulb } from "lucide-react";

import { Button } from "@/components/ui/button";
import { type SuggestionSeverity } from "@/lib/api";

import { useSuggestionsSummary } from "./useSuggestionsSummary";

interface SuggestionsBannerProps {
  workspaceId: string | undefined;
}

/** Direção E · Onda 4 + ADR-161 (Onda 8 #5) — banner de sugestões
 * pendentes em /plano.
 *
 * Tom segue `max_severity` da resposta `/suggestions/summary`:
 * - `danger` → vermelho ("ações urgentes")
 * - `warning` → amarelo
 * - `info` → azul
 *
 * Antes de Onda 8, o tom escalava por volume (count >= 4 = warning),
 * o que produzia banner azul calmo mesmo com 1 sugestão `danger`.
 * Agora reflete severidade real.
 */
export function SuggestionsBanner({ workspaceId }: SuggestionsBannerProps) {
  const { count, maxSeverity, loading } = useSuggestionsSummary(workspaceId);
  if (loading || count === 0 || maxSeverity === null) return null;
  const tone = maxSeverity;
  return (
    <div
      role="status"
      aria-live="polite"
      className={[
        "mb-6 flex items-start justify-between gap-3 rounded-lg border px-4 py-3",
        TONE_CLASSES[tone],
      ].join(" ")}
    >
      <div className="flex items-start gap-3">
        <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="text-sm font-medium">{primaryText(count, tone)}</p>
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

const TONE_CLASSES: Record<SuggestionSeverity, string> = {
  danger:
    "border-red-200 bg-red-50 text-red-900 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-100",
  warning:
    "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-100",
  info: "border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900/40 dark:bg-sky-900/20 dark:text-sky-100",
};

function primaryText(count: number, tone: SuggestionSeverity): string {
  if (tone === "danger") {
    return count === 1
      ? "1 sugestão crítica pendente"
      : `${count} sugestões pendentes — pelo menos 1 crítica`;
  }
  if (tone === "warning") {
    return count === 1
      ? "1 sugestão de atenção pendente"
      : `${count} sugestões pendentes — atenção recomendada`;
  }
  return count === 1
    ? "1 sugestão pendente do último relatório"
    : `${count} sugestões pendentes do último relatório`;
}
