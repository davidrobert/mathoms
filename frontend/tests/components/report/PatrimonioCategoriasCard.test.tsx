/**
 * A40.l71 (RV6-23) — render dos 3 estados na tabela de composição.
 *
 * Existe porque o spec de axe NÃO cobre isto: medido, remover o par `sr-only`
 * do travessão mantém `tests/a11y/accessibility.test.tsx` verde (célula com
 * travessão não é violação séria para o axe). Sem estas asserções o texto
 * acessível seria dead code na primeira refatoração.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PatrimonioCategoriasCard } from "@/components/report/cards/PatrimonioCategoriasCard";
import type { PatrimonioData } from "@/types/report-analysis";

function renderCard(
  composicao: { categoria: string; valor: number; pct: number }[],
) {
  return render(
    <PatrimonioCategoriasCard
      patrimonio={{ bruto: 50_000, composicao } as PatrimonioData}
    />,
  );
}

const POSITIVO = { categoria: "Veículos", valor: 50_000, pct: 100 };

describe("PatrimonioCategoriasCard — estados da composição", () => {
  it("não-apurado: travessão visual E texto lido pelo leitor de tela", () => {
    renderCard([{ categoria: "Investimentos Cônjuge", valor: 0, pct: 0 }]);

    expect(screen.getByText("Sem fonte apurada")).toBeDefined();
    expect(screen.getByText("— Sem fonte apurada para esta categoria.")).toBeDefined();
  });

  it("negativo: linha permanece, com nota de rodapé", () => {
    renderCard([{ categoria: "Outros imóveis", valor: -200_000, pct: 0 }]);

    const row = document.querySelector('[data-composition-state="negativo"]');
    expect(row).not.toBeNull();
    expect(
      screen.getByText(/Balde com valor negativo/),
    ).toBeDefined();
  });

  it("payload saudável não ganha nota de rodapé nenhuma", () => {
    renderCard([POSITIVO]);

    expect(screen.queryByText(/Balde com valor negativo/)).toBeNull();
    expect(screen.queryByText(/Sem fonte apurada/)).toBeNull();
    expect(
      document.querySelector('[data-composition-state="apurado"]'),
    ).not.toBeNull();
  });

  it("residência zerada não vira linha (ADR-215 P5, via predicado)", () => {
    renderCard([{ categoria: "Residência", valor: 0, pct: 0 }, POSITIVO]);

    expect(document.querySelectorAll("tbody tr")).toHaveLength(2); // 1 categoria + total
    expect(screen.queryByText("Residência")).toBeNull();
  });
});
