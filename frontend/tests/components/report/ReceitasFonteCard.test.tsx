import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ReceitasFonteCard } from "@/components/report/cards/ReceitasFonteCard";
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
    tabela_receitas_por_fonte_mensal: [
      {
        fonte: "receita_clt",
        total: 828_000,
        mensal_media: 69_000,
        participacao_pct: 75,
      },
      {
        fonte: "outras_receitas",
        total: 276_000,
        mensal_media: 23_000,
        participacao_pct: 25,
      },
    ],
    tabela_receita_por_natureza_mensal: [],
    tabela_consumo_por_categoria_mensal: [],
    ...overrides,
  };
}

function fluxoFixture(): FluxoCaixaSummary {
  const twelve = windowFixture("12m");
  const three = windowFixture("3m", {
    janela_meses: 3,
    mes_inicio: "2025-08",
    mes_fim: "2025-12",
    receita_total: 90_009,
    receita_mensal_media: 30_003,
    tabela_receitas_por_fonte_mensal: [
      {
        fonte: "receita_pj",
        total: 60_006,
        mensal_media: 20_002,
        participacao_pct: 66.67,
      },
      {
        fonte: "receita_aluguel",
        total: 30_003,
        mensal_media: 10_001,
        participacao_pct: 33.33,
      },
    ],
  });
  const janelas: FluxoJanelas = {
    "3m": three,
    "6m": windowFixture("6m"),
    "12m": twelve,
    ytd: windowFixture("ytd"),
  };
  return { janelas };
}

describe("<ReceitasFonteCard />", () => {
  it("renderiza 12M por default a partir das rows e escalares do E5", () => {
    render(<ReceitasFonteCard fluxo={fluxoFixture()} />);

    expect(screen.getByTestId("receita-window-kpi")).toHaveTextContent(
      "R$ 92.000,00",
    );
    expect(
      screen.getByText("12 meses documentados · jan/25 — dez/25"),
    ).toBeVisible();
    const table = within(screen.getByRole("table"));
    expect(table.getByText("CLT")).toBeVisible();
    expect(table.getByText("Outras receitas")).toBeVisible();
    expect(table.getByText("75,00%")).toBeVisible();
    expect(table.getByText("25,00%")).toBeVisible();
    expect(screen.getByText(/não representa renda sustentável/)).toBeVisible();
  });

  it("troca atomicamente para os números precomputados de 3M", async () => {
    const user = userEvent.setup();
    render(<ReceitasFonteCard fluxo={fluxoFixture()} />);

    const toggle = screen.getByRole("group", {
      name: "Janela das receitas por fonte",
    });
    await user.click(within(toggle).getByRole("button", { name: "3M" }));

    expect(screen.getByTestId("receita-window-kpi")).toHaveTextContent(
      "R$ 30.003,00",
    );
    expect(
      screen.getByText("3 meses documentados · ago/25 — dez/25"),
    ).toBeVisible();
    expect(screen.getByText("PJ")).toBeVisible();
    expect(screen.getByText("Aluguéis")).toBeVisible();
    expect(screen.queryByText("CLT")).toBeNull();
    expect(screen.getByText("66,67%")).toBeVisible();
  });

  it("declara degradação histórica sem toggle nem fallback full", () => {
    render(
      <ReceitasFonteCard fluxo={{ por_fonte: { receita_clt: 1_000_000 } }} />,
    );

    expect(screen.getByText(/relatório histórico/)).toBeVisible();
    expect(screen.queryByRole("group")).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByText("CLT")).toBeNull();
  });

  it("distingue janela sem documentação de janela documentada com receita zero", () => {
    const noMonths = fluxoFixture();
    noMonths.janelas = {
      ...noMonths.janelas,
      "12m": windowFixture("12m", {
        janela_meses: 0,
        mes_inicio: null,
        mes_fim: null,
        receita_mensal_media: 0,
        tabela_receitas_por_fonte_mensal: [],
      }),
    } as FluxoJanelas;
    const { rerender } = render(<ReceitasFonteCard fluxo={noMonths} />);
    expect(screen.getByText(/Não há meses documentados/)).toBeVisible();
    expect(screen.queryByTestId("receita-window-kpi")).toBeNull();

    const zero = fluxoFixture();
    zero.janelas = {
      ...zero.janelas,
      "12m": windowFixture("12m", {
        receita_mensal_media: 0,
        tabela_receitas_por_fonte_mensal: [],
      }),
    } as FluxoJanelas;
    rerender(<ReceitasFonteCard fluxo={zero} />);
    expect(screen.getByTestId("receita-window-kpi")).toHaveTextContent(
      "R$ 0,00",
    );
    expect(screen.getByText(/Sem entradas registradas/)).toBeVisible();
  });
});
