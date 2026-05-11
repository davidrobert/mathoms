/**
 * Unit tests — ADR-157 · IRPF Full Schema · UI lane.
 * ADR-189 — IrpfPgblCapacidadeCard: switch sobre `pgbl_status` em 4 estados.
 *
 * Cobre:
 * - Contrato de degradação graciosa: workspaces sem `irpf_kpis` no snapshot
 *   E5 não devem renderizar as seções S_IRPF_RENDA / S_IRPF_OTIMIZACAO.
 * - Workspaces com KPIs válidos exibem valores monetários canônicos.
 * - 4 estados do diagnóstico PGBL (copy literal de ADR-189 §4 / §6.1).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { IrpfRendaSection } from "@/components/report/sections/IrpfRendaSection";
import { IrpfOtimizacaoSection } from "@/components/report/sections/IrpfOtimizacaoSection";
import { IrpfPgblCapacidadeCard } from "@/components/report/cards/IrpfPgblCapacidadeCard";
import type { IrpfKpis, PgblStatus } from "@/types/irpf";
import type { ReportAnalysisData } from "@/lib/api";

const KPIS_BASE: IrpfKpis = {
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

function withStatus(status: PgblStatus, overrides: Partial<IrpfKpis> = {}): IrpfKpis {
  return { ...KPIS_BASE, pgbl_status: status, ...overrides };
}

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
    const data = { irpf_kpis: KPIS_BASE } as unknown as ReportAnalysisData;
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
    // Cards "Dependentes Declarados" e "Dedutíveis Subutilizados" foram
    // removidos até IRPFAnalyzer emitir números reais (eram prose-only).
    const data = { irpf_kpis: KPIS_BASE } as unknown as ReportAnalysisData;
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

describe("<IrpfPgblCapacidadeCard /> · ADR-189 · 4 estados", () => {
  it("Estado 1 — capacidade_disponivel: variante info, disclaimer presente, valor monetário", () => {
    const kpis = withStatus("capacidade_disponivel", {
      pgbl_capacidade_dedutivel_brl: "11600.00",
      pgbl_aportado_brl: "10000.00",
      pgbl_teto_brl: "21600.00",
    });
    const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
    expect(container.querySelector(".card-variant-info")).not.toBeNull();
    expect(screen.getByText(/Espaço dedutível remanescente · 2024/)).toBeInTheDocument();
    expect(screen.getByText(/Não é recomendação:/)).toBeInTheDocument();
    expect(screen.getByText(/tabela regressiva vs\. progressiva/)).toBeInTheDocument();
    expect(screen.getByText(/horizonte de resgate/)).toBeInTheDocument();
    expect(screen.getByText(/taxa de administração/)).toBeInTheDocument();
    expect(screen.getByText(/contribuição ao INSS/)).toBeInTheDocument();
    // Não usa "—" no estado positivo (zero monetário não aplicável aqui)
    const heroLine = container.querySelector(".font-mono.text-2xl");
    expect(heroLine?.textContent).not.toBe("—");
  });

  it("Estado 2 — modelo_simplificado: variante neutral, '—', sem disclaimer", () => {
    const kpis = withStatus("modelo_simplificado", {
      pgbl_capacidade_dedutivel_brl: "0",
      pgbl_aportado_brl: "0",
      pgbl_teto_brl: "0",
    });
    const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
    expect(container.querySelector(".card-variant-neutral")).not.toBeNull();
    expect(screen.getAllByText(/Não se aplica · 2024/).length).toBeGreaterThan(0);
    expect(screen.getByText(/modelo simplificado em 2024/)).toBeInTheDocument();
    expect(screen.getByText(/desconto fixo sobre os rendimentos tributáveis/)).toBeInTheDocument();
    expect(screen.getByText(/A capacidade de 12% só vale no modelo completo\./)).toBeInTheDocument();
    expect(screen.queryByText(/Não é recomendação:/)).toBeNull();
    const heroLine = container.querySelector(".font-mono.text-2xl");
    expect(heroLine?.textContent).toBe("—");
  });

  it("Estado 3 — no_teto: variante feature, R$ 0,00, sem disclaimer", () => {
    const kpis = withStatus("no_teto", {
      pgbl_capacidade_dedutivel_brl: "0",
      pgbl_aportado_brl: "24000.00",
      pgbl_teto_brl: "24000.00",
    });
    const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
    expect(container.querySelector(".card-variant-feature")).not.toBeNull();
    expect(screen.getByText(/Teto dedutível atingido · 2024/)).toBeInTheDocument();
    expect(screen.getByText(/esgotando os 12% dedutíveis/)).toBeInTheDocument();
    expect(
      screen.getByText(/Não há capacidade dedutível remanescente em 2024\./),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Não é recomendação:/)).toBeNull();
    const heroLine = container.querySelector(".font-mono.text-2xl");
    expect(heroLine?.textContent).not.toBe("—");
    expect(heroLine?.textContent ?? "").toMatch(/0,00/);
  });

  it("Estado 4 — sem_renda_tributavel: variante neutral, '—', sem disclaimer", () => {
    const kpis = withStatus("sem_renda_tributavel", {
      pgbl_capacidade_dedutivel_brl: "0",
      pgbl_aportado_brl: "0",
      pgbl_teto_brl: "0",
    });
    const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
    expect(container.querySelector(".card-variant-neutral")).not.toBeNull();
    expect(screen.getByText(/Não se aplica · 2024/)).toBeInTheDocument();
    expect(
      screen.getByText(/apenas rendimentos isentos ou de tributação exclusiva/),
    ).toBeInTheDocument();
    expect(screen.getByText(/PGBL deduz da renda tributável/)).toBeInTheDocument();
    expect(screen.queryByText(/Não é recomendação:/)).toBeNull();
    const heroLine = container.querySelector(".font-mono.text-2xl");
    expect(heroLine?.textContent).toBe("—");
  });
});
