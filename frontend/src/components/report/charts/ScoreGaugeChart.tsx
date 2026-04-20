"use client";

import {
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  PolarAngleAxis,
} from "recharts";
import { ReportCard } from "../ReportCard";
import { getScoreColorVar, getScoreLabel } from "../utils/scoreUtils";
import type { ScoreData } from "@/types/report-analysis";

/** F9 · F2.A · S1 — Gauge do Score Financeiro (0–10).
 *
 * Substitui o canvas `chart-score-gauge`. Mostra o valor com cor
 * semântica (vermelho < 4, laranja 4–6, verde ≥ 6) e a classificação
 * textual emitida pelo E5 (ex: "Atenção", "Muito Bom").
 */
export function ScoreGaugeChart({ score }: { score: ScoreData | undefined }) {
  if (!score) {
    return (
      <ReportCard variant="neutral" title="Score Financeiro">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Score não disponível.
        </p>
      </ReportCard>
    );
  }

  const valor = Math.max(0, Math.min(score.max, score.valor));
  const pct = (valor / score.max) * 100;

  const color = getScoreColorVar(valor, score.max);

  const data = [{ name: "score", value: pct, fill: color }];

  return (
    <ReportCard variant="neutral" title="Score Financeiro">
      <div className="flex flex-col items-center">
        <div className="relative w-full">
          <ResponsiveContainer width="100%" height={192}>
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="70%"
              outerRadius="100%"
              barSize={18}
              data={data}
              startAngle={180}
              endAngle={0}
            >
              <PolarAngleAxis
                type="number"
                domain={[0, 100]}
                angleAxisId={0}
                tick={false}
              />
              <RadialBar
                background={{ fill: "var(--surface-muted)" }}
                dataKey="value"
                cornerRadius={8}
              />
            </RadialBarChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center pb-4">
            <p
              className="font-mono text-4xl font-bold tabular-nums"
              style={{ color }}
            >
              {valor.toFixed(1).replace(".", ",")}
            </p>
            <p className="text-xs text-[var(--surface-muted-foreground)]">
              / {score.max}
            </p>
          </div>
        </div>
        <p
          className="mt-2 font-display text-sm font-semibold"
          style={{ color }}
        >
          {score.classificacao ?? getScoreLabel(valor, score.max)}
        </p>
      </div>
    </ReportCard>
  );
}
