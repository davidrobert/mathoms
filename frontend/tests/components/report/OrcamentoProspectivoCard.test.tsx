import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { OrcamentoProspectivoCard } from "@/components/report/cards/OrcamentoProspectivoCard";
import type {
  FluxoCaixaSummary,
  FluxoJanelaInterativa,
  FluxoJanelas,
  FluxoPeriodoInterativo,
} from "@/types/report-analysis";

function windowFixture(
  janela: FluxoPeriodoInterativo,
  overrides: Partial<FluxoJanelaInterativa> = {},
): FluxoJanelaInterativa {
  return {
    janela,
    janela_meses: 12,
    mes_inicio: "2025-01",
    mes_fim: "2025-12",
    receita_total: 1_104_000,
    despesa_total: 972_000,
    receita_mensal_media: 92_000,
    despesa_mensal_media: 81_000,
    despesa_consumo_mensal_media: 69_000,
    transferencia_patrimonial_mensal: 12_000,
    tabela_receitas_por_fonte_mensal: [],
    tabela_receita_por_natureza_mensal: [],
    tabela_consumo_por_categoria_mensal: [
      {
        categoria: "moradia",
        total: 579_600,
        mensal_media: 48_300,
        participacao_pct: 70,
        participacao_acumulada_pct: 70,
      },
      {
        categoria: "alimentacao",
        total: 248_400,
        mensal_media: 20_700,
        participacao_pct: 30,
        participacao_acumulada_pct: 100,
      },
    ],
    ...overrides,
  };
}

function fluxoFixture(): FluxoCaixaSummary {
  const three = windowFixture("3m", {
    janela_meses: 3,
    mes_inicio: "2025-08",
    mes_fim: "2025-12",
    despesa_mensal_media: 24_003,
    despesa_consumo_mensal_media: 21_003,
    transferencia_patrimonial_mensal: 3_000,
    tabela_consumo_por_categoria_mensal: [
      {
        categoria: "lazer_viagens",
        total: 42_006,
        mensal_media: 14_002,
        participacao_pct: 66.67,
        participacao_acumulada_pct: 66.67,
      },
      {
        categoria: "nao_identificado",
        total: 21_003,
        mensal_media: 7_001,
        participacao_pct: 33.33,
        participacao_acumulada_pct: 100,
      },
    ],
  });
  const janelas: FluxoJanelas = {
    "3m": three,
    "6m": windowFixture("6m"),
    "12m": windowFixture("12m"),
    ytd: windowFixture("ytd"),
  };
  return { janelas };
}

describe("<OrcamentoProspectivoCard />", () => {
  it("renderiza referência ex-aporte e Pareto emitido pelo E5", () => {
    render(<OrcamentoProspectivoCard fluxo={fluxoFixture()} />);

    expect(
      screen.getByRole("heading", { name: "Consumo por Categoria" }),
    ).toBeVisible();
    expect(screen.getByTestId("consumo-window-kpi")).toHaveTextContent(
      "R$ 69.000,00",
    );
    expect(
      screen.getByText("12 meses documentados · jan/25 — dez/25"),
    ).toBeVisible();
    const table = within(screen.getByRole("table"));
    expect(table.getByText("Moradia")).toBeVisible();
    expect(table.getByText("Alimentação")).toBeVisible();
    expect(table.getAllByText("70,00%")).toHaveLength(2);
    expect(table.getAllByText("100,00%")).toHaveLength(2);
    expect(
      screen.getByText(/Aportes e transferências patrimoniais/),
    ).toHaveTextContent("R$ 12.000,00/mês");
  });

  it("troca atomicamente para consumo, rows e transferência de 3M", async () => {
    const user = userEvent.setup();
    render(<OrcamentoProspectivoCard fluxo={fluxoFixture()} />);

    const toggle = screen.getByRole("group", {
      name: "Janela do consumo por categoria",
    });
    await user.click(within(toggle).getByRole("button", { name: "3M" }));

    expect(screen.getByTestId("consumo-window-kpi")).toHaveTextContent(
      "R$ 21.003,00",
    );
    expect(
      screen.getByText("3 meses documentados · ago/25 — dez/25"),
    ).toBeVisible();
    expect(screen.getByText("Lazer e viagens")).toBeVisible();
    expect(screen.getByText("Não identificado")).toBeVisible();
    expect(screen.queryByText("Moradia")).toBeNull();
    expect(
      screen.getByText(/Aportes e transferências patrimoniais/),
    ).toHaveTextContent("R$ 3.000,00/mês");
  });

  it("declara degradação histórica e ignora orçamento legado", () => {
    render(<OrcamentoProspectivoCard fluxo={undefined} />);
    expect(screen.getByText(/relatório histórico/)).toBeVisible();
    expect(screen.queryByRole("group")).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("preserva o zero medido e separa ausência de documentação", () => {
    const zero = fluxoFixture();
    zero.janelas = {
      ...zero.janelas,
      "12m": windowFixture("12m", {
        despesa_consumo_mensal_media: 0,
        transferencia_patrimonial_mensal: 0,
        tabela_consumo_por_categoria_mensal: [],
      }),
    } as FluxoJanelas;
    const { rerender } = render(<OrcamentoProspectivoCard fluxo={zero} />);
    expect(screen.getByTestId("consumo-window-kpi")).toHaveTextContent(
      "R$ 0,00",
    );
    expect(screen.getByText(/Sem consumo registrado/)).toBeVisible();

    const noMonths = fluxoFixture();
    noMonths.janelas = {
      ...noMonths.janelas,
      "12m": windowFixture("12m", {
        janela_meses: 0,
        mes_inicio: null,
        mes_fim: null,
        tabela_consumo_por_categoria_mensal: [],
      }),
    } as FluxoJanelas;
    rerender(<OrcamentoProspectivoCard fluxo={noMonths} />);
    expect(screen.getByText(/Não há meses documentados/)).toBeVisible();
    expect(screen.queryByTestId("consumo-window-kpi")).toBeNull();
  });
});
