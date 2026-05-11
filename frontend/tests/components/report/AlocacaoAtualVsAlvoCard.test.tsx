import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { AlocacaoAtualVsAlvoCard } from "@/components/report/cards";

const ALVO_BALANCED = {
  renda_fixa_pct: 60,
  acoes_pct: 30,
  imoveis_reits_pct: 5,
  liquidez_usd_pct: 5,
};

describe("<AlocacaoAtualVsAlvoCard />", () => {
  it("retorna null quando não há total nem classes (estado vazio)", () => {
    const { container } = render(
      <AlocacaoAtualVsAlvoCard
        investimentos={{ total: 0, tabela_classes: [] }}
        alocacaoAlvo={undefined}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("mostra CTA para definir alvo quando alocação-alvo ausente", () => {
    render(
      <AlocacaoAtualVsAlvoCard
        investimentos={{
          total: 100_000,
          tabela_classes: [{ categoria: "Renda Fixa", valor: 100_000, pct: 100 }],
        }}
        alocacaoAlvo={undefined}
      />,
    );
    expect(screen.getByText("Sem alvo definido")).toBeInTheDocument();
    expect(screen.getByText(/Defina sua alocação-alvo/)).toBeInTheDocument();
  });

  it("badge 'Carteira alinhada' quando todos os desvios ≤2pp", () => {
    render(
      <AlocacaoAtualVsAlvoCard
        investimentos={{
          total: 100_000,
          tabela_classes: [
            { categoria: "Renda Fixa", valor: 60_500, pct: 60.5 },
            { categoria: "Ações BR", valor: 29_500, pct: 29.5 },
            { categoria: "FIIs", valor: 5_000, pct: 5 },
            { categoria: "Internacional", valor: 5_000, pct: 5 },
          ],
        }}
        alocacaoAlvo={ALVO_BALANCED}
      />,
    );
    expect(screen.getByText("Carteira alinhada")).toBeInTheDocument();
    expect(screen.getByText(/Carteira aderente ao alvo/)).toBeInTheDocument();
  });

  it("badge 'Rebalancear: N classes' quando há desvio >5pp", () => {
    render(
      <AlocacaoAtualVsAlvoCard
        investimentos={{
          total: 100_000,
          tabela_classes: [
            { categoria: "Renda Fixa", valor: 50_000, pct: 50 },
            { categoria: "Ações BR", valor: 40_000, pct: 40 },
            { categoria: "FIIs", valor: 5_000, pct: 5 },
            { categoria: "Internacional", valor: 5_000, pct: 5 },
          ],
        }}
        alocacaoAlvo={ALVO_BALANCED}
      />,
    );
    expect(screen.getByText(/Rebalancear:/)).toBeInTheDocument();
    expect(screen.getByText(/Próximo aporte → Renda Fixa/)).toBeInTheDocument();
  });

  it("usa llmFooter quando disponível (override do determinístico)", () => {
    render(
      <AlocacaoAtualVsAlvoCard
        investimentos={{
          total: 100_000,
          tabela_classes: [{ categoria: "Renda Fixa", valor: 100_000, pct: 100 }],
        }}
        alocacaoAlvo={ALVO_BALANCED}
        llmFooter="Texto editorial vindo do E5N para sobrescrever fallback."
      />,
    );
    expect(
      screen.getByText("Texto editorial vindo do E5N para sobrescrever fallback."),
    ).toBeInTheDocument();
  });

  it("renderiza linha 'Fora do alvo' com nota de rodapé quando há Cripto/Outros", () => {
    render(
      <AlocacaoAtualVsAlvoCard
        investimentos={{
          total: 100_000,
          tabela_classes: [
            { categoria: "Renda Fixa", valor: 60_000, pct: 60 },
            { categoria: "Ações BR", valor: 28_000, pct: 28 },
            { categoria: "FIIs", valor: 4_000, pct: 4 },
            { categoria: "Internacional", valor: 3_000, pct: 3 },
            { categoria: "Cripto", valor: 5_000, pct: 5 },
          ],
        }}
        alocacaoAlvo={ALVO_BALANCED}
      />,
    );
    expect(screen.getAllByText("Fora do alvo").length).toBeGreaterThan(0);
    expect(screen.getByText(/Classes fora do plano/)).toBeInTheDocument();
  });
});
