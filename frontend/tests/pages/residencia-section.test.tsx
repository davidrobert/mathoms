/** ADR-215 P5 — ResidenciaSection (MembersTab subsection). */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";
import { ResidenciaSection } from "@/app/(app)/config/ResidenciaSection";

const WS_ID = "ws-1";
const API = "/api/v1";

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

describe("ResidenciaSection — empty state (sem imóveis no IRPF)", () => {
  it("mostra 'Moro alugado' e 'Decidir depois' quando lista vazia", async () => {
    server.use(
      http.get(`${API}/workspaces/:wid/properties`, () =>
        HttpResponse.json({
          workspace_id: WS_ID,
          residencia_status: "undeclared",
          properties: [],
        }),
      ),
    );
    render(<ResidenciaSection workspaceId={WS_ID} />);
    expect(
      await screen.findByText(/ainda não identificamos imóveis no seu irpf/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /moro alugado/i })).toBeInTheDocument();
  });
});

describe("ResidenciaSection — lista com sugestão fuzzy", () => {
  beforeEach(() => {
    server.use(
      http.get(`${API}/workspaces/:wid/properties`, () =>
        HttpResponse.json({
          workspace_id: WS_ID,
          residencia_status: "undeclared",
          properties: [
            {
              property_id: "p-tasso",
              titular_key: "david_robert",
              codigo_rfb: "12",
              descricao_sample: "CASA - RUA TASSO DA SILVEIRA, 61 - SP",
              endereco_canonical: "tasso silveira 61",
              first_seen_year: 2024,
              low_confidence: false,
              classification: null,
              override_source: null,
              classification_set_at: null,
              suggested_score: 100,
              suggested_residencia_principal: true,
            },
            {
              property_id: "p-apto",
              titular_key: "david_robert",
              codigo_rfb: "11",
              descricao_sample: "APTO COND BARAO DE CAPANEMA",
              endereco_canonical: null,
              first_seen_year: 2024,
              low_confidence: true,
              classification: null,
              override_source: null,
              classification_set_at: null,
              suggested_score: null,
              suggested_residencia_principal: false,
            },
          ],
        }),
      ),
    );
  });

  it("mostra badge 'sugerida pelo seu endereço no IRPF' no topo do ranking", async () => {
    render(<ResidenciaSection workspaceId={WS_ID} />);
    expect(
      await screen.findByText(/sugerida pelo seu endereço no IRPF/i),
    ).toBeInTheDocument();
  });

  it("mostra badge 'sem endereço estruturado' em low_confidence", async () => {
    render(<ResidenciaSection workspaceId={WS_ID} />);
    expect(
      await screen.findByText(/sem endereço estruturado/i),
    ).toBeInTheDocument();
  });

  it("aciona PUT classification quando usuário escolhe no dropdown", async () => {
    let putBody: unknown = null;
    server.use(
      http.put(
        `${API}/workspaces/:wid/properties/p-tasso/classification`,
        async ({ request }) => {
          putBody = await request.json();
          return HttpResponse.json({
            property_id: "p-tasso",
            titular_key: "david_robert",
            codigo_rfb: "12",
            descricao_sample: "CASA - RUA TASSO DA SILVEIRA, 61 - SP",
            endereco_canonical: "tasso silveira 61",
            first_seen_year: 2024,
            low_confidence: false,
            classification: "residencia_principal",
            override_source: "user_manual",
            classification_set_at: new Date().toISOString(),
            suggested_score: null,
            suggested_residencia_principal: false,
          });
        },
      ),
    );
    const user = userEvent.setup();
    render(<ResidenciaSection workspaceId={WS_ID} />);
    await screen.findByText(/CASA - RUA TASSO DA SILVEIRA/);

    const selects = screen.getAllByRole("combobox");
    await user.selectOptions(selects[0], "residencia_principal");

    await waitFor(() => {
      expect(putBody).toEqual({
        classification: "residencia_principal",
        override_source: "user_manual",
      });
    });
  });

  it("aciona PUT residencia-status ao clicar em 'Moro alugado'", async () => {
    let putBody: unknown = null;
    server.use(
      http.put(`${API}/workspaces/:wid/residencia-status`, async ({ request }) => {
        putBody = await request.json();
        return HttpResponse.json({ workspace_id: WS_ID, status: "rented" });
      }),
    );
    const user = userEvent.setup();
    render(<ResidenciaSection workspaceId={WS_ID} />);
    await screen.findByText(/CASA - RUA TASSO DA SILVEIRA/);

    await user.click(screen.getByRole("button", { name: /^moro alugado$/i }));

    await waitFor(() => {
      expect(putBody).toEqual({ status: "rented" });
    });
  });
});
