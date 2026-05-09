import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Top15AtivosCard, type TopAtivo } from "@/components/report/cards";

function ativo(overrides: Partial<TopAtivo> = {}): TopAtivo {
  return {
    posicao: 1,
    nome: "Tesouro IPCA+ 2045",
    classe: "Renda Fixa",
    membro: "david",
    instituicao: "Btg",
    valor: 300_000,
    pct_carteira: 30.0,
    tipo_origem: "investimento",
    ...overrides,
  };
}

describe("<Top15AtivosCard />", () => {
  it("renderiza linha de cada ativo com nome, classe, valor e %", () => {
    render(
      <Top15AtivosCard
        data={{
          top_ativos: [
            ativo({ posicao: 1, nome: "ITSA4", valor: 200_000, pct_carteira: 40 }),
            ativo({
              posicao: 2,
              nome: "Tesouro IPCA",
              classe: "Renda Fixa",
              valor: 150_000,
              pct_carteira: 30,
            }),
          ],
        }}
      />,
    );
    expect(screen.getByText("ITSA4")).toBeInTheDocument();
    expect(screen.getByText("Tesouro IPCA")).toBeInTheDocument();
    expect(screen.getAllByText(/Renda Fixa/)).not.toHaveLength(0);
    expect(screen.getByText("40.0%")).toBeInTheDocument();
    expect(screen.getByText("30.0%")).toBeInTheDocument();
  });

  it("renderiza membro como veio do backend (display name de family_members.nome_curto)", () => {
    render(
      <Top15AtivosCard
        data={{ top_ativos: [ativo({ membro: "Mariana" })] }}
      />,
    );
    expect(screen.getByText("Mariana")).toBeInTheDocument();
  });

  it("renderiza '—' quando membro vem vazio (workspace sem cônjuge)", () => {
    render(
      <Top15AtivosCard
        data={{ top_ativos: [ativo({ membro: "" })] }}
      />,
    );
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("conclusion alerta quando top1 concentra > 25% (concentração de risco)", () => {
    render(
      <Top15AtivosCard
        data={{
          top_ativos: [
            ativo({ nome: "Imóvel comercial", pct_carteira: 60, valor: 600_000 }),
            ativo({ posicao: 2, nome: "B", pct_carteira: 25 }),
            ativo({ posicao: 3, nome: "C", pct_carteira: 10 }),
          ],
        }}
      />,
    );
    expect(screen.getByText(/Atenção/)).toBeInTheDocument();
    expect(screen.getByText(/concentra/)).toBeInTheDocument();
  });

  it("conclusion neutra quando concentração não é alarmante", () => {
    render(
      <Top15AtivosCard
        data={{
          top_ativos: [
            ativo({ pct_carteira: 15 }),
            ativo({ posicao: 2, nome: "B", pct_carteira: 12 }),
            ativo({ posicao: 3, nome: "C", pct_carteira: 10 }),
          ],
        }}
      />,
    );
    expect(screen.getByText(/é o maior ativo individual/)).toBeInTheDocument();
    expect(screen.queryByText(/Atenção/)).not.toBeInTheDocument();
  });

  it("renderiza empty state quando top_ativos é vazio", () => {
    render(<Top15AtivosCard data={{ top_ativos: [] }} />);
    expect(
      screen.getByText(/Sem ativos individualizados neste período/),
    ).toBeInTheDocument();
  });

  it("renderiza empty state quando data é undefined", () => {
    render(<Top15AtivosCard data={undefined} />);
    expect(
      screen.getByText(/Sem ativos individualizados neste período/),
    ).toBeInTheDocument();
  });

  it("não inclui mais o bug 'R$ 0,00 de ' do antigo NarrativeChartCard", () => {
    render(
      <Top15AtivosCard data={{ top_ativos: [ativo()] }} />,
    );
    // Conclusão é derivada client-side a partir dos dados — nunca herda
    // string upstream com placeholders vazios.
    expect(screen.queryByText(/R\$ 0,00 de/)).not.toBeInTheDocument();
  });
});
