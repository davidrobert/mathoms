/**
 * v2.E.1 — specs do `<PeriodToggle>` segmented control.
 *
 * Cobre: render dos 4 botões com active correto, click dispara `onChange`,
 * `periodLabel` renderiza quando passado, click no botão já ativo é no-op.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PeriodToggle } from "@/components/report/ui/PeriodToggle";
import type { Period } from "@/components/report/ui/PeriodToggle";

describe("<PeriodToggle />", () => {
  it("renderiza 4 botões com label correto e marca o ativo", () => {
    const onChange = vi.fn<(p: Period) => void>();
    render(<PeriodToggle value="12m" onChange={onChange} />);

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(4);
    expect(tabs.map((t) => t.textContent)).toEqual(["3M", "6M", "12M", "Ano"]);

    const active = tabs.find((t) => t.getAttribute("aria-selected") === "true");
    expect(active?.textContent).toBe("12M");
  });

  it("click em outro período chama onChange com o id correto", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn<(p: Period) => void>();
    render(<PeriodToggle value="12m" onChange={onChange} />);

    await user.click(screen.getByRole("tab", { name: "6M" }));
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith("6m");

    await user.click(screen.getByRole("tab", { name: "Ano" }));
    expect(onChange).toHaveBeenLastCalledWith("ytd");
  });

  it("click no botão já ativo é no-op (não chama onChange)", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn<(p: Period) => void>();
    render(<PeriodToggle value="3m" onChange={onChange} />);

    await user.click(screen.getByRole("tab", { name: "3M" }));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("renderiza `periodLabel` quando passado", () => {
    render(
      <PeriodToggle value="12m" onChange={() => undefined} periodLabel="26/02 — 26/04" />,
    );
    expect(screen.getByText("26/02 — 26/04")).toBeInTheDocument();
  });

  it("não renderiza periodLabel quando ausente", () => {
    const { container } = render(<PeriodToggle value="12m" onChange={() => undefined} />);
    expect(container.querySelector("[data-period-label]")).toBeNull();
  });

  it("aceita className custom no container", () => {
    const { container } = render(
      <PeriodToggle value="12m" onChange={() => undefined} className="custom-cls" />,
    );
    expect(container.querySelector(".custom-cls")).toBeInTheDocument();
  });
});
