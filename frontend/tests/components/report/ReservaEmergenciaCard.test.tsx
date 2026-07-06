/**
 * A28.l9 — specs do `<ReservaEmergenciaCard/>` pós A28.l1/l4.
 *
 * Cobre: alvo dinâmico por perfil de renda (meses_alvo/alvo_brl/gap_brl,
 * PR 787), fallback genérico 6/12 para payload antigo, e rótulo de janela
 * de mensalização (ADR-306) no Despesas/mês.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ReservaEmergenciaCard } from "@/components/report/cards/ReservaEmergenciaCard";
import type { ReservaEmergenciaData } from "@/types/report-analysis";

const RESERVA_POS_L1: ReservaEmergenciaData = {
  despesas_mensais: 9_000,
  janela: "12m",
  janela_meses: 12,
  total_liquida: 100_000,
  cobertura_meses: 11.1,
  avaliacao_liquidity: "Adequada",
  meses_alvo: 18,
  alvo_brl: 162_000,
  gap_brl: 62_000,
  perfil_renda: "pj_dominante",
  nivel_6_meses: 54_000,
  nivel_12_meses: 108_000,
};

const RESERVA_LEGADA: ReservaEmergenciaData = {
  despesas_mensais: 9_000,
  total_liquida: 100_000,
  cobertura_meses: 11.1,
  avaliacao_liquidity: "Adequada",
  nivel_6_meses: 54_000,
  nivel_12_meses: 108_000,
};

describe("<ReservaEmergenciaCard />", () => {
  it("payload pós-l1: alvo por perfil substitui metas genéricas", () => {
    render(<ReservaEmergenciaCard reserva={RESERVA_POS_L1} />);

    expect(screen.getByText("Alvo (18 meses)")).toBeInTheDocument();
    expect(screen.getByText("Gap até o alvo")).toBeInTheDocument();
    expect(screen.queryByText("Meta 6 meses")).not.toBeInTheDocument();
    expect(screen.queryByText("Meta 12 meses")).not.toBeInTheDocument();

    // progressbar mira o alvo do perfil, não os 12 meses genéricos
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute(
      "aria-label",
      "Progresso rumo ao alvo de 18 meses de reserva",
    );
    // 100k / 162k ≈ 62%
    expect(Number(bar.getAttribute("aria-valuenow"))).toBeCloseTo(61.7, 0);

    // tooltip do alvo cita o perfil de renda humanizado
    expect(screen.getByLabelText("Sobre o alvo da reserva")).toBeInTheDocument();
  });

  it("payload legado: fallback para metas 6/12 e progressbar de 12 meses", () => {
    render(<ReservaEmergenciaCard reserva={RESERVA_LEGADA} />);

    expect(screen.getByText("Meta 6 meses")).toBeInTheDocument();
    expect(screen.getByText("Meta 12 meses")).toBeInTheDocument();
    expect(screen.queryByText(/Alvo \(/)).not.toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-label",
      "Progresso rumo à reserva de 12 meses",
    );
  });

  it("rótulo de janela (ADR-306): tooltip no Despesas/mês quando janela presente", () => {
    render(<ReservaEmergenciaCard reserva={RESERVA_POS_L1} />);
    expect(
      screen.getByLabelText("Sobre a janela de mensalização das despesas"),
    ).toBeInTheDocument();
  });

  it("payload antigo sem janela: sem tooltip (nada de rótulo inventado)", () => {
    render(<ReservaEmergenciaCard reserva={RESERVA_LEGADA} />);
    expect(
      screen.queryByLabelText("Sobre a janela de mensalização das despesas"),
    ).not.toBeInTheDocument();
  });
});
