"use client";

import { MonetaryValue } from "../../MonetaryValue";
import type { ApoliceResumo, ProtecaoPatrimonialData } from "@/types/protecao";

type StatusVigencia = "vigente" | "vencendo" | "vencida";

const STATUS_BADGE: Record<StatusVigencia, string> = {
  vigente: "bg-semantic-success/20 text-semantic-success",
  vencendo: "bg-semantic-warn/20 text-semantic-warn",
  vencida: "bg-semantic-danger/20 text-semantic-danger",
};

const STATUS_LABEL: Record<StatusVigencia, string> = {
  vigente: "Vigente",
  vencendo: "Vencendo em 30d",
  vencida: "Vencida",
};

function ApoliceRow({ apolice, status }: { apolice: ApoliceResumo; status: StatusVigencia }) {
  return (
    <tr
      className="border-b border-surface-divider/50"
      data-testid={`protecao-apolice-${apolice.apolice_numero}`}
    >
      <td>{apolice.apolice_numero}</td>
      <td>{apolice.seguradora}</td>
      <td>
        <span className={`rounded px-2 py-0.5 text-style-caption ${STATUS_BADGE[status]}`}>
          {STATUS_LABEL[status]}
        </span>
      </td>
      <td>
        {apolice.vigencia_inicio} → {apolice.vigencia_fim}
      </td>
      <td className="text-right">
        <MonetaryValue value={Number.parseFloat(apolice.premio_total_brl)} />
      </td>
      <td>{(apolice.tipos_bem || []).join(", ")}</td>
    </tr>
  );
}

/** Lista de apólices vigentes/vencendo/vencidas + multi-corretor metadata neutra (D6). */
export function ProtecaoApolices({ data }: { data: ProtecaoPatrimonialData }) {
  const total =
    data.apolices_vigentes.length + data.apolices_vencendo.length + data.apolices_vencidas.length;
  if (total === 0) {
    return null;
  }
  return (
    <div className="report-card report-card--neutral" data-testid="protecao-apolices">
      <h3 className="text-style-subtitle">Apólices ativas</h3>
      <table className="mt-3 w-full text-style-body">
        <thead>
          <tr className="border-b border-surface-divider">
            <th scope="col" className="text-left">Apólice</th>
            <th scope="col" className="text-left">Seguradora</th>
            <th scope="col" className="text-left">Status</th>
            <th scope="col" className="text-left">Vigência</th>
            <th scope="col" className="text-right">Prêmio anual</th>
            <th scope="col" className="text-left">Bens</th>
          </tr>
        </thead>
        <tbody>
          {data.apolices_vigentes
            .filter((a) => !data.apolices_vencendo.some((v) => v.apolice_numero === a.apolice_numero))
            .map((a) => (
              <ApoliceRow key={a.apolice_numero} apolice={a} status="vigente" />
            ))}
          {data.apolices_vencendo.map((a) => (
            <ApoliceRow key={a.apolice_numero} apolice={a} status="vencendo" />
          ))}
          {data.apolices_vencidas.map((a) => (
            <ApoliceRow key={a.apolice_numero} apolice={a} status="vencida" />
          ))}
        </tbody>
      </table>
      {data.corretoras_count > 1 && (
        <p className="mt-2 text-style-caption text-muted" data-testid="protecao-multi-corretor">
          {data.corretoras_count} corretoras distintas nas apólices vigentes —
          considere consolidar quando renovar (questão neutra, depende de relacionamento).
        </p>
      )}
    </div>
  );
}
