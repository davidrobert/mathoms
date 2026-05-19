/**
 * Unit tests do client `exposicaoCambial` (ADR-224 PR-C; mocked via MSW handlers ad-hoc — não polui defaults).
 */
import { beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";

import { clearToken, setToken } from "@/lib/api";
import {
  declareLastroOverride,
  fetchExposicaoCambialV2,
  listLastroOverrides,
  removeLastroOverride,
} from "@/lib/api/exposicaoCambial";
import { server } from "../mocks/server";

const API = "/api/v1";
const WS = "ws-test-001";

beforeEach(() => {
  clearToken();
  setToken("test-token");
});

const sampleResponse = {
  workspace_id: WS,
  total_brl: "50000.00",
  pct_investivel_financeiro: 10.0,
  por_moeda: [{ moeda: "USD", valor_brl: "50000.00", share_pct: 100.0 }],
  tier: "verde" as const,
  ativos_contribuintes: [
    {
      nome: "Wise USD",
      moeda: "USD",
      valor_brl: "50000.00",
      tipo: "caixa",
      lastro_source: "catalog" as const,
    },
  ],
  catalog_version: 1,
  source_run_id: "run-1",
  computed_at: "2026-05-19T19:00:00Z",
};

describe("fetchExposicaoCambialV2", () => {
  it("retorna response shape correto com tier + por_moeda + ativos_contribuintes", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial`, () =>
        HttpResponse.json(sampleResponse),
      ),
    );
    const result = await fetchExposicaoCambialV2(WS);
    expect(result.tier).toBe("verde");
    expect(result.total_brl).toBe("50000.00"); // Decimal string (ADR-090)
    expect(result.por_moeda).toHaveLength(1);
    expect(result.por_moeda[0].moeda).toBe("USD");
    expect(result.ativos_contribuintes[0].lastro_source).toBe("catalog");
  });

  it("retorna tier 'empty' quando workspace sem E5 artifact", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial`, () =>
        HttpResponse.json({
          ...sampleResponse,
          total_brl: "0.00",
          pct_investivel_financeiro: 0.0,
          por_moeda: [],
          tier: "empty",
          ativos_contribuintes: [],
          source_run_id: null,
        }),
      ),
    );
    const result = await fetchExposicaoCambialV2(WS);
    expect(result.tier).toBe("empty");
    expect(result.por_moeda).toEqual([]);
  });
});

describe("listLastroOverrides", () => {
  it("retorna lista vazia quando workspace sem overrides", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial/overrides`, () =>
        HttpResponse.json({ workspace_id: WS, overrides: [] }),
      ),
    );
    const result = await listLastroOverrides(WS);
    expect(result.overrides).toEqual([]);
    expect(result.workspace_id).toBe(WS);
  });
});

describe("declareLastroOverride", () => {
  it("POST retorna AssetOverrideResponse com 201 + audit fields", async () => {
    const overrideResponse = {
      id: "override-1",
      workspace_id: WS,
      match_kind: "ticker" as const,
      asset_match_key: "IVVB11",
      lastro_moeda: "BRL" as const,
      override_source: "user_manual",
      created_at: "2026-05-19T19:00:00Z",
      updated_at: "2026-05-19T19:00:00Z",
      created_by_user_id: "user-1",
    };
    server.use(
      http.post(
        `${API}/workspaces/${WS}/cards/exposicao-cambial/overrides`,
        () => HttpResponse.json(overrideResponse, { status: 201 }),
      ),
    );
    const result = await declareLastroOverride(WS, {
      match_kind: "ticker",
      asset_match_key: "IVVB11",
      lastro_moeda: "BRL",
    });
    expect(result.id).toBe("override-1");
    expect(result.lastro_moeda).toBe("BRL");
    expect(result.override_source).toBe("user_manual");
    expect(result.created_by_user_id).toBe("user-1");
  });
});

describe("removeLastroOverride", () => {
  it("DELETE retorna void com 204", async () => {
    server.use(
      http.delete(
        `${API}/workspaces/${WS}/cards/exposicao-cambial/overrides/ticker/IVVB11`,
        () => new HttpResponse(null, { status: 204 }),
      ),
    );
    await expect(
      removeLastroOverride(WS, "ticker", "IVVB11"),
    ).resolves.toBeUndefined();
  });

  it("encoda match_kind e key na URL (segurança contra path injection)", async () => {
    let calledUrl = "";
    server.use(
      http.delete(
        `${API}/workspaces/${WS}/cards/exposicao-cambial/overrides/:kind/:key`,
        ({ request }) => {
          calledUrl = new URL(request.url).pathname;
          return new HttpResponse(null, { status: 204 });
        },
      ),
    );
    await removeLastroOverride(WS, "ticker", "BTG GLOBAL/X");
    expect(calledUrl).toContain("BTG%20GLOBAL%2FX");
  });
});
