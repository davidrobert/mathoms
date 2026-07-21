/**
 * A37.l10 (PD-09) — StressScenarioCard: guard do parágrafo "Leitura:" +
 * copy para delta negativo de aporte.
 *
 * Em produção o cenário SEMPRE reduz a capacidade de aporte
 * (`CenariosConjugeAnalyzer`: aporte = aporte_base × fator_reduzido, fator < 1),
 * então o delta de aporte é negativo — o código anterior só emitia fragmentos
 * com delta > 0 e renderizava "Leitura: . Reforce…".
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { StressScenarioCard } from "@/components/report/cards/StressScenarioCard";

function cenariosNegativos() {
  return {
    labels: ["Sem renda do cônjuge"],
    aportes: [12000],
    prazos_if: [19.5],
    anos_if: [2046],
    premissas: { aporte_base: 20000 },
  };
}

describe("StressScenarioCard — Leitura (A37.l10 PD-09)", () => {
  it("delta de aporte negativo emite frase própria (regressão: 'Leitura: .')", () => {
    render(
      <StressScenarioCard
        cenarios={cenariosNegativos()}
        goals={{ if_prazo_anos: 14.2, if_ano: 2040 }}
      />,
    );
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura).not.toBeNull();
    expect(leitura?.textContent).toContain(
      "reduz a capacidade de aporte em 40%",
    );
    expect(leitura?.textContent).not.toMatch(/Leitura:\s*\./);
    expect(leitura?.textContent).toMatchSnapshot();
  });

  it("delta negativo sem prazo base ainda tem frase (payload real do dogfood)", () => {
    render(<StressScenarioCard cenarios={cenariosNegativos()} goals={undefined} />);
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura?.textContent).toContain("reduz a capacidade de aporte em 40%");
    expect(leitura?.textContent).not.toMatch(/Leitura:\s*\./);
  });

  it("delta positivo preserva a copy existente com joiner 'ou'", () => {
    render(
      <StressScenarioCard
        cenarios={{
          labels: ["Sem renda do cônjuge"],
          aportes: [18500],
          prazos_if: [19.5],
          anos_if: [2046],
          premissas: { aporte_base: 12000 },
        }}
        goals={{ if_prazo_anos: 14.2, if_ano: 2040 }}
      />,
    );
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura?.textContent).toContain("exige aporte 54% maior");
    expect(leitura?.textContent).toContain("ou estende a IF em 5a 4m");
  });

  it("só delta de prazo → frase com sujeito ('o cenário estende…')", () => {
    render(
      <StressScenarioCard
        cenarios={{
          labels: ["Sem renda do cônjuge"],
          aportes: [12000],
          prazos_if: [19.5],
          anos_if: [2046],
        }}
        goals={{ if_prazo_anos: 14.2, if_ano: 2040 }}
      />,
    );
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura?.textContent).toContain("o cenário estende a IF em 5a 4m");
  });

  it("sem nenhum fragmento (deltas zero) não renderiza 'Leitura:'", () => {
    render(
      <StressScenarioCard
        cenarios={{
          labels: ["Sem renda do cônjuge"],
          aportes: [12000],
          prazos_if: [14.2],
          anos_if: [2040],
          premissas: { aporte_base: 12000 },
        }}
        goals={{ if_prazo_anos: 14.2, if_ano: 2040 }}
      />,
    );
    expect(screen.queryByText(/Leitura:/)).toBeNull();
  });

  it("prazo estresse 999 (não atinge) não vira delta nem fragmento de prazo", () => {
    render(
      <StressScenarioCard
        cenarios={{
          labels: ["Sem renda do cônjuge"],
          aportes: [12000],
          prazos_if: [999],
          anos_if: [3025],
          premissas: { aporte_base: 20000 },
        }}
        goals={{ if_prazo_anos: 14.2, if_ano: 2040 }}
      />,
    );
    expect(screen.getByText("Não atinge")).toBeInTheDocument();
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura?.textContent).toContain("reduz a capacidade de aporte em 40%");
    expect(leitura?.textContent).not.toContain("estende a IF");
  });
});
