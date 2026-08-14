import { readFileSync } from "node:fs";
import { join } from "node:path";

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

const FIXTURE_PATH = join(
  __dirname,
  "../../e2e/fixtures/reports/janela-divergente.json",
);

const PERIODS = ["3m", "6m", "12m", "ytd"] as const;

function toCents(value: number): number {
  return Math.round(Number(value.toFixed(2)) * 100);
}

function brl(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  })
    .format(value)
    .replace(/\u00a0/g, " ");
}

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
    tabela_receita_por_natureza_mensal: [
      {
        natureza: "receita_clt",
        total: 828_000,
        mensal_media: 69_000,
        participacao_pct: 75,
      },
      {
        natureza: "receita_outras",
        total: 276_000,
        mensal_media: 23_000,
        participacao_pct: 25,
      },
    ],
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
        fonte: "pro_labore",
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
    tabela_receita_por_natureza_mensal: [
      {
        natureza: "receita_pj",
        total: 60_006,
        mensal_media: 20_002,
        participacao_pct: 66.67,
      },
      {
        natureza: "receita_aluguel",
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

    expect(
      screen.getByRole("heading", { name: "Composição das Receitas" }),
    ).toBeVisible();
    expect(screen.getByTestId("receita-window-kpi")).toHaveTextContent(
      "R$ 92.000,00",
    );
    expect(
      screen.getByText("12 meses documentados · jan/25 — dez/25"),
    ).toBeVisible();
    const strip = within(screen.getByTestId("receita-natureza-strip"));
    expect(strip.getByText("Por tipo")).toBeVisible();
    expect(strip.getByText("CLT")).toBeVisible();
    expect(strip.getByText("Outras")).toBeVisible();
    const table = within(screen.getByRole("table"));
    expect(table.getByText("CLT")).toBeVisible();
    expect(table.getByText("Outras receitas")).toBeVisible();
    expect(table.getByText("75,00%")).toBeVisible();
    expect(table.getByText("25,00%")).toBeVisible();
    expect(screen.getByText(/não representa renda sustentável/)).toBeVisible();
    expect(screen.getByText(/PJ agrupa pró-labore e lucros/)).toBeVisible();
  });

  it("troca atomicamente tipo e origem para os números precomputados de 3M", async () => {
    const user = userEvent.setup();
    render(<ReceitasFonteCard fluxo={fluxoFixture()} />);

    const toggle = screen.getByRole("group", {
      name: "Janela da composição das receitas",
    });
    await user.click(within(toggle).getByRole("button", { name: "3M" }));

    expect(screen.getByTestId("receita-window-kpi")).toHaveTextContent(
      "R$ 30.003,00",
    );
    expect(
      screen.getByText("3 meses documentados · ago/25 — dez/25"),
    ).toBeVisible();
    const strip = within(screen.getByTestId("receita-natureza-strip"));
    expect(strip.getByText("PJ")).toBeVisible();
    expect(strip.getByText("Pró-labore + lucros")).toBeVisible();
    expect(strip.getByText("Aluguéis")).toBeVisible();
    expect(strip.queryByText("CLT")).toBeNull();
    expect(screen.getByRole("table")).toHaveTextContent("Pró-labore");
    expect(screen.queryByText("CLT")).toBeNull();
    expect(strip.getByText("66,67%")).toBeVisible();
    expect(within(screen.getByRole("table")).getByText("66,67%")).toBeVisible();
  });

  it("ignora receita_por_natureza do bloco full — só a tabela da janela entra na tela", () => {
    const fluxo = {
      ...fluxoFixture(),
      receita_por_natureza: {
        receita_pj: 999_999,
        receita_clt: 1,
        receita_aluguel: 1,
        receita_outras: 1,
      },
    };
    render(<ReceitasFonteCard fluxo={fluxo} />);

    expect(screen.queryByText(/999\.999/)).toBeNull();
    expect(screen.getByTestId("receita-window-kpi")).toHaveTextContent(
      "R$ 92.000,00",
    );
    expect(screen.getByTestId("receita-natureza-strip")).toHaveTextContent(
      "CLT",
    );
  });

  it("declara degradação histórica sem toggle nem fallback full", () => {
    render(
      <ReceitasFonteCard fluxo={{ por_fonte: { receita_clt: 1_000_000 } }} />,
    );

    expect(screen.getByText(/relatório histórico/)).toBeVisible();
    expect(screen.queryByRole("group")).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByTestId("receita-natureza-strip")).toBeNull();
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
        tabela_receita_por_natureza_mensal: [],
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
        tabela_receita_por_natureza_mensal: [],
      }),
    } as FluxoJanelas;
    rerender(<ReceitasFonteCard fluxo={zero} />);
    expect(screen.getByTestId("receita-window-kpi")).toHaveTextContent(
      "R$ 0,00",
    );
    expect(screen.getByText(/Sem entradas registradas/)).toBeVisible();
  });
});

describe("janela-divergente — identidade ao centavo da tabela de natureza", () => {
  const fixture = JSON.parse(readFileSync(FIXTURE_PATH, "utf-8")) as {
    fluxo_caixa: { janelas: FluxoJanelas };
  };

  it.each(PERIODS)(
    "%s: soma das médias de natureza == receita_mensal_media",
    (period) => {
      const janela = fixture.fluxo_caixa.janelas[period];
      const soma = janela.tabela_receita_por_natureza_mensal.reduce(
        (acc, row) => acc + toCents(row.mensal_media),
        0,
      );
      expect(soma).toBe(toCents(janela.receita_mensal_media));
    },
  );

  it.each(PERIODS)(
    "%s: a faixa mostra as médias da tabela, não um derivado do cliente",
    async (period) => {
      const janela = fixture.fluxo_caixa.janelas[period];
      const user = userEvent.setup();
      render(<ReceitasFonteCard fluxo={fixture.fluxo_caixa} />);
      if (period !== "12m") {
        await user.click(
          screen.getByRole("button", { name: period.toUpperCase() }),
        );
      }

      expect(screen.getByTestId("receita-window-kpi")).toHaveTextContent(
        brl(janela.receita_mensal_media),
      );
      const strip = within(screen.getByTestId("receita-natureza-strip"));
      for (const row of janela.tabela_receita_por_natureza_mensal) {
        expect(strip.getByText(brl(row.mensal_media))).toBeVisible();
      }
    },
  );
});
