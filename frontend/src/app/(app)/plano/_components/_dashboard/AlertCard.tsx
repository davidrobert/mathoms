"use client";

import type { DashboardAlert } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

import { alertTone } from "./alertTone";

export function AlertCard({ alert }: { alert: DashboardAlert }) {
  const tone = alertTone(alert.severity);
  const Icon = tone.icon;

  return (
    <Card data-tone={tone.name} className={tone.cardClassName}>
      <CardContent className="flex items-start gap-3">
        <Icon
          className={`mt-0.5 h-5 w-5 shrink-0 ${tone.cardIconClassName}`}
          aria-hidden="true"
        />
        <div>
          <p className="font-medium">{alert.title}</p>
          <p className="mt-0.5 text-sm text-muted-foreground">{alert.message}</p>
        </div>
      </CardContent>
    </Card>
  );
}
