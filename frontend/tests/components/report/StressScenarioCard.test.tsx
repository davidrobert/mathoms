/**
 * A37.l10 (PD-09) — StressScenarioCard: guard do parágrafo "Leitura:" +
 * copy para delta negativo de aporte.
 *
 * Em produção o cenário SEMPRE reduz a capacidade de aporte
 * (`CenariosConjugeAnalyzer`: aporte = aporte_base × fator_reduzido, fator < 1),
 * então o delta de aporte é negativo — o código anterior só emitia fragmentos
 * com delta > 0 e renderizava "Leitura: . Reforce…".
 */
import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";

import { StressScenarioCard } from "@/components/report/cards/StressScenarioCard";

/** Valor exibido na linha `rotulo` da coluna `coluna` ("Cenário base" | "Cenário de estresse"). */
function valorNaColuna(coluna: string, rotulo: string): string {
  const col = screen.getByText(coluna).parentElement!;
  return within(col).getByText(rotulo).nextElementSibling?.textContent ?? "";
}

function cenariosNegativos() {
  return {
    labels: ["Sem renda do cônjuge"],
    aportes: [12000],
    prazos_if: [19.5],
    anos_if: [2046],
    premissas: { aporte_base: 20000 },
  };
}

describe("StressScenarioCard — Leitura (A37.l10 PD-09)", () => {
  it("delta de aporte negativo emite frase própria (regressão: 'Leitura: .')", () => {
    render(
      <StressScenarioCard
        cenarios={cenariosNegativos()}
        goals={{ if_prazo_anos: 14.2, if_ano: 2040 }}
      />,
    );
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura).not.toBeNull();
    expect(leitura?.textContent).toContain(
      "reduz a capacidade de aporte em 40%",
    );
    expect(leitura?.textContent).not.toMatch(/Leitura:\s*\./);
    expect(leitura?.textContent).toMatchSnapshot();
  });

  it("delta negativo sem prazo base ainda tem frase (payload real do dogfood)", () => {
    render(<StressScenarioCard cenarios={cenariosNegativos()} goals={undefined} />);
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura?.textContent).toContain("reduz a capacidade de aporte em 40%");
    expect(leitura?.textContent).not.toMatch(/Leitura:\s*\./);
  });

  it("delta positivo preserva a copy existente com joiner 'ou'", () => {
    render(
      <StressScenarioCard
        cenarios={{
          labels: ["Sem renda do cônjuge"],
          aportes: [18500],
          prazos_if: [19.5],
          anos_if: [2046],
          premissas: { aporte_base: 12000 },
        }}
        goals={{ if_prazo_anos: 14.2, if_ano: 2040 }}
      />,
    );
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura?.textContent).toContain("exige aporte 54% maior");
    expect(leitura?.textContent).toContain("ou estende a IF em 5a 4m");
  });

  it("só delta de prazo → frase com sujeito ('o cenário estende…')", () => {
    render(
      <StressScenarioCard
        cenarios={{
          labels: ["Sem renda do cônjuge"],
          aportes: [12000],
          prazos_if: [19.5],
          anos_if: [2046],
        }}
        goals={{ if_prazo_anos: 14.2, if_ano: 2040 }}
      />,
    );
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura?.textContent).toContain("o cenário estende a IF em 5a 4m");
  });

  it("sem nenhum fragmento (deltas zero) não renderiza 'Leitura:'", () => {
    render(
      <StressScenarioCard
        cenarios={{
          labels: ["Sem renda do cônjuge"],
          aportes: [12000],
          prazos_if: [14.2],
          anos_if: [2040],
          premissas: { aporte_base: 12000 },
        }}
        goals={{ if_prazo_anos: 14.2, if_ano: 2040 }}
      />,
    );
    expect(screen.queryByText(/Leitura:/)).toBeNull();
  });

  // ADR-373 D2: só retorno zero + aporte zero afirma inviabilidade; prazo ausente é
  // ausência, e "Não atinge" afirmava o que o payload não mede.
  it("prazo estresse 999 (legado) vira ausência, nunca delta nem fragmento de prazo", () => {
    render(
      <StressScenarioCard
        cenarios={{
          labels: ["Sem renda do cônjuge"],
          aportes: [12000],
          prazos_if: [999],
          anos_if: [3025],
          premissas: { aporte_base: 20000 },
        }}
        goals={{ if_prazo_anos: 14.2, if_ano: 2040 }}
      />,
    );
    expect(screen.queryByText("Não atinge")).toBeNull();
    expect(valorNaColuna("Cenário de estresse", "Prazo até IF")).toBe("—");
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura?.textContent).toContain("reduz a capacidade de aporte em 40%");
    expect(leitura?.textContent).not.toContain("estende a IF");
  });

  // Forma atual da não-convergência (PR #1158): o E5 emite null onde antes vinha
  // 999. Sem este ramo a coluna cairia num "—" mudo, perdendo o rótulo explícito.
  it("prazo estresse null é ausência, igual ao 999 legado", () => {
    render(
      <StressScenarioCard
        cenarios={{
          labels: ["Sem renda do cônjuge"],
          aportes: [12000],
          prazos_if: [null],
          anos_if: [null],
          premissas: { aporte_base: 20000 },
        }}
        goals={{ if_prazo_anos: 14.2, if_ano: 2040 }}
      />,
    );
    expect(screen.queryByText("Não atinge")).toBeNull();
    expect(valorNaColuna("Cenário de estresse", "Prazo até IF")).toBe("—");
    const leitura = screen.getByText(/Leitura:/).closest("p");
    expect(leitura?.textContent).toContain("reduz a capacidade de aporte em 40%");
    expect(leitura?.textContent).not.toContain("estende a IF");
  });
});

// Zero no lugar de ausente (COPY_GUIDELINES §4.3): sem meta de aporte, o card mostrava
// "R$ 0" nas duas colunas e "Não atinge" no prazo.
describe("StressScenarioCard — aporte não declarado", () => {
  const RESUMO_SEM_APORTE =
    "Quanto a perda da renda do cônjuge adia a independência financeira depende do " +
    "aporte mensal, que você ainda não declarou. Defina sua meta de aporte mensal em " +
    "Meu Plano → Aportes.";

  it("forma atual (null): o corpo é só a nota com o resumo do payload", () => {
    render(
      <StressScenarioCard
        cenarios={{
          labels: ["Sem renda do cônjuge"],
          aportes: [null],
          prazos_if: [null],
          anos_if: [null],
          premissas: { aporte_base: null },
          cenarios: [{ resumo: RESUMO_SEM_APORTE }],
        }}
      />,
    );
    expect(screen.getByRole("note")).toHaveTextContent(RESUMO_SEM_APORTE);
    expect(screen.queryByText("Cenário base")).toBeNull();
    expect(screen.queryByText(/R\$/)).toBeNull();
    expect(screen.queryByText("Não atinge")).toBeNull();
  });

  it("artefato legado (0): mostra ausência e nunca o resumo antigo com R$ 0,00", () => {
    render(
      <StressScenarioCard
        cenarios={{
          labels: ["Sem renda do cônjuge"],
          aportes: [0],
          prazos_if: [null],
          anos_if: [null],
          premissas: { aporte_base: 0 },
          cenarios: [{ resumo: "Sem renda do cônjuge, aporte cai para R$ 0,00/mês (66% do base)." }],
        }}
      />,
    );
    expect(screen.queryByRole("note")).toBeNull();
    expect(valorNaColuna("Cenário base", "Aporte mensal")).toBe("—");
    expect(valorNaColuna("Cenário de estresse", "Aporte mensal")).toBe("—");
    expect(valorNaColuna("Cenário de estresse", "Prazo até IF")).toBe("—");
    expect(screen.queryByText(/R\$/)).toBeNull();
    expect(screen.queryByText(/Leitura:/)).toBeNull();
  });
});
