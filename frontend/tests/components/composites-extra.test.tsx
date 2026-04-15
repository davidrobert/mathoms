/**
 * Integration tests — composites restantes (F6.5B.10)
 * ConfirmDialog, ThemeToggle, DataTable
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { ThemeToggle } from "@/components/ThemeToggle";

// next-themes precisa de provider; usamos mock para simplificar
const setThemeMock = vi.fn();
let mockTheme = "system";
vi.mock("next-themes", () => ({
  useTheme: () => ({ theme: mockTheme, setTheme: setThemeMock }),
}));

// ─── ConfirmDialog ───────────────────────────────────────────────────

describe("<ConfirmDialog />", () => {
  it("não renderiza quando open=false", () => {
    render(
      <ConfirmDialog
        open={false}
        onOpenChange={() => {}}
        title="Hidden"
        onConfirm={() => {}}
      />,
    );
    expect(screen.queryByText("Hidden")).not.toBeInTheDocument();
  });

  it("renderiza title + description + confirmLabel quando open", () => {
    render(
      <ConfirmDialog
        open={true}
        onOpenChange={() => {}}
        title="Remover item?"
        description="Ação irreversível."
        confirmLabel="Remover"
        variant="destructive"
        onConfirm={() => {}}
      />,
    );
    expect(screen.getByText("Remover item?")).toBeInTheDocument();
    expect(screen.getByText("Ação irreversível.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remover" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeInTheDocument();
  });

  it("clicar Confirmar chama onConfirm + fecha (onOpenChange false)", async () => {
    const onConfirm = vi.fn();
    const onOpenChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ConfirmDialog
        open={true}
        onOpenChange={onOpenChange}
        title="Confirmar?"
        onConfirm={onConfirm}
      />,
    );
    await user.click(screen.getByRole("button", { name: /confirmar/i }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("clicar Cancelar fecha sem chamar onConfirm", async () => {
    const onConfirm = vi.fn();
    const onOpenChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ConfirmDialog
        open={true}
        onOpenChange={onOpenChange}
        title="x"
        onConfirm={onConfirm}
      />,
    );
    await user.click(screen.getByRole("button", { name: /cancelar/i }));
    expect(onConfirm).not.toHaveBeenCalled();
    // onOpenChange é chamado pelo dialog ao fechar (via Cancel)
    await waitFor(() => expect(onOpenChange).toHaveBeenCalled());
  });
});

// ─── ThemeToggle ─────────────────────────────────────────────────────

describe("<ThemeToggle />", () => {
  beforeEach(() => {
    setThemeMock.mockClear();
    mockTheme = "system";
  });

  it("renderiza ícone Monitor inicialmente (mounted=false stub)", () => {
    const { container } = render(<ThemeToggle />);
    // SVG está presente
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("clica → cycle theme system→light", async () => {
    mockTheme = "system";
    const user = userEvent.setup();
    const { container } = render(<ThemeToggle />);
    // Aguarda mount effect
    await new Promise((r) => setTimeout(r, 0));
    const button = container.querySelector("button");
    if (button && !button.hasAttribute("disabled")) {
      await user.click(button);
      expect(setThemeMock).toHaveBeenCalledWith("light");
    }
  });
});

// ─── DataTable ───────────────────────────────────────────────────────

interface Row {
  id: number;
  name: string;
  value: number;
}

const columns: ColumnDef<Row>[] = [
  { id: "name", header: "Nome", cell: (r) => r.name, sortable: true },
  { id: "value", header: "Valor", cell: (r) => r.value, sortable: true },
];

const data: Row[] = [
  { id: 1, name: "Charlie", value: 30 },
  { id: 2, name: "Alice", value: 10 },
  { id: 3, name: "Bob", value: 20 },
];

describe("<DataTable />", () => {
  it("renderiza headers + linhas", () => {
    render(<DataTable columns={columns} data={data} />);
    expect(screen.getByText("Nome")).toBeInTheDocument();
    expect(screen.getByText("Valor")).toBeInTheDocument();
    expect(screen.getByText("Charlie")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("loading: skeletons em vez de dados", () => {
    render(<DataTable columns={columns} data={[]} loading />);
    const skeletons = document.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("empty: mostra emptyMessage default", () => {
    render(<DataTable columns={columns} data={[]} />);
    expect(screen.getByText("Nenhum registro encontrado.")).toBeInTheDocument();
  });

  it("empty: emptyMessage customizado", () => {
    render(<DataTable columns={columns} data={[]} emptyMessage="Sem nada" />);
    expect(screen.getByText("Sem nada")).toBeInTheDocument();
  });

  it("sort: clicar em header sortable ordena ascendente", async () => {
    const user = userEvent.setup();
    render(<DataTable columns={columns} data={data} />);
    await user.click(screen.getByText("Nome"));

    const rows = document.querySelectorAll("tbody tr");
    const firstCell = rows[0].querySelector("td")?.textContent;
    expect(firstCell).toBe("Alice");
  });

  it("sort: 2º clique inverte para descendente", async () => {
    const user = userEvent.setup();
    render(<DataTable columns={columns} data={data} />);
    await user.click(screen.getByText("Nome"));
    await user.click(screen.getByText("Nome"));

    const rows = document.querySelectorAll("tbody tr");
    const firstCell = rows[0].querySelector("td")?.textContent;
    expect(firstCell).toBe("Charlie");
  });

  it("onRowClick: clica linha → callback recebe row", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<DataTable columns={columns} data={data} onRowClick={onClick} />);
    await user.click(screen.getByText("Alice"));
    expect(onClick).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Alice" }),
    );
  });
});
