"use client";

import { MonetaryValue } from "../../MonetaryValue";
import type { BemGapCobertura, ProtecaoGapSinal } from "@/types/protecao";

const SINAL_COPY: Record<ProtecaoGapSinal, string> = {
  ok: "Cobertura próxima ao valor de mercado.",
  atencao_branda: "LMI abaixo do valor FIPE — considere revisar na renovação.",
  atencao: "LMI significativamente abaixo do FIPE — vale conversar com seu corretor.",
};

const SINAL_BADGE: Record<ProtecaoGapSinal, string> = {
  ok: "bg-semantic-success text-on-success",
  atencao_branda: "bg-semantic-warn text-on-warn",
  atencao: "bg-semantic-danger text-on-danger",
};

const SINAL_LABEL: Record<ProtecaoGapSinal, string> = {
  ok: "OK",
  atencao_branda: "Atenção",
  atencao: "Atenção forte",
};

/** KPI C V1 — tabela LMI vs FIPE por veículo segurado (ADR-240 D3). */
export function ProtecaoGapVeiculos({ bens }: { bens: BemGapCobertura[] }) {
  if (bens.length === 0) {
    return (
      <div className="report-card report-card--neutral" data-testid="protecao-gap-empty">
        <p className="text-style-body text-muted">
          Sem veículos com cobertura material identificados. Aguardando refresh FIPE
          ou apólice ingerida.
        </p>
      </div>
    );
  }

  return (
    <div className="report-card report-card--feature" data-testid="protecao-gap-veiculos">
      <h3 className="text-style-subtitle">Cobertura de bens — Veículos</h3>
      <table className="mt-3 w-full text-style-body">
        <thead>
          <tr className="border-b border-surface-divider">
            <th scope="col" className="text-left">Veículo</th>
            <th scope="col" className="text-right">LMI</th>
            <th scope="col" className="text-right">FIPE</th>
            <th scope="col" className="text-right">Gap</th>
            <th scope="col" className="text-left">Sinal</th>
          </tr>
        </thead>
        <tbody>
          {bens.map((b) => (
            <tr
              key={b.veiculo_id}
              className="border-b border-surface-divider/50"
              data-testid={`protecao-gap-row-${b.veiculo_id}`}
            >
              <td>{b.veiculo_descricao || b.veiculo_id}</td>
              <td className="text-right">
                <MonetaryValue value={Number.parseFloat(b.lmi_brl)} />
              </td>
              <td className="text-right">
                <MonetaryValue value={Number.parseFloat(b.fipe_brl)} />
              </td>
              <td className="text-right">{(Number.parseFloat(b.gap_pct) * 100).toFixed(1)}%</td>
              <td>
                <span className={`rounded px-2 py-0.5 text-style-caption ${SINAL_BADGE[b.sinal]}`}>
                  {SINAL_LABEL[b.sinal]}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-style-caption text-muted" data-testid="protecao-gap-help">
        {SINAL_COPY[mostSeriousSinal(bens)]}
      </p>
    </div>
  );
}

/** Pior sinal entre os bens listados (drives da copy do card). */
function mostSeriousSinal(bens: BemGapCobertura[]): ProtecaoGapSinal {
  const seriedade = bens.map((b) => b.sinal);
  if (seriedade.includes("atencao")) return "atencao";
  if (seriedade.includes("atencao_branda")) return "atencao_branda";
  return "ok";
}
