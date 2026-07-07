/**
 * A33.l2 P4 (ADR-238 D5, co-design product-designer 2026-07-07) —
 * card "Posição por Instituição e Moeda (31/12)".
 *
 * Cobre: hide-when-empty (null sem posição de informe), chip de fonte com
 * texto (nunca só cor), linha secundária em moeda original sempre visível,
 * nudge condicionado a informe_venceu_extrato, alert CBE condicionado a
 * cbe_obrigatorio e footnote PTAX compra.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PosicaoInformeCard } from "@/components/report/cards/PosicaoInformeCard";
import type { Posicao3112Row } from "@/types/report-analysis";

function rowInforme(overrides: Partial<Posicao3112Row> = {}): Posicao3112Row {
  return {
    instituicao: "Wise Multi-Currency Account — USD",
    moeda: "USD",
    valor_original: 5210.55,
    valor_brl: 32262.16,
    fonte: "informe_31_12",
    ptax_data: "2024-12-31",
    ptax_status: "applied",
    informe_venceu_extrato: false,
    divergencia_relevante: false,
    ano_base: 2024,
    tipo: "conta_exterior",
    ...overrides,
  };
}

function rowExtrato(overrides: Partial<Posicao3112Row> = {}): Posicao3112Row {
  return {
    instituicao: "itau (contacorrente)",
    moeda: "BRL",
    valor_original: null,
    valor_brl: 2000.0,
    fonte: "extrato",
    ptax_data: null,
    ptax_status: null,
    informe_venceu_extrato: false,
    divergencia_relevante: false,
    ano_base: null,
    tipo: "caixa",
    ...overrides,
  };
}

describe("PosicaoInformeCard", () => {
  it("hide-when-empty: sem posições retorna null", () => {
    const { container } = render(
      <PosicaoInformeCard posicoes={[]} cbeObrigatorio={false} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("hide-when-empty: só extrato (sem informe) também retorna null", () => {
    const { container } = render(
      <PosicaoInformeCard posicoes={[rowExtrato()]} cbeObrigatorio={false} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renderiza tabela com colunas do co-design e chips de fonte com texto", () => {
    render(
      <PosicaoInformeCard
        posicoes={[rowInforme(), rowExtrato()]}
        cbeObrigatorio={false}
      />,
    );
    expect(screen.getByText("Posição por Instituição e Moeda (31/12)")).toBeInTheDocument();
    expect(screen.getByText("Instituição")).toBeInTheDocument();
    expect(screen.getByText("Moeda")).toBeInTheDocument();
    expect(screen.getByText("Valor em 31/12")).toBeInTheDocument();
    expect(screen.getByText("Fonte")).toBeInTheDocument();
    // Chip nunca comunica só por cor — texto presente para ambas as fontes.
    expect(screen.getByText("Informe 31/12")).toBeInTheDocument();
    expect(screen.getByText("Extrato")).toBeInTheDocument();
  });

  it("linha secundária em moeda original sempre visível para ME; BRL sem secundária", () => {
    render(
      <PosicaoInformeCard
        posicoes={[rowInforme(), rowExtrato()]}
        cbeObrigatorio={false}
      />,
    );
    // USD 5.210,55 renderizado via Intl (en-US para USD) — símbolo $ presente.
    expect(screen.getByText(/\$5,210\.55/)).toBeInTheDocument();
    // Conta BRL: só o valor primário (nenhum texto "BRL 2.000,00" secundário).
    expect(screen.queryByText(/BRL 2\.000,00/)).not.toBeInTheDocument();
  });

  it("nudge aparece apenas quando informe venceu extrato", () => {
    const { rerender } = render(
      <PosicaoInformeCard posicoes={[rowInforme()]} cbeObrigatorio={false} />,
    );
    expect(
      screen.queryByText(/Posição de fechamento do ano/),
    ).not.toBeInTheDocument();
    rerender(
      <PosicaoInformeCard
        posicoes={[rowInforme({ informe_venceu_extrato: true })]}
        cbeObrigatorio={false}
      />,
    );
    expect(screen.getByText(/Posição de fechamento do ano/)).toBeInTheDocument();
    expect(screen.getByText(/reflete 31\/12/)).toBeInTheDocument();
  });

  it("alert CBE no topo condicionado a cbe_obrigatorio", () => {
    render(<PosicaoInformeCard posicoes={[rowInforme()]} cbeObrigatorio={true} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Declaração CBE ao Banco Central pode ser obrigatória.");
    expect(alert).toHaveTextContent("Confirme o enquadramento com seu contador.");
  });

  it("sem cbe_obrigatorio não renderiza alert", () => {
    render(<PosicaoInformeCard posicoes={[rowInforme()]} cbeObrigatorio={false} />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("footnote cita PTAX de compra de 31/12 do ano-base", () => {
    render(<PosicaoInformeCard posicoes={[rowInforme()]} cbeObrigatorio={false} />);
    expect(
      screen.getByText(/PTAX de compra de 31\/12\/2024 \(Banco Central\)/),
    ).toBeInTheDocument();
  });

  it("PTAX ausente: primário — com tooltip, secundária preserva moeda original", () => {
    render(
      <PosicaoInformeCard
        posicoes={[rowInforme({ valor_brl: null, ptax_status: "missing", ptax_data: null })]}
        cbeObrigatorio={false}
      />,
    );
    expect(screen.getByTitle("PTAX indisponível")).toBeInTheDocument();
    expect(screen.getByText(/\$5,210\.55/)).toBeInTheDocument();
  });
});
