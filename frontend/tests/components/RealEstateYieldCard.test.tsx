/**
 * Tests — Onda 2 P-C (ADR-216) — RealEstateYieldCard renderiza hero + tabela + alertas + empty.
 */
import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";

import { RealEstateYieldCard } from "@/components/report/cards/RealEstateYieldCard";
import type {
  RealEstateData,
  RealEstateImovel,
} from "@/types/report-analysis";

function makeImovel(overrides: Partial<RealEstateImovel> = {}): RealEstateImovel {
  return {
    property_id: "p1",
    descricao: "Apto Vila Madalena",
    classification: "locado",
    valor_imovel: 1200000,
    valor_imovel_origem: "irpf",
    aluguel_mensal_bruto: 2100,
    taxa_administracao_mensal: 210,
    iptu_mensal: 400,
    condominio_mensal: null,
    ir_retido_mensal: 0,
    meses_locado_no_ano: 12,
    vacancia_pct_empirica: 0,
    cap_rate_bruto_pct: 2.1,
    cap_rate_liquido_pct: 1.6,
    gap_reajuste_pct: null,
    status_contrato: "atualizado",
    indice_reajuste: "IGPM",
    data_ultimo_reajuste: "2024-08-15",
    endereco_canonical: "Rua Tasso da Silveira, 61 — Vila Madalena",
    imobiliaria_cnpj: null,
    imobiliaria_nome: "QuintoAndar",
    origem_aluguel: "informe",
    ...overrides,
  };
}

function makeData(overrides: Partial<RealEstateData> = {}): RealEstateData {
  return {
    cap_rate_liquido_pct: 1.3,
    cap_rate_bruto_pct: 1.7,
    componentes_calculo: {
      aluguel_anual_bruto: { valor: 25200, origem: "informe", confidence: "high" },
    },
    benchmarks: {
      cdi_liquido_pct: 8.99,
      ntnb_liquido_pct: 5.52,
      ifix_yield_pct: 9.2,
      as_of_date: "2026-05-15",
    },
    spreads_pp: { vs_cdi: -7.69, vs_ntnb: -4.22, vs_ifix: -7.9 },
    spread_brl_anual: { vs_cdi: -92280, vs_ntnb: -50640, vs_ifix: -94800 },
    concentracao_pct: 24,
    valor_total_imoveis: 1200000,
    imoveis: [makeImovel()],
    excluded_properties: [],
    alertas: [],
    ...overrides,
  };
}

describe("RealEstateYieldCard", () => {
  it("renderiza cap rate líquido em destaque", () => {
    render(<RealEstateYieldCard data={makeData()} />);
    expect(screen.getAllByText(/Cap rate líquido/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/1,30%/).length).toBeGreaterThan(0);
  });

  it("mostra os 3 benchmarks da tríade", () => {
    render(<RealEstateYieldCard data={makeData()} />);
    expect(screen.getByText(/CDI líq\./)).toBeInTheDocument();
    // "NTN-B real" aparece tanto na barra do hero quanto no footer
    expect(screen.getAllByText(/NTN-B real/).length).toBeGreaterThan(0);
    expect(screen.getByText(/IFIX 12m/)).toBeInTheDocument();
  });

  it("oculta a tabela quando há apenas 1 imóvel", () => {
    render(<RealEstateYieldCard data={makeData()} />);
    expect(screen.queryByText(/Detalhe por imóvel/)).not.toBeInTheDocument();
  });

  it("renderiza a tabela quando há ≥2 imóveis ordenados por valor descendente", () => {
    const data = makeData({
      imoveis: [
        makeImovel({ property_id: "p1", descricao: "Imóvel A", valor_imovel: 2000000 }),
        makeImovel({ property_id: "p2", descricao: "Imóvel B", valor_imovel: 1000000 }),
      ],
    });
    render(<RealEstateYieldCard data={data} />);
    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row");
    // 1 header + 2 data rows
    expect(rows).toHaveLength(3);
    expect(rows[1]).toHaveTextContent("Imóvel A");
    expect(rows[2]).toHaveTextContent("Imóvel B");
  });

  it("status_contrato 'reajuste_pendente' exibe badge correto", () => {
    const data = makeData({
      imoveis: [
        makeImovel({ property_id: "p1", descricao: "A", valor_imovel: 2000000 }),
        makeImovel({
          property_id: "p2",
          descricao: "B",
          valor_imovel: 1000000,
          status_contrato: "reajuste_pendente",
        }),
      ],
    });
    render(<RealEstateYieldCard data={data} />);
    expect(screen.getByText(/Reajuste pendente/i)).toBeInTheDocument();
  });

  it("renderiza alertas com severity warning", () => {
    const data = makeData({
      alertas: [
        {
          code: "concentracao_alta",
          severity: "warning",
          context: "Concentração em imóveis (45,0%) acima de 40% do patrimônio.",
        },
      ],
    });
    render(<RealEstateYieldCard data={data} />);
    expect(screen.getByText(/Concentração elevada em imóveis/)).toBeInTheDocument();
    expect(screen.getByText(/45,0%/)).toBeInTheDocument();
  });

  it("renderiza excluded_properties expandível", () => {
    const data = makeData({
      excluded_properties: [
        {
          property_id: "p2",
          descricao: "Casa Residência",
          classification: "residencia_principal",
          motivo: "Residência principal — não conta como investimento.",
        },
      ],
    });
    render(<RealEstateYieldCard data={data} />);
    expect(screen.getByText(/1 imóvel não incluído/)).toBeInTheDocument();
    expect(screen.getByText(/Casa Residência/)).toBeInTheDocument();
  });

  it("empty state quando data é null", () => {
    render(<RealEstateYieldCard data={null} />);
    expect(screen.getByText(/Você não tem imóveis de investimento/)).toBeInTheDocument();
  });

  it("empty state 'sem_dado' quando cap_rate_liquido_pct é null", () => {
    const data = makeData({ cap_rate_liquido_pct: null });
    render(<RealEstateYieldCard data={data} />);
    expect(screen.getByText(/Sem dados de aluguel suficientes/)).toBeInTheDocument();
  });

  it("footer cita a data dos benchmarks", () => {
    render(<RealEstateYieldCard data={makeData()} />);
    expect(screen.getByText(/2026-05-15/)).toBeInTheDocument();
  });

  it("mostra concentração no hero", () => {
    render(<RealEstateYieldCard data={makeData({ concentracao_pct: 35.8 })} />);
    expect(screen.getByText(/35,8%/)).toBeInTheDocument();
  });
});
