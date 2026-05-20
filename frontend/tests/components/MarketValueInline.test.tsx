/**
 * MarketValueInline (ADR-227 §D2 · Sprint A15 Onda 5b) — coverage POST + supersede.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";
import { MarketValueInline } from "@/components/members/MarketValueInline";

const API = "/api/v1";
const WS = "ws-test";
const PROP = "prop-test";

const _rowFresh = {
  id: "pmv-1",
  property_id: PROP,
  workspace_id: WS,
  valor_brl: "1200000.00",
  valuation_date: "2026-05-01",
  source: "user_declared" as const,
  confidence: null,
  notes: null,
  superseded_by_id: null,
  created_at: "2026-05-01T00:00:00Z",
  created_by_user_id: null,
};

describe("MarketValueInline", () => {
  it("exibe latest market value e IRPF de referência", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/property-market-values`, () =>
        HttpResponse.json([_rowFresh]),
      ),
    );
    render(
      <MarketValueInline
        workspaceId={WS}
        propertyId={PROP}
        propertyLabel="Apto X"
        valorIrpfBrl={800_000}
      />,
    );
    await waitFor(() => expect(screen.getByText(/Mercado/)).toBeInTheDocument());
    expect(screen.getByText(/IRPF:/)).toBeInTheDocument();
    expect(screen.getByText("Apto X")).toBeInTheDocument();
  });

  it("submete POST quando user clica em Declarar", async () => {
    const calls: unknown[] = [];
    server.use(
      http.get(`${API}/workspaces/${WS}/property-market-values`, () => HttpResponse.json([])),
      http.post(`${API}/workspaces/${WS}/property-market-values`, async ({ request }) => {
        calls.push(await request.json());
        return HttpResponse.json({ ..._rowFresh, valor_brl: "1500000.00" }, { status: 201 });
      }),
    );
    render(
      <MarketValueInline workspaceId={WS} propertyId={PROP} propertyLabel="Apto X" />,
    );
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/Novo valor de mercado/i), "1500000");
    await user.click(screen.getByRole("button", { name: /Declarar/i }));
    await waitFor(() => expect(calls.length).toBe(1));
    expect(calls[0]).toMatchObject({
      property_id: PROP,
      valor_brl: "1500000",
    });
  });
});
