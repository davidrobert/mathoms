"use client";

// Direção E · Onda 5 · ADR-153 — callout de Suggestion no relatório.
//
// Renderizado **inline** dentro de uma seção (S2/S7/U1...) filtrando
// suggestions pelo `section_id`. Fora da seção, o agregador
// `<SuggestionCalloutSummary/>` mostra a lista de "Próximos passos".
//
// No PDF (Playwright/server-side), os botões de ação não fazem
// sentido — degradamos para nota cinza com ID. Detecção: se
// `workspaceId` é vazio, não renderiza CTA "Promover para ação".

import Link from "next/link";
import { AlertOctagon, AlertTriangle, ArrowRight, Info } from "lucide-react";

import type { Suggestion, SuggestionSeverity } from "@/lib/api";
import { useSuggestions } from "@/hooks/useSuggestions";

const SEVERITY_VARIANTS: Record<
  SuggestionSeverity,
  {
    label: string;
    Icon: typeof Info;
    border: string;
    text: string;
    bg: string;
  }
> = {
  info: {
    label: "Informativo",
    Icon: Info,
    border: "border-l-sky-500",
    text: "text-sky-900 dark:text-sky-100",
    bg: "bg-sky-50/60 dark:bg-sky-900/20",
  },
  warning: {
    label: "Atenção",
    Icon: AlertTriangle,
    border: "border-l-amber-500",
    text: "text-amber-900 dark:text-amber-100",
    bg: "bg-amber-50/60 dark:bg-amber-900/20",
  },
  danger: {
    label: "Ação urgente",
    Icon: AlertOctagon,
    border: "border-l-red-500",
    text: "text-red-900 dark:text-red-100",
    bg: "bg-red-50/60 dark:bg-red-900/20",
  },
};

interface SuggestionCalloutInlineProps {
  /** Filtra `suggestions` por section_id (ex.: "S7"). */
  sectionId: string;
  /** Workspace para o link "Promover para ação". Vazio em PDF (degrada CTA). */
  workspaceId: string;
}

/** Callout inline — busca sugestões pendentes da seção e renderiza
 *  cards compactos com link "Promover para ação". */
export function SuggestionCalloutInline({
  sectionId,
  workspaceId,
}: SuggestionCalloutInlineProps) {
  const { suggestions, loading } = useSuggestions(workspaceId, "Pendente");
  if (loading) return null;
  const items = suggestions.filter((s) => s.section_id === sectionId);
  if (items.length === 0) return null;

  return (
    <div
      className="md:col-span-2 flex flex-col gap-2"
      data-suggestion-callout-section={sectionId}
    >
      {items.map((s) => (
        <SuggestionItem key={s.id} suggestion={s} workspaceId={workspaceId} />
      ))}
    </div>
  );
}

function SuggestionItem({
  suggestion,
  workspaceId,
}: {
  suggestion: Suggestion;
  workspaceId: string;
}) {
  const variant =
    SEVERITY_VARIANTS[suggestion.severity] ?? SEVERITY_VARIANTS.info;
  const Icon = variant.Icon;
  return (
    <div
      role="note"
      aria-label={`Sugestão (${variant.label}): ${suggestion.title}`}
      className={[
        "flex items-start justify-between gap-3 rounded-md border-l-[3px] border border-border px-4 py-3",
        variant.border,
        variant.bg,
      ].join(" ")}
    >
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${variant.text}`} />
        <div>
          <p className={`text-xs font-semibold uppercase tracking-wide ${variant.text}`}>
            {variant.label}
          </p>
          <p className="text-sm font-medium leading-snug">{suggestion.title}</p>
          <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
            {suggestion.rationale}
          </p>
        </div>
      </div>
      {workspaceId && (
        <Link
          href={`/acao?tab=inbox#SUG-${suggestion.id}`}
          className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-foreground hover:underline"
        >
          Promover para ação
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      )}
    </div>
  );
}

interface SuggestionCalloutSummaryProps {
  workspaceId: string;
}

/** Agregador "Próximos passos" — lista resumida no fim do relatório. */
export function SuggestionCalloutSummary({
  workspaceId,
}: SuggestionCalloutSummaryProps) {
  const { suggestions, loading } = useSuggestions(workspaceId, "Pendente");
  if (loading || suggestions.length === 0) return null;

  return (
    <section
      id="proximos-passos"
      aria-labelledby="proximos-passos-title"
      className="md:col-span-2 mt-8 rounded-[var(--radius-card)] border border-border bg-[var(--surface-card)] p-6"
    >
      <h2
        id="proximos-passos-title"
        className="font-heading text-lg font-semibold"
      >
        Próximos passos
      </h2>
      <p className="mt-1 text-xs text-muted-foreground">
        {suggestions.length === 1
          ? "1 sugestão acionável a partir deste relatório"
          : `${suggestions.length} sugestões acionáveis a partir deste relatório`}{" "}
        — revise em{" "}
        <Link href="/acao" className="font-medium underline hover:no-underline">
          /acao
        </Link>{" "}
        para virarem decisões.
      </p>
      <ul className="mt-4 flex flex-col gap-2">
        {suggestions.map((s) => {
          const variant =
            SEVERITY_VARIANTS[s.severity] ?? SEVERITY_VARIANTS.info;
          const Icon = variant.Icon;
          return (
            <li key={s.id} className="flex items-start gap-3">
              <Icon className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${variant.text}`} />
              <div className="flex-1">
                <p className="text-sm font-medium">{s.title}</p>
                <Link
                  href={`#${s.section_id}`}
                  className="text-[11px] text-muted-foreground hover:underline"
                >
                  Ver em contexto · §{s.section_id}
                </Link>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
