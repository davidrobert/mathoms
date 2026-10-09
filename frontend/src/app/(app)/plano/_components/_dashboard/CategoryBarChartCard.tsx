"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Text,
  Tooltip,
  XAxis,
  YAxis,
  type YAxisTickContentProps,
} from "recharts";
import type { DashboardChart } from "@/lib/api";
import { formatCompact, formatCurrency } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AXIS_TICK_STYLE, TOOLTIP_CONTENT_STYLE, TOOLTIP_ITEM_STYLE } from "./chartStyles";
import { categoryBarChartHeight, normalizeBarData } from "./dashboardHelpers";

const CATEGORY_AXIS_WIDTH = 112;
// O <Text> recebe a largura do eixo inteiro mas é ancorado em `width − tickSize − tickMargin`:
// quebrar na largura cheia empurra a linha 8px para fora do <svg>, que corta (overflow hidden).
// 104 também cai entre "Imóveis com uso" e "Imóveis com uso não" — a negação fica na 2ª linha.
const CATEGORY_LABEL_WIDTH = CATEGORY_AXIS_WIDTH - 8;

function CategoryTick({ x, y, textAnchor, verticalAnchor, className, payload }: YAxisTickContentProps) {
  const label = String(payload.value);
  return (
    <g>
      <title>{label}</title>
      <Text
        x={x}
        y={y}
        textAnchor={textAnchor}
        verticalAnchor={verticalAnchor}
        className={className}
        width={CATEGORY_LABEL_WIDTH}
        maxLines={2}
        lineHeight="1.2em"
        style={AXIS_TICK_STYLE}
      >
        {label}
      </Text>
    </g>
  );
}

/** Barra deitada para eixo de categorias (classes de investimento): na vertical, o recharts
 *  esconde o rótulo que colide com o vizinho e a classe só aparece no tooltip. */
export function CategoryBarChartCard({ chart }: { chart: DashboardChart }) {
  const { rows, keys } = normalizeBarData(chart);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{chart.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={categoryBarChartHeight(rows.length)}>
          <BarChart
            data={rows}
            layout="vertical"
            title={chart.title}
            margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
          >
            <CartesianGrid horizontal={false} strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              type="number"
              axisLine={false}
              tickLine={false}
              tick={{ style: AXIS_TICK_STYLE, className: "tabular-nums" }}
              tickFormatter={(v: number) => formatCompact(v)}
            />
            <YAxis
              type="category"
              dataKey="month"
              width={CATEGORY_AXIS_WIDTH}
              interval={0}
              axisLine={false}
              tickLine={false}
              tick={CategoryTick}
            />
            <Tooltip
              formatter={(value) => formatCurrency(Number(value))}
              itemStyle={TOOLTIP_ITEM_STYLE}
              contentStyle={TOOLTIP_CONTENT_STYLE}
              cursor={{ className: "fill-[var(--surface-row-hover)]" }}
            />
            {keys.length > 1 && <Legend />}
            {keys.map((dk) => (
              <Bar
                key={dk.key}
                dataKey={dk.key}
                name={dk.name}
                fill={dk.color}
                radius={[0, 4, 4, 0]}
                maxBarSize={24}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
