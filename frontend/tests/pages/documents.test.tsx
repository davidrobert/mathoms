/**
 * Integration tests — Documents page (F6.5B.3)
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import DocumentsPage from "@/app/(app)/documents/page";
import { server } from "../mocks/server";
import { makeDocument } from "../factories";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/documents",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

describe("DocumentsPage", () => {
  it("renderiza header + drop zone", async () => {
    server.use(
      http.get("/api/documents", () =>
        HttpResponse.json({ documents: [], total: 0 }),
      ),
    );
    render(<DocumentsPage />);
    expect(await screen.findByText("Documentos")).toBeInTheDocument();
    expect(screen.getByText(/Arraste arquivos aqui/)).toBeInTheDocument();
  });

  it("loading: spinner enquanto carrega", () => {
    server.use(http.get("/api/documents", () => new Promise(() => {})));
    const { container } = render(<DocumentsPage />);
    expect(container.querySelector("svg.animate-spin")).toBeInTheDocument();
  });

  it("empty state com CTA 'Enviar documentos' (F6.5D.12)", async () => {
    server.use(
      http.get("/api/documents", () =>
        HttpResponse.json({ documents: [], total: 0 }),
      ),
    );
    render(<DocumentsPage />);
    expect(await screen.findByText(/Nenhum documento enviado/)).toBeInTheDocument();
    expect(screen.getByText(/Enviar documentos/)).toBeInTheDocument();
  });

  it("renderiza tabela com documentos", async () => {
    server.use(
      http.get("/api/documents", () =>
        HttpResponse.json({
          documents: [
            makeDocument({ original_name: "extrato_jan.pdf", status: "ready" }),
            makeDocument({ original_name: "fatura.pdf", status: "needs_password" }),
          ],
          total: 2,
        }),
      ),
    );
    render(<DocumentsPage />);
    expect(await screen.findByText("extrato_jan.pdf")).toBeInTheDocument();
    expect(screen.getByText("fatura.pdf")).toBeInTheDocument();
    // Status badges visíveis
    expect(screen.getByText("Pronto")).toBeInTheDocument();
    expect(screen.getByText("Precisa de senha")).toBeInTheDocument();
  });

  it("banner needs_password aparece quando há docs bloqueados", async () => {
    server.use(
      http.get("/api/documents", () =>
        HttpResponse.json({
          documents: [makeDocument({ status: "needs_password" })],
          total: 1,
        }),
      ),
    );
    render(<DocumentsPage />);
    expect(await screen.findByText(/protegido\(s\) por senha/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Adicione senhas no vault/ })).toHaveAttribute("href", "/vault");
  });

  it("erro 500 ao listar mostra mensagem", async () => {
    server.use(
      http.get("/api/documents", () =>
        HttpResponse.json({ detail: "x" }, { status: 500 }),
      ),
    );
    render(<DocumentsPage />);
    expect(await screen.findByText(/Erro ao carregar documentos/)).toBeInTheDocument();
  });

  it("CTA 'Gerar Relatório' aparece quando há docs ready", async () => {
    server.use(
      http.get("/api/documents", () =>
        HttpResponse.json({
          documents: [
            makeDocument({ status: "ready" }),
            makeDocument({ status: "ready" }),
          ],
          total: 2,
        }),
      ),
    );
    render(<DocumentsPage />);
    const link = await screen.findByText(/Gerar Relatório \(2 docs\)/);
    expect(link.closest("a")).toHaveAttribute("href", "/pipeline");
  });

  it("delete: abre confirm dialog e remove ao confirmar", async () => {
    let deleted = false;
    server.use(
      http.get("/api/documents", () =>
        HttpResponse.json({
          documents: deleted
            ? []
            : [makeDocument({ original_name: "deletar.pdf", status: "ready" })],
          total: deleted ? 0 : 1,
        }),
      ),
      http.delete("/api/documents/:id", () => {
        deleted = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    render(<DocumentsPage />);
    await screen.findByText("deletar.pdf");

    // botão Trash2 (sem texto) — buscar via aria-label do svg ou via section parent
    const buttons = screen.getAllByRole("button");
    const deleteBtn = buttons.find((b) =>
      b.querySelector("svg.lucide-trash2") || b.className.includes("hover:text-destructive"),
    );
    expect(deleteBtn).toBeDefined();
    await user.click(deleteBtn!);

    // dialog abre
    expect(await screen.findByText(/Remover "deletar.pdf"/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^Remover$/ }));

    await waitFor(() => {
      expect(screen.queryByText("deletar.pdf")).not.toBeInTheDocument();
    });
  });
});
