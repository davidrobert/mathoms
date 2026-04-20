/**
 * Integration tests — Reports page (lista) — F6.5B.6
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import ReportsPage from "@/app/(app)/reports/page";
import { server } from "../mocks/server";
import { makeReport } from "../factories";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/reports",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

describe("ReportsPage (list)", () => {
  it("loading: spinner inicial", () => {
    server.use(http.get("/api/workspaces/:workspaceId/reports", () => new Promise(() => {})));
    const { container } = render(<ReportsPage />);
    expect(container.querySelector("svg.animate-spin")).toBeInTheDocument();
  });

  it("empty state com CTA para /documents (F6.5D.12)", async () => {
    server.use(
      http.get("/api/workspaces/:workspaceId/reports", () =>
        HttpResponse.json({ reports: [], total: 0 }),
      ),
    );
    render(<ReportsPage />);
    expect(await screen.findByText(/Nenhum relatório disponível/)).toBeInTheDocument();
    const cta = screen.getByText(/Enviar documentos/);
    expect(cta.closest("a")).toHaveAttribute("href", "/documents");
  });

  it("erro 500 mostra mensagem", async () => {
    server.use(
      http.get("/api/workspaces/:workspaceId/reports", () =>
        HttpResponse.json({ detail: "x" }, { status: 500 }),
      ),
    );
    render(<ReportsPage />);
    expect(await screen.findByText(/Erro ao carregar relatórios/)).toBeInTheDocument();
  });

  it("renderiza cards de relatórios com link e size", async () => {
    server.use(
      http.get("/api/workspaces/:workspaceId/reports", () =>
        HttpResponse.json({
          reports: [
            makeReport({ id: "r1", title: "Relatório Q1", period: "2026-01", size_bytes: 524288 }),
            makeReport({ id: "r2", title: "Relatório Q2", period: "2026-04" }),
          ],
          total: 2,
        }),
      ),
    );
    render(<ReportsPage />);
    expect(await screen.findByText("Relatório Q1")).toBeInTheDocument();
    expect(screen.getByText("Relatório Q2")).toBeInTheDocument();
    expect(screen.getByText("2026-01")).toBeInTheDocument();
    // link aponta para /reports/<id>
    const linkR1 = screen.getByText("Relatório Q1").closest("a");
    expect(linkR1).toHaveAttribute("href", "/reports/r1");
  });

  it("botão 'Gerar novo relatório' aponta para /pipeline", async () => {
    server.use(
      http.get("/api/workspaces/:workspaceId/reports", () =>
        HttpResponse.json({ reports: [], total: 0 }),
      ),
    );
    render(<ReportsPage />);
    await screen.findByText(/Nenhum relatório/);
    const btn = screen.getByText(/Gerar novo relatório/);
    expect(btn.closest("a")).toHaveAttribute("href", "/pipeline");
  });
});
