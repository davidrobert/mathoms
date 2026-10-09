/**
 * Percentual e número em copy pt-BR passam por `formatPercent`/`formatNumber`
 * (COPY_GUIDELINES §4.5–§4.6) — os componentes do relatório que trocaram para o
 * formatador compartilhado e não tinham arquivo de teste. Um arquivo só porque o
 * Vitest custa por arquivo, não por teste.
 *
 * Os demais call-sites da troca têm a asserção no teste do próprio componente.
 */
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";
import { render, screen } from "@testing-library/react";

import { AliquotaDualGauge } from "@/components/report/charts/AliquotaDualGauge";
import { ContrafluxoCard } from "@/components/report/cards/ContrafluxoCard";
import { EndividamentoCard } from "@/components/report/cards/EndividamentoCard";
import { EquilibrioCerbasiCard } from "@/components/report/cards/EquilibrioCerbasiCard";
import { IrpfIrPagoCard } from "@/components/report/cards/IrpfIrPagoCard";
import { IrpfSplitTrabalhoCapitalCard } from "@/components/report/cards/IrpfSplitTrabalhoCapitalCard";
import { ScoreCard } from "@/components/report/ui/ScoreCard";
import type { IrpfKpis } from "@/types/irpf";
import type { EquilibrioCerbasiData } from "@/types/report-analysis";
import { PERCENTUAL_COM_PONTO } from "../../shared/percentualPtBr";

describe("<ContrafluxoCard /> — percentual pt-BR", () => {
  it("subtítulo (2 casas) e tabela de cenários (1 casa) usam vírgula", () => {
    const { container } = render(
      <ContrafluxoCard
        contrafluxo={{
          selic_atual: 10.75,
          cenarios: { base: { selic: 10.5, cdi: 10.4 } },
        }}
        cdi_anual={10.65}
      />,
    );

    expect(screen.getByText("Selic atual: 10,75% a.a. | CDI: 10,65%")).toBeInTheDocument();
    expect(screen.getByText("10,5%")).toBeInTheDocument();
    expect(screen.getByText("10,4%")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
  });
});

describe("<EquilibrioCerbasiCard /> — percentual pt-BR", () => {
  // O produtor arredonda para 1 casa (`equilibrio_cerbasi_analyzer.py`): o número
  // cru interpolado saía "Presente (62.5%)" sem passar por `toFixed` nenhum.
  it("rótulos e aria-label usam vírgula; a largura da barra continua CSS", () => {
    const { container } = render(
      <EquilibrioCerbasiCard
        equilibrio={{ pct_presente: 62.5, pct_futuro: 37.5, classificacao: "Equilibrado" }}
      />,
    );

    expect(screen.getByText("Presente (62,5%)")).toBeInTheDocument();
    expect(screen.getByText("Futuro (37,5%)")).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: "Distribuição do fluxo: 62,5% para o presente, 37,5% para o futuro",
      }),
    ).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
    // `width: 62,5%` é declaração CSS inválida — a barra sumiria.
    const barra = container.querySelector<HTMLElement>('[role="img"] > div');
    expect(barra?.style.width).toBe("62.5%");
  });
});

describe("<EquilibrioCerbasiCard /> — ausente não vira zero (COPY_GUIDELINES §4.3)", () => {
  const AUSENTE = "Sem fluxo de caixa no período para calcular a divisão entre presente e futuro.";

  // Shape que as 6 fixtures E2E carregavam: sem `pct_*` e com `presente`/`futuro` em
  // fração. Nenhum produtor emitiu esse shape, e o card afirmava "Presente (0,0%)",
  // desenhava barras de largura 0 e imprimia o float cru "0.55". O produtor omite a
  // divisão quando não há base — o mesmo caminho.
  it("sem pct_presente/pct_futuro declara ausência em vez de afirmar 0,0%", () => {
    const equilibrio = {
      presente: 0.55,
      futuro: 0.3,
      padrao_vida: 0.15,
    } as unknown as EquilibrioCerbasiData;
    const { container } = render(<EquilibrioCerbasiCard equilibrio={equilibrio} />);

    expect(container.textContent).not.toMatch(/0,0\s?%/);
    expect(container.textContent).not.toContain("0.55");
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText(AUSENTE)).toBeInTheDocument();
  });

  // Os dois pcts dividem o mesmo todo: com um só, o outro sairia "0,0%" inventado.
  it("um pct sem o par também é ausência", () => {
    const { container } = render(<EquilibrioCerbasiCard equilibrio={{ pct_presente: 62.5 }} />);

    expect(container.textContent).not.toMatch(/0,0\s?%/);
    expect(screen.getByText(AUSENTE)).toBeInTheDocument();
  });

  it("zero real continua sendo publicado como zero", () => {
    render(
      <EquilibrioCerbasiCard
        equilibrio={{ pct_presente: 0, pct_futuro: 100, classificacao: "Investidor" }}
      />,
    );

    expect(screen.getByText("Presente (0,0%)")).toBeInTheDocument();
    expect(screen.getByText("Futuro (100,0%)")).toBeInTheDocument();
    expect(screen.queryByText(AUSENTE)).not.toBeInTheDocument();
  });
});

// Os empates abaixo são de propósito: `toFixed` arredonda o binário exato e dava
// o dígito de baixo (12.35 é 12.3499… em double). O relatório inteiro passou a
// arredondar o decimal exibido (COPY_GUIDELINES §4.5).
const IRPF_KPIS: IrpfKpis = {
  ano_base: 2024,
  anos_disponiveis: [2023, 2024],
  renda_anual_familiar_brl: "180000.00",
  renda_liquida_familiar_brl: "144000.00",
  ir_pago_total_brl: "24000.00",
  aliquota_sobre_tributavel_pct: "12.35",
  aliquota_sobre_total_pct: "9.85",
  pgbl_capacidade_dedutivel_brl: "5400.00",
  pgbl_status: "capacidade_disponivel",
  pgbl_aportado_brl: "10000.00",
  pgbl_teto_brl: "21600.00",
  split_trabalho_brl: "120000.00",
  split_capital_brl: "60000.00",
  evolucao_renda_anos: { "2023": "160000.00", "2024": "180000.00" },
};

describe("IRPF — alíquota de 2 casas no card e de 1 casa no gauge", () => {
  // O produtor serializa a alíquota com 2 casas; o gauge mostra 1. Com `toFixed`,
  // o gauge dizia "12,3%" ao lado do "12,35%" do card de IR pago.
  it("o card de IR pago e o gauge arredondam a mesma alíquota no mesmo sentido", () => {
    const { container } = render(
      <>
        <IrpfIrPagoCard kpis={IRPF_KPIS} />
        <AliquotaDualGauge kpis={IRPF_KPIS} />
      </>,
    );

    expect(screen.getByText("12,35%")).toBeInTheDocument();
    expect(screen.getByText("9,85%")).toBeInTheDocument();
    expect(screen.getByText("12,4%")).toBeInTheDocument();
    expect(screen.getByText("9,9%")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
  });

  it("o split trabalho × capital usa vírgula", () => {
    const { container } = render(<IrpfSplitTrabalhoCapitalCard kpis={IRPF_KPIS} />);

    expect(screen.getByText("66,7% do total")).toBeInTheDocument();
    expect(screen.getByText("33,3% do total")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
  });
});

describe("<EndividamentoCard /> — percentual pt-BR", () => {
  it("percentual do patrimônio e juros ao ano usam vírgula", () => {
    const { container } = render(
      <EndividamentoCard
        endividamento={{
          total_dividas: 50000,
          percentual_patrimonio: 12.35,
          dividas: [
            {
              descricao: "Financiamento imobiliário",
              saldo_devedor: 50000,
              taxa_juros_aa: 13.65,
              fontes: { saldo_devedor: "declarado", taxa_juros_aa: "declarado" },
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("12,4%")).toBeInTheDocument();
    expect(screen.getByText("13,65% a.a.")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
  });
});

describe("<ScoreCard /> — número pt-BR", () => {
  // jsdom não implementa canvas e loga erro a cada `getContext`. O gauge já
  // trata contexto nulo; o stub devolve o mesmo `null` sem sujar o log.
  let getContext: MockInstance<HTMLCanvasElement["getContext"]>;
  beforeEach(() => {
    getContext = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  });
  afterEach(() => getContext.mockRestore());

  it("nota, gauge, breakdown e contribuição usam vírgula", () => {
    render(
      <ScoreCard
        value={7.35}
        classe="Bom"
        breakdown={[
          { dimensao: "Liquidez", valor: 8.5, max: 10, peso: 0.25, contribuicao: 2.675 },
        ]}
      />,
    );

    expect(screen.getByText("7,4 — Bom")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Score 7,4 de 10, classificação BOM" }),
    ).toBeInTheDocument();
    expect(screen.getByText("8,5")).toBeInTheDocument();
    expect(screen.getByText("2,68")).toBeInTheDocument();
  });
});
