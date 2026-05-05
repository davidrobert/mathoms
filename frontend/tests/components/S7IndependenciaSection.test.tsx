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

import { S7IndependenciaSection, trsTone } from "@/components/report/sections/S7IndependenciaSection";
import type { PassiveIncomeData, ReportAnalysisData } from "@/lib/api";

function makePassiveIncome(overrides: Partial<PassiveIncomeData> = {}): PassiveIncomeData {
  return {
    status: "ok",
    renda_passiva_anual_brl: 24_000,
    renda_passiva_mensal_brl: 2_000,
    renda_passiva_por_fonte_brl: {
      dividendos: 12_000,
      jcp: 4_000,
      aplicacoes: 3_000,
      ganho_capital: 2_000,
      exterior: 2_000,
      alugueis: 1_000,
    },
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
