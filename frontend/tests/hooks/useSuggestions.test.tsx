/**
 * Tests — useSuggestions hook (Direção E · Onda 5 · ADR-153).
 *
 * Cobre lista por status, mutações que invalidam (refetch), e
 * regenerate para um Report.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { useSuggestions } from "@/hooks/useSuggestions";
import { clearToken, setToken } from "@/lib/api";
import { server } from "../mocks/server";

const API = "/api/v1";
const WS_ID = "ws-1";

beforeEach(() => {
  clearToken();
  setToken("test-token");
});

const aSuggestion = (id: string, status = "Pendente") => ({
  id,
  workspace_id: WS_ID,
  report_id: "rep-1",
  section_id: "S2",
  kind: "reserva_insuficiente",
  origin: "deterministic",
  severity: "warning",
  title: "Reforçar reserva",
  rationale: "Cobertura insuficiente",
  amount_brl: "5000.00",
  status,
  accepted_decision_id: null,
  dismissed_reason: null,
  accepted_at: null,
  dismissed_at: null,
  created_at: "2026-04-29T10:00:00Z",
  updated_at: "2026-04-29T10:00:00Z",
});

describe("useSuggestions", () => {
  it("carrega lista filtrada por status", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS_ID}/suggestions`, ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get("status")).toBe("Pendente");
        return HttpResponse.json({
          suggestions: [aSuggestion("s1"), aSuggestion("s2")],
          total: 2,
        });
      }),
    );
    const { result } = renderHook(() => useSuggestions(WS_ID, "Pendente"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.suggestions).toHaveLength(2);
    expect(result.current.error).toBe("");
  });

  it("retorna lista vazia quando workspace é undefined", async () => {
    const { result } = renderHook(() => useSuggestions(undefined));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.suggestions).toEqual([]);
  });

  it("accept dispara reload da lista", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/workspaces/${WS_ID}/suggestions`, () => {
        calls += 1;
        return HttpResponse.json({
          suggestions: calls === 1 ? [aSuggestion("s1")] : [],
          total: calls === 1 ? 1 : 0,
        });
      }),
      http.post(
        `${API}/workspaces/${WS_ID}/suggestions/s1/accept`,
        () => HttpResponse.json(aSuggestion("s1", "Aceita")),
      ),
    );
    const { result } = renderHook(() => useSuggestions(WS_ID, "Pendente"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.suggestions).toHaveLength(1);

    await result.current.accept("s1", { decision_code: "D01" });
    await waitFor(() =>
      expect(result.current.suggestions).toHaveLength(0),
    );
    expect(calls).toBeGreaterThanOrEqual(2);
  });

  it("dismiss persiste reason e refaz fetch", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS_ID}/suggestions`, () =>
        HttpResponse.json({ suggestions: [aSuggestion("s1")], total: 1 }),
      ),
      http.post(
        `${API}/workspaces/${WS_ID}/suggestions/s1/dismiss`,
        async ({ request }) => {
          const body = (await request.json()) as { reason: string };
          expect(body.reason).toBe("ja_considerei");
          return HttpResponse.json(aSuggestion("s1", "Descartada"));
        },
      ),
    );
    const { result } = renderHook(() => useSuggestions(WS_ID, "Pendente"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    const out = await result.current.dismiss("s1", { reason: "ja_considerei" });
    expect(out.status).toBe("Descartada");
  });

  it("regenerate retorna summary com count de criadas", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS_ID}/suggestions`, () =>
        HttpResponse.json({ suggestions: [], total: 0 }),
      ),
      http.post(
        `${API}/workspaces/${WS_ID}/reports/r1/regenerate-suggestions`,
        () =>
          HttpResponse.json({
            created: 2,
            skipped_dedup: 1,
            skipped_cap: 0,
            total_drafts: 3,
            suggestions: [aSuggestion("s1"), aSuggestion("s2")],
          }),
      ),
    );
    const { result } = renderHook(() => useSuggestions(WS_ID, "Pendente"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    const out = await result.current.regenerate("r1");
    expect(out.created).toBe(2);
    expect(out.skipped_dedup).toBe(1);
  });

  it("erro de rede expõe mensagem", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS_ID}/suggestions`, () =>
        HttpResponse.error(),
      ),
    );
    const { result } = renderHook(() => useSuggestions(WS_ID, "Pendente"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeTruthy();
    expect(result.current.suggestions).toEqual([]);
  });
});
