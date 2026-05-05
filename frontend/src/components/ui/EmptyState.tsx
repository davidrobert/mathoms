import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";

interface EmptyStateCTA {
  label: string;
  href?: string;
  onClick?: () => void;
  variant?: "primary" | "secondary";
}

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  layout?: "card" | "inline" | "hero";
  ctas?: EmptyStateCTA[];
  className?: string;
}

/**
 * Padrão unificado de empty state em 3 contextos:
 * - "card": centralizado dentro de Card, padding generoso
 * - "inline": borda dashed, compact, dentro de seção
 * - "hero": centrado em tela cheia ou bloco grande
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  layout = "card",
  ctas,
  className,
}: EmptyStateProps) {
  if (layout === "inline") {
    return (
      <div
        className={cn(
          "rounded-lg border border-dashed border-border bg-muted/20 px-4 py-6 text-center",
          className,
        )}
      >
        {Icon && (
          <Icon className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
        )}
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        {ctas && ctas.length > 0 && (
          <div className="mt-3 flex flex-col items-center gap-2 sm:flex-row sm:justify-center">
            {ctas.map((cta, i) => (
              <CTAButton key={i} cta={cta} size="sm" />
            ))}
          </div>
        )}
      </div>
    );
  }

  if (layout === "hero") {
    return (
      <div className={cn("mx-auto max-w-lg py-8 text-center", className)}>
        {Icon && (
          <Icon className="mx-auto mb-4 h-10 w-10 text-muted-foreground" />
        )}
        <h2 className="font-heading text-lg font-semibold">{title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>
        {ctas && ctas.length > 0 && (
          <div className="mt-6 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            {ctas.map((cta, i) => (
              <CTAButton key={i} cta={cta} size="default" />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={cn("py-12 text-center", className)}>
      {Icon && (
        <Icon className="mx-auto mb-4 h-10 w-10 text-muted-foreground/50" />
      )}
      <h2 className="font-heading text-lg font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      {ctas && ctas.length > 0 && (
        <div className="mt-6 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          {ctas.map((cta, i) => (
            <CTAButton key={i} cta={cta} size="sm" />
          ))}
        </div>
      )}
    </div>
  );
}

function CTAButton({
  cta,
  size,
}: {
  cta: EmptyStateCTA;
  size: "sm" | "default";
}) {
  const variant = cta.variant === "secondary" ? "outline" : "default";
  if (cta.href) {
    return (
      <Button
        variant={variant}
        size={size}
        nativeButton={false}
        render={<Link href={cta.href} />}
      >
        {cta.label}
      </Button>
    );
  }
  return (
    <Button variant={variant} size={size} onClick={cta.onClick}>
      {cta.label}
    </Button>
  );
}
