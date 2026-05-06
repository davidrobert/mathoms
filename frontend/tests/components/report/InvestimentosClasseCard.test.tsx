import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { InvestimentosClasseCard } from "@/components/report/cards";

describe("<InvestimentosClasseCard />", () => {
  it("renderiza nome da classe na coluna Classe (contrato backend = `categoria`)", () => {
    // Backend (pipeline/domain/services/investimentos_classes_analyzer.py) emite
    // `categoria`. Regressão histórica: frontend lia `classe`, deixando a coluna vazia.
    render(
      <InvestimentosClasseCard
        investimentos={{
          total: 4_085_100.68,
          tabela_classes: [
            { categoria: "Imóveis Investimento", valor: 3_140_698.27, pct: 76.9 },
            { categoria: "Renda Fixa", valor: 944_402.41, pct: 23.1 },
          ],
        }}
      />,
    );
    expect(screen.getByText("Imóveis Investimento")).toBeInTheDocument();
    expect(screen.getByText("Renda Fixa")).toBeInTheDocument();
    expect(screen.getByText("76.9%")).toBeInTheDocument();
    expect(screen.getByText("23.1%")).toBeInTheDocument();
  });

  it("mostra fallback quando tabela_classes está vazia", () => {
    render(<InvestimentosClasseCard investimentos={{ total: 0, tabela_classes: [] }} />);
    expect(
      screen.getByText(/Sem posições de investimento detalhadas neste período\./),
    ).toBeInTheDocument();
  });
});
