/**
 * Integration tests — AppShell (F6.5B.9)
 *
 * Cobre auth gate, navegação, mobile menu, logout, NotificationCenter render.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";

const replaceMock = vi.fn();
let pathnameMock = "/dashboard";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: replaceMock }),
  usePathname: () => pathnameMock,
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, onClick, ...rest }: any) => (
    <a href={href} onClick={onClick} {...rest}>
      {children}
    </a>
  ),
}));

import AppShell from "@/components/AppShell";

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
  replaceMock.mockClear();
  pathnameMock = "/dashboard";
});

describe("AppShell", () => {
  it("loading: spinner enquanto getMe carrega", () => {
    server.use(http.get("/api/auth/me", () => new Promise(() => {})));
    const { container } = render(<AppShell>conteudo</AppShell>);
    expect(container.querySelector("svg.animate-spin")).toBeInTheDocument();
  });

  it("auth gate: getMe falha → clearToken + replace /login", async () => {
    server.use(
      http.get("/api/auth/me", () =>
        HttpResponse.json({ detail: "x" }, { status: 401 }),
      ),
    );
    render(<AppShell>conteudo</AppShell>);
    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });
    expect(localStorage.getItem("fin_token")).toBeNull();
  });

  it("renderiza nav com 7 itens", async () => {
    render(<AppShell>conteudo</AppShell>);
    await screen.findByText("conteudo");
    for (const label of [
      "Dashboard",
      "Documentos",
      "Pipeline",
      "Transações",
      "Relatórios",
      "Cofre",
      "Configurações",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("destaca link ativo conforme pathname (drill-down style)", async () => {
    pathnameMock = "/transactions";
    render(<AppShell>conteudo</AppShell>);
    await screen.findByText("conteudo");
    const link = screen.getByText("Transações").closest("a")!;
    // link ativo recebe text-primary
    expect(link.className).toContain("text-primary");
  });

  it("F6.5: BUG-005 anti-regression — Vault está no nav", async () => {
    render(<AppShell>conteudo</AppShell>);
    await screen.findByText("conteudo");
    const cofreLink = screen.getByText("Cofre").closest("a")!;
    expect(cofreLink).toHaveAttribute("href", "/vault");
  });

  it("logout: clica Sair → clearToken + replace /login", async () => {
    const user = userEvent.setup();
    render(<AppShell>conteudo</AppShell>);
    await screen.findByText("conteudo");
    await user.click(screen.getByRole("button", { name: /sair/i }));
    expect(localStorage.getItem("fin_token")).toBeNull();
    expect(replaceMock).toHaveBeenCalledWith("/login");
  });

  it("mostra nome + email do user", async () => {
    server.use(
      http.get("/api/auth/me", () =>
        HttpResponse.json({
          id: "u1",
          email: "real@user.com",
          full_name: "Nome Real",
          is_active: true,
        }),
      ),
    );
    render(<AppShell>conteudo</AppShell>);
    expect(await screen.findByText("Nome Real")).toBeInTheDocument();
    expect(screen.getByText("real@user.com")).toBeInTheDocument();
  });

  it("mobile: clica botão menu → sidebar abre", async () => {
    const user = userEvent.setup();
    render(<AppShell>conteudo</AppShell>);
    await screen.findByText("conteudo");
    const menuBtn = screen.getByLabelText(/Abrir menu/);
    // sidebar tem -translate-x-full (fechada) inicialmente
    const sidebar = document.querySelector("aside")!;
    expect(sidebar.className).toContain("-translate-x-full");

    await user.click(menuBtn);
    expect(sidebar.className).toContain("translate-x-0");
  });

  it("renderiza children no main", async () => {
    render(<AppShell><div data-testid="child">Conteudo da Page</div></AppShell>);
    await screen.findByTestId("child");
    expect(screen.getByText("Conteudo da Page")).toBeInTheDocument();
  });
});
