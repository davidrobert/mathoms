import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
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
}

export function StatusBadge({ variant, children, className }: StatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn(variantStyles[variant], className)}
    >
      {children}
    </Badge>
  );
}
