import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Top15AtivosCard, type TopAtivo } from "@/components/report/cards";
import { PERCENTUAL_COM_PONTO } from "../../shared/percentualPtBr";
import type { MotivoBaldeImovel, VereditoBaldeImovel } from "@/types/patrimonio-imovel";

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
    expect(screen.getByText("40,0%")).toBeInTheDocument();
    expect(screen.getByText("30,0%")).toBeInTheDocument();
  });

  it("célula e conclusão formatam o percentual com vírgula decimal (pt-BR)", () => {
    const { container } = render(
      <Top15AtivosCard
        data={{
          top_ativos: [
            ativo({ nome: "Imóvel comercial", pct_carteira: 42.5, valor: 425_000 }),
            ativo({ posicao: 2, nome: "B", pct_carteira: 20.25 }),
            ativo({ posicao: 3, nome: "C", pct_carteira: 10.1 }),
          ],
        }}
      />,
    );
    expect(screen.getByText("42,5%")).toBeInTheDocument();
    expect(screen.getByText(/concentra 42,5% da carteira/)).toBeInTheDocument();
    // 42,5 + 20,25 + 10,1 = 72,85 → 72,9: meio para cima sobre o decimal exibido.
    // `toFixed(1)` dava 72.8 — arredonda o binário, que fica abaixo de 72,85.
    expect(screen.getByText(/top 3 somam 72,9%/)).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
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
      screen.getByText(/Sem ativos de carteira neste período/),
    ).toBeInTheDocument();
  });

  it("renderiza empty state quando data é undefined", () => {
    render(<Top15AtivosCard data={undefined} />);
    expect(
      screen.getByText(/Sem ativos de carteira neste período/),
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

  // ADR-246 — copy enquadra "Carteira" e explicita exclusão de residência
  it("usa título 'Top 15 Ativos da Carteira' (ADR-246)", () => {
    render(<Top15AtivosCard data={{ top_ativos: [ativo()] }} />);
    expect(screen.getByText("Top 15 Ativos da Carteira")).toBeInTheDocument();
  });

  it("renderiza subtítulo explicando exclusão de residência principal", () => {
    render(<Top15AtivosCard data={{ top_ativos: [ativo()] }} />);
    expect(
      screen.getByText(/Não inclui residência principal nem bens de uso pessoal/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Composição Patrimonial/)).toBeInTheDocument();
  });
});

// ADR-444 — imóvel com uso não apurado entra com valor e SEM peso, e nenhuma prescrição
// de diversificação recai sobre o que pode ser a residência.
describe("<Top15AtivosCard /> — imóvel com uso não apurado (ADR-444)", () => {
  const semPeso = (overrides: Partial<TopAtivo> = {}): TopAtivo =>
    ativo({
      nome: "Imóvel com uso não apurado",
      classe: "Imóveis com uso não apurado",
      tipo_origem: "imovel",
      classificacao_imovel: "desconhecido",
      instituicao: "",
      valor: 900_000,
      pct_carteira: null,
      ...overrides,
    });
  const naoApurada = (motivo: MotivoBaldeImovel): VereditoBaldeImovel => ({
    status: "nao_apurado",
    motivo,
    piso: false,
  });
  const comCasaNoTopo = [
    semPeso(),
    ativo({ posicao: 2, nome: "ITSA4", pct_carteira: 40, valor: 200_000 }),
    ativo({ posicao: 3, nome: "Tesouro", pct_carteira: 20, valor: 100_000 }),
  ];

  it("a célula de % do item sem peso mostra '—' e anuncia 'sem % da carteira'", () => {
    render(<Top15AtivosCard data={{ top_ativos: comCasaNoTopo }} />);
    expect(screen.getByText("sem % da carteira")).toBeInTheDocument();
    expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
  });

  it("o subtítulo deixa de prometer que a residência está fora", () => {
    render(<Top15AtivosCard data={{ top_ativos: comCasaNoTopo }} />);
    expect(screen.getByText(/podem incluir a residência principal/)).toBeInTheDocument();
    expect(screen.queryByText(/Não inclui residência principal/)).not.toBeInTheDocument();
  });

  it("o alarme de concentração passa ao maior item com %", () => {
    render(
      <Top15AtivosCard
        data={{ top_ativos: comCasaNoTopo }}
        residencia={naoApurada("nao_classificada")}
      />,
    );
    const insight = screen.getByText(/O maior item é um imóvel com uso não apurado/);
    expect(insight).toHaveTextContent(/Atenção: ITSA4 \(#2\) concentra 40,0%/);
    expect(insight).toHaveTextContent(/os 3 maiores com % somam 60,0%/);
  });

  it.each([
    ["nao_localizada", /não é preciso marcá-lo de novo/],
    ["sem_valor", /Se a família mudou de casa/],
    ["nao_classificada", /Marque qual imóvel é a residência/],
    ["nao_declarada", /se a família mora em imóvel próprio/],
  ] as const)("o CTA segue o motivo %s", (motivo, esperado) => {
    render(
      <Top15AtivosCard data={{ top_ativos: comCasaNoTopo }} residencia={naoApurada(motivo)} />,
    );
    expect(screen.getByText(/O maior item é um imóvel/)).toHaveTextContent(esperado);
  });

  it("em nao_localizada não pede para marcar a residência de novo", () => {
    render(
      <Top15AtivosCard
        data={{ top_ativos: comCasaNoTopo }}
        residencia={naoApurada("nao_localizada")}
      />,
    );
    expect(screen.getByText(/O maior item é um imóvel/)).not.toHaveTextContent(/Marque/);
  });

  it("com piso, desconhecido no #1 acima de 25% não recebe 'considere diversificação'", () => {
    const desconhecidoComPeso = semPeso({ classe: "Imóveis Investimento", pct_carteira: 35 });
    render(
      <Top15AtivosCard
        data={{ top_ativos: [desconhecidoComPeso, ativo({ posicao: 2, pct_carteira: 20 })] }}
        residencia={{ status: "apurado", motivo: null, piso: true }}
      />,
    );
    expect(screen.getByText(/pode ser parte da residência/)).toBeInTheDocument();
    expect(screen.queryByText(/Considere diversificação/)).not.toBeInTheDocument();
  });

  // ADR-420 §D2: sabidamente não-residência, o não classificado fica no lado conservador.
  it("sem piso, desconhecido no #1 acima de 25% mantém o alarme", () => {
    const desconhecidoComPeso = semPeso({ classe: "Imóveis Investimento", pct_carteira: 35 });
    render(
      <Top15AtivosCard
        data={{ top_ativos: [desconhecidoComPeso, ativo({ posicao: 2, pct_carteira: 20 })] }}
        residencia={{ status: "zero_apurado", motivo: null, piso: false }}
      />,
    );
    expect(screen.getByText(/Considere diversificação/)).toBeInTheDocument();
  });

  it("o top 3 soma só itens com %", () => {
    render(
      <Top15AtivosCard
        data={{
          top_ativos: [
            ativo({ pct_carteira: 15 }),
            semPeso({ posicao: 2 }),
            ativo({ posicao: 3, nome: "B", pct_carteira: 12 }),
            ativo({ posicao: 4, nome: "C", pct_carteira: 10 }),
          ],
        }}
      />,
    );
    expect(screen.getByText(/Top 3 somam 37,0% da carteira/)).toBeInTheDocument();
  });
});
