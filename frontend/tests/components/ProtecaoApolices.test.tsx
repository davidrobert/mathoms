/**
 * ProtecaoApolices (A37.l11 · PD-05) — coluna Seguradora renderiza display name
 * do catálogo (`seguradora_nome`), nunca o code cru; artifacts antigos degradam
 * para o code capitalizado.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ProtecaoApolices } from "@/components/report/sections/SProtecao/ProtecaoApolices";
import type { ApoliceResumo, ProtecaoPatrimonialData } from "@/types/protecao";

function apolice(overrides: Partial<ApoliceResumo>): ApoliceResumo {
  return {
    apolice_numero: "AP-1",
    seguradora: "porto",
    seguradora_nome: "Porto Seguro",
    vigencia_inicio: "2026-03-01",
    vigencia_fim: "2027-03-01",
    premio_total_brl: "1500.00",
    bens_count: 1,
    tipos_bem: ["veiculo"],
    ...overrides,
  };
}

function data(overrides: Partial<ProtecaoPatrimonialData>): ProtecaoPatrimonialData {
  return {
    premio_total_anual_brl: "4750.00",
    premio_decomposicao: {},
    pct_renda_anual: "0.023750",
    bens_com_gap_cobertura: [],
    gap_qualitativo: [],
    apolices_vigentes: [],
    apolices_vencendo: [],
    apolices_vencidas: [],
    corretoras_count: 1,
    seguradoras_count: 2,
    ...overrides,
  };
}

describe("ProtecaoApolices", () => {
  it("renderiza display name do catálogo — variantes da mesma cia com UM rótulo", () => {
    render(
      <ProtecaoApolices
        data={data({
          apolices_vigentes: [
            apolice({ apolice_numero: "AUTO-1" }),
            // Variante que o LLM emitiu como `portoseguro` — canonicalizada
            // pelo pipeline para code `porto` + mesmo display name.
            apolice({ apolice_numero: "COMB-2" }),
          ],
        })}
      />,
    );
    const rotulos = screen.getAllByText("Porto Seguro");
    expect(rotulos).toHaveLength(2);
    expect(screen.queryByText("porto")).not.toBeInTheDocument();
    expect(screen.queryByText("portoseguro")).not.toBeInTheDocument();
  });

  it("degrada para code capitalizado em artifact antigo sem seguradora_nome", () => {
    render(
      <ProtecaoApolices
        data={data({
          apolices_vigentes: [
            apolice({
              apolice_numero: "LEG-1",
              seguradora: "tokiomarine",
              seguradora_nome: undefined,
            }),
          ],
        })}
      />,
    );
    expect(screen.getByText("Tokiomarine")).toBeInTheDocument();
    expect(screen.queryByText("tokiomarine")).not.toBeInTheDocument();
  });

  it("snapshot — tabela com display names capitalizados", () => {
    // Snapshot estruturado (não DOM cru): o hook de trailing-whitespace do
    // pre-commit reescreve .snap com texto JSX multi-linha e quebra o match.
    render(
      <ProtecaoApolices
        data={data({
          apolices_vigentes: [
            apolice({
              apolice_numero: "AUTO-1",
              seguradora: "tokiomarine",
              seguradora_nome: "Tokio Marine",
            }),
            apolice({ apolice_numero: "COMB-1" }),
          ],
        })}
      />,
    );
    const rows = screen.getAllByTestId(/^protecao-apolice-/).map((tr) => {
      const cells = Array.from((tr as HTMLTableRowElement).cells);
      return { apolice: cells[0]?.textContent, seguradora: cells[1]?.textContent };
    });
    expect(rows).toMatchSnapshot();
  });
});
