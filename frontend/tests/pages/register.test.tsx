/**
 * Integration tests — Register page (F6.5B.1)
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import RegisterPage from "@/app/register/page";
import { server } from "../mocks/server";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/register",
}));

beforeEach(() => pushMock.mockClear());

describe("RegisterPage", () => {
  it("renderiza form completo", () => {
    render(<RegisterPage />);
    expect(screen.getByLabelText(/seu nome/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /criar conta/i })).toBeInTheDocument();
  });

  it("happy path → token salvo + push /plano (nextUrl default)", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);
    await user.type(screen.getByLabelText(/seu nome/i), "Novo User");
    await user.type(screen.getByLabelText(/email/i), "novo@test.com");
    await user.type(screen.getByLabelText(/senha/i), "senha123");
    await user.click(screen.getByRole("button", { name: /criar conta/i }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/plano"));
    expect(localStorage.getItem("fin_token")).toBe("test-token");
  });

  it("409 mostra mensagem custom 'já cadastrado'", async () => {
    server.use(
      http.post("/api/auth/register", () =>
        HttpResponse.json({ detail: "x" }, { status: 409 }),
      ),
    );
    const user = userEvent.setup();
    render(<RegisterPage />);
    await user.type(screen.getByLabelText(/nome/i), "x");
    await user.type(screen.getByLabelText(/email/i), "dup@test.com");
    await user.type(screen.getByLabelText(/senha/i), "senha123");
    await user.click(screen.getByRole("button", { name: /criar conta/i }));
    await waitFor(() => {
      expect(screen.getByText(/já está cadastrado/i)).toBeInTheDocument();
    });
  });

  it("422 mostra detail da validação", async () => {
    server.use(
      http.post("/api/auth/register", () =>
        HttpResponse.json({ detail: "Senha fraca" }, { status: 422 }),
      ),
    );
    const user = userEvent.setup();
    render(<RegisterPage />);
    await user.type(screen.getByLabelText(/nome/i), "x");
    await user.type(screen.getByLabelText(/email/i), "x@test.com");
    await user.type(screen.getByLabelText(/senha/i), "abcdef");
    await user.click(screen.getByRole("button", { name: /criar conta/i }));
    await waitFor(() => expect(screen.getByText(/Senha fraca/i)).toBeInTheDocument());
  });

  it("input password tem minLength=6 (HTML5 validation)", () => {
    render(<RegisterPage />);
    const pw = screen.getByLabelText(/senha/i) as HTMLInputElement;
    expect(pw.minLength).toBe(6);
  });

  it("link 'Entrar' aponta para /login?next=/plano (preserva destino default)", () => {
    render(<RegisterPage />);
    expect(screen.getByRole("link", { name: /entrar/i })).toHaveAttribute(
      "href",
      "/login?next=%2Fplano",
    );
  });
});
