/**
 * A37.l14 (PD-02) — título do card de decisões em S10 é neutro.
 *
 * "Top 5 Decisões de Impacto" hardcoded mentia quando o workspace tinha
 * menos de 5 decisões (dogfood: 3). A contagem real já vem na narrativa
 * (`charts.top5_decisoes.context`); o título não deve fixar número.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/components/report/cards", () => ({
  PontosFortesCard: () => null,
  PontosUrgentesCard: () => null,
}));
import { S10SinteseSection } from "@/components/report/sections/S10SinteseSection";
import type { ReportAnalysisData } from "@/lib/api";

const data = {
  narrativas: {
    charts: {
      top5_decisoes: {
        context: "3 decisões estratégicas de curto prazo.",
        conclusion: "Prioridade 1: Aporte mensal.",
      },
    },
  },
} as unknown as ReportAnalysisData;

describe("<S10SinteseSection /> — título do card de decisões (PD-02)", () => {
  it("usa título neutro sem contagem fixa", () => {
    render(<S10SinteseSection data={data} />);
    expect(screen.getByText("Decisões de Impacto")).toBeInTheDocument();
    expect(screen.queryByText(/Top 5/)).not.toBeInTheDocument();
  });
});
