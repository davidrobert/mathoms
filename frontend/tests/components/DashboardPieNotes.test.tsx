/**
 * Notas das pizzas do dashboard (`/plano` › Mês corrente).
 *
 * ADR-439 D2: a nota da residência não apurada diz a DIREÇÃO do erro — em três dos
 * motivos o valor da casa está, ou pode estar, dentro da fatia "Outros imóveis", cujo
 * rótulo afirma o contrário; em `sem_valor` ele fica fora do patrimônio. ADR-333: a base
 * da pizza de despesas declara o aporte que saiu dela.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PieNotes } from "@/app/(app)/plano/_components/_dashboard/PieNotes";
import type { MotivoBaldeImovel } from "@/types/report-analysis";

function renderResidencia(motivo: MotivoBaldeImovel) {
  render(<PieNotes notes={[{ kind: "residencia_nao_apurada", motivo }]} />);
  return screen.getByTestId("pie-notes");
}

describe("PieNotes — residência não apurada", () => {
  it.each([
    ["nao_classificada", /todos os imóveis contam em Outros imóveis/],
    ["nao_declarada", /todos os imóveis contam em Outros imóveis/],
    ["nao_localizada", /pode estar em Outros imóveis/],
    ["sem_valor", /fica fora do patrimônio/],
  ] as const)("%s diz para onde foi o valor", (motivo, direcao) => {
    expect(renderResidencia(motivo)).toHaveTextContent(direcao);
  });

  it("falta indicar a residência leva à ação", () => {
    renderResidencia("nao_declarada");
    expect(screen.getByRole("link", { name: "Marcar residência" })).toHaveAttribute(
      "href",
      "/config?tab=members",
    );
  });
});

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
