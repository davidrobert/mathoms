/**
 * Notas das pizzas do dashboard (`/plano` › Mês corrente).
 *
 * ADR-333: aporte é poupança, não consumo — sai das fatias de despesa, e a base da pizza
 * declara o valor que saiu dela.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PieNotes } from "@/app/(app)/plano/_components/_dashboard/PieNotes";

describe("PieNotes — base da pizza de despesas", () => {
  it("com aporte, declara o valor retirado", () => {
    render(<PieNotes notes={[{ kind: "base_despesas", janelaMeses: 12, aporteExcluido: 48000 }]} />);
    expect(screen.getByTestId("pie-notes")).toHaveTextContent(
      /^Últimos 12 meses documentados, sem os aportes em investimentos \(R\$\s48\.000\), que contam como poupança\.$/,
    );
  });

  it("sem aporte, só a base — no singular com um mês", () => {
    render(<PieNotes notes={[{ kind: "base_despesas", janelaMeses: 1, aporteExcluido: 0 }]} />);
    expect(screen.getByTestId("pie-notes")).toHaveTextContent(/^Último mês documentado\.$/);
  });
});
