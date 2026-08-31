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

function item(
  categoria: string,
  valor: number,
  i: number,
): ConsumoPontuaisItem {
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

/**
 * A40.l98 ([[ADR-425]] §D2) — a base declara o que exclui NA SUPERFÍCIE que a
 * publica. Sem esta linha o KPI "Gastos pontuais" é um número cujo denominador
 * o leitor não conhece: eram três produtores com filtros disjuntos, e o que
 * prescreve era o que menos filtrava.
 */
describe("<ConsumoConscienteCard /> · declaração da base", () => {
  const CONSUMO = {
    total_pontuais: 46000,
    total_pontuais_janela: 16000,
    folga_mensal: 14250,
    folga_pct: 71.25,
    equivalente_meses_poupanca: 1.1,
    analise: "",
    janela: "12m",
    janela_meses: 12,
    base_pontuais: {
      bruto: { valor: 127000, contagem: 18 },
      publicado: { valor: 46000, contagem: 3 },
      excluidos: {
        recorrente: { valor: 65000, contagem: 13 },
        transferencia_por_categoria: { valor: 16000, contagem: 2 },
        nao_identificado: { valor: 7000, contagem: 1 },
      },
      cobertura_nivel: "parcial",
      cobertura_motivo: null,
    },
  };

  function renderComBase(consumo: unknown) {
    mockUseConsumoPontuais.mockReturnValue({
      items: [],
      total: 0,
      totalValor: 0,
      isLoading: false,
      error: null,
    });
    return render(
      <ConsumoConscienteCard
        consumo={
          consumo as Parameters<typeof ConsumoConscienteCard>[0]["consumo"]
        }
      />,
    );
  }

  it("imprime cada causa de exclusão com valor e contagem", () => {
    const { container } = renderComBase(CONSUMO);
    const linha = container.querySelector("[data-consumo-base-declaracao]");
    expect(linha).not.toBeNull();
    const texto = linha!.textContent!.replace(/ /g, " ");
    expect(texto).toContain("18 lançamentos");
    expect(texto).toMatch(/recorrentes R\$\s?65\.000 \(13\)/);
    expect(texto).toMatch(/transferências R\$\s?16\.000 \(2\)/);
    // [[ADR-425]] §D1 — o residual não medido é impresso ONDE a base aparece.
    expect(texto).toMatch(/não classificados R\$\s?7\.000 \(1\)/);
    // A população e o escopo temporal vão IMPRESSOS ao lado do número (ADR-306 D1).
    expect(texto).toContain("período completo");
    expect(texto).toContain("cobertura parcial");
  });

  it("nível `null` não vira 'alta' — some, em vez de afirmar cobertura que não houve", () => {
    const { container } = renderComBase({
      ...CONSUMO,
      base_pontuais: {
        ...CONSUMO.base_pontuais,
        cobertura_nivel: null,
        cobertura_motivo: "sem_base_medivel: nenhum lançamento acima do limiar",
      },
    });
    const texto = container.querySelector(
      "[data-consumo-base-declaracao]",
    )!.textContent!;
    expect(texto).not.toMatch(/cobertura/);
    expect(texto).toContain("período completo");
  });

  it("some quando nada foi excluído — linha vazia seria ruído", () => {
    const { container } = renderComBase({
      ...CONSUMO,
      base_pontuais: {
        bruto: { valor: 46000, contagem: 3 },
        publicado: { valor: 46000, contagem: 3 },
        excluidos: {},
      },
    });
    expect(
      container.querySelector("[data-consumo-base-declaracao]"),
    ).toBeNull();
  });

  it("não quebra em payload anterior à lane (sem `base_pontuais`)", () => {
    const { base_pontuais: _omitido, ...semBase } = CONSUMO;
    const { container } = renderComBase(semBase);
    expect(
      container.querySelector("[data-consumo-base-declaracao]"),
    ).toBeNull();
    expect(screen.getByText("Equiv. meses de poupança")).toBeInTheDocument();
  });
});
