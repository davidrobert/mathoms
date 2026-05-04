/**
 * Unit tests — ADR-157 · IRPF Full Schema · UI lane.
 *
 * Cobre o contrato de degradação graciosa: workspaces sem `irpf_kpis` no
 * snapshot E5 não devem renderizar as seções S_IRPF_RENDA / S_IRPF_OTIMIZACAO.
 * Workspaces com KPIs presentes devem mostrar valores monetários canônicos.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { IrpfRendaSection } from "@/components/report/sections/IrpfRendaSection";
import { IrpfOtimizacaoSection } from "@/components/report/sections/IrpfOtimizacaoSection";
import type { ReportAnalysisData } from "@/lib/api";

const KPIS_PAYLOAD = {
  ano_base: 2024,
  anos_disponiveis: [2023, 2024],
  renda_anual_familiar_brl: "180000.00",
  renda_liquida_familiar_brl: "144000.00",
  ir_pago_total_brl: "24000.00",
  aliquota_sobre_tributavel_pct: "16.50",
  aliquota_sobre_total_pct: "13.30",
  pgbl_capacidade_dedutivel_brl: "5400.00",
  split_trabalho_brl: "120000.00",
  split_capital_brl: "60000.00",
  evolucao_renda_anos: { "2023": "160000.00", "2024": "180000.00" },
};

describe("<IrpfRendaSection />", () => {
  it("retorna null quando irpf_kpis ausente (degrada gracioso)", () => {
    const data = { periodo_dados: "2024-01" } as ReportAnalysisData;
    const { container } = render(<IrpfRendaSection data={data} />);
    expect(container.firstChild).toBeNull();
  });

  it("retorna null quando irpf_kpis tem shape inválido", () => {
    const data = { irpf_kpis: { foo: "bar" } } as unknown as ReportAnalysisData;
    const { container } = render(<IrpfRendaSection data={data} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza a seção e o título quando irpf_kpis válido", () => {
    const data = { irpf_kpis: KPIS_PAYLOAD } as unknown as ReportAnalysisData;
    render(<IrpfRendaSection data={data} />);
    expect(
      screen.getByRole("heading", { level: 2, name: /Renda Anual e Impostos/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: /Renda Anual Familiar/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: /^IR Pago$/i })).toBeInTheDocument();
  });
});

describe("<IrpfOtimizacaoSection />", () => {
  it("retorna null quando irpf_kpis ausente", () => {
    const data = {} as ReportAnalysisData;
    const { container } = render(<IrpfOtimizacaoSection data={data} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza apenas card PGBL quando irpf_kpis válido", () => {
    // Cards "Dependentes Declarados" e "Dedutíveis Subutilizados" foram removidos
    // até IRPFAnalyzer emitir números reais (eram prose-only). Spawn task aberta.
    const data = { irpf_kpis: KPIS_PAYLOAD } as unknown as ReportAnalysisData;
    render(<IrpfOtimizacaoSection data={data} />);
    expect(
      screen.getByRole("heading", { level: 2, name: /Otimização Tributária/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: /Capacidade PGBL/i })).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { level: 3, name: /Dependentes Declarados/i }),
    ).toBeNull();
    expect(
      screen.queryByRole("heading", { level: 3, name: /Dedutíveis Subutilizados/i }),
    ).toBeNull();
  });
});
