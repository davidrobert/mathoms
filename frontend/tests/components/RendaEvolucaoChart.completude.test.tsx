/**
 * ADR-266 · RendaEvolucaoChart — legenda de completude.
 *
 * Chart.js (canvas) não roda em jsdom — mockamos ChartLine para validar a
 * lógica de derivação e renderização da legenda de anos provisorio/incompleto.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import type { IrpfKpis } from "@/types/irpf";

vi.mock("@/components/report/charts/primitives", () => ({
  ChartLine: () => <div data-testid="chart-line" />,
  useChartTheme: () => ({ primary: "#000", categorical: ["#111", "#222"] }),
}));

vi.mock("@/components/report/charts/_shared", () => ({
  fmtBRL: (v: number) => `R$ ${v.toFixed(2)}`,
}));

import { RendaEvolucaoChart } from "@/components/report/charts/RendaEvolucaoChart";

const BASE_KPIS: IrpfKpis = {
  ano_base: 2024,
  anos_disponiveis: [2023, 2024],
  renda_anual_familiar_brl: "180000.00",
  renda_liquida_familiar_brl: "144000.00",
  ir_pago_total_brl: "24000.00",
  aliquota_sobre_tributavel_pct: "16.50",
  aliquota_sobre_total_pct: "13.30",
  pgbl_capacidade_dedutivel_brl: "5400.00",
  pgbl_status: "capacidade_disponivel",
  pgbl_aportado_brl: "10000.00",
  pgbl_teto_brl: "21600.00",
  split_trabalho_brl: "120000.00",
  split_capital_brl: "60000.00",
  evolucao_renda_anos: { "2023": "160000.00", "2024": "180000.00" },
};

describe("<RendaEvolucaoChart /> · ADR-266 legenda completude", () => {
  it("não renderiza legenda quando todos anos são completo", () => {
    const kpis: IrpfKpis = {
      ...BASE_KPIS,
      anos_completude_por_ano: { "2023": "completo", "2024": "completo" },
    };
    render(<RendaEvolucaoChart kpis={kpis} />);
    expect(screen.queryByLabelText(/completude diferenciada/i)).toBeNull();
  });

  it("renderiza chip 'provisório' para ano dentro da janela RFB", () => {
    const kpis: IrpfKpis = {
      ...BASE_KPIS,
      evolucao_renda_anos: {
        "2023": "160000.00",
        "2024": "180000.00",
        "2025": "5469.95",
      },
      anos_completude_por_ano: {
        "2023": "completo",
        "2024": "completo",
        "2025": "provisorio",
      },
    };
    render(<RendaEvolucaoChart kpis={kpis} />);
    expect(screen.getByText(/2025 · provisório/i)).toBeInTheDocument();
    // Chips de 2023/2024 (completos) NÃO aparecem na legenda.
    expect(screen.queryByText(/2023 ·/)).toBeNull();
    expect(screen.queryByText(/2024 ·/)).toBeNull();
  });

  it("renderiza chip 'incompleto' para ano com lacuna", () => {
    const kpis: IrpfKpis = {
      ...BASE_KPIS,
      evolucao_renda_anos: {
        "2023": "160000.00",
        "2024": "180000.00",
        "2025": "5469.95",
      },
      anos_completude_por_ano: {
        "2023": "completo",
        "2024": "completo",
        "2025": "incompleto",
      },
    };
    render(<RendaEvolucaoChart kpis={kpis} />);
    expect(screen.getByText(/2025 · incompleto/i)).toBeInTheDocument();
  });

  it("workspace pre-ADR-266 (sem anos_completude_por_ano) renderiza sem legenda", () => {
    render(<RendaEvolucaoChart kpis={BASE_KPIS} />);
    expect(screen.queryByLabelText(/completude diferenciada/i)).toBeNull();
  });
});
