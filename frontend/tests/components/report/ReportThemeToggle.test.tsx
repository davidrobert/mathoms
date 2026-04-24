/**
 * Fase 1 — smoke tests de ReportThemeToggle + useReportFontScale.
 * ADR-117 (theme toggle) + ADR-121 (font scale).
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ReportThemeToggle } from "@/components/report/ReportThemeToggle";
import { useReportFontScale } from "@/components/report/useReportFontScale";

const setThemeMock = vi.fn();
let mockResolved = "light";
vi.mock("next-themes", () => ({
  useTheme: () => ({
    resolvedTheme: mockResolved,
    setTheme: setThemeMock,
  }),
}));

describe("<ReportThemeToggle />", () => {
  beforeEach(() => {
    setThemeMock.mockClear();
    mockResolved = "light";
  });

  it("renderiza dois botões rotulados Light e Dark", () => {
    render(<ReportThemeToggle />);
    expect(screen.getByRole("button", { name: "Light" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dark" })).toBeInTheDocument();
  });

  it("marca Light como ativo quando resolvedTheme=light", () => {
    mockResolved = "light";
    render(<ReportThemeToggle />);
    const light = screen.getByRole("button", { name: "Light" });
    const dark = screen.getByRole("button", { name: "Dark" });
    expect(light).toHaveAttribute("data-active", "true");
    expect(dark).toHaveAttribute("data-active", "false");
  });

  it("clicar em Dark chama setTheme('dark')", async () => {
    const user = userEvent.setup();
    render(<ReportThemeToggle />);
    await user.click(screen.getByRole("button", { name: "Dark" }));
    expect(setThemeMock).toHaveBeenCalledWith("dark");
  });
});

describe("useReportFontScale()", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("retorna 'compact' como default quando storage vazio", () => {
    const { result } = renderHook(() => useReportFontScale());
    expect(result.current.scale).toBe("compact");
  });

  it("lê valor válido do localStorage", () => {
    window.localStorage.setItem("mathoms:report:font-scale", "comfortable");
    const { result } = renderHook(() => useReportFontScale());
    expect(result.current.scale).toBe("comfortable");
  });

  it("ignora valor inválido no storage e mantém default", () => {
    window.localStorage.setItem("mathoms:report:font-scale", "gigante");
    const { result } = renderHook(() => useReportFontScale());
    expect(result.current.scale).toBe("compact");
  });

  it("setScale escreve no storage e atualiza state", () => {
    const { result } = renderHook(() => useReportFontScale());
    act(() => result.current.setScale("normal"));
    expect(result.current.scale).toBe("normal");
    expect(window.localStorage.getItem("mathoms:report:font-scale")).toBe(
      "normal",
    );
  });
});
