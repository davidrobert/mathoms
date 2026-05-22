"use client";

import type { GapQualitativo } from "@/types/protecao";

const CATEGORIA_COPY: Record<string, { label: string; texto: string }> = {
  vida: {
    label: "Vida",
    texto:
      "Não identificamos apólice de vida ativa — vale considerar quando há dependentes financeiros ou dívida significativa.",
  },
  saude: {
    label: "Saúde",
    texto:
      "Não identificamos cobertura de saúde nos documentos. Verifique se está coberto via PJ/empresa, ou se vale ativar plano individual.",
  },
  rc_familiar: {
    label: "RC Familiar (V2)",
    texto: "Cobertura de responsabilidade civil familiar — modelagem em V2.",
  },
  rd_profissional: {
    label: "RD Profissional (V2)",
    texto: "Cobertura de responsabilidade profissional — modelagem em V2.",
  },
  ap: {
    label: "Acidentes Pessoais (V2)",
    texto: "Cobertura de acidentes pessoais — modelagem em V2.",
  },
};

/** KPI F — chips qualitativos. Renderiza apenas categorias com flag=true (ADR-240 D3). */
export function ProtecaoGapQualitativo({ gaps }: { gaps: GapQualitativo[] }) {
  const ativos = gaps.filter((g) => g.flag);
  if (ativos.length === 0) {
    return null;
  }
  return (
    <div className="report-card report-card--warn" data-testid="protecao-gap-qualitativo">
      <h3 className="text-style-subtitle">Pilares de proteção a avaliar</h3>
      <div className="mt-3 flex flex-wrap gap-2">
        {ativos.map((g) => (
          <span
            key={g.categoria}
            className="rounded-full bg-semantic-warn/20 px-3 py-1 text-style-caption"
            data-testid={`protecao-chip-${g.categoria}`}
          >
            {CATEGORIA_COPY[g.categoria]?.label ?? g.categoria}: não identificada
          </span>
        ))}
      </div>
      <ul className="mt-3 list-none text-style-body">
        {ativos.map((g) => (
          <li key={g.categoria} className="mt-1">
            <strong>{CATEGORIA_COPY[g.categoria]?.label ?? g.categoria}:</strong>{" "}
            {CATEGORIA_COPY[g.categoria]?.texto ?? g.rationale}
          </li>
        ))}
      </ul>
    </div>
  );
}
