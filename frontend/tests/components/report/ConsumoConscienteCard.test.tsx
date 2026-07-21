/**
 * Specs do `<ConsumoConscienteCard>` — labels pt-BR de categoria na lista de
 * gastos pontuais (A37.l6 · PD-08).
 *
 * Regressão guard: o card imprimia `t.categoria` verbatim do endpoint
 * `/reports/consumo-pontuais` — toda linha exibia código snake_case
 * (`nao_identificado`, `lazer_viagens`, …). Pós-fix, humaniza no frontend
 * via `@/lib/categoryLabels`; o DTO permanece cru (contrato estável da API).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import type { ConsumoPontuaisItem } from "@/lib/api/reports";

const mockUseConsumoPontuais = vi.fn();

vi.mock("@/hooks/useConsumoPontuais", () => ({
  useConsumoPontuais: (...args: unknown[]) => mockUseConsumoPontuais(...args),
}));

import { ConsumoConscienteCard } from "@/components/report/cards/ConsumoConscienteCard";

function item(categoria: string, valor: number, i: number): ConsumoPontuaisItem {
  return {
    data: "2026-04-15",
    descricao: `Gasto pontual ${i}`,
    valor,
    banco: "itau",
    categoria,
    tipo_conta: "corrente",
    titular: "Titular",
    transaction_hash: `hash-${i}`,
  };
}

function renderWithItems(items: ConsumoPontuaisItem[]) {
  mockUseConsumoPontuais.mockReturnValue({
    items,
    total: items.length,
    totalValor: items.reduce((acc, it) => acc + it.valor, 0),
    isLoading: false,
    error: null,
  });
  return render(<ConsumoConscienteCard consumo={undefined} />);
}

describe("<ConsumoConscienteCard />", () => {
  it("humaniza a categoria de cada gasto pontual (keys do payload dogfood)", () => {
    renderWithItems([
      item("nao_identificado", 5000, 1),
      item("lazer_viagens", 4000, 2),
      item("das_simples", 3000, 3),
      item("aporte_investimento", 2500, 4),
    ]);

    expect(screen.getByText(/Não identificado/)).toBeInTheDocument();
    expect(screen.getByText(/Lazer e viagens/)).toBeInTheDocument();
    expect(screen.getByText(/DAS \(Simples Nacional\)/)).toBeInTheDocument();
    expect(screen.getByText(/Aporte em investimentos/)).toBeInTheDocument();

    // Regressão: código cru do endpoint não pode vazar para a UI.
    expect(screen.queryByText(/nao_identificado/)).toBeNull();
    expect(screen.queryByText(/lazer_viagens/)).toBeNull();
    expect(screen.queryByText(/das_simples/)).toBeNull();
    expect(screen.queryByText(/aporte_investimento/)).toBeNull();
  });

  it("KR-B: categoria desconhecida cai em fallback sem `_` e sem inicial minúscula", () => {
    renderWithItems([item("categoria_futura_desconhecida", 2100, 1)]);

    const meta = screen.getByText(/2026-04-15/);
    const rendered = meta.textContent ?? "";
    expect(rendered).not.toMatch(/_/);
    // após o separador "· ", o label não inicia com minúscula-código
    const label = rendered.split("·")[1]?.trim() ?? "";
    expect(label.charAt(0)).not.toMatch(/[a-z]/);
  });

  it("mantém 'sem categoria' quando o item vem sem categoria", () => {
    const semCategoria = { ...item("", 2100, 1), categoria: "" };
    renderWithItems([semCategoria]);
    expect(screen.getByText(/sem categoria/)).toBeInTheDocument();
  });
});
