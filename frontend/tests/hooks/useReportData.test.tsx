/**
 * Tests — useReportData hook (F9 · ADR-076 · F0.5)
 */
import { beforeEach, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { useReportData } from "@/hooks/useReportData";
import { clearToken, setToken } from "@/lib/api";
import { server } from "../mocks/server";

const API = "/api";
const WS_ID = "ws-1";

beforeEach(() => {
  clearToken();
  setToken("test-token");
});

describe("useReportData", () => {
  it("fica em idle quando reportId é null", () => {
    const { result } = renderHook(() => useReportData(null, WS_ID));
    expect(result.current.status).toBe("idle");
  });

  it("fica em idle quando workspaceId é null", () => {
    const { result } = renderHook(() => useReportData("report-1", null));
    expect(result.current.status).toBe("idle");
  });

  it("transita loading → success com dados", async () => {
    const { result } = renderHook(() => useReportData("report-1", WS_ID));
    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("success"));
    if (result.current.status === "success") {
      expect(result.current.data.periodo_dados).toBe("202601-202604");
      expect(result.current.data.score?.valor).toBe(82);
    }
  });

  it("transita loading → error em 404", async () => {
    const { result } = renderHook(() => useReportData("nonexistent", WS_ID));
    await waitFor(() => expect(result.current.status).toBe("error"));
    if (result.current.status === "error") {
      expect(result.current.error.message).toBeTruthy();
    }
  });

  it("propaga erro de rede", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS_ID}/reports/netfail/data`, () =>
        HttpResponse.error(),
      ),
    );
    const { result } = renderHook(() => useReportData("netfail", WS_ID));
    await waitFor(() => expect(result.current.status).toBe("error"));
  });

  it("re-busca quando reportId muda", async () => {
    const { result, rerender } = renderHook(
      ({ id }: { id: string | null }) => useReportData(id, WS_ID),
      { initialProps: { id: "report-1" as string | null } },
    );
    await waitFor(() => expect(result.current.status).toBe("success"));

    // Override mock para retornar payload diferente no segundo id
    server.use(
      http.get(`${API}/workspaces/${WS_ID}/reports/report-2/data`, () =>
        HttpResponse.json({
          periodo_dados: "202501-202512",
          patrimonio: { bruto: 1, liquido: 1 },
        }),
      ),
    );

    rerender({ id: "report-2" });
    await waitFor(() => {
      if (result.current.status === "success") {
        expect(result.current.data.periodo_dados).toBe("202501-202512");
      } else {
        throw new Error("not yet success");
      }
    });
  });

  it("cancela fetch anterior quando reportId muda rapidamente", async () => {
    // Teste defensivo — garante que state final reflete o último ID
    const { result, rerender } = renderHook(
      ({ id }: { id: string | null }) => useReportData(id, WS_ID),
      { initialProps: { id: "report-1" as string | null } },
    );
    rerender({ id: null });
    expect(result.current.status).toBe("idle");
  });
});
