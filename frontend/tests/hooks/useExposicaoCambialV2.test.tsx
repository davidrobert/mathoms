/**
 * Tests — useExposicaoCambialV2 hook (ADR-224 PR-D foundations).
 *
 * Cobre load inicial + declare/remove com reload, error state, workspaceId null.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { useExposicaoCambialV2 } from "@/hooks/useExposicaoCambialV2";
import { clearToken, setToken } from "@/lib/api";
import { server } from "../mocks/server";

const API = "/api/v1";
const WS = "ws-001";

beforeEach(() => {
  clearToken();
  setToken("test-token");
});

const emptyCard = {
  workspace_id: WS,
  total_brl: "0.00",
  pct_investivel_financeiro: 0.0,
  por_moeda: [],
  tier: "empty",
  ativos_contribuintes: [],
  catalog_version: 1,
  source_run_id: null,
  computed_at: "2026-05-19T19:00:00Z",
};

const overrideFixture = {
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

describe("useExposicaoCambialV2", () => {
  it("carrega data + overrides em paralelo no mount", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial`, () =>
        HttpResponse.json(emptyCard),
      ),
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial/overrides`, () =>
        HttpResponse.json({ workspace_id: WS, overrides: [overrideFixture] }),
      ),
    );
    const { result } = renderHook(() => useExposicaoCambialV2(WS));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.tier).toBe("empty");
    expect(result.current.overrides).toHaveLength(1);
    expect(result.current.overrides[0].asset_match_key).toBe("IVVB11");
    expect(result.current.error).toBe("");
  });

  it("workspaceId null pula fetch e retorna estado vazio", async () => {
    const { result } = renderHook(() => useExposicaoCambialV2(null));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toBeNull();
    expect(result.current.overrides).toEqual([]);
  });

  it("declare dispara reload da lista de overrides", async () => {
    let listCalls = 0;
    server.use(
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial`, () =>
        HttpResponse.json(emptyCard),
      ),
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial/overrides`, () => {
        listCalls += 1;
        return HttpResponse.json({
          workspace_id: WS,
          overrides: listCalls === 1 ? [] : [overrideFixture],
        });
      }),
      http.post(
        `${API}/workspaces/${WS}/cards/exposicao-cambial/overrides`,
        () => HttpResponse.json(overrideFixture, { status: 201 }),
      ),
    );
    const { result } = renderHook(() => useExposicaoCambialV2(WS));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.overrides).toEqual([]);
    await act(async () => {
      await result.current.declare({
        match_kind: "ticker",
        asset_match_key: "IVVB11",
        lastro_moeda: "BRL",
      });
    });
    expect(result.current.overrides).toHaveLength(1);
    expect(listCalls).toBe(2);
  });

  it("remove dispara reload e remove override da lista", async () => {
    let listCalls = 0;
    server.use(
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial`, () =>
        HttpResponse.json(emptyCard),
      ),
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial/overrides`, () => {
        listCalls += 1;
        return HttpResponse.json({
          workspace_id: WS,
          overrides: listCalls === 1 ? [overrideFixture] : [],
        });
      }),
      http.delete(
        `${API}/workspaces/${WS}/cards/exposicao-cambial/overrides/ticker/IVVB11`,
        () => new HttpResponse(null, { status: 204 }),
      ),
    );
    const { result } = renderHook(() => useExposicaoCambialV2(WS));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.overrides).toHaveLength(1);
    await act(async () => {
      await result.current.remove("ticker", "IVVB11");
    });
    expect(result.current.overrides).toEqual([]);
  });

  it("captura erro de API em error state", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial`, () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
      http.get(`${API}/workspaces/${WS}/cards/exposicao-cambial/overrides`, () =>
        HttpResponse.json({ workspace_id: WS, overrides: [] }),
      ),
    );
    const { result } = renderHook(() => useExposicaoCambialV2(WS));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).not.toBe("");
  });
});
