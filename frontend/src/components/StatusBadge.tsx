import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import type { StatusVariant } from "@/lib/format";

const variantStyles: Record<StatusVariant, string> = {
  success:  "bg-gain/10 text-gain border-gain/20",
  warning:  "bg-alert/10 text-alert border-alert/20",
  error:    "bg-loss/10 text-loss border-loss/20",
  info:     "bg-info-financial/10 text-info-financial border-info-financial/20",
  neutral:  "bg-secondary text-secondary-foreground border-border",
  premium:  "bg-primary/10 text-primary border-primary/20",
  muted:    "bg-muted text-muted-foreground border-border",
};

interface StatusBadgeProps {
  variant: StatusVariant;
  children: React.ReactNode;
  className?: string;
  /** Distingue status que compartilham variante (ex.: `warning` cobre
   *  "Concluído com ressalva" e "Aguardando revisão"). Decorativo: o texto do
   *  badge já carrega o significado, então marque `aria-hidden` no ícone. */
  icon?: React.ReactNode;
}

export function StatusBadge({ variant, children, className, icon }: StatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn(variantStyles[variant], icon && "gap-1", className)}
    >
      {icon}
      {children}
    </Badge>
  );
}
