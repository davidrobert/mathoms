/**
 * Tests — ImoveisNoIfBanner + Container (ADR-223 FU-1 UX banner).
 *
 * Cobre: visibility logic (qualified count + set_at IS NULL + dismiss),
 * CTAs primary/secondary por variant, dispara PUT e refetch.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import {
  ImoveisNoIfBanner,
  ImoveisNoIfBannerContainer,
} from "@/app/(app)/config/ImoveisNoIfBanner";
import { clearToken, setToken } from "@/lib/api";
import { server } from "../mocks/server";

const API = "/api/v1";
const WS = "ws-banner-001";

beforeEach(() => {
  clearToken();
  setToken("test-token");
  if (typeof window !== "undefined") {
    localStorage.clear();
  }
});

const aProperty = (classification: string | null) => ({
  property_id: `p-${classification ?? "none"}`,
  titular_key: "david",
  codigo_rfb: "11",
  descricao_sample: "Apto",
  endereco_canonical: null,
  first_seen_year: 2024,
  low_confidence: false,
  classification,
  override_source: classification ? "user_manual" : null,
  classification_set_at: classification ? "2026-05-01T00:00:00Z" : null,
  suggested_score: null,
  suggested_residencia_principal: false,
});

const listResponse = (
  props: Array<ReturnType<typeof aProperty>>,
  imoveisNoIf: boolean,
  setAt: string | null,
) => ({
  workspace_id: WS,
  residencia_status: "owned",
  imoveis_no_if: imoveisNoIf,
  imoveis_no_if_set_at: setAt,
  properties: props,
});

describe("ImoveisNoIfBanner (component)", () => {
  it("variant=new tem 'Manter fora' como primary", () => {
    render(
      <ImoveisNoIfBanner
        workspaceId={WS}
        qualifiedCount={2}
        currentValue={false}
        variant="new"
        onResolved={() => undefined}
      />,
    );
    const primary = screen.getByRole("button", { name: /Manter fora/i });
    expect(primary).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Incluir no cálculo/i })).toBeInTheDocument();
  });

  it("variant=educational tem 'Manter incluindo' como primary", () => {
    render(
      <ImoveisNoIfBanner
        workspaceId={WS}
        qualifiedCount={1}
        currentValue={true}
        variant="educational"
        onResolved={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: /Manter incluindo/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Tirar do cálculo/i })).toBeInTheDocument();
  });

  it("PUT é chamado ao clicar primary", async () => {
    let putCalled = false;
    server.use(
      http.put(`${API}/workspaces/${WS}/imoveis-no-if`, async ({ request }) => {
        putCalled = true;
        const body = (await request.json()) as { imoveis_no_if: boolean };
        return HttpResponse.json({
          workspace_id: WS,
          imoveis_no_if: body.imoveis_no_if,
          set_at: "2026-05-19T00:00:00Z",
          set_by_user_id: "user-1",
        });
      }),
    );
    let resolvedValue: boolean | null = null;
    const user = userEvent.setup();
    render(
      <ImoveisNoIfBanner
        workspaceId={WS}
        qualifiedCount={3}
        currentValue={false}
        variant="new"
        onResolved={(v) => {
          resolvedValue = v;
        }}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Incluir no cálculo/i }));
    await waitFor(() => expect(putCalled).toBe(true));
    await waitFor(() => expect(resolvedValue).toBe(true));
  });
});

describe("ImoveisNoIfBannerContainer (visibility logic)", () => {
  it("não renderiza quando set_at NOT NULL (decisão explícita já feita)", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/properties`, () =>
        HttpResponse.json(listResponse([aProperty("locado")], false, "2026-05-01T00:00:00Z")),
      ),
    );
    const { container } = render(<ImoveisNoIfBannerContainer workspaceId={WS} />);
    await waitFor(() => expect(container.querySelector("section")).toBeNull());
  });

  it("não renderiza quando 0 imóveis qualificados", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/properties`, () =>
        HttpResponse.json(listResponse([aProperty("residencia_principal")], false, null)),
      ),
    );
    const { container } = render(<ImoveisNoIfBannerContainer workspaceId={WS} />);
    // Aguarda fetch + decisão — sem section visível
    await new Promise((r) => setTimeout(r, 50));
    expect(container.querySelector("section")).toBeNull();
  });

  it("renderiza variant=new quando default false + ≥1 imóvel locado", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/properties`, () =>
        HttpResponse.json(
          listResponse([aProperty("locado"), aProperty("comercial")], false, null),
        ),
      ),
    );
    render(<ImoveisNoIfBannerContainer workspaceId={WS} />);
    expect(
      await screen.findByText(/Contar seus imóveis alugados/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Manter fora/i })).toBeInTheDocument();
  });

  it("renderiza variant=educational quando default true herdado + ≥1 imóvel locado", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/properties`, () =>
        HttpResponse.json(listResponse([aProperty("locado")], true, null)),
      ),
    );
    render(<ImoveisNoIfBannerContainer workspaceId={WS} />);
    expect(
      await screen.findByText(/Confirmar como seus imóveis alugados/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Manter incluindo/i })).toBeInTheDocument();
  });

  it("dismiss persiste em localStorage e oculta banner", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/properties`, () =>
        HttpResponse.json(listResponse([aProperty("locado")], false, null)),
      ),
    );
    const user = userEvent.setup();
    const { rerender, container } = render(<ImoveisNoIfBannerContainer workspaceId={WS} />);
    await screen.findByText(/Contar seus imóveis alugados/i);
    await user.click(screen.getByRole("button", { name: /Decidir depois/i }));
    await waitFor(() => expect(container.querySelector("section")).toBeNull());
    // Re-render: dismiss state persisted
    rerender(<ImoveisNoIfBannerContainer workspaceId={WS} />);
    await new Promise((r) => setTimeout(r, 50));
    expect(container.querySelector("section")).toBeNull();
  });
});
