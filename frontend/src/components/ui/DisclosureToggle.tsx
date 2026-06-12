"use client";

// ADR-290 F3 — disclosure pattern compartilhado (inbox /acao + relatório).
// a11y: aria-expanded + aria-controls; o conteúdo controlado deve usar
// `hidden` real quando fechado (fora do tab order), não display via classe.

import { ChevronDown, ChevronRight } from "lucide-react";

interface DisclosureToggleProps {
  /** id do container controlado (aria-controls). */
  controlsId: string;
  expanded: boolean;
  onToggle: () => void;
  /** Ex.: "46 informativas" / "Mais 3 sugestões acionáveis". */
  label: string;
}

export function DisclosureToggle({
  controlsId,
  expanded,
  onToggle,
  label,
}: DisclosureToggleProps) {
  const Icon = expanded ? ChevronDown : ChevronRight;
  return (
    <button
      type="button"
      aria-expanded={expanded}
      aria-controls={controlsId}
      onClick={onToggle}
      className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      {label} — {expanded ? "ocultar" : "mostrar"}
    </button>
  );
}
