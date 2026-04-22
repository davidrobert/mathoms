"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardChart } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { normalizeBarData } from "./dashboardHelpers";

const TOOLTIP_ITEM_STYLE = {
  fontFamily: "var(--font-mono)",
  fontVariantNumeric: "tabular-nums",
} as const;

const TOOLTIP_CONTENT_STYLE = {
  borderRadius: "var(--radius-md)",
  border: "1px solid var(--border)",
  background: "var(--popover)",
  color: "var(--popover-foreground)",
} as const;

type BarEntryPayload = {
  month?: unknown;
  payload?: { month?: unknown };
} | null | undefined;

function makeBarClickHandler(onBarClick?: (label: string) => void) {
  if (!onBarClick) return undefined;
  return (entry: unknown) => {
    const e = entry as BarEntryPayload;
    const label = e?.month ?? e?.payload?.month;
    if (typeof label === "string") onBarClick(label);
  };
}

export function BarChartCard({
  chart,
  onBarClick,
}: {
  chart: DashboardChart;
  onBarClick?: (label: string) => void;
}) {
  const { rows, keys } = normalizeBarData(chart);
  const handleClick = makeBarClickHandler(onBarClick);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{chart.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={rows} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} className="text-muted-foreground" />
            <YAxis
              tick={{ fontSize: 12, className: "tabular-nums" }}
              className="text-muted-foreground"
              tickFormatter={(v: number) => formatCurrency(v)}
            />
            <Tooltip
              formatter={(value) => formatCurrency(Number(value))}
              itemStyle={TOOLTIP_ITEM_STYLE}
              contentStyle={TOOLTIP_CONTENT_STYLE}
            />
            <Legend />
            {keys.map((dk) => (
              <Bar
                key={dk.key}
                dataKey={dk.key}
                name={dk.name}
                fill={dk.color}
                radius={[4, 4, 0, 0]}
                cursor={onBarClick ? "pointer" : undefined}
                onClick={handleClick}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
