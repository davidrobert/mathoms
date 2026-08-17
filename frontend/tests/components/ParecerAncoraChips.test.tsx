import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ParecerAncoraChips } from "@/components/report/sections/SParecer/ParecerAncoraChips";
import type { Ancora } from "@/lib/api";

function ancora(overrides: Partial<Ancora>): Ancora {
  return {
    path: "$.passive_income.renda_passiva_anual_brl",
    rotulo: "renda_passiva_anual",
    valor_renderizado: "R$ 120.000,00",
    label: null,
    ...overrides,
  };
}

describe("ParecerAncoraChips — rótulo por folha (A40.l49)", () => {
  it("usa ancora.label quando o finalize carimbou o mapa", () => {
    render(
      <ParecerAncoraChips
        ancoras={[
          ancora({ label: "Renda passiva anual" }),
          ancora({
            path: "$.passive_income.renda_ativa_pj_excluida_brl",
            rotulo: "renda_ativa_pj_excluida",
            label: "Renda ativa PJ excluída",
            valor_renderizado: "R$ 80.000,00",
          }),
        ]}
      />,
    );
    expect(screen.getByText("Renda passiva anual")).toBeInTheDocument();
    expect(screen.getByText("Renda ativa PJ excluída")).toBeInTheDocument();
    expect(screen.queryByText("Renda passiva")).not.toBeInTheDocument();
  });

  it("cai no fallback do root quando label está ausente (parecer persistido)", () => {
    render(
      <ParecerAncoraChips
        ancoras={[ancora({ rotulo: "passive_income", label: null })]}
      />,
    );
    expect(screen.getByText("Renda passiva")).toBeInTheDocument();
  });
});
