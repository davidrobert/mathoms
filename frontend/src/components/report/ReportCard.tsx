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
      {/* Tudo aqui é `max-sm:` — abaixo de 640px o `shrink-0` fixava o
        * `headerRight` no max-content e anulava o `flex-wrap` de dentro dele (os
        * dois badges da S8 somam ~377px numa caixa de 310px; o seletor de
        * período da S2 vazava 32px), e sem rolagem horizontal o conteúdo ficava
        * inalcançável.
        *
        * O escopo estreito não é preciosismo: aplicar as mesmas regras em toda
        * largura é o candidato a explicar a divergência de pixel do S2 medida em
        * CI (verificação re-aberta em A40.l45 §Regressão 2 — este experimento
        * mede se o efeito é real ou é a flakiness já documentada na A40.l53).
        * Acima de 640px o header tem de continuar byte-idêntico ao que era. */}
      {(title || headerRight) && (
        <div className="mb-4 flex items-center justify-between gap-2 max-sm:flex-wrap">
          {title && (
            <h3 className="font-display text-lg font-semibold leading-tight max-sm:min-w-0">
              {title}
            </h3>
          )}
          {headerRight && (
            <div className="shrink-0 max-sm:min-w-0 max-sm:shrink">{headerRight}</div>
          )}
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
