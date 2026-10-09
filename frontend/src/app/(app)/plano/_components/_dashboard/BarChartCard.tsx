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
import { formatCompact, formatCurrency } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  formatIsoMonthShort,
  isMonthlyBarChart,
  LEGEND_PROPS,
  normalizeBarData,
} from "./dashboardHelpers";
import { AXIS_TICK_STYLE, TOOLTIP_CONTENT_STYLE, TOOLTIP_ITEM_STYLE } from "./chartStyles";

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
  className,
}: {
  chart: DashboardChart;
  onBarClick?: (label: string) => void;
  className?: string;
}) {
  const { rows, keys } = normalizeBarData(chart);
  const handleClick = makeBarClickHandler(onBarClick);
  const monthLabel = isMonthlyBarChart(chart) ? formatIsoMonthShort : undefined;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{chart.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={rows} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="month" tick={{ style: AXIS_TICK_STYLE }} tickFormatter={monthLabel} />
            <YAxis
              width={72}
              tick={{ style: AXIS_TICK_STYLE, className: "tabular-nums" }}
              tickFormatter={(v: number) => formatCompact(v)}
            />
            <Tooltip
              formatter={(value) => formatCurrency(Number(value))}
              labelFormatter={monthLabel ? (label) => monthLabel(String(label)) : undefined}
              itemStyle={TOOLTIP_ITEM_STYLE}
              contentStyle={TOOLTIP_CONTENT_STYLE}
            />
            <Legend {...LEGEND_PROPS} />
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
