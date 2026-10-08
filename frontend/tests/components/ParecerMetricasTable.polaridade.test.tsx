// A40.l92 — a trilha não pode encher conforme a métrica de teto piora.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ParecerMetricasTable } from "@/components/report/sections/SParecer/ParecerMetricasTable";
import type { Comparador, Metrica } from "@/lib/api/planner-review";

function endividamento(over: Partial<Metrica> = {}): Metrica {
  return {
    nome: "Taxa de endividamento (% do patrimônio bruto)",
    valor_atual: "45,0%",
    target: "≤ 20,0%",
    target_motivo: null,
    comparador: null,
    nivel_confianca: null,
    frequencia_revisao: "trimestral",
    section_id: "S2",
    tema_canonico: "Saúde de balanço",
    ...over,
  };
}

const TETO_VIOLADO: Comparador = { operador: "<=", conforme: false, progresso_pct: null };

function progresso(container: HTMLElement): HTMLProgressElement | null {
  return container.querySelector("progress");
}

describe("ParecerMetricasTable — polaridade do comparador", () => {
  it("teto violado em 25pp não desenha trilha cheia", () => {
    const { container } = render(
      <ParecerMetricasTable metricas={[endividamento({ comparador: TETO_VIOLADO })]} />,
    );

    expect(progresso(container)).toBeNull();
    expect(screen.getByText("Acima do limite")).toBeInTheDocument();
  });

  it("teto conforme diz o limite e também não tem barra", () => {
    const { container } = render(
      <ParecerMetricasTable
        metricas={[
          endividamento({
            valor_atual: "12,0%",
            comparador: { operador: "<=", conforme: true, progresso_pct: null },
          }),
        ]}
      />,
    );

    expect(progresso(container)).toBeNull();
    expect(screen.getByText("Dentro do limite")).toBeInTheDocument();
  });

  // O mesmo dado com o operador trocado: a direção vem do campo, não da string.
  it("o operador de piso faz a barra aparecer sobre o mesmo par de números", () => {
    const { container } = render(
      <ParecerMetricasTable
        metricas={[
          endividamento({
            target: "≥ 20,0%",
            comparador: { operador: ">=", conforme: true, progresso_pct: 100 },
          }),
        ]}
      />,
    );

    expect(progresso(container)?.value).toBe(100);
    expect(screen.getByText("Mínimo atingido")).toBeInTheDocument();
  });

  // 5,6 contra 6 meses: a barra a 93% lia "atingido" a 12px — por isso o status existe.
  it("piso abaixo do mínimo diz que não atingiu, com a barra como apoio", () => {
    const { container } = render(
      <ParecerMetricasTable
        metricas={[
          endividamento({
            nome: "Cobertura da reserva de emergência",
            valor_atual: "5,6 meses",
            target: "≥ 6,0 meses",
            comparador: { operador: ">=", conforme: false, progresso_pct: 93 },
          }),
        ]}
      />,
    );

    expect(screen.getByText("Abaixo do mínimo")).toBeInTheDocument();
    expect(progresso(container)?.value).toBe(93);
    expect(progresso(container)?.getAttribute("aria-valuetext")).toBe("5,6 meses de ≥ 6,0 meses");
  });

  it.each([
    ["alta", "Cobertura alta", "conforme"],
    ["parcial", "Cobertura parcial", "atencao"],
    ["insuficiente", "Cobertura insuficiente", "atencao"],
  ] as const)("despesas mostra o tier %s do produtor, nunca o veredito", (nivel, texto, tom) => {
    const { container } = render(
      <ParecerMetricasTable
        metricas={[
          endividamento({
            nome: "Despesas não identificadas (% do total, 12m)",
            valor_atual: "12,0%",
            target: null,
            target_motivo: "mede a leitura do relatório, não a família",
            nivel_confianca: nivel,
          }),
        ]}
      />,
    );

    expect(screen.getByText(texto)).toBeInTheDocument();
    expect(screen.queryByText("Acima do limite")).toBeNull();
    expect(container.querySelector(`[data-situacao="${tom}"]`)).not.toBeNull();
    expect(screen.getByText("Não afirmamos um alvo")).toBeInTheDocument();
  });

  // Parecer de era anterior ao campo: a leitura subtrai, e o front não reconstrói a
  // situação a partir de `target` — que era exatamente a regex que comia o glifo.
  it("sem comparador não desenha barra nem status, mesmo com alvo e valor presentes", () => {
    const { container } = render(<ParecerMetricasTable metricas={[endividamento()]} />);

    expect(progresso(container)).toBeNull();
    expect(screen.getByText("Sem comparação publicada")).toBeInTheDocument();
    expect(screen.queryByText("Acima do limite")).toBeNull();
  });

  it("a coluna se chama Situação", () => {
    render(<ParecerMetricasTable metricas={[endividamento({ comparador: TETO_VIOLADO })]} />);

    expect(screen.getByRole("columnheader", { name: "Situação" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Trilha" })).toBeNull();
  });
});
