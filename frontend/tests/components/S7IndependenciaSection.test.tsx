/**
 * Tests — Lane A8.3 (TRS real) · S7 com 4 KPIs + tooltip + 2 banners + empty states.
 *
 * Cobre matriz de cenários:
 * - 3 fases (acumulação · aproximação · independência) × 2 acumuladores
 *   (low/high) × 3 defasagens (none/info/warning) = 18 cenários.
 * - 2 empty states: ``sem_irpf`` e ``gerador_zero``.
 * - Helper ``trsTone`` cobre matriz de fase × yield.
 * - Caption permanente em acumulação aparece/some.
 * - Card "Em acumuladores" tom warning + sublabel quando >40%.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  S7IndependenciaSection,
  TRS_EFETIVA_TOOLTIP,
  trsTone,
} from "@/components/report/sections/S7IndependenciaSection";
import type {
  IFMonteCarloData,
  PassiveIncomeData,
  PremissasEconomicasData,
  ReportAnalysisData,
} from "@/lib/api";

function makePassiveIncome(overrides: Partial<PassiveIncomeData> = {}): PassiveIncomeData {
  return {
    status: "ok",
    renda_passiva_anual_brl: 24_000,
    renda_passiva_mensal_brl: 2_000,
    renda_passiva_por_fonte_brl: {
      dividendos: 12_000,
      jcp: 4_000,
      aplicacoes: 3_000,
      exterior: 3_000,
      alugueis: 2_000,
    },
    renda_ativa_pj_excluida_brl: 0,
    ganho_capital_excluido_brl: 2_000,
    patrimonio_gerador_brl: 1_000_000,
    trs_efetiva_pct: 2.4,
    ano_referencia_irpf: 2024,
    defasagem_meses: 5,
    acumuladores_pct_gerador: 12.0,
    ...overrides,
  };
}

function makeData(overrides: Partial<ReportAnalysisData> = {}): ReportAnalysisData {
  return {
    goals: { if_meta: 5_000_000, if_pct: 30, trs_pct: 5, ano_if: 2040, if_gap: 4_000_000 },
    passive_income: makePassiveIncome(),
    ...overrides,
  };
}

describe("trsTone", () => {
  it("acumulação (progresso < 50): SEMPRE neutro mesmo com TRS alta", () => {
    expect(trsTone(8, 5, 30)).toBe("neutral");
    expect(trsTone(0.5, 5, 30)).toBe("neutral");
  });

  it("aproximação (50-95): warning se yield < 70% da meta", () => {
    expect(trsTone(2.0, 5, 70)).toBe("warning"); // 2 < 5*0.7
    expect(trsTone(4.0, 5, 70)).toBe("neutral"); // 4 >= 3.5
  });

  it("independência (≥95): positive ≥ meta · warning < meta", () => {
    expect(trsTone(5.5, 5, 96)).toBe("positive");
    expect(trsTone(4.0, 5, 96)).toBe("warning");
  });
});

describe("<S7IndependenciaSection /> · empty states", () => {
  it("renderiza empty state sem_irpf com CTA Importar IRPF", () => {
    const data = makeData({ passive_income: makePassiveIncome({ status: "sem_irpf" }) });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.getByRole("heading", { level: 3, name: /Importe seu IRPF/i }),
    ).toBeInTheDocument();
    // EmptyState renderiza link como <a role="button"> — busca por texto.
    const cta = screen.getByText("Importar IRPF");
    expect(cta.closest("a")).toHaveAttribute("href", "/documents");
  });

  it("renderiza empty state gerador_zero (sem CTA)", () => {
    const data = makeData({ passive_income: makePassiveIncome({ status: "gerador_zero" }) });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.getByRole("heading", { level: 3, name: /TRS efetiva começa quando há patrimônio/i }),
    ).toBeInTheDocument();
  });

  it("não renderiza KPIs de TRS quando passive_income ausente", () => {
    const data = makeData({ passive_income: undefined });
    render(<S7IndependenciaSection data={data} />);
    // O label "TRS efetiva" só aparece dentro do bloco PassiveIncomeOk;
    // botão "Sobre TRS efetiva" tem aria-label específico que cobre ausência.
    expect(screen.queryByRole("button", { name: /Sobre TRS efetiva/i })).toBeNull();
  });
});

describe("<S7IndependenciaSection /> · caption de acumulação", () => {
  it("aparece quando progresso < 50", () => {
    const data = makeData({
      goals: { if_meta: 5_000_000, if_pct: 30, trs_pct: 5 },
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByText(/Carteira em acumulação/i)).toBeInTheDocument();
  });

  it("some quando progresso >= 50", () => {
    const data = makeData({
      goals: { if_meta: 5_000_000, if_pct: 60, trs_pct: 5 },
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.queryByText(/Carteira em acumulação/i)).toBeNull();
  });
});

describe("<S7IndependenciaSection /> · banners condicionais", () => {
  it("AcumuladoresBanner aparece quando pct > 40", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ acumuladores_pct_gerador: 60 }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByText(/sua carteira de renda está em ativos sem distribuição/i))
      .toBeInTheDocument();
  });

  it("AcumuladoresBanner some quando pct <= 40", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ acumuladores_pct_gerador: 35 }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.queryByText(/sua carteira de renda está em ativos sem distribuição/i),
    ).toBeNull();
  });

  it("DefasagemWarningBanner aparece quando defasagem >= 15m", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ defasagem_meses: 18, ano_referencia_irpf: 2023 }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByText(/IRPF de 2023 desatualizado/i)).toBeInTheDocument();
  });

  it("DefasagemWarningBanner some quando defasagem < 15m", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ defasagem_meses: 12, ano_referencia_irpf: 2024 }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.queryByText(/desatualizado/i)).toBeNull();
  });
});

describe("<S7IndependenciaSection /> · loop visual KPI↔banner", () => {
  it("card Em acumuladores tem sublabel '>40% subestima TRS' quando pct > 40", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ acumuladores_pct_gerador: 60 }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByText(/>40% subestima TRS/)).toBeInTheDocument();
  });

  it("card Em acumuladores mostra 'Sem ETFs/fundos acumuladores' quando 0", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ acumuladores_pct_gerador: 0 }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByText(/Sem ETFs\/fundos acumuladores/i)).toBeInTheDocument();
  });
});

describe("<S7IndependenciaSection /> · matriz fase × acumuladores × defasagem (18 cenários)", () => {
  const PHASES = [
    { name: "acumulacao", if_pct: 30 },
    { name: "aproximacao", if_pct: 70 },
    { name: "independencia", if_pct: 96 },
  ];
  const ACUMULADORES = [
    { name: "low", pct: 12 },
    { name: "high", pct: 60 },
  ];
  const DEFASAGENS = [
    { name: "none", meses: 5 },
    { name: "info", meses: 8 },
    { name: "warning", meses: 18 },
  ];

  for (const phase of PHASES) {
    for (const acum of ACUMULADORES) {
      for (const def of DEFASAGENS) {
        it(`renderiza 4 KPIs em ${phase.name} × ${acum.name} acumuladores × ${def.name} defasagem`, () => {
          const data = makeData({
            goals: { if_meta: 5_000_000, if_pct: phase.if_pct, trs_pct: 5 },
            passive_income: makePassiveIncome({
              acumuladores_pct_gerador: acum.pct,
              defasagem_meses: def.meses,
              ano_referencia_irpf: 2024,
            }),
          });
          render(<S7IndependenciaSection data={data} />);
          // 4 KPIs sempre presentes em status ok — usamos getAllByText pois
          // "Renda passiva" também aparece no NarrativeChartCard.
          expect(screen.getAllByText(/Renda passiva/i).length).toBeGreaterThan(0);
          expect(screen.getByText(/Patrimônio investido/i)).toBeInTheDocument();
          expect(screen.getByText(/Em acumuladores/i)).toBeInTheDocument();
        });
      }
    }
  }
});

describe("<S7IndependenciaSection /> · acessibilidade (label + tooltip)", () => {
  it("InfoTooltip tem aria-label descritivo, não apenas ícone", () => {
    const data = makeData();
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.getByRole("button", { name: /Sobre TRS efetiva/i }),
    ).toBeInTheDocument();
  });
});

// ─── A28.l9 — ressalva de premissas fallback no Monte Carlo ───

function makeMonteCarlo(overrides: Partial<IFMonteCarloData> = {}): IFMonteCarloData {
  return {
    // ADR-369 D1 — cenário nomeado: favorável é o ano mais CEDO (2036), adverso
    // é o mais tarde (2044). O fixture antigo lia `p10_ano_if: 2044`, que era
    // literalmente a inversão que o rename existe para desfazer.
    ano_if_cenario_favoravel: 2036,
    ano_if_cenario_central: 2040,
    ano_if_cenario_adverso: 2044,
    prob_if_ate_idade_meta: 0.31,
    idade_meta_usada: 60,
    sigma_usado: 0.15,
    exibir_cone: true,
    motivo_sem_cone: null,
    caminho_p10: [[2026, 1_000_000]],
    caminho_p50: [[2026, 1_000_000]],
    caminho_p90: [[2026, 1_000_000]],
    ...overrides,
  };
}

function makePremissasEconomicas(
  status: "completo" | "parcial",
  classStatus: "emitted" | "indisponivel",
): PremissasEconomicasData {
  return {
    status,
    snapshot_at: "2026-07-01T00:00:00Z",
    classes: [
      {
        classe_auvp: "renda_fixa",
        status: classStatus,
        retorno_real_esperado_pct_anual: classStatus === "emitted" ? "4.5" : null,
        sigma_anual_pct: null,
        fonte: null,
        fonte_origem: null,
        effective_from: null,
        justificativa: null,
        razao_indisponivel: classStatus === "indisponivel" ? "sem premissa" : null,
      },
    ],
  };
}

describe("IFMonteCarloBlock · premissas fallback (A28.l9)", () => {
  it("premissas parcial: Alert de ressalva acima do cone", () => {
    const data = makeData({
      if_monte_carlo: makeMonteCarlo(),
      premissas_economicas: makePremissasEconomicas("parcial", "indisponivel"),
    });
    render(<S7IndependenciaSection data={data} />);
    const alert = screen.getByTestId("s7-premissas-fallback-alert");
    expect(alert.textContent).toMatch(/premissas de mercado padrão/);
    expect(alert.textContent).toMatch(/referência, não como previsão/);
  });

  it("premissas completo: sem ressalva (cone renderiza limpo)", () => {
    const data = makeData({
      if_monte_carlo: makeMonteCarlo(),
      premissas_economicas: makePremissasEconomicas("completo", "emitted"),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.queryByTestId("s7-premissas-fallback-alert"),
    ).not.toBeInTheDocument();
  });

  it("bloco de premissas ausente (run pré-ADR-219): sem ressalva", () => {
    const data = makeData({ if_monte_carlo: makeMonteCarlo() });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.queryByTestId("s7-premissas-fallback-alert"),
    ).not.toBeInTheDocument();
  });

  // Projeção determinística sem prazo → idade-meta null. Antes a sentinela 999
  // somava à idade e o cone anunciava "até a idade 1040" (métrica fabricada).
  it("idade-meta ausente: omite a cláusula de probabilidade, mantém o cone", () => {
    const data = makeData({
      if_monte_carlo: makeMonteCarlo({
        idade_meta_usada: null,
        prob_if_ate_idade_meta: null,
      }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.queryByText(/Probabilidade de atingir IF/)).toBeNull();
    expect(screen.getByTestId("s7-if-cone-chart")).toBeInTheDocument();
  });

  it("motivo_sem_cone: role note + ícone, não só itálico (a11y A28.l9)", () => {
    const data = makeData({
      if_monte_carlo: makeMonteCarlo({
        exibir_cone: false,
        motivo_sem_cone: "Meta IF não configurada para este workspace.",
      }),
    });
    render(<S7IndependenciaSection data={data} />);
    const note = screen.getByRole("note", {
      name: "Motivo da ausência do cone de probabilidade",
    });
    expect(note.textContent).toMatch(/Meta IF não configurada/);
  });
});

/**
 * A40.l4 (PD-20 · ADR-191 §Emenda FP-03) — o card de TRS efetiva lia
 * `goals.trs_pct`, chave que o payload NÃO tem (o E5 emite `goals.if_trs`),
 * então o `?? 5.0` disparava 100% das vezes: constante de código impressa
 * como se fosse a meta da família. A casa sancionada do yield-alvo é
 * `ratios.rentabilidade.meta_pct` — a MESMA que o `kpi_rentabilidade` da S3 lê.
 *
 * O par SWR 4% (estimativa de renda passiva, regra de retirada) × yield-alvo
 * 5% (rentabilidade da carteira) são conceitos DISTINTOS e não se harmonizam:
 * colapsá-los desfaz a emenda FP-03 e encurta a meta de IF em ~20%.
 */
describe("<S7IndependenciaSection /> · yield-alvo (PD-20)", () => {
  const withRatios = (metaPct: unknown) =>
    makeData({
      ratios: { rentabilidade: { meta_pct: metaPct } },
    } as Partial<ReportAnalysisData>);

  it("imprime o yield-alvo do payload, não uma constante de código", () => {
    render(<S7IndependenciaSection data={withRatios(4.0)} />);
    expect(screen.getByText(/Yield-alvo 4,0%/)).toBeInTheDocument();
    expect(screen.queryByText(/Yield-alvo 5,0%/)).toBeNull();
  });

  it("não imprime meta alguma quando o payload não traz yield-alvo", () => {
    // `goals.trs_pct` presente e `ratios` ausente: a chave fantasma não pode
    // ressuscitar como fonte, e nenhum default entra no lugar.
    render(<S7IndependenciaSection data={makeData()} />);
    expect(screen.queryByText(/Yield-alvo/)).toBeNull();
    expect(screen.queryByText(/^Meta 5,0%$/)).toBeNull();
    // O valor observado continua visível — sustenta-se sem meta.
    expect(screen.getByText("2.4%")).toBeInTheDocument();
  });

  it("shape inesperado em meta_pct não imprime meta", () => {
    render(<S7IndependenciaSection data={withRatios("5.000000")} />);
    expect(screen.queryByText(/Yield-alvo/)).toBeNull();
  });

  // A copy do tooltip é asserida na constante, não no DOM: `TooltipContent`
  // só monta no open, então um assert por DOM passaria vazio (vacuoso).
  it("copy do tooltip não colapsa yield com taxa de retirada (ADR-191 §D5)", () => {
    expect(TRS_EFETIVA_TOOLTIP).not.toMatch(/Trinity/i);
    expect(TRS_EFETIVA_TOOLTIP).not.toMatch(/retirada sustentável/i);
    expect(TRS_EFETIVA_TOOLTIP).not.toMatch(/\b4%/);
    expect(TRS_EFETIVA_TOOLTIP).toMatch(/yield-alvo/i);
  });
});
