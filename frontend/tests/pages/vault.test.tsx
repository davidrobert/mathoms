/**
 * Integration tests — Vault page (F6.5B.8)
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import VaultPage from "@/app/(app)/vault/page";
import { server } from "../mocks/server";
import { makeVaultPassword } from "../factories";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/vault",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

describe("VaultPage", () => {
  it("renderiza header + form de adicionar senha", async () => {
    render(<VaultPage />);
    expect(await screen.findByText(/Vault de Senhas/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Rótulo/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/^Senha$/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /adicionar/i })).toBeInTheDocument();
  });

  it("loading: spinner enquanto carrega lista", () => {
    server.use(
      http.get("/api/vault/passwords", () => new Promise(() => {})), // never resolve
    );
    const { container } = render(<VaultPage />);
    // Spinner SVG renderizado (Loader2) com animate-spin
    expect(container.querySelector("svg.animate-spin")).toBeInTheDocument();
  });

  it("empty state: 'Nenhuma senha cadastrada'", async () => {
    server.use(
      http.get("/api/vault/passwords", () =>
        HttpResponse.json({ passwords: [], total: 0 }),
      ),
    );
    render(<VaultPage />);
    expect(await screen.findByText(/Nenhuma senha cadastrada/)).toBeInTheDocument();
  });

  it("renderiza lista de senhas existentes", async () => {
    server.use(
      http.get("/api/vault/passwords", () =>
        HttpResponse.json({
          passwords: [
            makeVaultPassword({ label: "Itaú IRPF" }),
            makeVaultPassword({ label: "Bradesco" }),
          ],
          total: 2,
        }),
      ),
    );
    render(<VaultPage />);
    expect(await screen.findByText("Itaú IRPF")).toBeInTheDocument();
    expect(screen.getByText("Bradesco")).toBeInTheDocument();
  });

  it("erro ao carregar mostra mensagem", async () => {
    server.use(
      http.get("/api/vault/passwords", () =>
        HttpResponse.json({ detail: "x" }, { status: 500 }),
      ),
    );
    render(<VaultPage />);
    expect(await screen.findByText(/Erro ao carregar senhas/)).toBeInTheDocument();
  });

  it("adicionar senha → reload + mostra success", async () => {
    let added = false;
    server.use(
      http.get("/api/vault/passwords", () =>
        HttpResponse.json({
          passwords: added ? [makeVaultPassword({ label: "Nova" })] : [],
          total: added ? 1 : 0,
        }),
      ),
      http.post("/api/vault/passwords", () => {
        added = true;
        return HttpResponse.json(makeVaultPassword({ label: "Nova" }));
      }),
    );
    const user = userEvent.setup();
    render(<VaultPage />);
    await screen.findByText(/Nenhuma senha cadastrada/);

    await user.type(screen.getByPlaceholderText(/Rótulo/i), "Nova");
    await user.type(screen.getByPlaceholderText(/^Senha$/i), "secret");
    await user.click(screen.getByRole("button", { name: /adicionar/i }));

    await waitFor(() => expect(screen.getByText(/Senha adicionada/)).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("Nova")).toBeInTheDocument());
  });

  it("erro 400 ao adicionar mostra detail", async () => {
    server.use(
      http.get("/api/vault/passwords", () =>
        HttpResponse.json({ passwords: [], total: 0 }),
      ),
      http.post("/api/vault/passwords", () =>
        HttpResponse.json({ detail: "Senha muito curta" }, { status: 400 }),
      ),
    );
    const user = userEvent.setup();
    render(<VaultPage />);
    await screen.findByText(/Nenhuma senha cadastrada/);

    await user.type(screen.getByPlaceholderText(/Rótulo/i), "x");
    await user.type(screen.getByPlaceholderText(/^Senha$/i), "y");
    await user.click(screen.getByRole("button", { name: /adicionar/i }));

    await waitFor(() => expect(screen.getByText(/Senha muito curta/)).toBeInTheDocument());
  });

  it("retry-unlock com 0 desbloqueios mostra mensagem 'nenhum'", async () => {
    server.use(
      http.get("/api/vault/passwords", () =>
        HttpResponse.json({ passwords: [makeVaultPassword({ label: "X" })], total: 1 }),
      ),
      http.post("/api/documents/retry-unlock", () => HttpResponse.json([])),
    );
    const user = userEvent.setup();
    render(<VaultPage />);
    await screen.findByText("X");
    await user.click(screen.getByRole("button", { name: /Tentar desbloquear/ }));
    await waitFor(() => {
      expect(screen.getByText(/Nenhum documento conseguiu ser desbloqueado/)).toBeInTheDocument();
    });
  });

  it("retry-unlock bem-sucedido mostra contador", async () => {
    server.use(
      http.get("/api/vault/passwords", () =>
        HttpResponse.json({ passwords: [makeVaultPassword({ label: "X" })], total: 1 }),
      ),
      http.post("/api/documents/retry-unlock", () =>
        HttpResponse.json([
          { id: "d1", status: "ready" },
          { id: "d2", status: "ready" },
          { id: "d3", status: "needs_password" },
        ]),
      ),
    );
    const user = userEvent.setup();
    render(<VaultPage />);
    await screen.findByText("X");
    await user.click(screen.getByRole("button", { name: /Tentar desbloquear/ }));
    await waitFor(() => {
      expect(screen.getByText(/2 documento\(s\) desbloqueado/)).toBeInTheDocument();
    });
  });
});
