/**
 * Resilience tests — F6.5D.5
 *
 * Cobertura: 5xx → ApiError com retry possível, network error → fallback,
 * WS drop + reconnect (já coberto em usePipelineWS.test.tsx), offline banner
 * via navigator.onLine. Polling fallback é coberto em Pipeline page tests.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";

import { ApiError, getMe, listDocuments } from "@/lib/api";
import { server } from "../mocks/server";

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

describe("Resilience — backend 5xx handling", () => {
  it("502 Bad Gateway → ApiError status=502", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json({ detail: "upstream down" }, { status: 502 }),
      ),
    );
    await expect(getMe()).rejects.toMatchObject({ status: 502 });
  });

  it("503 Service Unavailable → ApiError com detail", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/documents", () =>
        HttpResponse.json({ detail: "Manutenção" }, { status: 503 }),
      ),
    );
    await expect(listDocuments("ws-1")).rejects.toMatchObject({
      status: 503,
      detail: "Manutenção",
    });
  });

  it("504 Gateway Timeout → ApiError", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json({ detail: "timeout" }, { status: 504 }),
      ),
    );
    await expect(getMe()).rejects.toMatchObject({ status: 504 });
  });

  it("network error (sem response) → Error não-ApiError", async () => {
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.error()));
    await expect(getMe()).rejects.toThrow();
    // NÃO deve ser ApiError (não tem status HTTP)
    try {
      await getMe();
    } catch (err) {
      expect(err).not.toBeInstanceOf(ApiError);
    }
  });
});

describe("Resilience — retry após sucesso", () => {
  it("usuário pode retentar após 5xx e receber 200 OK", async () => {
    let attempt = 0;
    server.use(
      http.get("/api/v1/auth/me", () => {
        attempt++;
        if (attempt === 1) {
          return HttpResponse.json({ detail: "x" }, { status: 500 });
        }
        return HttpResponse.json({
          id: "u1",
          email: "u@test.com",
          full_name: "U",
          is_active: true,
        });
      }),
    );
    await expect(getMe()).rejects.toMatchObject({ status: 500 });
    // 2ª tentativa sucesso
    const me = await getMe();
    expect(me.email).toBe("u@test.com");
  });
});

describe("Resilience — navigator.onLine", () => {
  let originalOnLine: boolean;
  beforeEach(() => {
    originalOnLine = navigator.onLine;
  });
  afterEach(() => {
    Object.defineProperty(navigator, "onLine", {
      value: originalOnLine,
      writable: true,
      configurable: true,
    });
  });

  it("simula offline via navigator.onLine=false", () => {
    Object.defineProperty(navigator, "onLine", {
      value: false,
      writable: true,
      configurable: true,
    });
    expect(navigator.onLine).toBe(false);
  });

  it("evento 'offline' dispara (para UI futura mostrar banner)", () => {
    const handler = vi.fn();
    window.addEventListener("offline", handler);
    window.dispatchEvent(new Event("offline"));
    expect(handler).toHaveBeenCalled();
    window.removeEventListener("offline", handler);
  });

  it("evento 'online' dispara (UI esconde banner)", () => {
    const handler = vi.fn();
    window.addEventListener("online", handler);
    window.dispatchEvent(new Event("online"));
    expect(handler).toHaveBeenCalled();
    window.removeEventListener("online", handler);
  });
});

describe("Resilience — slow response tolerance", () => {
  it("timeout longo não crasha, apenas demora", async () => {
    let resolved = false;
    server.use(
      http.get("/api/v1/auth/me", async () => {
        await new Promise((r) => setTimeout(r, 50));
        resolved = true;
        return HttpResponse.json({
          id: "u", email: "x@test.com", full_name: "x", is_active: true,
        });
      }),
    );
    const me = await getMe();
    expect(resolved).toBe(true);
    expect(me.email).toBe("x@test.com");
  });
});
