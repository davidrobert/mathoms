/**
 * Report Premium UI v2.8 (ADR-148) — render dos componentes alimentados
 * pelo `SnapshotChangelogBuilder`: ComparisonItemsBlock + SnapshotChangelogList
 * + SectionSnapshotDiff (filtro por section_id).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  ComparisonItemsBlock,
  SnapshotChangelogList,
  type ComparisonItemView,
  type SnapshotChangelogEntryView,
} from "@/components/report/ui";
import { SectionSnapshotDiff } from "@/components/report/SectionSnapshotDiff";

describe("<ComparisonItemsBlock />", () => {
  it("não renderiza nada com items vazios", () => {
    const { container } = render(<ComparisonItemsBlock items={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza tabela com 3 linhas e sinais corretos (up/down/stable)", () => {
    const items: ComparisonItemView[] = [
      {
        section_id: "S1",
        section_label: "Patrimônio Líquido",
        before: 1_000_000,
        after: 1_100_000,
        delta_pct: 10.0,
        delta_signal: "up",
      },
      {
        section_id: "S2",
        section_label: "Receita Total",
        before: 50_000,
        after: 45_000,
        delta_pct: -10.0,
        delta_signal: "down",
      },
      {
        section_id: "T5",
        section_label: "Despesas Totais",
        before: 30_000,
        after: 30_100,
        delta_pct: 0.33,
        delta_signal: "stable",
      },
    ];
    const { container } = render(<ComparisonItemsBlock items={items} />);
    const rows = container.querySelectorAll("tbody tr");
    expect(rows.length).toBe(3);
    expect(rows[0].getAttribute("data-section-id")).toBe("S1");
    expect(rows[0].getAttribute("data-delta-signal")).toBe("up");
    expect(rows[1].getAttribute("data-delta-signal")).toBe("down");
    expect(rows[2].getAttribute("data-delta-signal")).toBe("stable");
    expect(screen.getByText("Patrimônio Líquido")).toBeInTheDocument();
    expect(screen.getByText("Receita Total")).toBeInTheDocument();
    expect(screen.getByText("Despesas Totais")).toBeInTheDocument();
  });
});

describe("<SnapshotChangelogList />", () => {
  it("não renderiza nada com entries vazias", () => {
    const { container } = render(<SnapshotChangelogList entries={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza <li> por entry com summary determinística", () => {
    const entries: SnapshotChangelogEntryView[] = [
      {
        section_id: "S1",
        summary: "Patrimônio Líquido cresceu 10,0% desde o relatório anterior",
        delta_signal: "up",
        delta_pct: 10.0,
      },
      {
        section_id: "S2",
        summary: "Receita Total caiu 10,0% desde o relatório anterior",
        delta_signal: "down",
        delta_pct: -10.0,
      },
    ];
    render(<SnapshotChangelogList entries={entries} />);
    const items = screen.getAllByRole("listitem");
    expect(items.length).toBe(2);
    expect(
      screen.getByText(/Patrimônio Líquido cresceu 10,0%/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Receita Total caiu 10,0%/),
    ).toBeInTheDocument();
  });
});

describe("<SectionSnapshotDiff />", () => {
  it("não renderiza nada quando comparisons/changelog são null", () => {
    const { container } = render(
      <SectionSnapshotDiff sectionId="S1" data={{ comparisons: null, changelog: null }} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("filtra items por sectionId e renderiza só os relevantes", () => {
    const data = {
      comparisons: [
        {
          section_id: "S1",
          section_label: "Patrimônio Líquido",
          before: 1_000_000,
          after: 1_100_000,
          delta_pct: 10.0,
          delta_signal: "up" as const,
        },
        {
          section_id: "S2",
          section_label: "Receita Total",
          before: 50_000,
          after: 55_000,
          delta_pct: 10.0,
          delta_signal: "up" as const,
        },
      ],
      changelog: [
        {
          section_id: "S1",
          summary: "Patrimônio Líquido cresceu 10,0% desde o relatório anterior",
          delta_signal: "up" as const,
          delta_pct: 10.0,
        },
      ],
    };
    render(<SectionSnapshotDiff sectionId="S1" data={data} />);
    expect(screen.getByTestId("section-snapshot-diff-S1")).toBeInTheDocument();
    expect(screen.getByText("Patrimônio Líquido")).toBeInTheDocument();
    // S2 não deve aparecer.
    expect(screen.queryByText("Receita Total")).not.toBeInTheDocument();
  });

  it("renderiza nada quando seção não tem items nem entries (todas estáveis)", () => {
    const data = {
      comparisons: [
        {
          section_id: "T5",
          section_label: "Despesas Totais",
          before: 30_000,
          after: 30_000,
          delta_pct: 0.0,
          delta_signal: "stable" as const,
        },
      ],
      changelog: [],
    };
    const { container } = render(<SectionSnapshotDiff sectionId="S1" data={data} />);
    // S1 não está em nenhum array; render nada.
    expect(container.firstChild).toBeNull();
  });
});
