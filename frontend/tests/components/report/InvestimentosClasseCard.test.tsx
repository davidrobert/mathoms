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

  it("declara a base do percentual no header e decompõe total investido (A37.l9)", () => {
    render(
      <InvestimentosClasseCard
        investimentos={{
          total: 200_000,
          total_financeiro: 80_000,
          total_imoveis_investimento: 120_000,
          tabela_classes: [
            {
              categoria: "Imóveis Investimento",
              valor: 120_000,
              pct: 60.0,
              pct_carteira_financeira: null,
            },
            { categoria: "Renda Fixa", valor: 80_000, pct: 40.0, pct_carteira_financeira: 100.0 },
          ],
        }}
      />,
    );
    expect(screen.getByText("% do total investido")).toBeInTheDocument();
    expect(
      screen.getByText(/Base: total investido = carteira financeira/),
    ).toBeInTheDocument();
  });

  it("omite a decomposição quando payload antigo não traz os subtotais", () => {
    render(
      <InvestimentosClasseCard
        investimentos={{
          total: 100_000,
          tabela_classes: [{ categoria: "Renda Fixa", valor: 100_000, pct: 100.0 }],
        }}
      />,
    );
    expect(screen.queryByText(/Base: total investido/)).not.toBeInTheDocument();
  });
});
