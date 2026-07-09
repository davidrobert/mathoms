/**
 * V0 "O que mudou desde o último relatório" (SNAPSHOT_CHANGELOG_V3 W4/D6 ·
 * ADR-190 §Emenda 2026-07-09) — render do `VariacaoSection`: manchete neutra
 * do M_PL + tabela de indicadores formatada por unidade + rodapé de
 * completude. Substitui os testes de ComparisonItemsBlock/SnapshotChangelogList
 * /SectionSnapshotDiff (deletados em W4-T07).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { VariacaoSection } from "@/components/report/VariacaoSection";
import type { ComparisonItemRead, ReportAnalysisData } from "@/lib/api";

function makeItem(overrides: Partial<ComparisonItemRead>): ComparisonItemRead {
  return {
    section_id: "M_PL",
    section_label: "Patrimônio Líquido",
    before: 1_150_000,
    after: 1_200_000,
    delta_pct: 4.3,
    delta_signal: "up",
    direction_positive: "up",
    unit: "brl",
    ...overrides,
  };
}

const FULL_DATA: ReportAnalysisData = {
  comparisons: [
    makeItem({}),
    makeItem({
      section_id: "M_TAXA_POUPANCA",
      section_label: "Taxa de Poupança",
      before: 12.0,
      after: 15.0,
      delta_pct: 25.0,
      delta_signal: "up",
      direction_positive: "up",
      unit: "pp",
    }),
    makeItem({
      section_id: "M_RESERVA_MESES",
      section_label: "Reserva de Emergência",
      before: 5.8,
      after: 6.0,
      delta_pct: 3.4,
      delta_signal: "up",
      direction_positive: "up",
      unit: "meses",
    }),
    makeItem({
      section_id: "M_AUVP_DESVIO",
      section_label: "Desvio da Alocação Alvo",
      before: 8.0,
      after: 8.1,
      delta_pct: 1.3,
      delta_signal: "stable",
      direction_positive: "down",
      unit: "pp",
    }),
  ],
  comparison_periods: { current: "202604", previous: "202603" },
};

describe("<VariacaoSection /> — V0 (ADR-190 §Emenda)", () => {
  it("payload completo: manchete neutra + lista por unidade + rodapé de completude", () => {
    const { container } = render(<VariacaoSection data={FULL_DATA} />);

    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "O que mudou desde o último relatório",
      }),
    ).toBeInTheDocument();

    // Manchete M_PL: Δ = +R$ 50.000,00 com sinal explícito (Intl usa NBSP).
    const headline = screen.getByTestId("v0-headline");
    expect(headline.textContent).toMatch(/\+R\$\s*50\.000,00/);

    // Neutra: sem cor semântica de gain/loss e sem glifo de direção.
    const delta = screen.getByTestId("v0-headline-delta");
    expect(delta.className).not.toMatch(/text-gain|text-loss/);
    expect(headline.textContent).not.toMatch(/[▲▼]/);
    expect(headline.querySelector(".sr-only")?.textContent).toBe(
      "Patrimônio líquido variou R$\u00a050.000,00 a mais desde março de 2026",
    );

    // Caption obrigatória logo abaixo da manchete.
    expect(screen.getByTestId("v0-headline-caption").textContent).toBe(
      "Mostramos a variação total do patrimônio no período. A separação entre aporte, rendimento e efeito de mercado ainda não está disponível.",
    );

    // Lista: M_PL fora, stable fora — só taxa (pp) e reserva (meses).
    const rows = container.querySelectorAll("tbody tr");
    expect(rows.length).toBe(2);
    expect(screen.queryByText("Desvio da Alocação Alvo")).toBeNull();

    const taxaCells = container.querySelectorAll(
      'tr[data-section-id="M_TAXA_POUPANCA"] td',
    );
    expect(taxaCells[1].textContent).toBe("12,0%");
    expect(taxaCells[2].textContent).toBe("15,0%");
    expect(taxaCells[3].textContent).toContain("+3,0 pp");
    expect(taxaCells[3].textContent).toContain("▲");

    const reservaCells = container.querySelectorAll(
      'tr[data-section-id="M_RESERVA_MESES"] td',
    );
    expect(reservaCells[1].textContent).toBe("5,8 meses");
    expect(reservaCells[2].textContent).toBe("6,0 meses");
    expect(reservaCells[3].textContent).toContain("+0,2 mês");

    // Rodapé de completude (1 stable entre os não-headline).
    expect(screen.getByTestId("v0-stable-footer").textContent).toBe(
      "Outro indicador acompanhado permaneceu estável.",
    );
  });

  it("rodapé plural: 2+ stables entre os não-headline usam o template canônico", () => {
    const data: ReportAnalysisData = {
      comparisons: [
        makeItem({}),
        makeItem({
          section_id: "M_TAXA_POUPANCA",
          section_label: "Taxa de Poupança",
          delta_signal: "stable",
          unit: "pp",
        }),
        makeItem({
          section_id: "M_AUVP_DESVIO",
          section_label: "Desvio da Alocação Alvo",
          delta_signal: "stable",
          direction_positive: "down",
          unit: "pp",
        }),
      ],
      comparison_periods: { current: "202604", previous: "202603" },
    };
    render(<VariacaoSection data={data} />);
    expect(screen.getByTestId("v0-stable-footer").textContent).toBe(
      "Outros 2 indicadores acompanhados permaneceram estáveis.",
    );
    // Lista vazia mas M_PL presente → só manchete + caption, sem tabela.
    expect(screen.queryByTestId("v0-indicators-table")).toBeNull();
    expect(screen.getByTestId("v0-headline")).toBeInTheDocument();
  });

  it("sem M_PL: renderiza a lista direto, sem manchete", () => {
    const data: ReportAnalysisData = {
      comparisons: [
        makeItem({
          section_id: "M_TAXA_POUPANCA",
          section_label: "Taxa de Poupança",
          before: 12.0,
          after: 15.0,
          delta_signal: "up",
          unit: "pp",
        }),
      ],
      comparison_periods: { current: "202604", previous: "202603" },
    };
    render(<VariacaoSection data={data} />);
    expect(screen.queryByTestId("v0-headline")).toBeNull();
    expect(screen.queryByTestId("v0-headline-caption")).toBeNull();
    expect(screen.getByTestId("v0-indicators-table")).toBeInTheDocument();
    expect(screen.getByText("Taxa de Poupança")).toBeInTheDocument();
  });

  it("comparisons null (primeiro relatório) e vazio: seção não renderiza", () => {
    const { container: c1 } = render(
      <VariacaoSection data={{ comparisons: null, comparison_periods: null }} />,
    );
    expect(c1.firstChild).toBeNull();

    const { container: c2 } = render(<VariacaoSection data={{ comparisons: [] }} />);
    expect(c2.firstChild).toBeNull();
  });

  it("subtítulo com períodos reais formatados (yyyymm → mês por extenso)", () => {
    render(<VariacaoSection data={FULL_DATA} />);
    expect(screen.getByTestId("v0-subtitle").textContent).toBe(
      "Este relatório (abril de 2026) comparado ao anterior (março de 2026). Listamos apenas variações relevantes.",
    );
  });

  it("subtítulo genérico quando comparison_periods é null", () => {
    const data: ReportAnalysisData = {
      comparisons: [makeItem({})],
      comparison_periods: null,
    };
    render(<VariacaoSection data={data} />);
    expect(screen.getByTestId("v0-subtitle").textContent).toBe(
      "Comparado ao relatório anterior. Listamos apenas variações relevantes.",
    );
    expect(
      screen.getByTestId("v0-headline").querySelector(".sr-only")?.textContent,
    ).toBe(
      "Patrimônio líquido variou R$\u00a050.000,00 a mais desde o relatório anterior",
    );
  });

  it("regressão W2 (ADR-190 D3): pp subindo com direction_positive=down pinta vermelho", () => {
    const data: ReportAnalysisData = {
      comparisons: [
        makeItem({
          section_id: "M_AUVP_DESVIO",
          section_label: "Desvio da Alocação Alvo",
          before: 5.0,
          after: 8.0,
          delta_pct: 60.0,
          delta_signal: "up",
          direction_positive: "down",
          unit: "pp",
        }),
      ],
      comparison_periods: { current: "202604", previous: "202603" },
    };
    const { container } = render(<VariacaoSection data={data} />);
    const deltaCell = container.querySelector(
      'tr[data-section-id="M_AUVP_DESVIO"] td:last-child',
    ) as HTMLElement;
    expect(deltaCell.style.color).toBe("var(--semantic-danger)");
    // Glifo continua apontando a direção REAL do movimento (▲), só a cor julga.
    expect(deltaCell.textContent).toContain("▲");
    expect(deltaCell.textContent).toContain("+3,0 pp");
    expect(deltaCell.getAttribute("aria-label")).toBe(
      "Desvio da Alocação Alvo subiu 3,0 pp — avaliação ruim",
    );
  });

  it("manchete com variação negativa: sinal do Intl, aria 'a menos'", () => {
    const data: ReportAnalysisData = {
      comparisons: [makeItem({ before: 1_200_000, after: 1_150_000, delta_signal: "down" })],
      comparison_periods: { current: "202604", previous: "202603" },
    };
    render(<VariacaoSection data={data} />);
    const headline = screen.getByTestId("v0-headline");
    expect(headline.textContent).toMatch(/-R\$\s*50\.000,00/);
    expect(headline.querySelector(".sr-only")?.textContent).toBe(
      "Patrimônio líquido variou R$\u00a050.000,00 a menos desde março de 2026",
    );
  });
});
