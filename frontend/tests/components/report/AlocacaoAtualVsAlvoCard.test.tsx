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

  describe("prescrição suprimida pelo produtor (ADR-394 §Emenda · ADR-400)", () => {
    const DESALINHADA: AlocacaoDerived["comparaveis"] = [
      { classe: "renda_fixa", valor_brl: 50_000, componentes: ["Renda Fixa"], atual_pct: 50, alvo_pct: 60, desvio_pp: -10, severity: "rebalancear" },
      { classe: "acoes_br", valor_brl: 40_000, componentes: ["Ações BR"], atual_pct: 40, alvo_pct: 30, desvio_pp: 10, severity: "rebalancear" },
      { classe: "fiis", valor_brl: 6_000, componentes: ["FIIs"], atual_pct: 6, alvo_pct: 3, desvio_pp: 3, severity: "atencao" },
      { classe: "acoes_int", valor_brl: 4_000, componentes: ["Internacional"], atual_pct: 4, alvo_pct: 7, desvio_pp: -3, severity: "atencao" },
      { classe: "fora_alvo", valor_brl: 0, componentes: [], atual_pct: 0, alvo_pct: 0, desvio_pp: 0, severity: "alinhado" },
    ];

    function suprimida(motivo: string, overrides: Partial<AlocacaoDerived> = {}) {
      return makeDerived({
        carteira_liquida_brl: 100_000,
        has_alvo: true,
        desvio_max_pct: null,
        next_aporte_classe: null,
        comparaveis: DESALINHADA,
        motivo_supressao: motivo,
        ...overrides,
      });
    }

    function expectSemPrescricao(): void {
      const prescricoes = [
        /Rebalancear/i,
        /Atenção/i,
        /Carteira alinhada|aderente/i,
        /Próximo aporte →/,
        /Maior desvio/i,
        /Rebalanceamento/i,
      ];
      for (const prescricao of prescricoes) {
        expect(screen.queryAllByText(prescricao), String(prescricao)).toHaveLength(0);
      }
    }

    it("cobertura incompleta: nem badge nem rodapé prescrevem, e a causa é declarada", () => {
      render(<AlocacaoAtualVsAlvoCard derived={suprimida("cobertura_incompleta: conjuge")} />);
      expectSemPrescricao();
      expect(screen.getByText("Sem indicação de classe")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Não indicamos a classe do próximo aporte: os investimentos do cônjuge não foram apurados.",
        ),
      ).toBeInTheDocument();
    });

    it("cobertura incompleta: o KPI declara que o total não é total", () => {
      render(<AlocacaoAtualVsAlvoCard derived={suprimida("cobertura_incompleta: conjuge")} />);
      expect(
        screen.getByText("Este total não inclui os investimentos do cônjuge."),
      ).toBeInTheDocument();
    });

    it("incerteza de classe parcial (2–10%): desvio máximo fica no payload, fora do card", () => {
      render(
        <AlocacaoAtualVsAlvoCard
          derived={suprimida("nao_classificado: 5.1% da carteira", { desvio_max_pct: 10 })}
        />,
      );
      expectSemPrescricao();
      expect(
        screen.getByText(
          "Não indicamos a classe do próximo aporte: parte da carteira está sem classe definida.",
        ),
      ).toBeInTheDocument();
      expect(screen.queryByText(/Este total não inclui/)).toBeNull();
    });

    it("carteira dentro de 2pp com cobertura incompleta não vira elogio", () => {
      render(
        <AlocacaoAtualVsAlvoCard
          derived={suprimida("cobertura_incompleta: conjuge", { comparaveis: BALANCED.comparaveis })}
        />,
      );
      expectSemPrescricao();
    });

    it("a descrição sobrevive: a tabela por classe continua com atual, alvo e desvio", () => {
      render(<AlocacaoAtualVsAlvoCard derived={suprimida("balde_negativo: veiculos")} />);
      expect(screen.getAllByText("Renda Fixa").length).toBeGreaterThan(0);
      expect(screen.getByRole("columnheader", { name: "Desvio (pp)" })).toBeInTheDocument();
      expect(screen.getAllByText("-10,0").length).toBeGreaterThan(0);
    });

    // A cor e o ícone da linha são o veredito de magnitude: nenhum token semântico
    // sobra no card (a linha de caixa sem excesso também não usa nenhum).
    it.each([
      "cobertura_incompleta: conjuge",
      "nao_classificado: 5.1% da carteira",
    ])("linhas sem veredito de cor nem ícone: %s", (motivo) => {
      const { container } = render(<AlocacaoAtualVsAlvoCard derived={suprimida(motivo)} />);
      expect(container.innerHTML).not.toMatch(/--semantic-/);
      expect(container.querySelector(".lucide-circle-x, .lucide-triangle-alert, .lucide-circle-check")).toBeNull();
    });

    it("texto do E5N gravado antes do fix não volta a atribuir a causa errada", () => {
      render(
        <AlocacaoAtualVsAlvoCard
          derived={suprimida("cobertura_incompleta: conjuge")}
          llmFooter="Renda Fixa 50%→60%. Próximo aporte não indicado: parte da carteira sem classe definida. Rebalanceamento anual."
        />,
      );
      expect(screen.queryByText(/sem classe definida/)).toBeNull();
      expect(screen.getByText(/os investimentos do cônjuge não foram apurados/)).toBeInTheDocument();
    });

    it("sem alvo, o motivo não disputa o badge: o CTA de definir alvo vence", () => {
      render(
        <AlocacaoAtualVsAlvoCard
          derived={suprimida("cobertura_incompleta: conjuge", { has_alvo: false })}
        />,
      );
      expect(screen.getByText("Sem alvo definido")).toBeInTheDocument();
      expect(screen.getByText(/Defina sua alocação-alvo/)).toBeInTheDocument();
    });
  });

  it("motivo_supressao null (payload comum) mantém a prescrição de hoje", () => {
    render(
      <AlocacaoAtualVsAlvoCard
        derived={makeDerived({
          carteira_liquida_brl: 100_000,
          has_alvo: true,
          desvio_max_pct: 10,
          next_aporte_classe: "renda_fixa",
          motivo_supressao: null,
          comparaveis: [
            { classe: "renda_fixa", valor_brl: 50_000, componentes: ["Renda Fixa"], atual_pct: 50, alvo_pct: 60, desvio_pp: -10, severity: "rebalancear" },
            { classe: "acoes_br", valor_brl: 50_000, componentes: ["Ações BR"], atual_pct: 50, alvo_pct: 40, desvio_pp: 10, severity: "rebalancear" },
          ],
        })}
      />,
    );
    expect(screen.getByText("Rebalancear: 2 classes")).toBeInTheDocument();
    expect(screen.getByText(/Próximo aporte → Renda Fixa/)).toBeInTheDocument();
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
