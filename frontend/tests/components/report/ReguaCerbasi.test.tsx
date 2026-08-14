/**
 * A40.l47 PR2 — a legenda do apêndice não tem régua própria.
 *
 * O gate é de CLASSE, não de instância: qualquer régua que o enforcer publique tem de
 * aparecer inteira, e nenhum rótulo/faixa pode existir só na legenda. Antes, a legenda
 * era texto fixo e divergia do código em 4 pontos — incluindo a faixa do rótulo comum
 * (a 35% de futuro o relatório imprimia "Investidor" e a legenda dizia "Equilibrado").
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ApendiceBSection } from "@/components/report/sections/ApendicesSections";
import type { ReportAnalysisData } from "@/lib/api";

function makeData(faixas: unknown): ReportAnalysisData {
  return {
    equilibrio_cerbasi: { classificacao_faixas: faixas },
  } as unknown as ReportAnalysisData;
}

const REGUA_DEFAULT = [
  { minimo_futuro_pct: 30, label: "Investidor" },
  { minimo_futuro_pct: 20, label: "Equilibrado" },
  { minimo_futuro_pct: 10, label: "Endividado consciente" },
  { minimo_futuro_pct: 0, label: "Gastador" },
];

describe("legenda do Equilíbrio Cerbasi", () => {
  it("imprime todos os rótulos da régua publicada", () => {
    render(<ApendiceBSection data={makeData(REGUA_DEFAULT)} />);
    for (const { label } of REGUA_DEFAULT) {
      expect(screen.getByText(new RegExp(label))).toBeInTheDocument();
    }
  });

  it("a faixa do rótulo do meio casa com o enforcer, não com a legenda antiga", () => {
    // Enforcer: Equilibrado = [20, 30). A legenda hardcoded dizia 20–40.
    render(<ApendiceBSection data={makeData(REGUA_DEFAULT)} />);
    expect(screen.getByText(/Equilibrado \(20–30%\)/)).toBeInTheDocument();
    expect(screen.queryByText(/20–40/)).toBeNull();
  });

  it("nenhum rótulo aparece quando a régua não vem no payload", () => {
    render(<ApendiceBSection data={makeData(undefined)} />);
    for (const { label } of REGUA_DEFAULT) {
      expect(screen.queryByText(new RegExp(label))).toBeNull();
    }
    expect(screen.getByText(/proporção ideal ~70% presente/)).toBeInTheDocument();
  });

  it("régua custom aparece inteira e a default não vaza", () => {
    const custom = makeData([
      { minimo_futuro_pct: 45, label: "Poupador" },
      { minimo_futuro_pct: 0, label: "Consumidor" },
    ]);
    render(<ApendiceBSection data={custom} />);
    expect(screen.getByText(/Poupador \(≥45%\)/)).toBeInTheDocument();
    expect(screen.getByText(/Consumidor \(<45%\)/)).toBeInTheDocument();
    expect(screen.queryByText(/Investidor/)).toBeNull();
  });

  it("faixa com shape inválido é descartada em vez de imprimir lixo", () => {
    render(<ApendiceBSection data={makeData([{ minimo_futuro_pct: "30", label: 7 }])} />);
    expect(screen.queryByText(/NaN|undefined|\[object/)).toBeNull();
  });
});
