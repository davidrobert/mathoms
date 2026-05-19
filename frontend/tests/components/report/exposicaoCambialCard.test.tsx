/**
 * Tests — ExposicaoCambialCard V2 mode (ADR-224 PR-E).
 *
 * Cobre fallback V1 (sem workspaceId), substituição V2 após hook resolver,
 * badges de lastro_source, declare flow inline (sem modal).
 */
import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { ExposicaoCambialCard } from "@/components/report/cards/ExposicaoCambialCard";
import { clearToken, setToken } from "@/lib/api";
import { server } from "../../mocks/server";
import type { ExposicaoCambialData } from "@/types/report-analysis";

const API = "/api/v1";
const WS = "ws-card-001";

beforeEach(() => {
  clearToken();
  setToken("test-token");
});

const v1Data: ExposicaoCambialData = {
  total_brl: 50000,
  pct_investivel_financeiro: 10,
  tier: "verde",
  por_moeda: [{ moeda: "USD", valor_brl: 50000, pct_total_cambial: 100 }],
  detalhes: [],
};

const v2Empty = {
  workspace_id: WS,
  total_brl: "0.00",
  pct_investivel_financeiro: 0,
  por_moeda: [],
  tier: "empty" as const,
  ativos_contribuintes: [],
  catalog_version: 1,
  source_run_id: null,
  computed_at: "2026-05-19T20:00:00Z",
};

const v2Data = {
  workspace_id: WS,
  total_brl: "75000.00",
  pct_investivel_financeiro: 15.0,
  por_moeda: [{ moeda: "USD", valor_brl: "75000.00", share_pct: 100.0 }],
  tier: "verde" as const,
  ativos_contribuintes: [
    {
      nome: "IVVB11",
      moeda: "USD",
      valor_brl: "75000.00",
      tipo: "ativo",
      lastro_source: "catalog" as const,
    },
    {
      nome: "Fundo Misterioso",
      moeda: "BRL",
      valor_brl: "10000.00",
      tipo: "ativo",
      lastro_source: "fallback_classe" as const,
    },
  ],
  catalog_version: 1,
  source_run_id: "run-1",
  computed_at: "2026-05-19T20:00:00Z",
};

describe("ExposicaoCambialCard V2 mode (com workspaceId)", () => {
  it("sem workspaceId renderiza V1 (fallback)", async () => {
    render(<ExposicaoCambialCard data={v1Data} />);
    expect(await screen.findByText(/Exposição Cambial/i)).toBeInTheDocument();
    // V1 não tem section "Ativos contribuintes"
    expect(screen.queryByText(/Ativos contribuintes/i)).not.toBeInTheDocument();
  });

  it("com workspaceId mostra ativos_contribuintes + badge de lastro_source", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial`, () => HttpResponse.json(v2Data)),
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial/overrides`, () =>
        HttpResponse.json({ workspace_id: WS, overrides: [] }),
      ),
    );
    render(<ExposicaoCambialCard data={v1Data} workspaceId={WS} />);
    expect(await screen.findByText(/Ativos contribuintes/i)).toBeInTheDocument();
    expect(screen.getByText("IVVB11")).toBeInTheDocument();
    expect(screen.getByText(/catálogo Mathoms/i)).toBeInTheDocument();
    expect(screen.getByText(/lastro não declarado/i)).toBeInTheDocument();
  });

  it("V2 empty mostra mensagem '100% denominado em real'", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial`, () =>
        HttpResponse.json(v2Empty),
      ),
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial/overrides`, () =>
        HttpResponse.json({ workspace_id: WS, overrides: [] }),
      ),
    );
    render(<ExposicaoCambialCard data={v1Data} workspaceId={WS} />);
    expect(await screen.findByText(/100% denominado em real/i)).toBeInTheDocument();
  });

  it("clicar 'Declarar lastro' abre dropdown inline + salvar dispara POST", async () => {
    let postCalled = false;
    server.use(
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial`, () => HttpResponse.json(v2Data)),
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial/overrides`, () =>
        HttpResponse.json({ workspace_id: WS, overrides: [] }),
      ),
      http.post(`${API}/workspaces/${WS}/cards/exposicao-cambial/overrides`, async () => {
        postCalled = true;
        return HttpResponse.json(
          {
            id: "o-1",
            workspace_id: WS,
            match_kind: "description",
            asset_match_key: "Fundo Misterioso",
            lastro_moeda: "USD",
            override_source: "user_manual",
            created_at: "2026-05-19T20:00:00Z",
            updated_at: "2026-05-19T20:00:00Z",
            created_by_user_id: "user-1",
          },
          { status: 201 },
        );
      }),
    );
    const user = userEvent.setup();
    render(<ExposicaoCambialCard data={v1Data} workspaceId={WS} />);
    await screen.findByText("Fundo Misterioso");
    const declareButtons = screen.getAllByText(/Declarar lastro/i);
    await user.click(declareButtons[1]); // Fundo Misterioso (segundo botão)
    const select = await screen.findByLabelText(/Selecione o lastro/i);
    await user.selectOptions(select, "USD");
    await user.click(screen.getByText(/Salvar/i));
    await waitFor(() => expect(postCalled).toBe(true));
  });
});
