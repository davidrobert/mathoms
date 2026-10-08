// A40.l92 — a trilha não pode encher conforme a métrica de teto piora.
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ParecerMetricasTable } from "@/components/report/sections/SParecer/ParecerMetricasTable";
import type { Metrica } from "@/lib/api/planner-review";

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

describe("ParecerMetricasTable — polaridade do comparador", () => {
  it("teto violado em 25pp não desenha trilha cheia", () => {
    const { container } = render(<ParecerMetricasTable metricas={[endividamento()]} />);

    expect(container.querySelector("progress")).toBeNull();
  });
});
