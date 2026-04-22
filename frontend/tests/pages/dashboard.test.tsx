/**
 * Integration tests — Dashboard page (F6.5B.2)
 *
 * Foco: render KPIs/charts/empty/error/loading + reload + drill-down.
 * Recharts é mockado para evitar overhead de renderização SVG em jsdom.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";
import { makeDashboard, makeKPI } from "../factories";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams(),
}));

// Recharts ResponsiveContainer mede via ResizeObserver — mockado em setup.ts
// mas vamos simplificar mockando os charts inteiros para o test focar em UI/data
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: any) => (
      <div data-testid="chart-container" style={{ width: 800, height: 400 }}>
        {children}
      </div>
    ),
  };
});

import DashboardPage from "@/app/(app)/dashboard/page";

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
  pushMock.mockClear();
});

describe("DashboardPage", () => {
  it("loading: 4 skeletons de KPICard inicial", () => {
    server.use(http.get("/api/v1/workspaces/:workspaceId/dashboard", () => new Promise(() => {})));
    render(<DashboardPage />);
    const skeletons = document.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("empty: 'Nenhuma análise disponível' com CTA Pipeline (F6.5D.12)", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/dashboard", () =>
        HttpResponse.json(makeDashboard({ kpis: [], charts: [] })),
      ),
    );
    render(<DashboardPage />);
    expect(await screen.findByText(/Nenhuma análise disponível/)).toBeInTheDocument();
    const cta = screen.getByText(/Ir para Pipeline/);
    expect(cta.closest("a")).toHaveAttribute("href", "/pipeline");
  });

  it("error: EmptyState 'Erro ao carregar' + Tentar novamente", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/dashboard", () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    render(<DashboardPage />);
    expect(await screen.findByText(/Erro ao carregar dados/)).toBeInTheDocument();
    expect(screen.getByText(/Tentar novamente/)).toBeInTheDocument();
  });

  it("renderiza KPIs", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/dashboard", () =>
        HttpResponse.json(
          makeDashboard({
            kpis: [
              makeKPI({ label: "Receitas", value: "R$ 12.500,00", raw_value: 12500 }),
              makeKPI({ label: "Despesas", value: "R$ 8.400,00", raw_value: -8400 }),
            ],
          }),
        ),
      ),
    );
    render(<DashboardPage />);
    expect(await screen.findByText("Receitas")).toBeInTheDocument();
    expect(screen.getByText("R$ 12.500,00")).toBeInTheDocument();
    expect(screen.getByText("Despesas")).toBeInTheDocument();
  });

  it("data_freshness null → badge 'Sem dados'", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/dashboard", () =>
        HttpResponse.json(
          makeDashboard({
            kpis: [makeKPI({ label: "x", value: "y" })],
            data_freshness: null,
          }),
        ),
      ),
    );
    render(<DashboardPage />);
    expect(await screen.findByText(/Sem dados/)).toBeInTheDocument();
  });

  it("botão refresh recarrega (chama API novamente)", async () => {
    let callCount = 0;
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/dashboard", () => {
        callCount++;
        return HttpResponse.json(
          makeDashboard({ kpis: [makeKPI({ label: "Saldo", value: "R$ 1" })] }),
        );
      }),
    );
    const user = userEvent.setup();
    render(<DashboardPage />);
    await screen.findByText("Saldo");
    expect(callCount).toBe(1);

    const refreshBtn = screen.getByLabelText(/Atualizar dashboard/);
    await user.click(refreshBtn);
    await waitFor(() => expect(callCount).toBe(2));
  });

  it("retry após erro chama API e mostra dados", async () => {
    let attempt = 0;
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/dashboard", () => {
        attempt++;
        if (attempt === 1) {
          return HttpResponse.json({ detail: "x" }, { status: 500 });
        }
        return HttpResponse.json(
          makeDashboard({ kpis: [makeKPI({ label: "OK", value: "0" })] }),
        );
      }),
    );
    const user = userEvent.setup();
    render(<DashboardPage />);
    await screen.findByText(/Erro ao carregar dados/);
    await user.click(screen.getByText(/Tentar novamente/));
    expect(await screen.findByText("OK")).toBeInTheDocument();
  });
});
