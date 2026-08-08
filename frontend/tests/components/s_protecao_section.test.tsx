/**
 * A19 L1 P3 (ADR-240) — S_ProtecaoSection render tests.
 *
 * 3 cenários ADR-240 G6:
 *   a) Workspace com seguros (owner case) — renderiza todos os subgrupos
 *   b) Workspace sem apólices — seção retorna null (não renderiza)
 *   c) Combinada multi-bem — renderiza ambos bens em ProtecaoApolices
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import type { ReportAnalysisData } from "@/lib/api/reports";
import type { ProtecaoPatrimonialData } from "@/types/protecao";
import { S_ProtecaoSection } from "@/components/report/sections/S_ProtecaoSection";

function makeProtecao(over?: Partial<ProtecaoPatrimonialData>): ProtecaoPatrimonialData {
  return {
    premio_total_anual_brl: "4750.00",
    premio_decomposicao: { auto: "4100.00", residencial: "650.00" },
    pct_renda_anual: "0.023750",
    bens_com_gap_cobertura: [
      {
        veiculo_id: "v-1",
        veiculo_descricao: "Yamaha NMAX",
        lmi_brl: "80000.00",
        fipe_brl: "80000.00",
        gap_pct: "0.000000",
        sinal: "ok",
      },
      {
        veiculo_id: "v-toro",
        veiculo_descricao: "Fiat Toro",
        lmi_brl: "60000.00",
        fipe_brl: "100000.00",
        gap_pct: "0.400000",
        sinal: "atencao",
      },
    ],
    gap_qualitativo: [
      { categoria: "vida", flag: true, rationale: "dependentes_menores_18" },
      { categoria: "saude", flag: false, rationale: "evidencia_pagamento_saude" },
    ],
    apolices_vigentes: [
      {
        apolice_numero: "AUTO-1",
        seguradora: "tokiomarine",
        vigencia_inicio: "2026-03-01",
        vigencia_fim: "2027-03-01",
        premio_total_brl: "1500.00",
        bens_count: 1,
        tipos_bem: ["veiculo"],
      },
      {
        apolice_numero: "COMB-1",
        seguradora: "porto",
        vigencia_inicio: "2026-04-10",
        vigencia_fim: "2027-04-10",
        premio_total_brl: "3250.00",
        bens_count: 2,
        tipos_bem: ["imovel", "veiculo"],
      },
    ],
    apolices_vencendo: [],
    apolices_vencidas: [],
    corretoras_count: 2,
    seguradoras_count: 2,
    ...over,
  };
}

function makeData(over?: Partial<ReportAnalysisData>): ReportAnalysisData {
  return { protecao_patrimonial: makeProtecao(), ...over } as ReportAnalysisData;
}

describe("S_ProtecaoSection", () => {
  describe("Cenário A — workspace com seguros (owner)", () => {
    it("renderiza KPI Hero G + KPI B", () => {
      render(<S_ProtecaoSection data={makeData()} />);
      expect(screen.getByTestId("protecao-kpi-hero")).toBeInTheDocument();
      expect(screen.getByTestId("protecao-kpi-g")).toBeInTheDocument();
      // KPI B em faixa "ok" (2.375% entre 1% e 3%)
      expect(screen.getByTestId("protecao-kpi-b")).toHaveTextContent("2.38%");
      expect(screen.getByTestId("protecao-kpi-b-sinal")).toHaveTextContent("Faixa observada");
    });

    it("renderiza tabela de gap por veículo com badge correto", () => {
      render(<S_ProtecaoSection data={makeData()} />);
      expect(screen.getByTestId("protecao-gap-veiculos")).toBeInTheDocument();
      expect(screen.getByTestId("protecao-gap-row-v-1")).toBeInTheDocument();
      expect(screen.getByTestId("protecao-gap-row-v-toro")).toBeInTheDocument();
    });

    it("renderiza chips qualitativos apenas para flag=true", () => {
      render(<S_ProtecaoSection data={makeData()} />);
      // Vida flag=true → renderiza
      expect(screen.getByTestId("protecao-chip-vida")).toBeInTheDocument();
      // Saúde flag=false → NÃO renderiza
      expect(screen.queryByTestId("protecao-chip-saude")).not.toBeInTheDocument();
    });

    it("renderiza tabela de apólices vigentes", () => {
      render(<S_ProtecaoSection data={makeData()} />);
      expect(screen.getByTestId("protecao-apolice-AUTO-1")).toBeInTheDocument();
      expect(screen.getByTestId("protecao-apolice-COMB-1")).toBeInTheDocument();
    });

    it("mostra metadata multi-corretor quando count > 1", () => {
      render(<S_ProtecaoSection data={makeData()} />);
      expect(screen.getByTestId("protecao-multi-corretor")).toBeInTheDocument();
    });

    it("renderiza crosslink para S8 Previdência", () => {
      render(<S_ProtecaoSection data={makeData()} />);
      expect(screen.getByTestId("protecao-crosslink-s8")).toBeInTheDocument();
    });
  });

  describe("Cenário B — workspace sem apólices", () => {
    it("retorna null quando protecao_patrimonial=null", () => {
      const { container } = render(
        <S_ProtecaoSection data={{ protecao_patrimonial: null } as ReportAnalysisData} />,
      );
      expect(container.firstChild).toBeNull();
    });

    it("retorna null quando protecao_patrimonial=undefined", () => {
      const { container } = render(
        <S_ProtecaoSection data={{} as ReportAnalysisData} />,
      );
      expect(container.firstChild).toBeNull();
    });
  });

  describe("Cenário C — combinada multi-bem (Porto Toro+casa)", () => {
    it("apólice combinada com bens_count=2 aparece com 2 tipos_bem", () => {
      render(<S_ProtecaoSection data={makeData()} />);
      const combRow = screen.getByTestId("protecao-apolice-COMB-1");
      expect(combRow).toHaveTextContent("imovel");
      expect(combRow).toHaveTextContent("veiculo");
    });
  });

  describe("Empty states (degradação)", () => {
    it("mostra placeholder quando bens_com_gap_cobertura vazio (FIPE pendente)", () => {
      const data = makeData({
        protecao_patrimonial: makeProtecao({ bens_com_gap_cobertura: [] }),
      });
      render(<S_ProtecaoSection data={data} />);
      expect(screen.getByTestId("protecao-gap-empty")).toBeInTheDocument();
    });

    it("não renderiza chips qualitativo quando todas as flags=false", () => {
      const data = makeData({
        protecao_patrimonial: makeProtecao({
          gap_qualitativo: [
            { categoria: "vida", flag: false, rationale: "ok" },
            { categoria: "saude", flag: false, rationale: "ok" },
          ],
        }),
      });
      render(<S_ProtecaoSection data={data} />);
      expect(screen.queryByTestId("protecao-gap-qualitativo")).not.toBeInTheDocument();
    });

    it("não renderiza metadata multi-corretor quando count=1", () => {
      const data = makeData({
        protecao_patrimonial: makeProtecao({ corretoras_count: 1 }),
      });
      render(<S_ProtecaoSection data={data} />);
      expect(screen.queryByTestId("protecao-multi-corretor")).not.toBeInTheDocument();
    });
  });

  describe("Faixas Cerbasi (KPI B)", () => {
    it("pct < 1% → sinal atenção", () => {
      const data = makeData({
        protecao_patrimonial: makeProtecao({ pct_renda_anual: "0.005000" }),
      });
      render(<S_ProtecaoSection data={data} />);
      expect(screen.getByTestId("protecao-kpi-b-sinal")).toHaveTextContent("Atenção");
    });

    it("3% < pct ≤ 5% → ok-forte", () => {
      const data = makeData({
        protecao_patrimonial: makeProtecao({ pct_renda_anual: "0.040000" }),
      });
      render(<S_ProtecaoSection data={data} />);
      expect(screen.getByTestId("protecao-kpi-b-sinal")).toHaveTextContent("Bem dimensionado");
    });

    it("pct > 5% → atenção", () => {
      const data = makeData({
        protecao_patrimonial: makeProtecao({ pct_renda_anual: "0.070000" }),
      });
      render(<S_ProtecaoSection data={data} />);
      expect(screen.getByTestId("protecao-kpi-b-sinal")).toHaveTextContent("Atenção");
    });
  });
});

describe("KPI B — escopo declarado (ADR-240 §Emenda 2026-08-08)", () => {
  const escopoParcial = {
    premio_inclui_cadastro_manual: false,
    categorias_somente_no_cadastro: ["vida"],
    veredito_pct_renda_suprimido: true,
  };

  function comEscopoParcial() {
    return {
      protecao_patrimonial: makeProtecao({ escopo_cobertura: escopoParcial }),
    } as ReportAnalysisData;
  }

  it("emite o veredito de faixa quando o escopo documental é completo", () => {
    render(<S_ProtecaoSection data={makeData()} />);
    expect(screen.getByTestId("protecao-kpi-b-sinal")).toBeInTheDocument();
    expect(screen.queryByTestId("protecao-kpi-b-escopo")).not.toBeInTheDocument();
  });

  it("suprime o veredito quando há cobertura fora dos documentos", () => {
    render(<S_ProtecaoSection data={comEscopoParcial()} />);
    expect(screen.queryByTestId("protecao-kpi-b-sinal")).not.toBeInTheDocument();
    expect(screen.getByTestId("protecao-kpi-b-escopo")).toHaveTextContent(/não avaliamos a faixa/);
  });

  it("mantém o valor do KPI visível — suprime o julgamento, não o dado", () => {
    render(<S_ProtecaoSection data={comEscopoParcial()} />);
    expect(screen.getByTestId("protecao-kpi-b")).toHaveTextContent("2.38%");
  });

  it("artifact antigo sem o bloco segue emitindo o veredito", () => {
    const semEscopo = makeProtecao();
    delete semEscopo.escopo_cobertura;
    render(<S_ProtecaoSection data={{ protecao_patrimonial: semEscopo } as ReportAnalysisData} />);
    expect(screen.getByTestId("protecao-kpi-b-sinal")).toBeInTheDocument();
  });
});
