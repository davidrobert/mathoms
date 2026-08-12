import { cn } from "@/lib/cn";
import type { CardVariant } from "@/generated/report-layout";
import type { ReactNode } from "react";

interface ReportCardProps {
  variant?: CardVariant;
  size?: "full" | "half";
  title?: string;
  /** Conteúdo renderizado à direita do título (ex: PeriodToggle, badge). */
  headerRight?: ReactNode;
  /** Texto analítico renderizado abaixo do conteúdo do card (padrão chart-conclusion do HTML). */
  conclusion?: string;
  children: ReactNode;
  className?: string;
}

/** F9 · ADR-076 · F1.1 — Card canônico do relatório, com variants do DNA.
 *
 * As classes `.card-variant-*` vêm de `design-tokens/tokens.json` gerado
 * em `frontend/src/styles/tokens.css`. Mudanças de borda/fundo passam por
 * tokens.json — nunca hardcode aqui.
 */
export function ReportCard({
  variant = "feature",
  size = "full",
  title,
  headerRight,
  conclusion,
  children,
  className,
}: ReportCardProps) {
  return (
    <section
      className={cn(
        `card-variant-${variant}`,
        "shadow-[var(--shadow-card)] transition-shadow hover:shadow-[var(--shadow-card-hover)]",
        size === "half" && "md:col-span-1",
        size === "full" && "md:col-span-2",
        className,
      )}
    >
      {/* `flex-wrap` porque `shrink-0` + título longo não cabem lado a lado em
        * 390px: o badge da S8 vazava 121px e o seletor de período da S2, 32px,
        * ambos fora da caixa e sem rolagem para alcançá-los. Quebrar a linha
        * preserva os dois; encolher o badge cortaria o texto dele. */}
      {(title || headerRight) && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          {title && (
            <h3 className="min-w-0 font-display text-lg font-semibold leading-tight">
              {title}
            </h3>
          )}
          {/* `shrink-0` só a partir de 640px: em telefone ele fixava a largura no
            * max-content e anulava o `flex-wrap` de quem vem dentro (os dois
            * badges da S8 somam ~377px numa caixa de 310px). */}
          {headerRight && <div className="min-w-0 sm:shrink-0">{headerRight}</div>}
        </div>
      )}
      {children}
      {conclusion && (
        <div
          data-chart-conclusion
          className="mt-4 rounded-[var(--radius-md)] border-l-[3px] border-[var(--brand-info)] bg-[color-mix(in_srgb,var(--brand-info)_6%,var(--surface-card))] px-3 py-2.5 text-xs leading-relaxed text-[var(--surface-foreground)]"
        >
          {conclusion}
        </div>
      )}
    </section>
  );
}
