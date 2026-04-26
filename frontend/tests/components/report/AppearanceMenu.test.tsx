/**
 * AppearanceMenu — popover unificado fonte+tema (ADR-121 Fase 4 refinement
 * 2026-04-26) + smoke tests do hook useReportFontScale.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AppearanceMenu } from "@/components/report/shell/AppearanceMenu";
import { useReportFontScale } from "@/components/report/useReportFontScale";

const setThemeMock = vi.fn();
let mockResolved = "light";
vi.mock("next-themes", () => ({
  useTheme: () => ({
    resolvedTheme: mockResolved,
    setTheme: setThemeMock,
  }),
}));

describe("<AppearanceMenu />", () => {
  beforeEach(() => {
    setThemeMock.mockClear();
    mockResolved = "light";
    window.localStorage.clear();
  });

  it("renderiza trigger Aa com aria-label Aparência", () => {
    render(<AppearanceMenu />);
    const trigger = screen.getByRole("button", { name: "Aparência" });
    expect(trigger).toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("não exibe o painel até o trigger ser clicado", () => {
    render(<AppearanceMenu />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("clicar no trigger abre o painel com seções de tamanho e tema", async () => {
    const user = userEvent.setup();
    render(<AppearanceMenu />);
    await user.click(screen.getByRole("button", { name: "Aparência" }));
    expect(screen.getByRole("dialog", { name: "Aparência" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Tamanho do texto" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Tema do relatório" })).toBeInTheDocument();
  });

  it("Escape fecha o painel", async () => {
    const user = userEvent.setup();
    render(<AppearanceMenu />);
    await user.click(screen.getByRole("button", { name: "Aparência" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("click fora fecha o painel", async () => {
    const user = userEvent.setup();
    render(
      <div>
        <button type="button">fora</button>
        <AppearanceMenu />
      </div>,
    );
    await user.click(screen.getByRole("button", { name: "Aparência" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "fora" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("clicar em opção de tamanho persiste no localStorage e fecha o painel", async () => {
    const user = userEvent.setup();
    render(<AppearanceMenu />);
    await user.click(screen.getByRole("button", { name: "Aparência" }));
    await user.click(screen.getByRole("button", { name: "Confortável" }));
    expect(window.localStorage.getItem("mathoms:report:font-scale")).toBe(
      "comfortable",
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("clicar em Dark chama setTheme('dark') e fecha o painel", async () => {
    const user = userEvent.setup();
    render(<AppearanceMenu />);
    await user.click(screen.getByRole("button", { name: "Aparência" }));
    await user.click(screen.getByRole("button", { name: "Dark" }));
    expect(setThemeMock).toHaveBeenCalledWith("dark");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("marca tamanho ativo refletindo o estado do hook", async () => {
    window.localStorage.setItem("mathoms:report:font-scale", "comfortable");
    const user = userEvent.setup();
    render(<AppearanceMenu />);
    await user.click(screen.getByRole("button", { name: "Aparência" }));
    expect(screen.getByRole("button", { name: "Confortável" })).toHaveAttribute(
      "data-active",
      "true",
    );
    expect(screen.getByRole("button", { name: "Normal" })).toHaveAttribute(
      "data-active",
      "false",
    );
  });
});

describe("useReportFontScale()", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("retorna 'normal' como default quando storage vazio", () => {
    const { result } = renderHook(() => useReportFontScale());
    expect(result.current.scale).toBe("normal");
  });

  it("lê valor válido do localStorage", () => {
    window.localStorage.setItem("mathoms:report:font-scale", "comfortable");
    const { result } = renderHook(() => useReportFontScale());
    expect(result.current.scale).toBe("comfortable");
  });

  it("ignora valor inválido no storage e mantém default", () => {
    window.localStorage.setItem("mathoms:report:font-scale", "gigante");
    const { result } = renderHook(() => useReportFontScale());
    expect(result.current.scale).toBe("normal");
  });

  it("setScale escreve no storage e atualiza state", () => {
    const { result } = renderHook(() => useReportFontScale());
    act(() => result.current.setScale("compact"));
    expect(result.current.scale).toBe("compact");
    expect(window.localStorage.getItem("mathoms:report:font-scale")).toBe(
      "compact",
    );
  });
});
