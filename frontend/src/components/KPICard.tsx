import { cn } from "@/lib/utils";
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
}

export function KPICard({ label, value, delta, icon: Icon, loading, className }: KPICardProps) {
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

  return (
    <Card className={cn("p-0", className)}>
      <CardContent>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{label}</span>
          {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
        </div>
        <p className="mt-1 text-2xl font-semibold tracking-tight font-mono tabular-nums">
          {value}
        </p>
        {delta && (
          <Delta
            value={delta.value}
            percent={delta.percent}
            invert={delta.invert}
            className="mt-1 text-xs"
          />
        )}
      </CardContent>
    </Card>
  );
}
