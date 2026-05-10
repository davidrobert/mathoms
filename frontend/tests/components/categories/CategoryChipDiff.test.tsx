/**
 * Unit tests — CategoryChipDiff (A11.cat-overrides-ux W4 · ADR-185).
 *
 * Cobre Set diff client-side: 3 estados (default/added/removed) + edge
 * cases de normalização (whitespace, dedupe). Componente é puro — não
 * exige MSW nem WorkspaceProvider.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CategoryChipDiff } from "@/components/categories/CategoryChipDiff";

describe("<CategoryChipDiff />", () => {
  it("renderiza chips default quando current === defaults", () => {
    render(
      <CategoryChipDiff
        current={["ALUGUEL", "IPTU"]}
        defaultKeywords={["ALUGUEL", "IPTU"]}
        onChange={vi.fn()}
      />,
    );
    const defaults = screen.getAllByTestId("chip-default");
    expect(defaults).toHaveLength(2);
    expect(screen.queryByTestId("chip-added")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chip-removed")).not.toBeInTheDocument();
  });

  it("marca keyword extra como 'added'", () => {
    render(
      <CategoryChipDiff
        current={["ALUGUEL", "IPTU", "CONDOMINIO"]}
        defaultKeywords={["ALUGUEL", "IPTU"]}
        onChange={vi.fn()}
      />,
    );
    const added = screen.getByTestId("chip-added");
    expect(added.textContent).toContain("CONDOMINIO");
  });

  it("escondida no accordion quando keyword default foi removida", async () => {
    const user = userEvent.setup();
    render(
      <CategoryChipDiff
        current={["ALUGUEL"]}
        defaultKeywords={["ALUGUEL", "IPTU"]}
        onChange={vi.fn()}
      />,
    );
    // Removida não fica visível inicialmente.
    expect(screen.queryByTestId("chip-removed")).not.toBeInTheDocument();
    const trigger = screen.getByText(/removida do padrão/);
    await user.click(trigger);
    const removed = screen.getByTestId("chip-removed");
    expect(removed.textContent).toContain("IPTU");
  });

  it("normaliza whitespace antes do diff (trim)", () => {
    render(
      <CategoryChipDiff
        current={["  ALUGUEL  ", "iptu"]}
        defaultKeywords={["ALUGUEL", "iptu"]}
        onChange={vi.fn()}
      />,
    );
    // Após .trim() ambos batem com defaults — sem 'added' nem 'removed'.
    expect(screen.queryByTestId("chip-added")).not.toBeInTheDocument();
    expect(screen.queryByText(/removida do padrão/)).not.toBeInTheDocument();
  });

  it("adicionar keyword chama onChange com lista deduplicada", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <CategoryChipDiff
        current={["ALUGUEL"]}
        defaultKeywords={["ALUGUEL"]}
        onChange={onChange}
      />,
    );
    const input = screen.getByLabelText("Adicionar keyword");
    await user.type(input, "NOVA_KW");
    await user.click(screen.getByLabelText("Adicionar"));
    expect(onChange).toHaveBeenCalledWith(["ALUGUEL", "NOVA_KW"]);
  });

  it("remover chip chama onChange filtrado", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <CategoryChipDiff
        current={["ALUGUEL", "IPTU"]}
        defaultKeywords={["ALUGUEL", "IPTU"]}
        onChange={onChange}
      />,
    );
    const removeBtn = screen.getByLabelText("Remover ALUGUEL");
    await user.click(removeBtn);
    expect(onChange).toHaveBeenCalledWith(["IPTU"]);
  });

  it("readOnly desativa controles", () => {
    render(
      <CategoryChipDiff
        current={["ALUGUEL"]}
        defaultKeywords={["ALUGUEL"]}
        onChange={vi.fn()}
        readOnly
      />,
    );
    expect(screen.queryByLabelText("Adicionar keyword")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Remover ALUGUEL")).not.toBeInTheDocument();
  });

  it("estado vazio ('Sem keywords ativas') quando current vazio e defaults vazios", () => {
    render(
      <CategoryChipDiff
        current={[]}
        defaultKeywords={[]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/Sem keywords ativas/)).toBeInTheDocument();
  });
});
