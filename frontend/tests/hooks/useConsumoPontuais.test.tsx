/**
 * Tests — useConsumoPontuais hook (S2 · ConsumoConscienteCard).
 *
 * Anti-regressão da skip silenciosa de 28 baselines visuais (commit
 * `ba29df1` introduziu o card; visual specs com mock route catch-all
 * `{}` quebravam shape e disparavam ErrorBoundary, derrubando `<article>`
 * inteiro — `section#S1[data-report-section]` count===0). O fix coerce
 * resposta malformada para defaults seguros antes de entregar ao consumer.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { useConsumoPontuais } from "@/hooks/useConsumoPontuais";
import { clearToken, setToken } from "@/lib/api";
import { WorkspaceProvider } from "@/lib/WorkspaceProvider";
import { server } from "../mocks/server";

const API = "/api/v1";
const WS_ID = "ws-1";

beforeEach(() => {
  clearToken();
  setToken("test-token");
});

function wrapper({ children }: { children: React.ReactNode }) {
  return <WorkspaceProvider>{children}</WorkspaceProvider>;
}

describe("useConsumoPontuais", () => {
  it("entrega items=[] e total=0 em resposta bem formada vazia", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS_ID}/reports/consumo-pontuais`, () =>
        HttpResponse.json({
          period: "3m",
          date_from: "2026-01-01",
          date_to: "2026-04-01",
          items: [],
          total: 0,
          total_valor: 0,
        }),
      ),
    );
    const { result } = renderHook(() => useConsumoPontuais("3m"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.items).toEqual([]);
    expect(result.current.total).toBe(0);
    expect(result.current.totalValor).toBe(0);
  });

  it("coerce response malformada (items undefined) p/ items=[] sem crash", async () => {
    // Cenário herdado da regressão: route catch-all em mocks E2E retornando
    // `{}` — sem o coerce, `pontuais.length` em ConsumoConscienteCard joga
    // TypeError e dispara ErrorBoundary do ReportShell.
    server.use(
      http.get(
        `${API}/workspaces/${WS_ID}/reports/consumo-pontuais`,
        () => HttpResponse.json({}),
      ),
    );
    const { result } = renderHook(() => useConsumoPontuais("3m"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(Array.isArray(result.current.items)).toBe(true);
    expect(result.current.items).toEqual([]);
    expect(result.current.total).toBe(0);
    expect(result.current.totalValor).toBe(0);
  });

  it("propaga erro de rede com items=[] como fallback seguro", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS_ID}/reports/consumo-pontuais`, () =>
        HttpResponse.error(),
      ),
    );
    const { result } = renderHook(() => useConsumoPontuais("3m"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBeTruthy();
    expect(result.current.items).toEqual([]);
  });
});
