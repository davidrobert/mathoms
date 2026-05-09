/**
 * Unit tests — PlanoDeAcaoSection (A7.2a · ADR-136 · ADR-152)
 *
 * Pós PR3 (read-only no relatório): a seção lista decisões em modo
 * leitura e expõe link "Gerenciar em /acao →". Filtros de status e CTA
 * "Marcar como executada" foram movidos para /acao — aqui validamos
 * **ausência** desses elementos write-mode.
 *
 * MSW intercepta /workspaces/:id/decisions.
 */
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";

import { PlanoDeAcaoSection } from "@/components/report/sections/PlanoDeAcao";
import { server } from "../mocks/server";

const API = "/api/v1";
const WS_ID = "ws-test-uuid-1";

function makeDecision(overrides: Partial<{
  id: string;
  code: string;
  title: string;
  status: string;
  amount_brl: string | null;
  supersedes_id: string | null;
  decided_at: string | null;
  executed_at: string | null;
}> = {}) {
  return {
    id: overrides.id ?? "dec-1",
    workspace_id: WS_ID,
    code: overrides.code ?? "D01",
    title: overrides.title ?? "Decisão fictícia",
    rationale: null,
    amount_brl: overrides.amount_brl ?? null,
    status: overrides.status ?? "Pendente",
    supersedes_id: overrides.supersedes_id ?? null,
    decided_at: overrides.decided_at ?? null,
    executed_at: overrides.executed_at ?? null,
    created_at: "2026-04-27T00:00:00Z",
    updated_at: "2026-04-27T00:00:00Z",
  };
}

describe("<PlanoDeAcaoSection /> @A7.2a", () => {
  it("renderiza linhas de decisões com code + status badge", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/decisions`, () =>
        HttpResponse.json({
          decisions: [
            makeDecision({ id: "d1", code: "D01", title: "Quitar dívida fictícia", status: "Decidido" }),
            makeDecision({ id: "d2", code: "D02", title: "Aporte mensal", status: "Pendente" }),
          ],
          total: 2,
        }),
      ),
    );

    render(<PlanoDeAcaoSection workspaceId={WS_ID} />);

    await waitFor(() => {
      expect(screen.getByText("D01")).toBeInTheDocument();
    });
    expect(screen.getByText("Quitar dívida fictícia")).toBeInTheDocument();
    expect(screen.getByText("D02")).toBeInTheDocument();
    expect(screen.getByText("Decidido")).toBeInTheDocument();
    expect(screen.getByText("Pendente")).toBeInTheDocument();
  });

  it("expõe link 'Gerenciar em /acao →' no header da seção", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/decisions`, () =>
        HttpResponse.json({ decisions: [], total: 0 }),
      ),
    );

    render(<PlanoDeAcaoSection workspaceId={WS_ID} />);

    const link = await screen.findByRole("link", { name: /gerenciar em \/acao/i });
    expect(link).toHaveAttribute("href", "/acao");
  });

  it("não expõe filtros de status nem CTA write (read-only no relatório)", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/decisions`, () =>
        HttpResponse.json({
          decisions: [
            makeDecision({ id: "d1", code: "D01", status: "Decidido", title: "Decidida X" }),
          ],
          total: 1,
        }),
      ),
    );

    render(<PlanoDeAcaoSection workspaceId={WS_ID} />);

    await waitFor(() => expect(screen.getByText("Decidida X")).toBeInTheDocument());

    // Tabs de filtro: gone.
    expect(screen.queryByRole("tab", { name: "Pendente" })).toBeNull();
    expect(screen.queryByRole("tablist")).toBeNull();
    // CTA write: gone.
    expect(
      screen.queryByRole("button", { name: /marcar como executada/i }),
    ).toBeNull();
  });
});
