/**
 * Percentual em copy pt-BR usa vírgula decimal (COPY_GUIDELINES §4.6) — os dois
 * cards trocados para `formatPercent` que não tinham arquivo de teste. Um arquivo
 * só porque o Vitest custa por arquivo, não por teste.
 *
 * Os demais call-sites da troca têm a asserção no teste do próprio componente.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ContrafluxoCard } from "@/components/report/cards/ContrafluxoCard";
import { EquilibrioCerbasiCard } from "@/components/report/cards/EquilibrioCerbasiCard";
import { PERCENTUAL_COM_PONTO } from "../../shared/percentualPtBr";

describe("<ContrafluxoCard /> — percentual pt-BR", () => {
  it("subtítulo (2 casas) e tabela de cenários (1 casa) usam vírgula", () => {
    const { container } = render(
      <ContrafluxoCard
        contrafluxo={{
          selic_atual: 10.75,
          cenarios: { base: { selic: 10.5, cdi: 10.4 } },
        }}
        cdi_anual={10.65}
      />,
    );

    expect(screen.getByText("Selic atual: 10,75% a.a. | CDI: 10,65%")).toBeInTheDocument();
    expect(screen.getByText("10,5%")).toBeInTheDocument();
    expect(screen.getByText("10,4%")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
  });
});

describe("<EquilibrioCerbasiCard /> — percentual pt-BR", () => {
  // O produtor arredonda para 1 casa (`equilibrio_cerbasi_analyzer.py`): o número
  // cru interpolado saía "Presente (62.5%)" sem passar por `toFixed` nenhum.
  it("rótulos e aria-label usam vírgula; a largura da barra continua CSS", () => {
    const { container } = render(
      <EquilibrioCerbasiCard
        equilibrio={{ pct_presente: 62.5, pct_futuro: 37.5, classificacao: "Equilibrado" }}
      />,
    );

    expect(screen.getByText("Presente (62,5%)")).toBeInTheDocument();
    expect(screen.getByText("Futuro (37,5%)")).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: "Distribuição do fluxo: 62,5% para o presente, 37,5% para o futuro",
      }),
    ).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
    // `width: 62,5%` é declaração CSS inválida — a barra sumiria.
    const barra = container.querySelector<HTMLElement>('[role="img"] > div');
    expect(barra?.style.width).toBe("62.5%");
  });
});
