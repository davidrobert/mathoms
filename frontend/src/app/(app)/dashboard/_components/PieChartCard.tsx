"use client";

import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { DashboardChart } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_COLORS, normalizePieData } from "./dashboardHelpers";

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

function makeSliceClickHandler(onSliceClick?: (name: string) => void) {
  if (!onSliceClick) return undefined;
  return (entry: { name?: string }) => {
    if (entry?.name) onSliceClick(entry.name);
  };
}

export function PieChartCard({
  chart,
  onSliceClick,
}: {
  chart: DashboardChart;
  onSliceClick?: (name: string) => void;
}) {
  const data = normalizePieData(chart);
  const handleClick = makeSliceClickHandler(onSliceClick);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{chart.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius="80%"
              innerRadius="45%"
              paddingAngle={2}
              strokeWidth={0}
              cursor={onSliceClick ? "pointer" : undefined}
              onClick={handleClick}
            >
              {data.map((entry, idx) => (
                <Cell key={entry.name} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => formatCurrency(Number(value))}
              itemStyle={TOOLTIP_ITEM_STYLE}
              contentStyle={TOOLTIP_CONTENT_STYLE}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
