// A40.l89 · ADR-399 D1 — KPI órfão perde o comparador, não a linha.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ParecerMetricasTable } from "@/components/report/sections/SParecer/ParecerMetricasTable";
import type { Metrica } from "@/lib/api/planner-review";

function metrica(over: Partial<Metrica> = {}): Metrica {
  return {
    nome: "Rentabilidade da carteira (TRS efetiva)",
    valor_atual: "1,7%",
    target: null,
    target_motivo: "rentabilidade observada não tem alvo canônico",
    frequencia_revisao: "trimestral",
    section_id: "S7",
    tema_canonico: "Renda passiva",
    ...over,
  };
}

describe("ParecerMetricasTable — KPI sem alvo canônico", () => {
  it("mostra o motivo no lugar do alvo, nunca célula vazia", () => {
    render(<ParecerMetricasTable metricas={[metrica()]} />);

    // Vazio o leitor lê como "não mediram" — afirmação diferente de "não afirmamos".
    expect(screen.getByText("Não afirmamos um alvo")).toBeInTheDocument();
    expect(
      screen.getByText("rentabilidade observada não tem alvo canônico"),
    ).toBeInTheDocument();
  });

  it("mantém a linha e o valor observado", () => {
    render(<ParecerMetricasTable metricas={[metrica()]} />);

    expect(
      screen.getByText("Rentabilidade da carteira (TRS efetiva)"),
    ).toBeInTheDocument();
    expect(screen.getByText("1,7%")).toBeInTheDocument();
  });

  it("não renderiza a trilha e anuncia a ausência ao leitor de tela", () => {
    const { container } = render(<ParecerMetricasTable metricas={[metrica()]} />);

    // `—` sozinho é o único portador de significado e some para o SR (1.3.1).
    expect(container.querySelector("progress")).toBeNull();
    expect(screen.getByText("Sem trilha")).toBeInTheDocument();
    expect(container.querySelector('tr[data-alvo="ausente"]')).not.toBeNull();
  });

  it("não quebra a página quando o alvo é nulo", () => {
    // `extractNumber(null)` sem guarda lança TypeError, e o único ErrorBoundary é
    // de rota — derrubaria o relatório inteiro, não só a seção.
    expect(() =>
      render(<ParecerMetricasTable metricas={[metrica({ valor_atual: null })]} />),
    ).not.toThrow();
  });

  it("serve o alvo quando ele tem procedência", () => {
    render(<ParecerMetricasTable metricas={[metrica({ target: "≥ 18 meses" })]} />);

    expect(screen.getByText("≥ 18 meses")).toBeInTheDocument();
    expect(screen.queryByText("Não afirmamos um alvo")).toBeNull();
  });
});
