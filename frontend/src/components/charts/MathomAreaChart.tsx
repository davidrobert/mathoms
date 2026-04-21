"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { cn } from "@/lib/cn";
import { formatCurrency } from "@/lib/format";

interface DataKeyDef {
  key: string;
  name: string;
  color: string;
}

interface MathomAreaChartProps {
  data: Record<string, unknown>[];
  dataKeys: DataKeyDef[];
  xAxisKey: string;
  title?: string;
  height?: number;
  className?: string;
}

export function MathomAreaChart({
  data,
  dataKeys,
  xAxisKey,
  title,
  height = 300,
  className,
}: MathomAreaChartProps) {
  return (
    <div className={cn("w-full", className)}>
      {title && (
        <h3 className="mb-3 text-sm font-medium text-foreground">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis
            dataKey={xAxisKey}
            tick={{ fontSize: 12 }}
            className="text-muted-foreground"
          />
          <YAxis
            tick={{ fontSize: 12 }}
            className="text-muted-foreground"
            tickFormatter={(v: number) => formatCurrency(v)}
          />
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
          {dataKeys.map((dk) => (
            <Area
              key={dk.key}
              type="monotone"
              dataKey={dk.key}
              name={dk.name}
              stroke={dk.color}
              fill={dk.color}
              fillOpacity={0.15}
              strokeWidth={2}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
