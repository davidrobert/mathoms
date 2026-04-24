/**
 * ADR-117 · Fase 3 — smoke tests dos primitivos UI do relatório.
 *
 * Canvas (ScoreCard usa ChartGaugeSemi) não é testado visualmente — jsdom
 * não tem HTMLCanvasElement.getContext. Testes focam em: render sem erro,
 * roles ARIA corretos, computação de status (deadlineStatus), handlers.
 */
import { describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  Alert,
  Badge,
  IconBadge,
  SectionDivider,
  KpiCard,
  KpiGrid,
  KpiStrip,
  PontoForteItem,
  PontosFortesList,
  CollapsibleSectionHeader,
  SplitCards,
  ComparisonBlock,
  PriorityBadge,
  DeadlineBadge,
  deadlineStatus,
  EffortBadge,
  Timeline,
  ChangelogList,
  Kanban,
  NotasCard,
  NotasInsightsGrid,
  NotasInsightCard,
} from "@/components/report/ui";

describe("<Alert />", () => {
  it("usa role=alert em severity=danger", () => {
    render(<Alert severity="danger">Crítico</Alert>);
    expect(screen.getByRole("alert")).toHaveTextContent("Crítico");
  });
  it("usa role=status em demais severities", () => {
    render(<Alert severity="info">Info</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Info");
  });
});

describe("<Badge />", () => {
  it("renderiza conteúdo + data-badge-color", () => {
    const { container } = render(<Badge color="yellow">alpha</Badge>);
    expect(container.querySelector("[data-badge-color='yellow']")).toBeInTheDocument();
  });
});

describe("<IconBadge />", () => {
  it("aplica role=img quando ariaLabel presente", () => {
    render(<IconBadge ariaLabel="Check">✓</IconBadge>);
    expect(screen.getByRole("img", { name: "Check" })).toBeInTheDocument();
  });
});

describe("<SectionDivider />", () => {
  it("renderiza role=separator", () => {
    render(<SectionDivider icon="§" ariaLabel="Fim" />);
    expect(screen.getByRole("separator", { name: "Fim" })).toBeInTheDocument();
  });
});

describe("KPI family", () => {
  it("KpiCard mostra label + value", () => {
    render(<KpiCard label="Total" value="R$ 100" />);
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("R$ 100")).toBeInTheDocument();
  });
  it("KpiCard hero aplica data-kpi-hero", () => {
    const { container } = render(<KpiCard label="X" value="1" hero />);
    expect(container.querySelector("[data-kpi-hero]")).toBeInTheDocument();
  });
  it("KpiGrid aplica grid columns", () => {
    const { container } = render(
      <KpiGrid columns={6}>
        <KpiCard label="a" value="1" />
      </KpiGrid>,
    );
    const grid = container.firstElementChild as HTMLElement;
    expect(grid.style.gridTemplateColumns).toContain("6");
  });
  it("KpiStrip renderiza todos items", () => {
    render(
      <KpiStrip
        items={[
          { label: "A", value: "1" },
          { label: "B", value: "2", tone: "gap" },
          { label: "C", value: "3", progress: 0.5 },
        ]}
      />,
    );
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("C")).toBeInTheDocument();
  });
});

describe("<PontoForteItem />", () => {
  it("renderiza titulo + descricao", () => {
    render(
      <PontosFortesList>
        <PontoForteItem titulo="Reserva OK" descricao="12 meses cobertos" />
      </PontosFortesList>,
    );
    expect(screen.getByText("Reserva OK")).toBeInTheDocument();
    expect(screen.getByText("12 meses cobertos")).toBeInTheDocument();
  });
});

describe("<CollapsibleSectionHeader />", () => {
  it("chama onToggle no clique e aria-expanded reflete collapsed", async () => {
    const onToggle = vi.fn();
    const user = userEvent.setup();
    render(
      <CollapsibleSectionHeader title="t" collapsed={false} onToggle={onToggle}>
        child
      </CollapsibleSectionHeader>,
    );
    const btn = screen.getByRole("button", { name: /t/i });
    expect(btn).toHaveAttribute("aria-expanded", "true");
    await user.click(btn);
    expect(onToggle).toHaveBeenCalledTimes(1);
  });
  it("quando collapsed, hint aparece e conteúdo fica hidden", () => {
    render(
      <CollapsibleSectionHeader
        title="t"
        collapsed
        onToggle={() => {}}
        hint="(6 cards)"
      >
        <div data-testid="payload">payload</div>
      </CollapsibleSectionHeader>,
    );
    expect(screen.getByText("(6 cards)")).toBeInTheDocument();
    expect(screen.getByTestId("payload").closest("[hidden]")).toBeTruthy();
  });
});

describe("<SplitCards /> / <ComparisonBlock />", () => {
  it("renderiza children e labels de comparação", () => {
    render(
      <>
        <SplitCards>
          <div data-testid="L">L</div>
          <div data-testid="R">R</div>
        </SplitCards>
        <ComparisonBlock
          before={{ label: "Antes", value: "A" }}
          after={{ label: "Depois", value: "B" }}
        />
      </>,
    );
    expect(screen.getByTestId("L")).toBeInTheDocument();
    expect(screen.getByTestId("R")).toBeInTheDocument();
    expect(screen.getByText("Antes")).toBeInTheDocument();
    expect(screen.getByText("Depois")).toBeInTheDocument();
  });
});

describe("Status badges", () => {
  it("PriorityBadge mostra label correto", () => {
    render(<PriorityBadge level="alta" />);
    expect(screen.getByText("Alta")).toBeInTheDocument();
  });
  it("EffortBadge compact mostra letra", () => {
    render(<EffortBadge effort="S" compact />);
    expect(screen.getByText("S")).toBeInTheDocument();
  });
  it("DeadlineBadge aplica data-deadline-status", () => {
    const { container } = render(<DeadlineBadge iso="2025-01-01" now={new Date("2026-04-24")} />);
    expect(container.querySelector("[data-deadline-status='vencida']")).toBeInTheDocument();
  });
});

describe("deadlineStatus()", () => {
  const now = new Date("2026-04-24T12:00:00Z");
  it("vencida quando iso está no passado", () => {
    expect(deadlineStatus("2026-04-20", now)).toBe("vencida");
  });
  it("urgente em até 7 dias", () => {
    expect(deadlineStatus("2026-04-28", now)).toBe("urgente");
  });
  it("ok em mais de 7 dias", () => {
    expect(deadlineStatus("2026-05-10", now)).toBe("ok");
  });
  it("retorna ok para ISO inválido", () => {
    expect(deadlineStatus("not-a-date", now)).toBe("ok");
  });
});

describe("<Timeline />", () => {
  it("renderiza <ol> com N items", () => {
    render(
      <Timeline
        items={[
          { id: "1", date: "24/04", action: "A", status: "feito" },
          { id: "2", date: "25/04", action: "B", status: "pendente" },
        ]}
      />,
    );
    expect(screen.getByRole("list").children.length).toBe(2);
  });
});

describe("<ChangelogList />", () => {
  it("renderiza ciclo + entries", () => {
    render(
      <ChangelogList
        ciclo="Q2/2026"
        entries={[{ id: "e1", headline: "Mudou X" }]}
      />,
    );
    expect(screen.getByText("Q2/2026")).toBeInTheDocument();
    expect(screen.getByText("Mudou X")).toBeInTheDocument();
  });
});

describe("<Kanban />", () => {
  it("distribui items em 3 colunas e chama onMove", async () => {
    const onMove = vi.fn();
    const user = userEvent.setup();
    render(
      <Kanban
        onMove={onMove}
        items={[
          { id: "1", titulo: "A", coluna: "a_fazer" },
          { id: "2", titulo: "B", coluna: "em_andamento" },
          { id: "3", titulo: "C", coluna: "concluido" },
        ]}
      />,
    );
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("C")).toBeInTheDocument();
    await user.click(screen.getAllByLabelText(/Mover para Em andamento/i)[0]);
    expect(onMove).toHaveBeenCalledWith("1", "em_andamento");
  });
});

describe("<NotasCard />", () => {
  it("chama onChange após debounce", async () => {
    const onChange = vi.fn();
    vi.useFakeTimers();
    const { rerender } = render(
      <NotasCard value="" onChange={onChange} debounceMs={200} />,
    );
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "oi" } });
    expect(onChange).not.toHaveBeenCalled();
    await act(async () => {
      vi.advanceTimersByTime(250);
    });
    expect(onChange).toHaveBeenCalledWith("oi");
    vi.useRealTimers();
    rerender(<NotasCard value="oi" onChange={onChange} />);
  });
  it("maxChars trunca input", () => {
    const onChange = vi.fn();
    render(<NotasCard value="" onChange={onChange} maxChars={3} />);
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "abcdef" } });
    expect(textarea.value).toBe("abc");
  });
});

describe("<NotasInsightsGrid />", () => {
  it("renderiza 3 insight cards", () => {
    render(
      <NotasInsightsGrid>
        <NotasInsightCard tone="score" label="A" value="1" />
        <NotasInsightCard tone="cerbasi" label="B" value="2" />
        <NotasInsightCard tone="periodo" label="C" value="3" />
      </NotasInsightsGrid>,
    );
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("C")).toBeInTheDocument();
  });
});
