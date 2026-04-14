"use client";

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from "recharts";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/format";

const CHART_COLORS = Array.from({ length: 12 }, (_, i) => `var(--chart-${i + 1})`);

interface PieDataItem {
  name: string;
  value: number;
  color?: string;
}

interface FinPieChartProps {
  data: PieDataItem[];
  title?: string;
  height?: number;
  className?: string;
}

export function FinPieChart({
  data,
  title,
  height = 300,
  className,
}: FinPieChartProps) {
  return (
    <div className={cn("w-full", className)}>
      {title && (
        <h3 className="mb-3 text-sm font-medium text-foreground">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
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
          >
            {data.map((entry, idx) => (
              <Cell
                key={entry.name}
                fill={entry.color ?? CHART_COLORS[idx % CHART_COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => formatCurrency(Number(value))}
            contentStyle={{
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              background: "var(--popover)",
              color: "var(--popover-foreground)",
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
