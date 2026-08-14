/**
 * A40.l47 PR3 (RV4-18) — a reserva declara a base que usou e o que ficou de fora.
 *
 * O numerador da reserva lê o agregado patrimonial (`reserva_liquidez.py`), não a seção
 * de investimentos, então a base pode exceder a carteira exibida **por construção** — e
 * nenhum invariante de conservação acusa, porque o cálculo confere. `base_denominador` e
 * `excluido_da_reserva` existiam no payload sem nenhum leitor em `frontend/src`.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ReservaEmergenciaCard } from "@/components/report/cards/ReservaEmergenciaCard";
import type { ReservaEmergenciaData } from "@/types/report-analysis";

function makeReserva(over: Partial<ReservaEmergenciaData> = {}): ReservaEmergenciaData {
  return {
    despesas_mensais: 10_000,
    custo_essencial_mensal: 6_000,
    base_denominador: "custo_essencial",
    total_liquida: 80_000,
    cobertura_meses: 13.3,
    nivel_6_meses: 36_000,
    nivel_12_meses: 72_000,
    excluido_da_reserva: {
      investimentos_nao_liquidos: 0,
      caixa_moeda_estrangeira: 0,
      caixa_nao_classificado: 50_000,
    },
    ...over,
  };
}

describe("ReservaEmergenciaCard · base declarada", () => {
  it("nomeia a base do denominador da cobertura", () => {
    render(<ReservaEmergenciaCard reserva={makeReserva()} />);
    expect(screen.getByText(/base da cobertura/i)).toBeInTheDocument();
    expect(screen.getByText(/custo essencial/i)).toBeInTheDocument();
  });

  it("distingue base essencial de despesa total", () => {
    render(
      <ReservaEmergenciaCard reserva={makeReserva({ base_denominador: "despesa_total" })} />,
    );
    expect(screen.getByText(/despesa total/i)).toBeInTheDocument();
    expect(screen.queryByText(/custo essencial/i)).toBeNull();
  });

  it("declara o que ficou fora da reserva quando há exclusão", () => {
    render(<ReservaEmergenciaCard reserva={makeReserva()} />);
    expect(screen.getByText(/fora da reserva/i)).toBeInTheDocument();
    expect(screen.getByText(/caixa não classificado/i)).toBeInTheDocument();
  });

  it("omite o bloco de exclusão quando nada foi excluído", () => {
    const reserva = makeReserva({
      excluido_da_reserva: {
        investimentos_nao_liquidos: 0,
        caixa_moeda_estrangeira: 0,
        caixa_nao_classificado: 0,
      },
    });
    render(<ReservaEmergenciaCard reserva={reserva} />);
    expect(screen.queryByText(/fora da reserva/i)).toBeNull();
  });

  it("payload antigo sem os campos não quebra nem inventa base", () => {
    render(
      <ReservaEmergenciaCard
        reserva={{ total_liquida: 80_000, cobertura_meses: 13.3, despesas_mensais: 6_000 }}
      />,
    );
    expect(screen.queryByText(/base da cobertura/i)).toBeNull();
    expect(screen.queryByText(/fora da reserva/i)).toBeNull();
    expect(screen.getByText(/13,3 meses/)).toBeInTheDocument();
  });
});
