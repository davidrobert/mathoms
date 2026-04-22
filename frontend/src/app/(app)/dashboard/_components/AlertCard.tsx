"use client";

import { AlertCircle, AlertTriangle } from "lucide-react";
import type { DashboardAlert } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

export function AlertCard({ alert }: { alert: DashboardAlert }) {
  const isCritical = alert.severity === "critical";
  const Icon = isCritical ? AlertCircle : AlertTriangle;
  const borderColor = isCritical ? "border-l-red-500" : "border-l-amber-500";
  const iconColor = isCritical ? "text-red-500" : "text-amber-500";

  return (
    <Card className={`border-l-4 ${borderColor}`}>
      <CardContent className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${iconColor}`} />
        <div>
          <p className="font-medium">{alert.title}</p>
          <p className="mt-0.5 text-sm text-muted-foreground">{alert.message}</p>
        </div>
      </CardContent>
    </Card>
  );
}
