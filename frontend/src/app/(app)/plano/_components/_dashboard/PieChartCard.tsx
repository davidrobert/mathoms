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
import { TOOLTIP_CONTENT_STYLE, TOOLTIP_ITEM_STYLE } from "./chartStyles";
import { CHART_COLORS, LEGEND_PROPS } from "./dashboardHelpers";
import { normalizePieData, type PieSlice } from "./dashboardPie";
import { PieNotes } from "./PieNotes";

function makeSliceClickHandler(onSliceClick?: (id: string) => void) {
  if (!onSliceClick) return undefined;
  return (entry: { payload?: Partial<PieSlice> }) => {
    const id = entry?.payload?.id;
    if (id) onSliceClick(id);
  };
}

export function PieChartCard({
  chart,
  onSliceClick,
}: {
  chart: DashboardChart;
  onSliceClick?: (id: string) => void;
}) {
  const pie = normalizePieData(chart);
  const handleClick = makeSliceClickHandler(pie.clickable ? onSliceClick : undefined);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{chart.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <PieNotes notes={pie.notes} />
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pie.slices}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius="80%"
              innerRadius="45%"
              paddingAngle={2}
              strokeWidth={0}
              cursor={handleClick ? "pointer" : undefined}
              onClick={handleClick}
            >
              {pie.slices.map((entry, idx) => (
                <Cell key={entry.id} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => formatCurrency(Number(value))}
              itemStyle={TOOLTIP_ITEM_STYLE}
              contentStyle={TOOLTIP_CONTENT_STYLE}
            />
            <Legend {...LEGEND_PROPS} />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
