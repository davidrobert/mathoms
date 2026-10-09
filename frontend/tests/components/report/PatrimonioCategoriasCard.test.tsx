/**
 * A40.l71 (RV6-23) — render dos 3 estados na tabela de composição.
 *
 * Existe porque o spec de axe NÃO cobre isto: medido, remover o par `sr-only`
 * do travessão mantém `tests/a11y/accessibility.test.tsx` verde (célula com
 * travessão não é violação séria para o axe). Sem estas asserções o texto
 * acessível seria dead code na primeira refatoração.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { PatrimonioCategoriasCard } from "@/components/report/cards/PatrimonioCategoriasCard";
import type { PatrimonioData } from "@/types/report-analysis";
import { PERCENTUAL_COM_PONTO } from "../../shared/percentualPtBr";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: unknown; href: string }) => (
    <a href={href}>{children as never}</a>
  ),
}));

function renderCard(
  composicao: { categoria: string; valor: number; pct: number; [k: string]: unknown }[],
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

  // A linha "Total Bruto" já dizia "100,0%"; as linhas da mesma coluna, "42.9%".
  it("percentual da linha usa vírgula decimal, como o total (pt-BR)", () => {
    const { container } = renderCard([
      { categoria: "Veículos", valor: 21_430, pct: 42.86 },
      { categoria: "Caixa e Moeda Estrangeira", valor: 28_570, pct: 57.14 },
    ]);

    expect(screen.getByText("42,9%")).toBeDefined();
    expect(screen.getByText("57,1%")).toBeDefined();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
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

describe("PatrimonioCategoriasCard — residência não apurada (ADR-439 D2)", () => {
  const residencia = (motivo: string) => ({
    categoria: "Residência",
    valor: 0,
    pct: 0,
    estado: "nao_apurado",
    motivo,
  });

  it("não localizada: diz onde pode estar o valor, e a ação só vem com a condição de venda", () => {
    renderCard([residencia("nao_localizada"), POSITIVO]);

    expect(screen.getByText("Não apurada")).toBeDefined();
    expect(screen.getByText(/não localizamos na declaração o imóvel marcado/)).toBeDefined();
    expect(screen.getByText(/Se ele foi vendido ou transferido, a marcação ficou desatualizada/)).toBeDefined();
    expect(screen.getByRole("link", { name: /Atualizar residência/ })).toBeDefined();
    expect(screen.queryByText("— Sem fonte apurada para esta categoria.")).toBeNull();
  });

  it("não declarada: o CTA da ADR-215 aparece pela primeira vez no relatório", () => {
    renderCard([residencia("nao_declarada"), POSITIVO]);

    const link = screen.getByRole("link", { name: /Indicar residência/ });
    expect(link.getAttribute("href")).toBe("/config?tab=members");
  });

  // A frase antiga não dizia direção nenhuma; as duas formas do motivo apontam para lados opostos.
  it("sem valor: diz a direção do erro nos dois ramos", () => {
    renderCard([residencia("sem_valor"), POSITIVO]);

    expect(screen.getByText(/Se ainda é próprio, ficou fora da soma, e o patrimônio real é maior/)).toBeDefined();
    expect(screen.getByText(/Se foi vendido ou transferido, a residência atual pode estar em Outros imóveis/)).toBeDefined();
  });

  // O travessão casa a nota com a célula `—` só para quem vê; lido, abriria a frase.
  it("o travessão do rodapé não chega ao leitor de tela", () => {
    renderCard([residencia("nao_declarada"), POSITIVO]);

    const nota = screen.getByTestId("nota-residencia-nao-apurada");
    expect(nota.querySelector('[aria-hidden="true"]')?.textContent).toBe("— ");
  });
});
