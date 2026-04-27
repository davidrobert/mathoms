/**
 * Unit tests — PlanoDeAcaoSection (A7.2a · ADR-136)
 *
 * Cobre: load → render rows → filtra por status → CTA execute chama POST.
 * MSW intercepta /workspaces/:id/decisions[/:id/execute].
 */
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

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
    // Status badges (não confundir com tabs do filtro — ambos têm os labels)
    expect(screen.getAllByText("Decidido").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Pendente").length).toBeGreaterThanOrEqual(1);
  });

  it("filtra por status quando o usuário clica num tab", async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${API}/workspaces/:wsId/decisions`, () =>
        HttpResponse.json({
          decisions: [
            makeDecision({ id: "d1", code: "D01", status: "Decidido", title: "Decidida X" }),
            makeDecision({ id: "d2", code: "D02", status: "Pendente", title: "Pendente Y" }),
          ],
          total: 2,
        }),
      ),
    );

    render(<PlanoDeAcaoSection workspaceId={WS_ID} />);

    await waitFor(() => expect(screen.getByText("Decidida X")).toBeInTheDocument());

    await user.click(screen.getByRole("tab", { name: "Pendente" }));

    expect(screen.queryByText("Decidida X")).toBeNull();
    expect(screen.getByText("Pendente Y")).toBeInTheDocument();
  });

  it("CTA 'Marcar como executada' chama POST /execute para Decidido", async () => {
    const user = userEvent.setup();
    let executeCalled = false;
    server.use(
      http.get(`${API}/workspaces/:wsId/decisions`, () =>
        HttpResponse.json({
          decisions: [
            makeDecision({ id: "d1", code: "D01", status: "Decidido", title: "T" }),
          ],
          total: 1,
        }),
      ),
      http.post(`${API}/workspaces/:wsId/decisions/:id/execute`, () => {
        executeCalled = true;
        return HttpResponse.json(
          makeDecision({
            id: "d1",
            code: "D01",
            status: "Executado",
            executed_at: "2026-04-27",
            title: "T",
          }),
        );
      }),
    );

    render(<PlanoDeAcaoSection workspaceId={WS_ID} />);

    const btn = await screen.findByRole("button", { name: /marcar como executada/i });
    await user.click(btn);

    await waitFor(() => expect(executeCalled).toBe(true));
  });
});
