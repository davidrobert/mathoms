"use client";

import { MonetaryValue } from "../../MonetaryValue";
import type { ProtecaoPatrimonialData } from "@/types/protecao";

/** Faixas Cerbasi para KPI B — ancoradas em `protecao_analyzer.py::_PCT_RENDA_FAIXAS`. */
type PctRendaSinal = "atencao" | "ok" | "ok_forte";

function pctRendaSinal(pct: number): PctRendaSinal {
  if (pct < 0.01) return "atencao";
  if (pct < 0.03) return "ok";
  if (pct < 0.05) return "ok_forte";
  return "atencao";
}

const SINAL_LABEL: Record<PctRendaSinal, string> = {
  atencao: "Atenção",
  ok: "Faixa observada",
  ok_forte: "Bem dimensionado",
};

const SINAL_COLOR: Record<PctRendaSinal, string> = {
  atencao: "text-semantic-warn",
  ok: "text-semantic-success",
  ok_forte: "text-semantic-success",
};

/** KPI G (hero) + KPI B (% renda) — primeiro card do S_PROTECAO. */
export function ProtecaoKpiHero({ data }: { data: ProtecaoPatrimonialData }) {
  const premioTotal = Number.parseFloat(data.premio_total_anual_brl);
  const pctRenda = Number.parseFloat(data.pct_renda_anual);
  const sinal = pctRendaSinal(pctRenda);
  const decomp = data.premio_decomposicao;

  return (
    <div className="report-card report-card--highlight" data-testid="protecao-kpi-hero">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <div className="text-style-caption text-muted">Prêmio total anual</div>
          <MonetaryValue value={premioTotal} size="hero" data-testid="protecao-kpi-g" />
          <div className="text-style-caption mt-1">
            {Object.entries(decomp).map(([tipo, valor]) => (
              <span key={tipo} className="mr-3">
                <strong>{tipo}:</strong> <MonetaryValue value={Number.parseFloat(valor)} />
              </span>
            ))}
          </div>
        </div>
        <div>
          <div className="text-style-caption text-muted">% renda anual em prêmios</div>
          <div
            className={`text-style-kpi ${SINAL_COLOR[sinal]}`}
            data-testid="protecao-kpi-b"
          >
            {(pctRenda * 100).toFixed(2)}%
          </div>
          <div className="text-style-caption mt-1" data-testid="protecao-kpi-b-sinal">
            {SINAL_LABEL[sinal]}
          </div>
        </div>
      </div>
    </div>
  );
}
