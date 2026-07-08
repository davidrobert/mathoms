"use client";

import { FileQuestion, FileWarning, ScanLine } from "lucide-react";

import { StatusBadge } from "@/components/StatusBadge";
import { cn } from "@/lib/cn";
import {
  NATURE_SPEC,
  natureForCode,
  natureLabelForCode,
  type ReviewNature,
} from "@/lib/review-nature";

/** Ícone por natureza — distinção nunca é só cor (WCAG): ícone + rótulo + forma. */
const NATURE_ICON: Record<ReviewNature, typeof ScanLine> = {
  nossa_leitura: ScanLine,
  seu_documento: FileWarning,
  documento_faltando: FileQuestion,
};

/** Selo de natureza do card de review (A32.l6 PR2, decisão Q4: selo na
 * review principal, sem aba separada). Code sem natureza → sem selo. */
export function ReviewNatureBadge({ code }: { code: string }) {
  const nature = natureForCode(code);
  const label = natureLabelForCode(code);
  if (!nature || !label) return null;
  const spec = NATURE_SPEC[nature];
  const Icon = NATURE_ICON[nature];
  return (
    <StatusBadge
      variant={spec.variant}
      className={cn("shrink-0", spec.dashed && "border-dashed")}
    >
      <Icon aria-hidden className="h-3 w-3" />
      {label}
    </StatusBadge>
  );
}
