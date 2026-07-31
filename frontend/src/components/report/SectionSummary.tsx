import { cn } from "@/lib/cn";
import type { ReportAnalysisData } from "@/lib/api";
import { resolveSectionSummary } from "./utils/sectionSummarySource";

interface SectionSummaryProps {
  data: ReportAnalysisData;
  sectionId: string;
  className?: string;
}

/**
 * Parágrafo editorial de abertura de seção — render site ÚNICO (ADR-356).
 *
 * A precedência (LLM → E5.N → derivado) vive em `resolveSectionSummary`;
 * aqui só se escolhe o registro visual:
 *
 * - `derived` → mesmo markup dos 5 blocos de fallback que este componente
 *   substituiu (zero delta visual onde nada novo chega).
 * - `e5n` / `llm` → caixa de destaque. Registro foreground sem `font-medium`:
 *   os textos do E5.N são expositivos, não conclusões editoriais.
 *
 * Deve ser filho direto do grid do ReportSection (herda md:col-span-2).
 */
export function SectionSummary({
  data,
  sectionId,
  className,
}: SectionSummaryProps) {
  const resolved = resolveSectionSummary(sectionId, data);
  if (!resolved) return null;

  if (resolved.source === "derived") {
    return (
      <p
        className={cn(
          "md:col-span-2 text-sm text-[var(--surface-muted-foreground)]",
          className,
        )}
      >
        {resolved.text}
      </p>
    );
  }

  return (
    <div
      className={cn(
        "md:col-span-2 rounded-[var(--radius-card)] border-l-4 border-[var(--brand-primary)]",
        "bg-[color-mix(in_srgb,var(--brand-primary)_4%,var(--surface-card))]",
        "px-5 py-4 shadow-[var(--shadow-card)]",
        className,
      )}
    >
      <p className="text-sm leading-relaxed text-[var(--surface-foreground)]">
        {resolved.text}
      </p>
    </div>
  );
}
