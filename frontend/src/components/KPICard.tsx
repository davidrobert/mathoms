import { cn } from "@/lib/cn";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Delta } from "@/components/Delta";
import type { LucideIcon } from "lucide-react";

interface KPICardProps {
  label: string;
  value: string;
  delta?: { value: number; percent?: number; invert?: boolean };
  icon?: LucideIcon;
  loading?: boolean;
  className?: string;
  /** F11.2b — hierarquia: primeiro KPI forte; demais visualmente subordinados. */
  emphasis?: "primary" | "secondary";
}

export function KPICard({
  label,
  value,
  delta,
  icon: Icon,
  loading,
  className,
  emphasis = "primary",
}: KPICardProps) {
  if (loading) {
    return (
      <Card className={cn("p-0", className)}>
        <CardContent className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-7 w-32" />
          <Skeleton className="h-4 w-20" />
        </CardContent>
      </Card>
    );
  }

  const labelCls =
    emphasis === "secondary" ? "text-xs text-muted-foreground" : "text-sm text-muted-foreground";
  const valueCls =
    emphasis === "secondary"
      ? "mt-1 text-lg font-medium tracking-tight font-mono tabular-nums text-foreground/95"
      : "mt-1 text-2xl font-semibold tracking-tight font-mono tabular-nums";

  return (
    <Card className={cn("p-0", className)}>
      <CardContent>
        <div className="flex items-center justify-between">
          <span className={labelCls}>{label}</span>
          {Icon && (
            <Icon
              className={cn(
                "h-4 w-4 text-muted-foreground",
                emphasis === "secondary" && "h-3.5 w-3.5 opacity-80",
              )}
            />
          )}
        </div>
        <p className={valueCls}>{value}</p>
        {delta && (
          <Delta
            value={delta.value}
            percent={delta.percent}
            invert={delta.invert}
            className={cn(
              "mt-1",
              emphasis === "secondary" ? "text-[11px] font-normal opacity-90" : "text-xs",
            )}
          />
        )}
      </CardContent>
    </Card>
  );
}
