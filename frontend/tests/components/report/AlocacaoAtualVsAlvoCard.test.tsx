import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  AlocacaoAtualVsAlvoCard,
  type AlocacaoDerived,
} from "@/components/report/cards";

const NO_CAIXA: AlocacaoDerived["caixa"] = {
  valor_brl: 0,
  atual_pct_patrimonio: 0,
  alvo_pct: null,
  excesso_pp: null,
  sinal_excesso: false,
};

function makeDerived(overrides: Partial<AlocacaoDerived> = {}): AlocacaoDerived {
  return {
    comparaveis: [],
    desvio_max_pct: null,
    next_aporte_classe: null,
    carteira_liquida_brl: 0,
    caixa: NO_CAIXA,
    imoveis_fisicos_brl: 0,
    has_alvo: false,
    rf_comparacao: "agregada",
    alvo_renormalizado_defensivo: false,
    ...overrides,
  };
}

const BALANCED: AlocacaoDerived = makeDerived({
  carteira_liquida_brl: 100_000,
  has_alvo: true,
  desvio_max_pct: 1,
  comparaveis: [
    { classe: "renda_fixa", valor_brl: 61_000, componentes: ["Renda Fixa"], atual_pct: 61, alvo_pct: 60, desvio_pp: 1, severity: "alinhado" },
    { classe: "acoes_br", valor_brl: 29_000, componentes: ["Ações BR"], atual_pct: 29, alvo_pct: 30, desvio_pp: -1, severity: "alinhado" },
    { classe: "acoes_int", valor_brl: 5_000, componentes: ["Internacional"], atual_pct: 5, alvo_pct: 5, desvio_pp: 0, severity: "alinhado" },
    { classe: "fiis", valor_brl: 5_000, componentes: ["FIIs"], atual_pct: 5, alvo_pct: 5, desvio_pp: 0, severity: "alinhado" },
    { classe: "fora_alvo", valor_brl: 0, componentes: [], atual_pct: 0, alvo_pct: 0, desvio_pp: 0, severity: "alinhado" },
  ],
});

describe("<AlocacaoAtualVsAlvoCard />", () => {
  it("retorna null quando derived ausente (payload E5 pré-PR6)", () => {
    const { container } = render(<AlocacaoAtualVsAlvoCard derived={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it("retorna null quando carteira e caixa são zero (estado vazio)", () => {
    const { container } = render(<AlocacaoAtualVsAlvoCard derived={makeDerived()} />);
    expect(container.firstChild).toBeNull();
  });

  it("mostra CTA para definir alvo quando has_alvo=false", () => {
    render(
      <AlocacaoAtualVsAlvoCard
        derived={makeDerived({
          carteira_liquida_brl: 100_000,
          has_alvo: false,
          comparaveis: [
            { classe: "renda_fixa", valor_brl: 100_000, componentes: ["Renda Fixa"], atual_pct: 100, alvo_pct: null, desvio_pp: null, severity: "neutro" },
          ],
        })}
      />,
    );
    expect(screen.getByText("Sem alvo definido")).toBeInTheDocument();
    expect(screen.getByText(/Defina sua alocação-alvo/)).toBeInTheDocument();
  });

  it("badge 'Carteira alinhada' quando todos os desvios ≤2pp", () => {
    render(<AlocacaoAtualVsAlvoCard derived={BALANCED} />);
    expect(screen.getByText("Carteira alinhada")).toBeInTheDocument();
    expect(screen.getByText(/Carteira aderente ao alvo/)).toBeInTheDocument();
  });

  it("badge 'Rebalancear: N classes' + próximo aporte quando há desvio >5pp", () => {
    render(
      <AlocacaoAtualVsAlvoCard
        derived={makeDerived({
          carteira_liquida_brl: 100_000,
          has_alvo: true,
          desvio_max_pct: 10,
          next_aporte_classe: "renda_fixa",
          comparaveis: [
            { classe: "renda_fixa", valor_brl: 50_000, componentes: ["Renda Fixa"], atual_pct: 50, alvo_pct: 60, desvio_pp: -10, severity: "rebalancear" },
            { classe: "acoes_br", valor_brl: 40_000, componentes: ["Ações BR"], atual_pct: 40, alvo_pct: 30, desvio_pp: 10, severity: "rebalancear" },
            { classe: "acoes_int", valor_brl: 5_000, componentes: ["Internacional"], atual_pct: 5, alvo_pct: 5, desvio_pp: 0, severity: "alinhado" },
            { classe: "fiis", valor_brl: 5_000, componentes: ["FIIs"], atual_pct: 5, alvo_pct: 5, desvio_pp: 0, severity: "alinhado" },
            { classe: "fora_alvo", valor_brl: 0, componentes: [], atual_pct: 0, alvo_pct: 0, desvio_pp: 0, severity: "alinhado" },
          ],
        })}
      />,
    );
    expect(screen.getByText(/Rebalancear:/)).toBeInTheDocument();
    expect(screen.getByText(/Próximo aporte → Renda Fixa/)).toBeInTheDocument();
  });

  it("usa llmFooter quando disponível (override do determinístico)", () => {
    render(
      <AlocacaoAtualVsAlvoCard
        derived={BALANCED}
        llmFooter="Texto editorial vindo do E5N para sobrescrever fallback."
      />,
    );
    expect(
      screen.getByText("Texto editorial vindo do E5N para sobrescrever fallback."),
    ).toBeInTheDocument();
  });

  it("renderiza linha 'Fora do alvo' com nota de rodapé quando fora_alvo > 0", () => {
    render(
      <AlocacaoAtualVsAlvoCard
        derived={makeDerived({
          carteira_liquida_brl: 100_000,
          has_alvo: true,
          comparaveis: [
            { classe: "renda_fixa", valor_brl: 60_000, componentes: ["Renda Fixa"], atual_pct: 60, alvo_pct: 60, desvio_pp: 0, severity: "alinhado" },
            { classe: "fora_alvo", valor_brl: 5_000, componentes: ["Cripto"], atual_pct: 5, alvo_pct: 0, desvio_pp: 5, severity: "atencao" },
            { classe: "acoes_br", valor_brl: 28_000, componentes: ["Ações BR"], atual_pct: 28, alvo_pct: 30, desvio_pp: -2, severity: "alinhado" },
            { classe: "acoes_int", valor_brl: 3_000, componentes: ["Internacional"], atual_pct: 3, alvo_pct: 5, desvio_pp: -2, severity: "alinhado" },
            { classe: "fiis", valor_brl: 4_000, componentes: ["FIIs"], atual_pct: 4, alvo_pct: 5, desvio_pp: -1, severity: "alinhado" },
          ],
        })}
      />,
    );
    expect(screen.getAllByText("Fora do alvo").length).toBeGreaterThan(0);
    expect(screen.getByText(/Classes fora do plano/)).toBeInTheDocument();
  });

  it("exibe linha de caixa com sinal de excesso quando sinal_excesso=true", () => {
    render(
      <AlocacaoAtualVsAlvoCard
        derived={makeDerived({
          carteira_liquida_brl: 100_000,
          has_alvo: true,
          comparaveis: BALANCED.comparaveis,
          caixa: {
            valor_brl: 30_000,
            atual_pct_patrimonio: 23.08,
            alvo_pct: 10,
            excesso_pp: 13.08,
            sinal_excesso: true,
          },
        })}
      />,
    );
    expect(screen.getByText(/Reserva \(Caixa\)/)).toBeInTheDocument();
    expect(screen.getByText(/Excesso de caixa/)).toBeInTheDocument();
  });
});
