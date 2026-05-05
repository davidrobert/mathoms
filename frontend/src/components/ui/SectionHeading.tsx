import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface SectionHeadingProps {
  icon?: LucideIcon;
  label: string;
  count?: number;
  badge?: ReactNode;
  action?: ReactNode;
  level?: 2 | 3;
  className?: string;
}

/**
 * Padrão unificado de H2/H3 para seções em /plano e outros contextos.
 *
 * Visual: [icon 14px] LABEL UPPERCASE  (count) [badge]   [action]
 */
export function SectionHeading({
  icon: Icon,
  label,
  count,
  badge,
  action,
  level = 2,
  className,
}: SectionHeadingProps) {
  const Tag = level === 3 ? "h3" : "h2";
  return (
    <div className={cn("mb-3 flex items-center justify-between", className)}>
      <Tag className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {Icon && <Icon className="h-3.5 w-3.5" />}
        {label}
        {count != null && (
          <span className="ml-1 font-mono text-xs tabular-nums normal-case">
            ({count})
          </span>
        )}
        {badge && <span className="ml-2 normal-case">{badge}</span>}
      </Tag>
      {action && <div>{action}</div>}
    </div>
  );
}
