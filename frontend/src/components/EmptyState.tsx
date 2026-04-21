import { cn } from "@/lib/cn";
import { FileText, BarChart3, Inbox, AlertCircle, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

const variantIcons: Record<string, LucideIcon> = {
  "no-documents": FileText,
  "no-reports": BarChart3,
  "no-data": Inbox,
  "error": AlertCircle,
};

interface EmptyStateProps {
  variant?: "no-documents" | "no-reports" | "no-data" | "error";
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
  className?: string;
}

export function EmptyState({
  variant = "no-data",
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  const Icon = icon ?? variantIcons[variant] ?? Inbox;

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-center",
        className
      )}
    >
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
        <Icon className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="text-sm font-medium text-foreground">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {action && (
        action.href ? (
          <Button variant="link" className="mt-4" nativeButton={false} render={<a href={action.href} />}>
            {action.label}
          </Button>
        ) : (
          <Button variant="link" className="mt-4" onClick={action.onClick}>
            {action.label}
          </Button>
        )
      )}
    </div>
  );
}
