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

/** Onda 10 #4 — severidades canalizadas pelos tokens semânticos do
 * design-system (`tokens.css` §--semantic-*). Mapeamento:
 *
 * - `info`    → `--semantic-info-financial` (azul informativo)
 * - `warning` → `--semantic-alert`           (laranja de atenção)
 * - `danger`  → `--semantic-loss`            (vermelho de perda/risco)
 *
 * Fonte do bg: `color-mix(in oklab, <tone> 8-10%, transparent)` —
 * mesma técnica adotada por `<EstrategiaAporteCard/>`,
 * `<ReportShell/>` (§warn) e demais cards do relatório. Dark mode
 * derivado automaticamente via `tokens.css` (não precisa de
 * `dark:` aliases).
 */
const SEVERITY_VARIANTS: Record<
  SuggestionSeverity,
  {
    label: string;
    Icon: typeof Info;
    /** CSS var do tom — usado em border-left, text-color e mix de bg. */
    tokenVar: string;
    /** Fallback de bg-mix percentual (warn precisa um pouco mais que info/danger). */
    bgMixPct: number;
  }
> = {
  info: {
    label: "Informativo",
    Icon: Info,
    tokenVar: "var(--semantic-info-financial)",
    bgMixPct: 8,
  },
  warning: {
    label: "Atenção",
    Icon: AlertTriangle,
    tokenVar: "var(--semantic-alert)",
    bgMixPct: 10,
  },
  danger: {
    label: "Ação urgente",
    Icon: AlertOctagon,
    tokenVar: "var(--semantic-loss)",
    bgMixPct: 10,
  },
};

function severityStyle(tokenVar: string, bgMixPct: number) {
  return {
    borderLeftColor: tokenVar,
    color: tokenVar,
    backgroundColor: `color-mix(in oklab, ${tokenVar} ${bgMixPct}%, transparent)`,
  } as const;
}

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
  const tone = severityStyle(variant.tokenVar, variant.bgMixPct);
  return (
    <div
      role="note"
      aria-label={`Sugestão (${variant.label}): ${suggestion.title}`}
      className="flex items-start justify-between gap-3 rounded-md border border-border border-l-[3px] px-4 py-3"
      style={{
        borderLeftColor: tone.borderLeftColor,
        backgroundColor: tone.backgroundColor,
      }}
    >
      <div className="flex items-start gap-3">
        <Icon
          className="mt-0.5 h-4 w-4 shrink-0"
          style={{ color: tone.color }}
        />
        <div>
          <p
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: tone.color }}
          >
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
              <Icon
                className="mt-0.5 h-3.5 w-3.5 shrink-0"
                style={{ color: variant.tokenVar }}
              />
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
