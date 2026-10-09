/**
 * Direção E · Onda 7 #4 (ADR-156) — Patrimônio single-source.
 *
 * Garante que PlanoKpiRow + IFHeroCard renderizam exatamente o mesmo
 * número de patrimônio quando alimentados pelo mesmo `PatrimonioSnapshot`.
 * Bloqueia regressão de "dois caminhos divergentes" identificada na
 * revisão de produto pré-Onda 7.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { IFHeroCard } from "@/app/(app)/plano/_components/IFHeroCard";
import { PlanoKpiRow } from "@/app/(app)/plano/_components/PlanoKpiRow";
import type {
  IFProgress,
  PatrimonioSnapshot,
} from "@/app/(app)/plano/_components/usePlanoOverview";
import type { IFGoalResponse } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { PERCENTUAL_COM_PONTO } from "../shared/percentualPtBr";

const SNAPSHOT: PatrimonioSnapshot = {
  value: 487_321.55,
  asOf: "2026-04-27T00:00:00Z",
  sourceReportId: "rep-1",
};

const PROGRESS: IFProgress = {
  pct: 24.7,
  faltante: 1_487_321.55,
};

const IF_GOAL: IFGoalResponse = {
  id: "if-1",
  workspace_id: "ws-1",
  effective_from: "2026-01-01",
  is_template: false,
  inputs: {
    renda_passiva_mensal_brl: 12000,
    horizonte_anos: 25,
    trs_pct: 4.0,
    retorno_real_anual_pct: 6.0,
    taxa_retirada_conservadora_pct: 4.0,
  },
  derived: {
    if_meta_brl: 1_974_643.10,
    if_meta_conservadora_brl: 3_600_000,
    aporte_necessario_mensal_brl: 4_500,
    aporte_mensal_com_patrimonio_atual_brl: null,
    patrimonio_atual_utilizado_brl: null,
  },
} as unknown as IFGoalResponse;

describe("Patrimônio single-source @ADR-156 @Onda7", () => {
  it("PlanoKpiRow + IFHeroCard mostram exatamente o mesmo valor de patrimônio", () => {
    render(
      <div>
        <PlanoKpiRow
          patrimonioSnapshot={SNAPSHOT}
          ifGoal={IF_GOAL}
          ifProgress={PROGRESS}
          aporteGoal={null}
          loading={false}
        />
        <IFHeroCard
          goal={IF_GOAL}
          progress={PROGRESS}
          patrimonio={SNAPSHOT.value}
        />
      </div>,
    );

    const expected = formatCurrency(SNAPSHOT.value);
    const heroValue = screen.getByTestId("if-hero-patrimonio");
    expect(heroValue.textContent).toBe(expected);

    const matches = screen.getAllByText((_, node) => {
      if (!node) return false;
      if (node.children.length > 0) return false;
      return node.textContent?.trim() === expected;
    });
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });

  it("PlanoKpiRow degrada para — no patrimônio quando snapshot é null", () => {
    const { container } = render(
      <PlanoKpiRow
        patrimonioSnapshot={null}
        ifGoal={null}
        ifProgress={null}
        aporteGoal={null}
        loading={false}
      />,
    );
    const patrimonioCard = container.querySelector(
      "[data-slot=card]",
    ) as HTMLElement | null;
    expect(patrimonioCard?.textContent).toContain("Patrimônio líquido");
    expect(patrimonioCard?.textContent).toContain("—");
  });
});

describe("IFHeroCard + PlanoKpiRow — percentual pt-BR (COPY_GUIDELINES §4.6)", () => {
  // Valores distintos entre si: cada asserção só casa o seu call-site.
  const goal: IFGoalResponse = {
    ...IF_GOAL,
    inputs: {
      ...IF_GOAL.inputs,
      trs_pct: 4.5,
      retorno_real_anual_pct: 5.5,
      taxa_retirada_conservadora_pct: 3.5,
    },
  };

  it("progresso, aria-label da barra e parâmetros do cálculo usam vírgula", () => {
    const { container } = render(
      <div>
        <PlanoKpiRow
          patrimonioSnapshot={SNAPSHOT}
          ifGoal={goal}
          ifProgress={PROGRESS}
          aporteGoal={null}
          loading={false}
        />
        <IFHeroCard goal={goal} progress={PROGRESS} patrimonio={SNAPSHOT.value} />
      </div>,
    );

    // KPI do PlanoKpiRow + número grande do hero.
    expect(screen.getAllByText("24,7%")).toHaveLength(2);
    expect(
      screen.getByRole("progressbar", {
        name: "Progresso rumo à meta de independência financeira: 24,7%",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("4,5% a.a.")).toBeInTheDocument();
    expect(screen.getByText("5,5% a.a.")).toBeInTheDocument();
    expect(screen.getByText("Meta conservadora (3,5%)")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
  });
});
